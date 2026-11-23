"""Style des polices installées (filtre de la liste des polices du panneau Texte) : avec empattements, sans
empattements, manuscrite, fantaisie, chasse fixe. Lu dans les fichiers de police eux-mêmes (tables « OS/2 » :
classe de famille IBM et PANOSE, « post » : chasse fixe, « name » : nom de la famille), sans bibliothèque. Les
résultats sont gardés dans %LOCALAPPDATA%\\Pixane\\styles-polices.json (refaits pour les fichiers nouveaux ou
modifiés)."""
from __future__ import annotations

import json
import os
import struct
from pathlib import Path

SERIF, SANS, MANUSCRITE, FANTAISIE, FIXE = "serif", "sans", "manuscrite", "fantaisie", "fixe"
STYLES = (SERIF, SANS, MANUSCRITE, FANTAISIE, FIXE)
EXTENSIONS = (".ttf", ".otf", ".ttc", ".otc")
VERSION = 2


def _dossiers() -> list[Path]:
    d = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
    if os.environ.get("LOCALAPPDATA"):
        d.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts")
    return d


def _cache() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Pixane"
    suite = os.environ.get("PIXANE_REGLAGES", "")
    return base / (f"styles-polices-{suite}.json" if suite else "styles-polices.json")


def _tables(data: bytes, debut: int) -> dict:
    n = struct.unpack_from(">H", data, debut + 4)[0]
    t = {}
    for i in range(n):
        tag, _somme, pos, long = struct.unpack_from(">4sIII", data, debut + 12 + 16 * i)
        t[tag] = (pos, long)
    return t


def _noms(data: bytes, pos: int) -> set[str]:
    """Noms de famille (1 et 16) de la table « name »."""
    _fmt, n, chaines = struct.unpack_from(">HHH", data, pos)
    noms = set()
    for i in range(n):
        plat, enc, _lang, ident, long, dec = struct.unpack_from(">HHHHHH", data, pos + 6 + 12 * i)
        if ident not in (1, 16):
            continue
        brut = data[pos + chaines + dec: pos + chaines + dec + long]
        try:
            if plat == 3 or plat == 0:
                noms.add(brut.decode("utf-16-be").strip())
            elif plat == 1 and enc == 0:
                noms.add(brut.decode("mac_roman").strip())
        except UnicodeDecodeError:
            pass
    return {x for x in noms if x}


def classer(classe: int, panose: bytes, fixe: bool) -> str:
    """Style d'après la classe de famille IBM (octet haut), le PANOSE et la chasse fixe ; "" si inconnu."""
    genre = panose[0] if panose else 0
    if fixe or (genre == 2 and panose[3] == 9):
        return FIXE
    if genre == 3 or classe == 10:
        return MANUSCRITE
    if genre in (4, 5) or classe in (9, 12):
        return FANTAISIE
    if genre == 2:
        if 2 <= panose[1] <= 10:
            return SERIF
        if 11 <= panose[1] <= 15:
            return SANS
    if classe in (1, 2, 3, 4, 5, 7):
        return SERIF
    if classe == 8:
        return SANS
    return ""


def lire_fichier(chemin: Path) -> list[tuple[list[str], str]]:
    """[(noms de famille, style)] pour chaque police du fichier (plusieurs dans un .ttc)."""
    data = chemin.read_bytes()
    if data[:4] == b"ttcf":
        n = struct.unpack_from(">I", data, 8)[0]
        debuts = list(struct.unpack_from(f">{n}I", data, 12))
    else:
        debuts = [0]
    res = []
    for debut in debuts:
        try:
            t = _tables(data, debut)
            noms = _noms(data, t[b"name"][0]) if b"name" in t else set()
            classe, panose, fixe = 0, b"", False
            if b"OS/2" in t:
                pos = t[b"OS/2"][0]
                classe = data[pos + 30]
                panose = data[pos + 32: pos + 42]
            if b"post" in t:
                fixe = struct.unpack_from(">I", data, t[b"post"][0] + 12)[0] != 0
            if noms:
                res.append((sorted(noms), classer(classe, panose, fixe)))
        except (struct.error, IndexError, KeyError):
            continue
    return res


_styles: dict[str, str] | None = None


def styles() -> dict[str, str]:
    """{famille: style} pour les polices installées (style "" : inconnu, montrée seulement dans « Toutes »)."""
    global _styles
    if _styles is not None:
        return _styles
    try:
        cache = json.loads(_cache().read_text(encoding="utf-8"))
        if cache.get("version") != VERSION:
            cache = {}
    except (OSError, ValueError):
        cache = {}
    fichiers = cache.get("fichiers", {})
    nouveaux = {}
    for d in _dossiers():
        try:
            liste = [f for f in d.iterdir() if f.suffix.lower() in EXTENSIONS]
        except OSError:
            continue
        for f in liste:
            try:
                cle = f"{f.stat().st_mtime_ns}:{f.stat().st_size}"
            except OSError:
                continue
            ancien = fichiers.get(str(f))
            if ancien and ancien[0] == cle:
                nouveaux[str(f)] = ancien
                continue
            try:
                nouveaux[str(f)] = [cle, lire_fichier(f)]
            except OSError:
                pass
    if nouveaux != fichiers:
        try:
            _cache().parent.mkdir(parents=True, exist_ok=True)
            tmp = _cache().with_suffix(".part")
            tmp.write_text(json.dumps({"version": VERSION, "fichiers": nouveaux, "formes": cache.get("formes", {})}),
                           encoding="utf-8")
            os.replace(tmp, _cache())
        except OSError:
            pass
    votes: dict[str, dict[str, int]] = {}
    for _cle, polices in nouveaux.values():
        for noms, style in polices:
            for nom in noms:
                v = votes.setdefault(nom, {})
                v[style] = v.get(style, 0) + 1
    res = {}
    for nom, v in votes.items():           # le style le plus fréquent parmi les fichiers de la famille (connu d'abord)
        connus = {k: n for k, n in v.items() if k}
        res[nom] = max(connus, key=connus.get) if connus else ""
    # rattrapages pour les familles sans indication : liste de Google, mots du nom, dessin du « I »
    google = _categories_google()
    formes = cache.get("formes", {}) if cache else {}
    formes_avant = dict(formes)
    for nom, style in res.items():
        g = google.get(nom) or google.get(_sans_graisse(nom))
        if g:                                  # classement de Google (fait à la main) : il passe d'abord
            res[nom] = g
            continue
        if style:
            continue
        style = _par_nom(nom)
        if not style:
            if nom not in formes:
                formes[nom] = _par_forme(nom)
            style = formes[nom]
        res[nom] = style
    if formes != formes_avant:
        try:
            tmp = _cache().with_suffix(".part")
            tmp.write_text(json.dumps({"version": VERSION, "fichiers": nouveaux, "formes": formes}), encoding="utf-8")
            os.replace(tmp, _cache())
        except OSError:
            pass
    _styles = res
    return res


GRAISSES = ("thin", "extralight", "extra light", "ultralight", "light", "semilight", "book", "regular", "medium",
            "semibold", "semi bold", "demibold", "bold", "extrabold", "extra bold", "ultrabold", "black", "heavy",
            "condensed", "semicondensed", "extended", "expanded", "italic", "oblique", "narrow", "cond", "cd")


def _sans_graisse(nom: str) -> str:
    mots = nom.split()
    while len(mots) > 1 and mots[-1].lower().strip("-") in GRAISSES:
        mots.pop()
    return " ".join(mots)


def _categories_google() -> dict[str, str]:
    """{famille: style} d'après la liste des polices Google (si elle est déjà téléchargée)."""
    try:
        from . import polices_google
        liste = polices_google.liste()
    except Exception:
        return {}
    conv = {"serif": SERIF, "sans-serif": SANS, "handwriting": MANUSCRITE, "display": FANTAISIE, "monospace": FIXE}
    return {x["family"]: conv[x["category"]] for x in liste if x.get("category") in conv}


MOTS = ((FIXE, ("mono", "code", "typewriter", "courier", "console", "terminal")),
        (MANUSCRITE, ("script", "hand", "brush", "marker", "writer", "writing", "signature", "calligraph", "pen ",
                      "kindy", "chalk", "crayon")),
        (FANTAISIE, ("dingbat", "symbol", "ornament", "fraktur", "gothicg", "stencil", "grunge", "dirty", "horror",
                     "outline", "shadow", "3d", "pixel", "gradient")),
        (SERIF, ("serif", "roman", "antiqua", "garamond", "bodoni", "didot", "slab", "text")),
        (SANS, ("sans", "grotesk", "grotesque", "gothic", "geometric", "uni ")))


def _par_nom(nom: str) -> str:
    n = nom.lower() + " "
    if "sans serif" in n or "sans-serif" in n:
        return SANS
    for style, mots in MOTS:
        if any(m in n for m in mots):
            return style
    return ""


def _par_forme(nom: str) -> str:
    """Le « I » majuscule dessiné : une barre simple -> sans empattements ; une barre avec des pieds -> avec
    empattements ; autre chose (plusieurs morceaux, contours, irrégulier) -> fantaisie."""
    try:
        import numpy as np
        from PySide6.QtCore import QRect, Qt
        from PySide6.QtGui import QColor, QFont, QImage, QPainter
    except ImportError:
        return FANTAISIE
    taille = 80
    img = QImage(taille * 2, taille * 2, QImage.Format_Grayscale8)
    img.fill(QColor(0, 0, 0))
    f = QFont(nom)
    f.setPixelSize(taille)
    p = QPainter(img)
    p.setFont(f)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRect(0, 0, taille * 2, taille * 2), Qt.AlignCenter, "I")
    p.end()
    a = np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())[:, :img.width()] > 128
    lignes = np.where(a.any(axis=1))[0]
    if len(lignes) < taille * 0.4:
        return FANTAISIE
    haut, bas = lignes[0], lignes[-1]
    h = bas - haut + 1
    largeurs, morceaux = [], []
    for y in range(haut, bas + 1):
        xs = np.where(a[y])[0]
        if len(xs) == 0:
            return FANTAISIE                       # barre coupée
        largeurs.append(xs[-1] - xs[0] + 1)
        morceaux.append(1 + int(np.count_nonzero(np.diff(xs) > 1)))
    largeurs = np.array(largeurs, float)
    milieu = largeurs[int(h * 0.3): int(h * 0.7)]
    if len(milieu) == 0 or max(morceaux[int(h * 0.3): int(h * 0.7)]) > 1:
        return FANTAISIE                           # contour, hachures : plusieurs morceaux par ligne
    tige = float(np.median(milieu))
    if tige <= 0 or milieu.std() > tige * 0.15:
        return FANTAISIE                           # barre irrégulière
    pied = max(largeurs[: max(1, int(h * 0.08))].max(), largeurs[-max(1, int(h * 0.08)):].max())
    return SERIF if pied > tige * 1.6 else SANS


def style_de(famille: str) -> str:
    """Style d'une famille de la liste de Qt (le nom de Qt peut différer un peu de celui du fichier)."""
    s = styles()
    if famille in s:
        return s[famille]
    base = _sans_graisse(famille)
    if base in s:
        return s[base]
    proches = [k for k in s if famille.startswith(k) or k.startswith(famille)]
    if proches:
        return s[max(proches, key=len)]
    return _par_nom(famille) or FANTAISIE


def oublier() -> None:
    """Après l'installation d'une police : relire au prochain filtre."""
    global _styles
    _styles = None
