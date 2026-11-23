"""Moteur IA : ComfyUI lancé en arrière-plan, sans fenêtre.

Le programme cherche d'abord un ComfyUI déjà ouvert (port 8188, celui de Comfy Desktop).
Sinon, il lance le ComfyUI installé sur le PC sur le port 8189 et l'arrête à la fermeture.
"""
from __future__ import annotations

import glob
import io
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import websocket

from . import recettes
from .langue import tr

DOSSIER_APP = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Pixane"
FICHIER_CONFIG = DOSSIER_APP / "config.json"
PORT_EXTERNE = 8188   # ComfyUI Desktop, s'il est ouvert
PORT_INTERNE = 8189   # notre moteur caché

NOEUDS_NECESSAIRES = ["InpaintCropImproved", "INPAINT_InpaintWithModel", "UltimateSDUpscale"]


class ErreurMoteur(Exception):
    pass


class Annule(Exception):
    pass


def lire_config() -> dict:
    try:
        return json.loads(FICHIER_CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def dossier_comfyui(d: Path) -> Path | None:
    """Dossier qui contient main.py, à partir du dossier donné ou d'un dossier parent courant
    (ComfyUI portable : <dossier>\\ComfyUI ; ComfyUI Desktop : <dossier de base>\\ComfyUI\\ComfyUI)."""
    for c in (d, d / "ComfyUI", d / "ComfyUI" / "ComfyUI"):
        if (c / "main.py").is_file():
            return c
    return None


def python_comfyui(d: Path) -> Path | None:
    """Python qui fait tourner ComfyUI (dossier de main.py donné)."""
    for p in (d / ".venv" / "Scripts" / "python.exe",             # ComfyUI Desktop
              d.parent / "python_embeded" / "python.exe",         # ComfyUI portable
              d.parent / ".venv" / "Scripts" / "python.exe",
              d.parent.parent / ".venv" / "Scripts" / "python.exe"):
        if p.is_file():
            return p
    return None


def candidats_comfyui() -> list[Path]:
    """Endroits où chercher ComfyUI, du plus sûr au moins sûr."""
    candidats = []
    conf = lire_config()
    if conf.get("comfyui_dir"):
        candidats.append(Path(conf["comfyui_dir"]))
    try:                                   # choisi dans l'installateur (registre, réglages de Pixane)
        from PySide6.QtCore import QSettings
        choisi = QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane")).value("comfyui_dir")
        if choisi:
            candidats.append(Path(str(choisi)))
    except Exception:
        pass
    try:                                   # ComfyUI Desktop : son dossier de base
        base = json.loads((Path(os.environ.get("APPDATA", "")) / "ComfyUI" / "config.json")
                          .read_text(encoding="utf-8")).get("basePath")
        if base:
            candidats.append(Path(base))
    except (OSError, ValueError):
        pass
    candidats.append(DOSSIER_APP / "moteur" / "ComfyUI_windows_portable")   # installé par Pixane
    candidats.append(DOSSIER_APP.parent / "Chrypix" / "moteur" / "ComfyUI_windows_portable")   # ancien nom
    return candidats


def trouver_comfyui() -> dict | None:
    """Renvoie {dir, python, chemins_modeles} ou None si ComfyUI n'est pas installé."""
    conf = lire_config()
    for c in candidats_comfyui():
        d = dossier_comfyui(c)
        python = python_comfyui(d) if d else None
        if d and python:
            chemins = conf.get("extra_model_paths")
            if not chemins:
                yamls = glob.glob(os.path.join(os.environ.get("APPDATA", ""), "Comfy Desktop",
                                               "instance-model-paths", "*.yaml"))
                yamls.sort(key=os.path.getmtime, reverse=True)
                chemins = yamls[0] if yamls else None
            return {"dir": d, "python": python, "chemins_modeles": chemins}
    return None


def _multipart(champs: dict, fichiers: dict) -> tuple[bytes, str]:
    limite = uuid.uuid4().hex
    corps = io.BytesIO()
    for nom, valeur in champs.items():
        corps.write(f'--{limite}\r\nContent-Disposition: form-data; name="{nom}"\r\n\r\n{valeur}\r\n'.encode())
    for nom, (fichier, donnees, mime) in fichiers.items():
        corps.write(f'--{limite}\r\nContent-Disposition: form-data; name="{nom}"; filename="{fichier}"\r\n'
                    f'Content-Type: {mime}\r\n\r\n'.encode())
        corps.write(donnees)
        corps.write(b"\r\n")
    corps.write(f"--{limite}--\r\n".encode())
    return corps.getvalue(), f"multipart/form-data; boundary={limite}"


class Moteur:
    def __init__(self):
        self.url: str | None = None
        self.processus: subprocess.Popen | None = None
        self.etat = "arrêté"
        self.client_id = uuid.uuid4().hex
        self._verrou = threading.Lock()
        self._arret = threading.Event()   # le programme se ferme
        self.infos: dict = {}             # /object_info de ComfyUI (ce qu'il sait faire, ses modèles)
        self.noeuds_manquants: list[str] = []
        self.externe = False              # ComfyUI déjà ouvert (ComfyUI Desktop) : Pixane ne peut pas le relancer

    # ------------------------------------------------------------------ réseau
    def _requete(self, chemin: str, donnees: bytes | None = None, type_contenu: str = "application/json",
                 delai: float = 30) -> bytes:
        req = urllib.request.Request(self.url + chemin, data=donnees,
                                     headers={"Content-Type": type_contenu} if donnees is not None else {})
        with urllib.request.urlopen(req, timeout=delai) as r:
            return r.read()

    def _json(self, chemin: str, objet=None, delai: float = 30):
        donnees = json.dumps(objet).encode() if objet is not None else None
        return json.loads(self._requete(chemin, donnees, delai=delai))

    @staticmethod
    def _repond(url: str) -> bool:
        try:
            with urllib.request.urlopen(url + "/system_stats", timeout=2) as r:
                return r.status == 200
        except (OSError, urllib.error.URLError):
            return False

    # ------------------------------------------------------------ démarrage
    def demarrer(self, signaler=lambda texte: None) -> None:
        """Bloquant (à appeler dans un fil secondaire)."""
        for port in (PORT_EXTERNE, PORT_INTERNE):
            url = f"http://127.0.0.1:{port}"
            if self._repond(url):
                self.url = url
                self.externe = port == PORT_EXTERNE
                self._verifier_noeuds()
                self.etat = "prêt"
                signaler(tr("prêt (ComfyUI déjà ouvert)") if port == PORT_EXTERNE else tr("prêt"))
                return

        install = trouver_comfyui()
        if install is None:
            self.etat = "introuvable"
            raise ErreurMoteur(tr("ComfyUI n'est pas installé sur ce PC (ou pas à l'endroit attendu)."))

        if self._arret.is_set():
            return
        signaler(tr("démarrage…"))
        DOSSIER_APP.mkdir(parents=True, exist_ok=True)
        journal = open(DOSSIER_APP / "moteur.log", "w", encoding="utf-8", errors="replace")
        commande = [str(install["python"]), "main.py", "--listen", "127.0.0.1", "--port", str(PORT_INTERNE),
                    "--disable-auto-launch"]
        if install["chemins_modeles"]:
            commande += ["--extra-model-paths-config", install["chemins_modeles"]]
        self.processus = subprocess.Popen(commande, cwd=install["dir"], stdout=journal, stderr=subprocess.STDOUT,
                                          stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        self.url = f"http://127.0.0.1:{PORT_INTERNE}"
        debut = time.time()
        while time.time() - debut < 240:
            if self._arret.is_set():
                self.arreter()
                return
            if self.processus.poll() is not None:
                self.etat = "erreur"
                raise ErreurMoteur(tr("Le moteur s'est arrêté au démarrage. Détails : {fichier}",
                                      fichier=DOSSIER_APP / 'moteur.log'))
            if self._repond(self.url):
                self._verifier_noeuds()
                self.etat = "prêt"
                signaler(tr("prêt"))
                return
            time.sleep(1)
        self.etat = "erreur"
        raise ErreurMoteur(tr("Le moteur ne répond pas après 4 minutes."))

    def _verifier_noeuds(self):
        """Lit ce que ComfyUI a (extensions, modèles). S'il manque quelque chose, Pixane le proposera
        (completer_moteur) ; les actions qui en ont besoin préviennent en attendant."""
        infos = self._json("/object_info", delai=60)
        self.infos = infos
        self.noeuds_manquants = [n for n in NOEUDS_NECESSAIRES if n not in infos]
        recettes.configurer(infos)          # Flux Fill : version complète ou GGUF, selon ce qui est installé

    def dossiers_modeles(self) -> dict[str, list[str]]:
        """Dossiers de modèles de ComfyUI, par genre (le premier est celui où il range les nouveaux)."""
        try:
            return {d["name"]: d["folders"] for d in self._json("/experiment/models", delai=30)}
        except Exception:
            return {}

    def arreter(self):
        self._arret.set()
        if self.processus and self.processus.poll() is None:
            self.processus.terminate()
            try:
                self.processus.wait(10)
            except subprocess.TimeoutExpired:
                self.processus.kill()
        self.processus = None
        self.etat = "arrêté"

    # ------------------------------------------------------------ travail
    def envoyer_image(self, png: bytes) -> str:
        nom = f"{uuid.uuid4().hex}.png"
        corps, type_contenu = _multipart({"subfolder": "pixane", "type": "input", "overwrite": "true"},
                                         {"image": (nom, png, "image/png")})
        rep = json.loads(self._requete("/upload/image", corps, type_contenu, delai=120))
        return f"{rep['subfolder']}/{rep['name']}" if rep.get("subfolder") else rep["name"]

    def executer(self, prompt: dict, sorties: dict[str, str], annuler: threading.Event,
                 progres=lambda info: None, nb_morceaux: int = 1) -> list[tuple[str, bytes]]:
        """Lance une recette et renvoie [(libellé, png), ...] dans l'ordre de `sorties`.

        `progres` reçoit un dict {secondes, etape, fraction (0..1 ou None), restant (s ou None)}.
        """
        with self._verrou:
            suivi = Suivi(prompt, nb_morceaux)
            ws = self._ouvrir_ws()
            try:
                try:
                    rep = self._json("/prompt", {"prompt": prompt, "client_id": self.client_id})
                except urllib.error.HTTPError as e:
                    raise ErreurMoteur(tr("ComfyUI refuse la recette : {detail}",
                                          detail=e.read().decode(errors="replace")[:800]))
                pid = rep["prompt_id"]
                derniere_verif = 0.0
                while True:
                    if annuler.is_set():
                        try:                              # (ComfyUI répond ici par un corps vide : pas de json)
                            self._requete("/queue", json.dumps({"delete": [pid]}).encode())
                            self._requete("/interrupt", b"{}")
                        except (OSError, ValueError):
                            pass
                        raise Annule()
                    fini = False
                    if ws is not None:
                        fini = self._lire_ws(ws, pid, suivi)
                    else:
                        time.sleep(1)
                    # contrôle de secours par l'historique (toutes les 3 s)
                    if not fini and time.time() - derniere_verif > 3:
                        derniere_verif = time.time()
                        fini = pid in self._json(f"/history/{pid}")
                    progres(suivi.info())
                    if fini:
                        break
            finally:
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass
            entree = self._json(f"/history/{pid}").get(pid)
            if entree is None:
                raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
            statut = entree.get("status", {})
            if statut.get("status_str") != "success":
                messages = [m for m in statut.get("messages", []) if m[0] == "execution_error"]
                detail = messages[0][1].get("exception_message", "") if messages else ""
                raise ErreurMoteur(tr("Erreur pendant le calcul. {detail}", detail=detail.strip()[:600]))
            resultats = []
            for noeud, libelle in sorties.items():
                for texte in entree["outputs"].get(noeud, {}).get("text", []):   # sortie texte (PreviewAny)
                    resultats.append((libelle, str(texte).encode("utf-8")))
                images = entree["outputs"].get(noeud, {}).get("images", [])
                for i, im in enumerate(images):
                    params = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"],
                                                     "type": im["type"]})
                    donnees = self._requete(f"/view?{params}", delai=120)
                    resultats.append((f"{libelle} {i + 1}" if len(images) > 1 else libelle, donnees))
            return resultats

    # ------------------------------------------------------------ suivi en direct (WebSocket)
    def _ouvrir_ws(self):
        try:
            ws = websocket.create_connection(self.url.replace("http", "ws", 1) + f"/ws?clientId={self.client_id}",
                                             timeout=5)
            ws.settimeout(0.5)
            return ws
        except Exception:
            return None  # sans suivi en direct : on se contente de l'historique

    @staticmethod
    def _lire_ws(ws, pid: str, suivi: "Suivi") -> bool:
        """Lit les messages disponibles ; renvoie True quand le travail `pid` est terminé."""
        while True:
            try:
                brut = ws.recv()
            except Exception:  # délai dépassé ou connexion perdue : on rend la main
                return False
            if not isinstance(brut, str):
                continue  # image d'aperçu : ignorée
            try:
                msg = json.loads(brut)
            except ValueError:
                continue
            t, d = msg.get("type"), msg.get("data") or {}
            if d.get("prompt_id") not in (None, pid):
                continue
            if t == "executing":
                if d.get("node") is None and d.get("prompt_id") == pid:
                    return True
                suivi.noeud(d.get("node"))
            elif t == "progress":
                suivi.avance(d.get("node"), d.get("value", 0), d.get("max", 1))
            elif t in ("execution_success", "execution_error", "execution_interrupted"):
                return True


ETAPES = {   # textes traduits à l'affichage par tr()
    "LoadImage": "Préparation de l'image", "InpaintCropImproved": "Découpe autour de la zone",
    "INPAINT_LoadInpaintModel": "Chargement de LaMa", "INPAINT_InpaintWithModel": "LaMa efface",
    "UNETLoader": "Chargement de Flux", "DualCLIPLoader": "Chargement de Flux", "VAELoader": "Chargement de Flux",
    "CLIPTextEncode": "Préparation", "InpaintModelConditioning": "Préparation",
    "KSampler": "Calcul Flux", "VAEDecode": "Décodage", "InpaintStitchImproved": "Assemblage",
    "UpscaleModelLoader": "Chargement de RealESRGAN", "ImageUpscaleWithModel": "Agrandissement RealESRGAN",
    "ImageScaleBy": "Mise à la taille", "UltimateSDUpscale": "Redessin des détails", "PreviewImage": "Finition",
}
LOURDS = ("KSampler", "UltimateSDUpscale")


class Suivi:
    """Transforme les messages de ComfyUI en étape, pourcentage et temps restant."""

    def __init__(self, prompt: dict, nb_morceaux: int = 1):
        self.classes = {k: v["class_type"] for k, v in prompt.items()}
        self.lourd = next((k for k, c in self.classes.items() if c in LOURDS), None)
        self.nb_morceaux = max(1, nb_morceaux)
        self.debut = time.time()
        self.etape = tr("En attente du moteur")
        self.detail = ""
        self.noeud_actuel = None
        self.lourd_fini = False
        self.morceau = 0
        self._derniere_valeur = -1
        self.fraction_lourd = 0.0
        self.debut_calcul = None

    def noeud(self, n):
        if self.lourd is not None and self.noeud_actuel == self.lourd and n != self.lourd:
            self.lourd_fini = True
        self.noeud_actuel = n
        self.etape = tr(ETAPES.get(self.classes.get(n, ""), "Calcul"))
        self.detail = ""
        if n == self.lourd and self.fraction_lourd == 0:
            self.etape = tr("Chargement du modèle en mémoire")

    def avance(self, n, valeur, maximum):
        maximum = max(1, maximum)
        if n is not None and n != self.noeud_actuel:
            self.noeud(n)
        if self.lourd is not None and self.noeud_actuel == self.lourd:
            if self.debut_calcul is None:
                self.debut_calcul = time.time()
            if valeur < self._derniere_valeur:
                self.morceau = min(self.morceau + 1, self.nb_morceaux - 1)
            self._derniere_valeur = valeur
            self.fraction_lourd = min(1.0, (self.morceau + valeur / maximum) / self.nb_morceaux)
            self.etape = tr(ETAPES.get(self.classes.get(self.lourd, ""), "Calcul"))
            self.detail = (tr("morceau {n} sur {total}", n=self.morceau + 1, total=self.nb_morceaux)
                           if self.nb_morceaux > 1 else tr("étape {n} sur {total}", n=valeur, total=maximum))
        else:
            self.detail = f"{valeur} / {maximum}"

    def info(self) -> dict:
        if self.lourd is None:
            fraction = None
        elif self.lourd_fini:
            fraction = 0.97
        else:
            fraction = 0.05 + 0.9 * self.fraction_lourd
        restant = None
        if self.debut_calcul and 0.08 < self.fraction_lourd < 1 and not self.lourd_fini:
            ecoule = time.time() - self.debut_calcul
            restant = int(ecoule / self.fraction_lourd * (1 - self.fraction_lourd)) + 3
        etape = f"{self.etape} — {self.detail}" if self.detail else self.etape
        return {"secondes": int(time.time() - self.debut), "etape": etape, "fraction": fraction,
                "restant": restant}
