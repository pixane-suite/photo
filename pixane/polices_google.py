"""Polices gratuites de Google Fonts dans « Trouver une police semblable » (option, décochée d'office).

Source : Fontsource (api.fontsource.org pour la liste, cdn.jsdelivr.net pour les fichiers), qui met à disposition
les polices de Google Fonts fichier par fichier, avec la licence de chacune (presque toutes OFL-1.1 ; aussi
Apache-2.0, UFL-1.0 : toutes gratuites, usage commercial compris).

- Une seule fois (processus d'arrière-plan, comme la mémoire des polices installées) : la liste, puis le style
  normal de chaque famille (alphabet latin, environ 50 Ko chacune, environ 100 Mo en tout) dans
  %LOCALAPPDATA%\\Pixane\\polices-google ; puis sa mémoire des polices (les lettres de chaque police, comme
  polices.memoire). Les polices ne sont pas installées dans Windows : elles servent seulement à comparer.
- Recherche : comparées comme les polices installées ; celles du haut du classement sont chargées dans Pixane le
  temps de la recherche (QFontDatabase.addApplicationFont), puis retirées.
- « Télécharger et installer » : tous les styles de la famille choisie, installés pour l'utilisateur
  (%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts + registre HKCU, sans droits d'administrateur), utilisables tout de suite.
"""
from __future__ import annotations

import json
import os
import pickle
import re
import time
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LISTE_URL = "https://api.fontsource.org/v1/fonts"
FICHIER_URL = "https://cdn.jsdelivr.net/fontsource/fonts/{id}@latest/latin-{poids}-{style}.ttf"
AGENT = "Pixane"
VERSION = 1
_memoire: dict | None = None
_date = None
_chargees: dict[str, tuple[int, str]] = {}          # famille en mémoire -> (id Qt, vrai nom de famille)


def dossier() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "polices-google"
    if os.environ.get("PIXANE_REGLAGES"):                 # essais : à part
        nom += "-" + os.environ["PIXANE_REGLAGES"]
    return base / nom


def _fichier_memoire() -> Path:
    return dossier() / "polices.memoire"


def _telecharger_octets(url: str, essais: int = 3) -> bytes:
    for k in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except OSError:
            if k == essais - 1:
                raise
            time.sleep(2 * (k + 1))
    return b""


def liste() -> list[dict]:
    """Familles de Google Fonts avec l'alphabet latin (sans les polices d'icônes), d'après la liste enregistrée."""
    try:
        d = json.loads((dossier() / "liste.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [x for x in d if x.get("type") == "google" and "latin" in x.get("subsets", [])
            and x.get("category") != "icons"]


def _normal(x: dict) -> tuple[int, str]:
    poids = 400 if 400 in x["weights"] else min(x["weights"], key=lambda v: abs(v - 400))
    style = "normal" if "normal" in x["styles"] else x["styles"][0]
    return poids, style


def fichier_normal(x: dict) -> Path:
    return dossier() / "normal" / f"{x['id']}.ttf"


def _versions() -> dict:
    try:
        return json.loads((dossier() / "versions.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def telecharger(progres=None, arret=None, forcer: bool = False) -> int:
    """La liste (refaite si elle a plus de 30 jours, ou forcer) et le style normal des familles qui manquent ou qui
    ont changé (date de mise à jour de la liste) ; les polices retirées de Google Fonts sont effacées. progres(fait,
    total) ; arret() -> True pour s'arrêter. Renvoie le nombre de familles disponibles."""
    d = dossier()
    (d / "normal").mkdir(parents=True, exist_ok=True)
    fl = d / "liste.json"
    if forcer or not fl.is_file() or time.time() - fl.stat().st_mtime > 30 * 86400:
        donnees = _telecharger_octets(LISTE_URL)
        json.loads(donnees)                                # contrôle : du JSON
        tmp = fl.with_suffix(".part")
        tmp.write_bytes(donnees)
        os.replace(tmp, fl)
    familles = liste()
    versions = _versions()
    connues = {x["id"] for x in familles}
    for f in (d / "normal").glob("*.ttf"):                # retirées de Google Fonts : effacées
        if f.stem not in connues:
            f.unlink(missing_ok=True)
            versions.pop(f.stem, None)
    manquent = [x for x in familles if not fichier_normal(x).is_file()
                or versions.get(x["id"], x.get("lastModified")) != x.get("lastModified")]
    fait = [len(familles) - len(manquent)]

    def un(x):
        if arret is not None and arret():
            return
        poids, style = _normal(x)
        try:
            octets = _telecharger_octets(FICHIER_URL.format(id=x["id"], poids=poids, style=style))
        except OSError:
            return
        if octets[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"true"):    # un vrai fichier de police
            f = fichier_normal(x)
            tmp = f.with_suffix(".part")
            tmp.write_bytes(octets)
            os.replace(tmp, f)
            versions[x["id"]] = x.get("lastModified")
        fait[0] += 1
        if progres is not None:
            progres(fait[0], len(familles))
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(un, manquent))
    for x in familles:                                    # premières versions : la date de la liste
        if fichier_normal(x).is_file():
            versions.setdefault(x["id"], x.get("lastModified"))
    tmp = d / "versions.part"
    tmp.write_text(json.dumps(versions), encoding="utf-8")
    os.replace(tmp, d / "versions.json")
    a_refaire = d / "a_refaire.json"                      # leur mémoire est à refaire
    deja = set(json.loads(a_refaire.read_text(encoding="utf-8"))) if a_refaire.is_file() else set()
    a_refaire.write_text(json.dumps(sorted(deja | {x["id"] for x in manquent})), encoding="utf-8")
    return sum(1 for x in familles if fichier_normal(x).is_file())


def preparer_memoire(progres=None) -> int:
    """Les lettres de chaque police téléchargée (comme la mémoire des polices installées), enregistrées toutes les
    100. À lancer dans un processus avec une QGuiApplication. Renvoie le nombre de polices en mémoire."""
    from PySide6.QtGui import QFontDatabase
    from . import polices_semblables as ps
    mem = dict(memoire(forcer=True))
    familles = liste()
    connues = {x["id"] for x in familles}
    a_refaire = dossier() / "a_refaire.json"
    refaire = set(json.loads(a_refaire.read_text(encoding="utf-8"))) if a_refaire.is_file() else set()
    mem = {k: v for k, v in mem.items() if v[5] in connues and v[5] not in refaire}
    famille_de = {x["id"]: x["family"] for x in familles}
    # une variante rangée sous le nom d'une autre police (ex. Pushster, nommée « Lobster » dans son fichier) : la
    # vraie police de ce nom passe d'abord
    for k, v in list(mem.items()):
        if famille_de.get(v[5]) != k and any(f == k for f in famille_de.values()):
            del mem[k]
    faites = 0
    for k, x in enumerate(familles):
        f = fichier_normal(x)
        if not f.is_file():
            continue
        if any(v[5] == x["id"] for v in mem.values()):
            continue
        ident = QFontDatabase.addApplicationFont(str(f))
        noms = QFontDatabase.applicationFontFamilies(ident) if ident >= 0 else []
        if noms and noms[0] in mem and noms[0] != x["family"]:
            noms = []                    # même nom interne qu'une autre police (variante) : la vraie est gardée
        if noms:
            try:
                entree = ps.lettres_police(noms[0])
            except Exception:
                entree = None
            if entree is not None and entree[2]:
                mem[noms[0]] = tuple(entree) + (x["id"], x.get("license", ""))
                faites += 1
        if ident >= 0:
            QFontDatabase.removeApplicationFont(ident)
        if faites and faites % 100 == 0:
            _enregistrer(mem)
        if progres is not None:
            progres(k + 1, len(familles))
    _enregistrer(mem)
    a_refaire.unlink(missing_ok=True)
    return len(mem)


def _enregistrer(mem: dict) -> None:
    global _memoire, _date
    f = _fichier_memoire()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f"{f.name}.{os.getpid()}.part")
    tmp.write_bytes(zlib.compress(pickle.dumps({"version": VERSION, "familles": mem}, protocol=4), 6))
    os.replace(tmp, f)
    _memoire, _date = mem, f.stat().st_mtime


def memoire(forcer: bool = False) -> dict:
    """{famille: (comme la mémoire des polices installées..., id Fontsource, licence)} ; vide si l'option est
    désactivée ou pas encore prête. Relue si le fichier a changé."""
    global _memoire, _date
    if not forcer and not active():
        return {}
    try:
        date = _fichier_memoire().stat().st_mtime
    except OSError:
        return {}
    if _memoire is None or date != _date:
        try:
            d = pickle.loads(zlib.decompress(_fichier_memoire().read_bytes()))
            _memoire = d["familles"] if d.get("version") == VERSION else {}
        except Exception:
            _memoire = {}
        _date = date
    return _memoire


def active() -> bool:
    from PySide6.QtCore import QSettings
    v = QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane")).value("polices_google", False)
    return str(v).lower() in ("true", "1")


def pretes() -> int:
    """Nombre de polices Google prêtes pour la recherche."""
    return len(memoire(forcer=True))


def source(famille: str) -> tuple[str, str]:
    v = memoire(forcer=True).get(famille)
    return (v[5], v[6]) if v else ("", "")


def charger(famille: str) -> str:
    """Charge dans Pixane (pas dans Windows) le fichier de cette police Google ; renvoie son nom de famille."""
    if famille in _chargees:
        return _chargees[famille][1]
    from PySide6.QtGui import QFontDatabase
    ident_police = source(famille)[0]
    f = dossier() / "normal" / f"{ident_police}.ttf"
    if not ident_police or not f.is_file():
        return ""
    ident = QFontDatabase.addApplicationFont(str(f))
    noms = QFontDatabase.applicationFontFamilies(ident) if ident >= 0 else []
    if not noms:
        return ""
    _chargees[famille] = (ident, noms[0])
    return noms[0]


def liberer() -> None:
    """Retire de Pixane les polices Google chargées pour une recherche."""
    from PySide6.QtGui import QFontDatabase
    for ident, _nom in _chargees.values():
        QFontDatabase.removeApplicationFont(ident)
    _chargees.clear()


def effacer() -> None:
    """Option décochée : le dossier des polices Google est effacé."""
    global _memoire, _date
    import shutil
    liberer()
    shutil.rmtree(dossier(), ignore_errors=True)
    _memoire, _date = None, None


# ------------------------------------------------------------------ installer une police
def _nom_fichier(texte: str) -> str:
    return re.sub(r"[^A-Za-z0-9 _-]", "", texte).strip() or "police"


NOMS_POIDS = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold",
              700: "Bold", 800: "ExtraBold", 900: "Black"}


def installer(ident: str, progres=None) -> tuple[str, list[str]]:
    """Télécharge tous les styles de la famille (alphabet latin) et les installe pour l'utilisateur Windows.
    Renvoie (nom de famille, fichiers installés). Les polices sont aussi chargées dans Pixane (utilisables tout de
    suite, sans redémarrer)."""
    import ctypes
    import winreg
    from PySide6.QtGui import QFontDatabase
    x = next((y for y in liste() if y["id"] == ident), None)
    if x is None:
        raise OSError(f"police inconnue : {ident}")
    cible = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    cible.mkdir(parents=True, exist_ok=True)
    styles = [(p, s) for p in x["weights"] for s in x["styles"]]
    faits, famille = [], x["family"]
    famille_qt = famille
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows NT\CurrentVersion\Fonts") as cle:
        for k, (poids, style) in enumerate(styles):
            octets = _telecharger_octets(FICHIER_URL.format(id=ident, poids=poids, style=style))
            if octets[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
                continue
            nom_style = NOMS_POIDS.get(poids, str(poids)) + (" Italic" if style == "italic" else "")
            f = cible / f"{_nom_fichier(famille)}-{nom_style.replace(' ', '')}.ttf"
            f.write_bytes(octets)
            winreg.SetValueEx(cle, f"{famille} {nom_style} (TrueType)", 0, winreg.REG_SZ, str(f))
            try:
                ctypes.windll.gdi32.AddFontResourceW(str(f))
            except (AttributeError, OSError):
                pass
            ident_qt = QFontDatabase.addApplicationFont(str(f))
            noms = QFontDatabase.applicationFontFamilies(ident_qt) if ident_qt >= 0 else []
            if noms:
                famille_qt = noms[0]
            faits.append(str(f))
            if progres is not None:
                progres(k + 1, len(styles))
    try:                                              # les autres programmes ouverts voient la nouvelle police
        HWND_BROADCAST, WM_FONTCHANGE = 0xFFFF, 0x001D
        ctypes.windll.user32.SendMessageTimeoutW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0, 0x0002, 1000, None)
    except (AttributeError, OSError):
        pass
    return famille_qt, faits


# ------------------------------------------------------------------ arrière-plan
def lancer_en_fond(forcer: bool = False) -> None:
    """Télécharge et prépare dans un processus à part (priorité basse, sans fenêtre). Rien si c'est déjà fait.
    forcer : la liste est retéléchargée tout de suite (« Mettre à jour les polices Google maintenant »)."""
    import subprocess
    import sys
    racine = Path(__file__).resolve().parents[1]
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe" and (exe.parent / "pythonw.exe").is_file():
        exe = exe.parent / "pythonw.exe"
    drapeaux = 0
    if os.name == "nt":
        drapeaux = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    try:
        subprocess.Popen([str(exe), "-m", "pixane.polices_google", "--preparer"] + (["--forcer"] if forcer else []),
                         cwd=str(racine),
                         creationflags=drapeaux, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, env=dict(os.environ))
    except OSError:
        pass


def en_preparation() -> bool:
    v = dossier() / "preparation.verrou"
    return v.exists() and time.time() - v.stat().st_mtime < 3600


if __name__ == "__main__":                       # processus d'arrière-plan lancé par Pixane
    import sys
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication(sys.argv)
    if "--preparer" in sys.argv:
        verrou = dossier() / "preparation.verrou"
        try:
            verrou.parent.mkdir(parents=True, exist_ok=True)
            if en_preparation():
                sys.exit(0)                      # un autre est déjà en route
            verrou.write_text(str(os.getpid()))
            n = telecharger(progres=lambda f, t: verrou.touch() if f % 50 == 0 else None,
                            forcer="--forcer" in sys.argv)
            preparer_memoire(progres=lambda f, t: verrou.touch() if f % 50 == 0 else None)
        finally:
            verrou.unlink(missing_ok=True)
        sys.exit(0)
