"""Styles de calque : effets non destructifs (ombres, lueurs, contour, biseau, incrustations, ombre au sol).

Un calque garde ses pixels d'origine ; son style (liste d'effets + opacité du remplissage) est appliqué à chaque
affichage. Le calcul se fait en numpy, seulement autour des pixels visibles du calque (plus la marge des effets),
et le résultat est gardé en mémoire tant que le calque ne change pas (les calques sont immuables).

Mieux que Photoshop :
- plusieurs effets du même type (deux contours, trois ombres…) ;
- ombre « réaliste » : nette près de l'objet, de plus en plus floue en s'éloignant ;
- ombre au sol en perspective (objet détouré posé sur un sol), réglée en glissant sur la photo ;
- les tailles suivent le calque quand on l'agrandit (Ctrl+T, Taille de l'image, Upscale).

Angles : en degrés, sens inverse des aiguilles d'une montre, 0 = lumière venant de la droite (comme Photoshop).
"""
from __future__ import annotations

import json
import math
import weakref
from dataclasses import dataclass, field, replace

import numpy as np
from PIL import Image
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage, QPainter

from .degrades import table
from .langue import tr

# ------------------------------------------------------------------ description des effets
# Pour chaque type : nom affiché et réglages (clé, libellé, genre, valeur par défaut, minimum, maximum).
# Genres : couleur, pourcent (0..100), px (taille en pixels, suit l'échelle du calque), angle, choix, case, nombre.
MODES = {"normal": "Normal", "produit": "Produit", "ecran": "Écran", "incrustation": "Incrustation"}

TYPES = {
    "ombre": "Ombre portée",
    "ombre_interne": "Ombre interne",
    "lueur": "Lueur externe",
    "lueur_interne": "Lueur interne",
    "contour": "Contour",
    "biseau": "Biseau et relief",
    "couleur": "Incrustation couleur",
    "degrade": "Incrustation dégradé",
    "motif": "Incrustation de motif",
    "ombre_sol": "Ombre au sol",
}

REGLAGES = {
    "ombre": [
        ("couleur", "Couleur", "couleur", "#000000"),
        ("mode", "Mode", "choix", "produit", MODES),
        ("opacite", "Opacité", "pourcent", 60),
        ("angle", "Angle de la lumière", "angle", 120),
        ("global", "Lumière commune à tous les calques", "case", True),
        ("distance", "Distance", "px", 12, 0, 500),
        ("taille", "Flou", "px", 14, 0, 250),
        ("etendue", "Étendue", "pourcent", 0),
        ("realiste", "Ombre réaliste (nette près de l'objet, floue en s'éloignant)", "case", False),
    ],
    "ombre_interne": [
        ("couleur", "Couleur", "couleur", "#000000"),
        ("mode", "Mode", "choix", "produit", MODES),
        ("opacite", "Opacité", "pourcent", 60),
        ("angle", "Angle de la lumière", "angle", 120),
        ("global", "Lumière commune à tous les calques", "case", True),
        ("distance", "Distance", "px", 5, 0, 250),
        ("taille", "Flou", "px", 8, 0, 250),
        ("etendue", "Resserrement", "pourcent", 0),
    ],
    "lueur": [
        ("couleur", "Couleur", "couleur", "#ffd966"),
        ("mode", "Mode", "choix", "ecran", MODES),
        ("opacite", "Opacité", "pourcent", 75),
        ("taille", "Taille", "px", 18, 1, 250),
        ("etendue", "Étendue", "pourcent", 0),
    ],
    "lueur_interne": [
        ("couleur", "Couleur", "couleur", "#fff7c0"),
        ("mode", "Mode", "choix", "ecran", MODES),
        ("opacite", "Opacité", "pourcent", 75),
        ("taille", "Taille", "px", 10, 1, 250),
        ("etendue", "Resserrement", "pourcent", 0),
        ("source", "Source", "choix", "bord", {"bord": "Bords", "centre": "Centre"}),
    ],
    "contour": [
        ("couleur", "Couleur", "couleur", "#000000"),
        ("opacite", "Opacité", "pourcent", 100),
        ("taille", "Épaisseur", "px", 4, 1, 250),
        ("position", "Position", "choix", "exterieur",
         {"exterieur": "À l'extérieur", "centre": "Au centre", "interieur": "À l'intérieur"}),
    ],
    "biseau": [
        ("forme", "Style", "choix", "interne",
         {"interne": "Biseau interne", "externe": "Biseau externe", "estampage": "Estampage"}),
        ("profondeur", "Profondeur", "pourcent", 100, 1, 500),
        ("direction", "Direction", "choix", "haut", {"haut": "Vers le haut", "bas": "Vers le bas"}),
        ("taille", "Taille", "px", 6, 1, 250),
        ("adoucir", "Adoucir", "px", 0, 0, 50),
        ("angle", "Angle de la lumière", "angle", 120),
        ("global", "Lumière commune à tous les calques", "case", True),
        ("altitude", "Hauteur de la lumière", "nombre", 30, 0, 90),
        ("clair", "Couleur des reflets", "couleur", "#ffffff"),
        ("opacite_clair", "Opacité des reflets", "pourcent", 75),
        ("sombre", "Couleur des ombres", "couleur", "#000000"),
        ("opacite_sombre", "Opacité des ombres", "pourcent", 75),
    ],
    "couleur": [
        ("couleur", "Couleur", "couleur", "#d62828"),
        ("mode", "Mode", "choix", "normal", MODES),
        ("opacite", "Opacité", "pourcent", 100),
    ],
    "degrade": [
        ("degrade", "Dégradé", "degrade", None),        # points (pixane.degrades) ; None : couleur1 -> couleur2
        ("mode", "Mode", "choix", "normal", MODES),
        ("opacite", "Opacité", "pourcent", 100),
        ("forme", "Forme", "choix", "lineaire", {"lineaire": "Linéaire", "radial": "Radial"}),
        ("angle", "Angle", "angle", 90),
        ("echelle", "Échelle", "pourcent", 100, 10, 150),
        ("inverser", "Inverser", "case", False),
    ],
    "motif": [
        ("motif", "Motif", "motif", "Krita 4/01_canvas.png#0"),
        ("mode", "Mode", "choix", "normal", MODES),
        ("opacite", "Opacité", "pourcent", 100),
        ("echelle", "Échelle", "pourcent", 100, 10, 1000),
    ],
    "ombre_sol": [
        ("couleur", "Couleur", "couleur", "#000000"),
        ("opacite", "Opacité", "pourcent", 55),
        ("tx", "Direction (gauche / droite)", "nombre", 60, -300, 300),
        ("ty", "Longueur (en arrière / en avant)", "nombre", -35, -200, 200),
        ("flou", "Flou au pied", "px", 2, 0, 100),
        ("flou_loin", "Flou au bout", "px", 25, 0, 250),
        ("estompe", "Estompe au bout", "pourcent", 70),
    ],
}

# ordre d'empilement (comme Photoshop) : sous le calque, puis dessus
ORDRE = ["ombre_sol", "ombre", "lueur", "couleur", "degrade", "motif", "ombre_interne", "lueur_interne", "biseau", "contour"]
SOUS = {"ombre_sol", "ombre", "lueur"}


def defauts(type_: str) -> dict:
    return {r[0]: r[3] for r in REGLAGES[type_]}


@dataclass(frozen=True, eq=False)
class Effet:
    type: str
    reglages: dict = field(default_factory=dict)
    actif: bool = True

    def r(self, cle):
        return self.reglages.get(cle, defauts(self.type).get(cle))

    def vers_dict(self) -> dict:
        return {"type": self.type, "actif": self.actif, "reglages": dict(self.reglages)}

    @staticmethod
    def depuis_dict(d: dict) -> "Effet":
        if d.get("type") not in TYPES:
            raise ValueError(d.get("type"))
        return Effet(d["type"], {**defauts(d["type"]), **(d.get("reglages") or {})}, bool(d.get("actif", True)))

    @staticmethod
    def nouveau(type_: str, **reglages) -> "Effet":
        return Effet(type_, {**defauts(type_), **reglages})


@dataclass(frozen=True, eq=False)
class Style:
    effets: tuple = ()
    remplissage: float = 1.0      # opacité du contenu seul (les effets restent) : 0 = contour ou ombre sans le texte

    def vide(self) -> bool:
        return not any(e.actif for e in self.effets) and self.remplissage >= 0.999

    def vers_dict(self) -> dict:
        return {"effets": [e.vers_dict() for e in self.effets], "remplissage": self.remplissage}

    def vers_json(self) -> str:
        return json.dumps(self.vers_dict(), ensure_ascii=False)

    @staticmethod
    def depuis_dict(d: dict) -> "Style":
        effets = []
        for e in d.get("effets") or []:
            try:
                effets.append(Effet.depuis_dict(e))
            except (ValueError, TypeError, KeyError):
                pass                                   # effet inconnu (version plus récente) : ignoré
        return Style(tuple(effets), float(d.get("remplissage", 1.0)))

    @staticmethod
    def depuis_json(texte: str) -> "Style":
        return Style.depuis_dict(json.loads(texte))

    def mis_a_l_echelle(self, k: float) -> "Style":
        """Tailles en pixels multipliées par k (le calque a été agrandi ou réduit)."""
        if abs(k - 1) < 1e-6:
            return self
        effets = []
        for e in self.effets:
            px = {r[0] for r in REGLAGES[e.type] if r[2] == "px"}
            effets.append(replace(e, reglages={c: (round(v * k, 2) if c in px else v) for c, v in e.reglages.items()}))
        return replace(self, effets=tuple(effets))

    def avec_angle_global(self, angle: float) -> "Style":
        effets = tuple(replace(e, reglages={**e.reglages, "angle": angle}) if e.reglages.get("global") else e
                       for e in self.effets)
        return replace(self, effets=effets)

    def angle_global(self):
        for e in self.effets:
            if e.reglages.get("global"):
                return e.reglages.get("angle")
        return None


def nom_effet(type_: str) -> str:
    return tr(TYPES[type_])


# ------------------------------------------------------------------ outils numpy
def _boite(a: np.ndarray, r: int, axe: int) -> np.ndarray:
    n = a.shape[axe]
    c = np.cumsum(a, axis=axe, dtype=np.float32)
    pad = [(0, 0), (0, 0)]
    pad[axe] = (1, 0)
    c = np.pad(c, pad)
    i = np.arange(n)
    return (np.take(c, np.minimum(i + r + 1, n), axis=axe) - np.take(c, np.maximum(i - r, 0), axis=axe)) / (2 * r + 1)


def flou(a: np.ndarray, sigma: float) -> np.ndarray:
    """Flou gaussien approché (3 boîtes) ; les grands flous sont calculés sur une image réduite."""
    if sigma < 0.4:
        return a
    h, w = a.shape
    f = int(sigma // 4) if sigma > 8 else 1
    if f > 1:
        H, W = -(-h // f) * f, -(-w // f) * f
        b = np.pad(a, ((0, H - h), (0, W - w))).reshape(H // f, f, W // f, f).mean((1, 3))
        b = flou(b, sigma / f)
        grand = Image.fromarray(b.astype(np.float32), "F").resize((W, H), Image.BILINEAR)
        return np.asarray(grand)[:h, :w]
    r = max(1, int(round(sigma * 0.93)))
    for _ in range(3):
        a = _boite(_boite(a, r, 0), r, 1)
    return a


def _seuil(x: float, s: float) -> tuple[float, float]:
    """Pour un bord droit flouté de σ = s : valeur du flou à la distance x du bord (dehors), et sa pente."""
    v = 0.5 * math.erfc(x / (s * math.sqrt(2)))
    g = math.exp(-x * x / (2 * s * s)) / (s * math.sqrt(2 * math.pi))
    return v, max(g, 1e-6)


def dilater(a: np.ndarray, r: float) -> np.ndarray:
    """Zone a agrandie de r pixels, bord arrondi et lissé (1 px)."""
    if r <= 0.05:
        return a
    s = max(0.8, r / 2)
    v, g = _seuil(r, s)
    f = flou(a, s)
    # lissage d'1 px au bord ; loin du bord (f ≈ 0) la pente ne vaut plus : on s'éteint avec f
    return np.clip((f - v) / g + 0.5, 0, 1) * np.clip(f / v, 0, 1)


def eroder(a: np.ndarray, r: float) -> np.ndarray:
    if r <= 0.05:
        return a
    return 1 - dilater(1 - a, r)


def decaler(a: np.ndarray, dx: float, dy: float, fond: float = 0.0) -> np.ndarray:
    dx, dy = int(round(dx)), int(round(dy))
    h, w = a.shape
    res = np.full_like(a, fond)
    if abs(dx) >= w or abs(dy) >= h:
        return res
    res[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = a[max(0, -dy):h - max(0, dy),
                                                                  max(0, -dx):w - max(0, dx)]
    return res


def _rgb(hexa: str) -> np.ndarray:
    hexa = hexa.lstrip("#")
    return np.array([int(hexa[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def _melange(mode: str, b: np.ndarray, s: np.ndarray) -> np.ndarray:
    if mode == "produit":
        return b * s
    if mode == "ecran":
        return 1 - (1 - b) * (1 - s)
    if mode == "incrustation":
        return np.where(b < 0.5, 2 * b * s, 1 - 2 * (1 - b) * (1 - s))
    return np.broadcast_to(s, b.shape)


def poser(acc: np.ndarray, couleur, alpha: np.ndarray, mode: str = "normal") -> None:
    """Pose une couche (couleur unie ou tableau h×w×3, transparence alpha) sur acc (RGBA prémultiplié, float)."""
    a = acc[..., 3:4]
    e = np.clip(alpha, 0, 1)[..., None]
    s = couleur if isinstance(couleur, np.ndarray) and couleur.ndim == 3 else np.asarray(couleur, np.float32)
    if mode != "normal":
        b = np.where(a > 1e-4, acc[..., :3] / np.maximum(a, 1e-4), 0)
        s = (1 - a) * s + a * _melange(mode, b, s)
    acc[..., :3] = e * s + (1 - e) * acc[..., :3]
    acc[..., 3:4] = e + a * (1 - e)


def _direction(angle: float) -> tuple[float, float]:
    """Vecteur (écran) vers lequel va la lumière : l'ombre part dans ce sens."""
    t = math.radians(angle)
    return -math.cos(t), math.sin(t)


# ------------------------------------------------------------------ chaque effet
def _ombre(A, e):
    dx, dy = _direction(e.r("angle"))
    d = e.r("distance")
    s = e.r("taille") / 2
    base = dilater(A, e.r("etendue") / 100 * e.r("taille"))
    base = decaler(base, dx * d, dy * d)
    if e.r("realiste") and s > 0.5:
        net, large = flou(base, s * 0.25), flou(base, s * 1.6)
        pres = np.clip(flou(A, max(1.0, d + s)) * 2.2, 0, 1)        # près de l'objet : net et plus sombre
        o = pres * net * 1.0 + (1 - pres) * large * 0.75
    else:
        o = flou(base, s)
    return o * (1 - A)                                              # le calque masque son ombre (comme Photoshop)


def _ombre_interne(A, e):
    dx, dy = _direction(e.r("angle"))
    d = e.r("distance")
    s = e.r("taille") / 2
    dehors = decaler(1 - A, dx * d, dy * d, fond=1.0)
    dehors = dilater(dehors, e.r("etendue") / 100 * e.r("taille"))
    return flou(dehors, s) * A


def _lueur(A, e):
    t = e.r("taille")
    et = e.r("etendue") / 100
    g = flou(dilater(A, t * et), max(0.5, t * (1 - et) / 2))
    return np.clip(g * 2, 0, 1) * (1 - A)


def _lueur_interne(A, e):
    t = e.r("taille")
    et = e.r("etendue") / 100
    f = flou(eroder(A, t * et), max(0.5, t * (1 - et) / 2))
    if e.r("source") == "centre":
        g = np.clip(2 * f - 1, 0, 1)
    else:
        g = np.clip(2 * (1 - f), 0, 1)
    return g * A


def _contour(A, e):
    t = e.r("taille")
    pos = e.r("position")
    if pos == "interieur":
        return A * (1 - eroder(A, t))
    if pos == "centre":
        return dilater(A, t / 2) * (1 - eroder(A, t / 2))
    return dilater(A, t) * (1 - A)


def _biseau(A, e):
    """Reflets et ombres (alpha clair, alpha sombre) d'après une carte de relief tirée des bords du calque."""
    t = max(1.0, e.r("taille"))
    forme = e.r("forme")
    f = flou(A, t / 2)
    if forme == "externe":
        H = np.clip(f * 2, 0, 1)
        zone = dilater(A, t) * (1 - A)
    elif forme == "estampage":
        H = f
        zone = dilater(A, t / 2)
    else:
        H = np.clip((f - 0.5) * 2, 0, 1)
        zone = A
    if e.r("adoucir") > 0:
        H = flou(H, e.r("adoucir") / 2)
    k = t * e.r("profondeur") / 100 * (-1 if e.r("direction") == "bas" else 1)
    gy, gx = np.gradient(H.astype(np.float32))
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(H)
    n = np.sqrt(nx * nx + ny * ny + nz * nz)
    az, alt = math.radians(e.r("angle")), math.radians(e.r("altitude"))
    lx, ly, lz = math.cos(alt) * math.cos(az), -math.cos(alt) * math.sin(az), math.sin(alt)
    eclairage = (nx * lx + ny * ly + nz * lz) / n
    plat = lz
    clair = np.clip((eclairage - plat) / max(1e-3, 1 - plat), 0, 1)
    sombre = np.clip((plat - eclairage) / max(1e-3, plat), 0, 1)
    return clair * zone, sombre * zone


def _degrade(A, e, boite):
    h, w = A.shape
    x0, y0, x1, y1 = boite
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ech = max(0.05, e.r("echelle") / 100)
    if e.r("forme") == "radial":
        rayon = max(1.0, math.hypot(x1 - x0, y1 - y0) / 2 * ech)
        t = np.hypot(xx - cx, yy - cy) / rayon
    else:
        a = math.radians(e.r("angle"))
        ux, uy = math.cos(a), -math.sin(a)
        demi = (abs(ux) * (x1 - x0) + abs(uy) * (y1 - y0)) / 2 * ech
        t = ((xx - cx) * ux + (yy - cy) * uy) / max(1.0, demi) * 0.5 + 0.5
    t = np.clip(t, 0, 1)
    if e.r("inverser"):
        t = 1 - t
    tab = table(points_degrade(e), None, 1024)
    i = np.clip(np.rint(t * 1023), 0, 1023).astype(np.int32)
    return tab[i, :3], tab[i, 3]


def effet_degrade_glisse(image: QImage, a, b, forme: str, points: dict, peinture: QColor,
                        opacite: float) -> "Effet":
    """Outil Dégradé sur un texte : l'effet « Incrustation dégradé » qui suit le glissé de a à b (sens, longueur par
    rapport aux lettres, forme). Les points « couleur de peinture » prennent la couleur du moment (un style garde
    ses couleurs)."""
    from .degrades import PEINTURE, normaliser
    from .document import FORMAT_IMAGE, tableau
    d = normaliser(points)
    for p in d["couleurs"]:
        if p["couleur"] == PEINTURE:
            p["couleur"] = QColor(peinture).name()
    dx, dy = b.x() - a.x(), b.y() - a.y()
    angle = round(math.degrees(math.atan2(-dy, dx))) % 360
    if angle > 180:
        angle -= 360
    alpha = tableau(image.convertToFormat(FORMAT_IMAGE))[:, :, 3]
    ys, xs = np.nonzero(alpha)
    echelle = 100
    if len(ys):
        w, h = xs.max() + 1 - xs.min(), ys.max() + 1 - ys.min()
        longueur = math.hypot(dx, dy)
        if forme == "radial":
            etendue = math.hypot(w, h) / 2
        else:
            u = math.radians(angle)
            etendue = abs(math.cos(u)) * w + abs(math.sin(u)) * h
        echelle = round(max(10, min(150, longueur / max(1.0, etendue) * 100)))
    return Effet.nouveau("degrade", degrade=d, angle=angle, forme="radial" if forme == "radial" else "lineaire",
                         echelle=echelle, opacite=round(opacite * 100))


def avec_effet(style: "Style | None", effet: "Effet") -> "Style":
    """Le style avec cet effet : remplace le premier effet du même type, sinon l'ajoute."""
    effets = list(style.effets) if style is not None else []
    for i, e in enumerate(effets):
        if e.type == effet.type:
            effets[i] = effet
            break
    else:
        effets.append(effet)
    return Style(tuple(effets), style.remplissage if style is not None else 1.0)


def _points(*couleurs) -> dict:
    """Dégradé (pixane.degrades) d'après des (couleur, position), sans transparence."""
    return {"couleurs": [{"pos": p, "couleur": c, "milieu": 0.5} for c, p in couleurs],
            "opacites": [{"pos": 0, "opacite": 1, "milieu": 0.5}, {"pos": 1, "opacite": 1, "milieu": 0.5}]}


def points_degrade(e) -> dict:
    """Les points du dégradé d'un effet « Incrustation dégradé » (anciens styles : couleur1 -> couleur2)."""
    from .degrades import deux_couleurs, normaliser
    d = e.reglages.get("degrade")
    if d:
        return normaliser(d)
    return deux_couleurs(QColor(e.reglages.get("couleur1") or "#000000").name(),
                         QColor(e.reglages.get("couleur2") or "#ffffff").name())


def _pied(A) -> tuple[float, float, float] | None:
    """Ligne du sol sous l'objet : (y du pied, x du centre, hauteur de l'objet)."""
    lignes = np.nonzero(A.max(axis=1) > 0.3)[0]
    if not len(lignes):
        return None
    haut, bas = lignes[0], lignes[-1]
    cols = np.nonzero(A[max(haut, bas - 3):bas + 1].max(axis=0) > 0.3)[0]
    return float(bas), float(cols.mean()), float(bas - haut + 1)


def bout_ombre_sol(A_complet: np.ndarray, e) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Pour la poignée sur la photo : (pied, bout de l'ombre) en pixels de l'image."""
    p = _pied(A_complet)
    if p is None:
        return None
    pied, cx, hauteur = p
    return (cx, pied), (cx + e.r("tx") / 100 * hauteur, pied + e.r("ty") / 100 * hauteur)


def _ombre_sol(A, e):
    p = _pied(A)
    if p is None:
        return np.zeros_like(A)
    pied, _cx, hauteur = p
    tx, ty = e.r("tx") / 100 * hauteur, e.r("ty") / 100 * hauteur
    if abs(ty) < 2:
        ty = 2 if ty >= 0 else -2
    h, w = A.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    t = (yy - pied) / ty                               # 0 au pied, 1 au bout de l'ombre
    sy = pied - t * hauteur                            # point de l'objet qui projette cette ombre
    sx = xx - t * tx
    ok = (t >= 0) & (t <= 1) & (sx >= 0) & (sx <= w - 1) & (sy >= 0) & (sy <= h - 1)
    o = np.zeros_like(A)
    o[ok] = A[np.clip(sy[ok].round().astype(int), 0, h - 1), np.clip(sx[ok].round().astype(int), 0, w - 1)]
    tt = np.clip(t, 0, 1)
    net = flou(o, max(0.5, e.r("flou") / 2))
    large = flou(o, max(0.5, e.r("flou_loin") / 2))
    o = net * (1 - tt) + large * tt
    return o * (1 - e.r("estompe") / 100 * tt) * (1 - A)


def marge(style: Style) -> int:
    m = 2
    for e in style.effets:
        if not e.actif:
            continue
        t = e.r("taille") or 0
        if e.type == "ombre":
            m = max(m, e.r("distance") + 2.2 * t + e.r("etendue") / 100 * t + 4)
        elif e.type in ("lueur", "contour", "biseau"):
            m = max(m, 1.6 * t + 4)
    return int(math.ceil(m))


# ------------------------------------------------------------------ rendu d'un calque
def rendre_style(image: QImage, style: Style) -> QImage:
    """Image du calque (même taille, FORMAT ARGB32 prémultiplié) avec ses effets."""
    from .document import FORMAT_CALQUE, FORMAT_IMAGE, image_vide, tableau
    W, H = image.width(), image.height()
    t = tableau(image.convertToFormat(FORMAT_IMAGE))
    alpha = t[:, :, 3]
    ys, xs = np.nonzero(alpha)
    if not len(ys):
        return image
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    m = marge(style)
    X0, Y0, X1, Y1 = max(0, x0 - m), max(0, y0 - m), min(W, x1 + m), min(H, y1 + m)
    for e in style.effets:                           # ombre au sol : elle peut partir loin de l'objet
        if e.actif and e.type == "ombre_sol":
            hauteur = y1 - y0
            bx, by = e.r("tx") / 100 * hauteur, e.r("ty") / 100 * hauteur
            fl = e.r("flou_loin") * 1.2 + 4
            X0, X1 = max(0, int(min(X0, x0 + min(0, bx) - fl))), min(W, int(max(X1, x1 + max(0, bx) + fl)))
            Y0, Y1 = max(0, int(min(Y0, y1 + min(0, by) - fl))), min(H, int(max(Y1, y1 + max(0, by) + fl)))
    morceau = t[Y0:Y1, X0:X1].astype(np.float32) / 255
    A = morceau[..., 3].copy()
    boite = (x0 - X0, y0 - Y0, x1 - X0, y1 - Y0)
    acc = np.zeros(A.shape + (4,), np.float32)
    # par type dans l'ordre de Photoshop ; pour un même type, le premier de la liste passe devant (dessiné en dernier)
    actifs = [e for e in style.effets if e.actif]
    effets = sorted(actifs, key=lambda e: (ORDRE.index(e.type), -actifs.index(e)))
    contenu_pose = False

    def contenu():
        a = A * style.remplissage
        acc[..., :3] = morceau[..., :3] * a[..., None] + acc[..., :3] * (1 - a[..., None])
        acc[..., 3] = a + acc[..., 3] * (1 - a)

    for e in effets:
        if e.type not in SOUS and not contenu_pose:
            contenu()
            contenu_pose = True
        op = (e.r("opacite") if e.r("opacite") is not None else 100) / 100
        if e.type == "ombre":
            poser(acc, _rgb(e.r("couleur")), _ombre(A, e) * op, e.r("mode"))
        elif e.type == "ombre_sol":
            poser(acc, _rgb(e.r("couleur")), _ombre_sol(A, e) * op, "normal")
        elif e.type == "lueur":
            poser(acc, _rgb(e.r("couleur")), _lueur(A, e) * op, e.r("mode"))
        elif e.type == "couleur":
            poser(acc, _rgb(e.r("couleur")), A * op, e.r("mode"))
        elif e.type == "degrade":
            rgb, alpha = _degrade(A, e, boite)
            poser(acc, rgb, A * op * alpha, e.r("mode"))
        elif e.type == "motif":
            from .motifs import pavage, tuile
            tu = tuile(e.r("motif"), max(0.1, e.r("echelle") / 100))
            if tu is not None:        # motif répété depuis le coin de l'image (raccord entre calques)
                pv = pavage(tu, A.shape[1], A.shape[0], int(X0), int(Y0)).astype(np.float32) / 255
                poser(acc, pv[..., :3], A * op * pv[..., 3], e.r("mode"))
        elif e.type == "ombre_interne":
            poser(acc, _rgb(e.r("couleur")), _ombre_interne(A, e) * op, e.r("mode"))
        elif e.type == "lueur_interne":
            poser(acc, _rgb(e.r("couleur")), _lueur_interne(A, e) * op, e.r("mode"))
        elif e.type == "biseau":
            clair, sombre = _biseau(A, e)
            poser(acc, _rgb(e.r("clair")), clair * e.r("opacite_clair") / 100, "ecran")
            poser(acc, _rgb(e.r("sombre")), sombre * e.r("opacite_sombre") / 100, "produit")
        elif e.type == "contour":
            poser(acc, _rgb(e.r("couleur")), _contour(A, e) * op, "normal")
    if not contenu_pose:
        contenu()
    a = acc[..., 3:4]
    rgb = np.where(a > 1e-4, acc[..., :3] / np.maximum(a, 1e-4), 0)
    out = np.dstack([rgb, a]) * 255 + 0.5
    out = np.ascontiguousarray(np.clip(out, 0, 255).astype(np.uint8))
    h, w = out.shape[:2]
    q = QImage(out.data, w, h, w * 4, FORMAT_IMAGE)
    res = image_vide(W, H)
    p = QPainter(res)
    p.setCompositionMode(QPainter.CompositionMode_Source)
    p.drawImage(QPoint(int(X0), int(Y0)), q)
    p.end()
    return res.convertToFormat(FORMAT_CALQUE)


_cache: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def image_rendue(calque) -> QImage:
    """Image affichée d'un calque : ses pixels, ou ses pixels avec son style (gardée en mémoire)."""
    style = getattr(calque, "style", None)
    if style is None or style.vide():
        return calque.image
    r = _cache.get(calque)
    if r is None:
        r = rendre_style(calque.image, style)
        _cache[calque] = r
    return r


# ------------------------------------------------------------------ styles tout prêts
def _s(*effets, remplissage=1.0) -> Style:
    return Style(tuple(Effet.nouveau(t, **kw) for t, kw in effets), remplissage)


def styles_prets() -> list[tuple[str, Style]]:
    return [(tr(n), s) for n, s in [
        ("Ombre douce", _s(("ombre", dict(distance=8, taille=22, opacite=45)))),
        ("Ombre réaliste", _s(("ombre", dict(distance=14, taille=30, opacite=70, realiste=True)))),
        ("Ombre au sol", _s(("ombre_sol", {}))),
        ("Autocollant", _s(("contour", dict(couleur="#ffffff", taille=10)),
                           ("ombre", dict(distance=4, taille=10, opacite=40)))),
        ("Contour noir", _s(("contour", dict(couleur="#000000", taille=4)))),
        ("Contour seul", _s(("contour", dict(couleur="#ffffff", taille=3, position="centre")), remplissage=0.0)),
        ("Néon", _s(("couleur", dict(couleur="#ffffff")),
                    ("lueur_interne", dict(couleur="#00e5ff", taille=6, mode="normal", opacite=90)),
                    ("lueur", dict(couleur="#00e5ff", taille=28, opacite=95)),
                    ("lueur", dict(couleur="#00a2ff", taille=60, opacite=60)))),
        ("Or", _s(("degrade", dict(couleur1="#a8741a", couleur2="#ffe9a0", angle=90,
                                          degrade=_points(("#7a5512", 0), ("#c99a2e", .35), ("#fff3c0", .7), ("#e8c25a", 1)))),
                  ("biseau", dict(taille=8, profondeur=180, altitude=35, opacite_sombre=55)),
                  ("contour", dict(couleur="#6b4a10", taille=1.5, position="exterieur")),
                  ("ombre", dict(distance=5, taille=10, opacite=50)))),
        ("Chrome", _s(("degrade", dict(couleur1="#3a3f45", couleur2="#f4f7fa", angle=90,
                                              degrade=_points(("#3a3f45", 0), ("#9aa3ac", .48), ("#2b3036", .5),
                                                              ("#ffffff", .52), ("#f4f7fa", 1)))),
                      ("biseau", dict(taille=6, profondeur=250, altitude=45)),
                      ("contour", dict(couleur="#d9dee3", taille=1.5)))),
        ("Relief", _s(("biseau", dict(forme="estampage", taille=6, profondeur=150)))),
        ("Gravé", _s(("ombre_interne", dict(distance=3, taille=4, opacite=75)),
                     ("biseau", dict(direction="bas", taille=3, profondeur=100, opacite_clair=40)),
                     ("ombre", dict(couleur="#ffffff", mode="ecran", distance=1, taille=1, opacite=50)))),
        ("Feu", _s(("degrade", dict(couleur1="#c00000", couleur2="#ffe14d", angle=90,
                                           degrade=_points(("#8a0000", 0), ("#c00000", .3), ("#ff7a00", .65), ("#ffe14d", 1)))),
                   ("lueur", dict(couleur="#ff6a00", taille=24, opacite=85)))),
        ("Bonbon", _s(("couleur", dict(couleur="#ff4f9a")),
                      ("biseau", dict(taille=12, profondeur=120, adoucir=4, altitude=50, opacite_sombre=35)),
                      ("lueur_interne", dict(couleur="#ffffff", taille=12, opacite=35, source="centre")))),
        ("Verre", _s(("lueur_interne", dict(couleur="#ffffff", taille=10, opacite=55)),
                     ("biseau", dict(taille=8, profondeur=120, opacite_sombre=40)),
                     ("contour", dict(couleur="#ffffff", taille=1.5, opacite=70)),
                     ("ombre", dict(distance=6, taille=14, opacite=30)), remplissage=0.15)),
        ("Ombre longue", _s(*[("ombre", dict(couleur="#1b1b2f", mode="normal", opacite=100 - k * 2, angle=135,
                                              distance=k * 1.25, taille=0.6, **{"global": False}))
                               for k in range(1, 36)])),
        ("Contour double", _s(("contour", dict(couleur="#ffffff", taille=7)),       # le premier passe devant
                              ("contour", dict(couleur="#000000", taille=14)))),
        ("Arc-en-ciel", _s(("degrade", dict(angle=0, degrade=_points(
            ("#ff1e1e", 0), ("#ff9a00", .2), ("#ffe600", .4), ("#22d04a", .6), ("#1e7bff", .8), ("#9b30ff", 1)))),
                           ("contour", dict(couleur="#ffffff", taille=3)))),
        ("Glitch", _s(("ombre", dict(couleur="#00f0ff", mode="ecran", opacite=100, angle=180, distance=5, taille=0,
                                     **{"global": False})),
                      ("ombre", dict(couleur="#ff0055", mode="ecran", opacite=100, angle=0, distance=5, taille=0,
                                     **{"global": False})))),
        ("Rétro 80", _s(("degrade", dict(angle=90, degrade=_points(
            ("#ff2a8a", 0), ("#ff7b3a", .45), ("#ffe45c", .55), ("#fff6c8", 1)))),
                        ("contour", dict(couleur="#ffffff", taille=2)),
                        ("ombre", dict(couleur="#2b0f5c", mode="normal", opacite=100, angle=135, distance=8, taille=0,
                                       **{"global": False})),
                        ("lueur", dict(couleur="#ff2a8a", taille=26, opacite=55)))),
        ("Argent", _s(("degrade", dict(angle=90, degrade=_points(
            ("#6d737a", 0), ("#d8dde2", .45), ("#9aa1a8", .55), ("#f7f9fb", 1)))),
                      ("biseau", dict(taille=5, profondeur=160, altitude=40, opacite_sombre=45)),
                      ("contour", dict(couleur="#50565c", taille=1.5)),
                      ("ombre", dict(distance=4, taille=8, opacite=40)))),
        ("Glace", _s(("degrade", dict(angle=90, degrade=_points(("#7fc8ff", 0), ("#d9f2ff", .6), ("#ffffff", 1)))),
                     ("lueur_interne", dict(couleur="#ffffff", taille=8, opacite=70)),
                     ("biseau", dict(taille=4, profondeur=140, opacite_sombre=25, sombre="#2a6fb0")),
                     ("contour", dict(couleur="#bfe6ff", taille=1.5)),
                     ("lueur", dict(couleur="#6ccaff", taille=18, opacite=60)))),
        ("Bande dessinée", _s(("couleur", dict(couleur="#ffd400")),
                              ("contour", dict(couleur="#000000", taille=6)),
                              ("ombre", dict(couleur="#e0261b", mode="normal", opacite=100, angle=135, distance=11,
                                             taille=0, **{"global": False})))),
    ]]
