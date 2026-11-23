"""Essai du téléchargeur du moteur IA, sans Internet : petit serveur local (avec reprise « Range »).

Vérifie : téléchargement, empreinte SHA-256, reprise après arrêt, fichier abîmé refusé, archive zip décompressée,
fenêtre (liste, licence obligatoire). Lancement : PIXANE_REGLAGES=Pixane-essais python tests/essai_installation.py
"""
import hashlib
import io
import os
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from pixane import installation_moteur as im  # noqa: E402

GROS = os.urandom(6 * 1024 * 1024 + 123)
z = io.BytesIO()
with zipfile.ZipFile(z, "w") as f:
    f.writestr("depot-abc123/__init__.py", "# extension")
    f.writestr("depot-abc123/sous/fichier.txt", "bonjour")
    f.writestr("depot-abc123/../../evasion.txt", "non")
ZIP = z.getvalue()
z2 = io.BytesIO()
with zipfile.ZipFile(z2, "w") as f:
    f.writestr("depot-def456/__init__.py", "# extension v2")
ZIP2 = z2.getvalue()
GROS2 = os.urandom(1024 * 1024 + 7)
FICHIERS = {"/gros.bin": GROS, "/ext.zip": ZIP, "/ext2.zip": ZIP2, "/gros2.bin": GROS2,
            "/comfy2.7z": b"archive"}
LENT = threading.Event()


class Serveur(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        data = FICHIERS.get(self.path)
        if data is None:
            self.send_error(404)
            return
        debut = 0
        rng = self.headers.get("Range")
        if rng:
            debut = int(rng.split("=")[1].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {debut}-{len(data) - 1}/{len(data)}")
        else:
            self.send_response(200)
        self.send_header("Content-Length", str(len(data) - debut))
        self.end_headers()
        try:
            for i in range(debut, len(data), 256 * 1024):
                self.wfile.write(data[i:i + 256 * 1024])
                if LENT.is_set():
                    time.sleep(0.05)
        except (ConnectionError, OSError):
            pass


serveur = ThreadingHTTPServer(("127.0.0.1", 0), Serveur)
threading.Thread(target=serveur.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{serveur.server_address[1]}"

app = QApplication(sys.argv)
erreurs = []


def verifier(cond, texte):
    print(("ok   " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def executer(inst: im.Installation, arreter_apres: float | None = None) -> tuple[bool, str]:
    resultat = {}
    inst.fini.connect(lambda ok, m: resultat.update(ok=ok, m=m))
    inst.lancer()
    debut = time.time()
    while "ok" not in resultat and time.time() - debut < 60:
        app.processEvents()
        if arreter_apres is not None and time.time() - debut > arreter_apres:
            inst.arret.set()
        time.sleep(0.02)
    app.processEvents()
    return resultat.get("ok"), resultat.get("m", "délai dépassé")


modele = im.Element("gros", "gros", URL + "/gros.bin", len(GROS), hashlib.sha256(GROS).hexdigest(), "MIT",
                    "modele", "ComfyUI/models/essai/gros.bin")
extension = im.Element("ext", "ext", URL + "/ext.zip", None, None, "MIT", "zip", "ComfyUI/custom_nodes/ext")

with tempfile.TemporaryDirectory() as tmp:
    dossier = Path(tmp) / "moteur"
    r = im.racine(dossier)
    cible = r / modele.dest
    part = cible.with_name(cible.name + ".part")

    # 1. arrêt au milieu : un .part reste, pas de fichier final
    LENT.set()
    ok, m = executer(im.Installation(dossier, [modele]), arreter_apres=0.5)
    verifier(ok is False, "arrêt demandé : installation non terminée")
    verifier(part.is_file() and 0 < part.stat().st_size < len(GROS),
             f"un morceau est gardé ({part.stat().st_size if part.is_file() else 0} octets)")
    verifier(not cible.exists(), "pas de fichier final après un arrêt")

    # 2. reprise : le reste seulement, puis vérification et fichier final
    LENT.clear()
    deja = part.stat().st_size
    inst = im.Installation(dossier, [modele, extension])
    ok, m = executer(inst)
    verifier(ok is True, f"reprise et fin : {m}")
    verifier(cible.is_file() and cible.read_bytes() == GROS, "fichier final identique à l'original")
    verifier(inst._recu <= len(GROS) - deja + len(ZIP) + 10, "seul le reste a été téléchargé")
    verifier((r / "ComfyUI/custom_nodes/ext/__init__.py").is_file(), "archive : dossier du dessus enlevé")
    verifier((r / "ComfyUI/custom_nodes/ext/sous/fichier.txt").read_text() == "bonjour", "archive : sous-dossier")
    verifier(not (Path(tmp) / "evasion.txt").exists() and not (r / "ComfyUI" / "evasion.txt").exists(),
             "archive : rien écrit hors du dossier")
    verifier((r / "pixane.json").is_file(), "marque « installé par Pixane » écrite")
    verifier((dossier / im.MARQUE).is_file(), "marque du dossier (pour le désinstalleur) écrite")
    verifier(not im.comfyui_etranger(dossier), "notre dossier n'est pas pris pour un ComfyUI étranger")
    verifier(not (dossier / "telechargements").exists(), "dossier de téléchargements nettoyé")
    from PySide6.QtCore import QSettings
    verifier(QSettings("Pixane", "Pixane-essais").value("comfyui_dir") == str(r), "dossier retenu dans les réglages")

    # 3. relancer : rien n'est retéléchargé
    inst = im.Installation(dossier, [modele, extension])
    ok, m = executer(inst)
    verifier(ok is True and inst._recu == 0, "déjà installé : rien retéléchargé")

    # 4. empreinte fausse : refusé, le .part est jeté
    faux = replace(modele, sha256="0" * 64, dest="ComfyUI/models/essai/faux.bin")
    ok, m = executer(im.Installation(dossier, [faux]))
    verifier(ok is False and "empreinte" in m, "fichier abîmé refusé")
    verifier(not (r / faux.dest).exists() and not (r / "ComfyUI/models/essai/faux.bin.part").exists(),
             "fichier abîmé effacé")

    # 5. adresse introuvable : arrêt propre avec message
    absent = replace(modele, url=URL + "/absent.bin", dest="ComfyUI/models/essai/absent.bin")
    ok, m = executer(im.Installation(dossier, [absent]))
    verifier(ok is False and "404" in m, "adresse introuvable signalée")

with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / im.PORTABLE / "ComfyUI").mkdir(parents=True)
    (Path(tmp) / im.PORTABLE / "ComfyUI" / "main.py").write_text("")
    verifier(im.comfyui_etranger(Path(tmp)), "ComfyUI d'un autre : reconnu")
    verifier(not im.inscriptible(Path(os.environ.get("SystemRoot", "C:/Windows")) / "pixane-essai"), "dossier protégé : refusé")
    verifier(im.inscriptible(Path(tmp) / "sous" / "dossier"), "dossier à créer dans un dossier permis : accepté")
    f = im.FenetreInstallation(dossier=tmp, accepte=True)
    verifier(not f.b_lancer.isEnabled(), "ComfyUI d'un autre : installation refusée dans ce dossier")
    f.close()

# 6. mises à jour : nouvelle version d'une extension, d'un modèle (autre fichier) et de ComfyUI
import subprocess  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    dossier = Path(tmp) / "moteur"
    r = im.racine(dossier)
    (r / "ComfyUI").mkdir(parents=True)
    (r / "ComfyUI" / "main.py").write_text("v1")
    comfy1 = im.Element("comfyui", "ComfyUI", URL + "/comfy1.7z", 7, "1" * 64, "GPL-3.0", "7z")
    ok, m = executer(im.Installation(dossier, [modele, extension]))
    infos = im.lire_infos(dossier)
    infos["versions"]["comfyui"] = im._signature(comfy1)          # ComfyUI v1 « déjà installé »
    (r / im.INFOS).write_text(__import__("json").dumps(infos), encoding="utf-8")
    verifier(ok and set(infos["versions"]) >= {"gros", "ext"}, "versions installées retenues dans pixane.json")
    verifier(all(im.etat_element(dossier, e) == "ok" for e in (modele, extension, comfy1)), "tout est à jour")

    modele2 = replace(modele, url=URL + "/gros2.bin", taille=len(GROS2), sha256=hashlib.sha256(GROS2).hexdigest(),
                      dest="ComfyUI/models/essai/gros2.bin")
    extension2 = replace(extension, url=URL + "/ext2.zip")
    comfy2 = replace(comfy1, url=URL + "/comfy2.7z", taille=7, sha256=hashlib.sha256(b"archive").hexdigest())
    verifier([im.etat_element(dossier, e) for e in (modele2, extension2, comfy2)] == ["absent", "maj", "maj"],
             "nouvelles versions repérées (modèle à télécharger, extension et ComfyUI à mettre à jour)")
    vrai_run = subprocess.run

    def faux_7zr(cmd, **k):                                          # « décompresse » un ComfyUI v2
        sortie = Path(next(x for x in cmd if x.startswith("-o"))[2:]) / im.PORTABLE / "ComfyUI"
        (sortie / "models").mkdir(parents=True)
        (sortie / "main.py").write_text("v2")
        (sortie / "models" / "vide_v2.txt").write_text("")
        return subprocess.CompletedProcess(cmd, 0, "", "")
    im.subprocess.run = faux_7zr
    outil = im.Element("7zr", "7zr", URL + "/gros.bin", len(GROS), hashlib.sha256(GROS).hexdigest(), "LGPL",
                       "outil")
    ok, m = executer(im.Installation(dossier, [outil, comfy2, extension2, modele2]))
    im.subprocess.run = vrai_run
    verifier(ok is True, f"mise à jour faite : {m}")
    verifier((r / "ComfyUI" / "main.py").read_text() == "v2", "ComfyUI remplacé par la nouvelle version")
    verifier((r / "ComfyUI/custom_nodes/ext/__init__.py").read_text() == "# extension v2"
             and not (r / "ComfyUI/custom_nodes/ext/sous").exists(), "extension remplacée (ancienne version enlevée)")
    verifier((r / modele2.dest).read_bytes() == GROS2, "nouveau modèle téléchargé")
    verifier(not (r / modele.dest).exists(), "ancien modèle effacé")
    verifier(not (r / "ComfyUI/models/vide_v2.txt").exists(), "dossier models de l'ancien ComfyUI gardé")
    verifier(not (dossier / "mise_a_jour").exists() and not (dossier / "ancien_comfyui").exists(),
             "dossiers temporaires nettoyés")
    verifier(all(im.etat_element(dossier, e) == "ok" for e in (modele2, extension2, comfy2)),
             "après la mise à jour : tout est à jour")
    ok, m = executer(inst := im.Installation(dossier, [outil, comfy2, extension2, modele2]))
    verifier(ok and inst._recu == 0, "relancer : rien retéléchargé (7-Zip non plus)")
    # moteur installé avant le suivi des versions : rien n'est imposé
    infos = im.lire_infos(dossier)
    infos.pop("versions")
    (r / im.INFOS).write_text(__import__("json").dumps(infos), encoding="utf-8")
    verifier(im.etat_element(dossier, extension) == "ok", "ancien moteur sans versions : pris tel quel")

# 7. catalogue et fenêtre
cat = im.catalogue(True, False)
verifier(all(e.sha256 for e in cat if e.genre in ("modele", "outil", "7z")), "catalogue : toutes les empreintes")
verifier("nvidia.7z" in cat[1].url and "cu126" in im.catalogue(False)[1].url, "ComfyUI selon le pilote")
verifier(len(im.catalogue(True, True)) == len(cat) + 1, "Flux Schnell facultatif")
taille = sum(e.taille or 0 for e in cat)
print(f"     total sans Schnell : {im.go(taille)} ; avec : {im.go(taille + im.taille_schnell())}")
with tempfile.TemporaryDirectory() as tmp:
    f = im.FenetreInstallation(dossier=tmp)
    f.c_traducteur.setChecked(False)          # le traducteur a ses propres essais (essai_modifier)
    verifier(f.liste.topLevelItemCount() == len(f.elements()), "fenêtre : un élément par ligne")
    verifier(not f.b_lancer.isEnabled(), "fenêtre : licence non acceptée -> bouton grisé")
    f.c_licence.setChecked(True)
    verifier(f.b_lancer.isEnabled(), "fenêtre : licence acceptée -> bouton actif")
    avant = f.liste.topLevelItemCount()        # (Depth Anything, coché d'office, en plus du catalogue de base)
    f.c_schnell.setChecked(True)
    verifier(f.liste.topLevelItemCount() == avant + 1, "fenêtre : Schnell ajouté à la liste")
    f.c_description.setChecked(True)
    verifier(f.liste.topLevelItemCount() == avant + 2, "fenêtre : Qwen3.5 2B (description) ajouté à la liste")
    print("     " + f.place.text())
    f.close()

serveur.shutdown()
print(f"\n{len(erreurs)} erreur(s)")
sys.stdout.flush()
os._exit(1 if erreurs else 0)
