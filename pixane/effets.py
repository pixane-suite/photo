"""Effets créatifs du menu Filtres : rétro (demi-teinte, VHS, pellicule ancienne, pixel art), peinture (aquarelle,
peinture à l'huile, croquis, bande dessinée), effet miniature, lumière (reflet d'objectif, rayons de soleil, fuites de
lumière) et bordures (Polaroid, cadre, coins arrondis, bords déchirés, passe-partout).

Même contrat que filtres.py : tableau RGBA (uint8, ou float32 sur l'échelle 0..255 pour un calque 16 / 32 bits) ->
tableau RGBA de même forme. Les effets travaillent en 8 bits (ce sont des effets de style) ; seule la sortie reprend le
type d'entrée.
"""
from __future__ import annotations

import math

import numpy as np

from .langue import tr

# type -> liste de (clé, libellé, min, max, défaut, unité) ; même forme que filtres.FILTRES
EFFETS = {
    "demi_teinte": [("taille", "Taille des points", 3, 60, 8, " px"), ("angle", "Angle", 0, 90, 45, "°"),
                    ("mode", "Couleurs", 0, 1, 0, "")],
    "vhs": [("force", "Force", 0, 100, 60, ""), ("lignes", "Lignes de balayage", 0, 100, 50, " %"),
            ("bruit", "Bruit", 0, 100, 35, " %")],
    "pellicule": [("age", "Âge (couleurs passées)", 0, 100, 60, " %"), ("grain", "Grain", 0, 100, 45, " %"),
                  ("rayures", "Rayures et poussières", 0, 100, 40, " %")],
    "pixel_art": [("taille", "Taille des pixels", 2, 64, 8, " px"), ("couleurs", "Nombre de couleurs", 2, 64, 16, "")],
    "aquarelle": [("force", "Force", 1, 100, 60, ""), ("papier", "Grain du papier", 0, 100, 40, " %")],
    "huile": [("rayon", "Taille de la touche", 2, 20, 5, " px"), ("relief", "Relief de la peinture", 0, 100, 30, " %")],
    "croquis": [("trait", "Finesse du trait", 1, 30, 8, " px"), ("couleur", "Couleurs", 0, 1, 0, ""),
                ("contraste", "Contraste", 0, 100, 50, " %")],
    "bd": [("niveaux", "Nombre de teintes", 2, 12, 5, ""), ("traits", "Épaisseur des traits", 0, 5, 2, " px")],
    "miniature": [("position", "Hauteur de la zone nette", 0, 100, 55, " %"),
                  ("largeur", "Largeur de la zone nette", 2, 80, 25, " %"), ("flou", "Flou", 1, 60, 8, " px"),
                  ("saturation", "Couleurs plus vives", 0, 100, 35, " %")],
    "reflet": [("cx", "Centre horizontal", 0, 100, 25, " %"), ("cy", "Centre vertical", 0, 100, 25, " %"),
               ("force", "Force", 0, 100, 70, ""), ("taille", "Taille", 5, 100, 35, " %")],
    "rayons": [("cx", "Centre horizontal", 0, 100, 50, " %"), ("cy", "Centre vertical", 0, 100, 20, " %"),
               ("force", "Force", 0, 100, 60, ""), ("longueur", "Longueur", 5, 100, 50, " %"),
               ("seuil", "Seuil des parties claires", 0, 255, 170, "")],
    "fuites": [("teinte", "Couleur", 0, 3, 0, ""), ("cote", "Côté", 0, 4, 0, ""), ("force", "Force", 0, 100, 60, ""),
               ("variante", "Variante", 0, 20, 1, "")],
    "bordure": [("style", "Style", 0, 5, 0, ""), ("epaisseur", "Épaisseur", 1, 30, 5, " %"),
                ("couleur", "Couleur", 0, 2, 0, "")],
}

GROUPES = [("Rétro", ("demi_teinte", "vhs", "pellicule", "pixel_art")),
           ("Peinture", ("aquarelle", "huile", "croquis", "bd")),
           ("Lumière", ("reflet", "rayons", "fuites")),
           ("", ("miniature", "bordure"))]


def noms() -> dict:
    return {"demi_teinte": tr("Demi-teinte (pop art)"), "vhs": tr("Cassette VHS"), "pellicule": tr("Pellicule ancienne"),
            "pixel_art": tr("Pixel art"), "aquarelle": tr("Aquarelle"), "huile": tr("Peinture à l'huile"),
            "croquis": tr("Croquis au crayon"), "bd": tr("Bande dessinée"), "miniature": tr("Effet miniature"),
            "reflet": tr("Reflet d'objectif"), "rayons": tr("Rayons de soleil"), "fuites": tr("Fuites de lumière"),
            "bordure": tr("Bordure et cadre")}


def noms_groupes() -> dict:
    return {"Rétro": tr("Rétro"), "Peinture": tr("Peinture"), "Lumière": tr("Lumière")}


def libelles() -> dict:
    return {"Taille des points": tr("Taille des points"), "Couleurs": tr("Couleurs"),
            "Lignes de balayage": tr("Lignes de balayage"), "Bruit": tr("Bruit"),
            "Âge (couleurs passées)": tr("Âge (couleurs passées)"), "Grain": tr("Grain"),
            "Rayures et poussières": tr("Rayures et poussières"), "Taille des pixels": tr("Taille des pixels"),
            "Nombre de couleurs": tr("Nombre de couleurs"), "Grain du papier": tr("Grain du papier"),
            "Taille de la touche": tr("Taille de la touche"), "Relief de la peinture": tr("Relief de la peinture"),
            "Finesse du trait": tr("Finesse du trait"), "Contraste": tr("Contraste"),
            "Nombre de teintes": tr("Nombre de teintes"), "Épaisseur des traits": tr("Épaisseur des traits"),
            "Hauteur de la zone nette": tr("Hauteur de la zone nette"),
            "Largeur de la zone nette": tr("Largeur de la zone nette"), "Flou": tr("Flou"),
            "Couleurs plus vives": tr("Couleurs plus vives"), "Taille": tr("Taille"), "Longueur": tr("Longueur"),
            "Seuil des parties claires": tr("Seuil des parties claires"), "Couleur": tr("Couleur"), "Côté": tr("Côté"),
            "Variante": tr("Variante"), "Style": tr("Style"), "Épaisseur": tr("Épaisseur")}


def choix(type_: str, cle: str) -> list[str] | None:
    return {("demi_teinte", "mode"): [tr("Noir et blanc"), tr("Quadrichromie (CMJN)")],
            ("croquis", "couleur"): [tr("Crayon gris"), tr("Crayons de couleur")],
            ("fuites", "teinte"): [tr("Orange chaud"), tr("Rose"), tr("Bleu froid"), tr("Arc-en-ciel")],
            ("fuites", "cote"): [tr("Gauche"), tr("Droite"), tr("Haut"), tr("Bas"), tr("Coins")],
            ("bordure", "style"): [tr("Polaroid"), tr("Cadre simple"), tr("Coins arrondis"), tr("Bords déchirés"),
                                   tr("Passe-partout"), tr("Pellicule (film)")],
            ("bordure", "couleur"): [tr("Blanc"), tr("Noir"), tr("Crème")]}.get((type_, cle))


# ------------------------------------------------------------------ outils
def _u8(t: np.ndarray) -> np.ndarray:
    return np.clip(np.round(t), 0, 255).astype(np.uint8) if t.dtype != np.uint8 else t


def _sortie(rgb: np.ndarray, t: np.ndarray, alpha: np.ndarray | None = None) -> np.ndarray:
    """rgb float 0..255 (h, w, 3) -> même type que t, transparence d'origine (ou alpha donné)."""
    out = np.empty(t.shape, np.float32)
    out[..., :3] = rgb
    out[..., 3] = t[..., 3] if alpha is None else alpha
    if t.dtype.kind == "f":
        return np.clip(out, 0, 255).astype(np.float32)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def _flou(f: np.ndarray, rayon: float) -> np.ndarray:
    from .filtres import flou_flottant
    return flou_flottant(f, rayon) if rayon > 0.3 else f.astype(np.float32)


def _gris(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _ecran(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Mode Superposition « Écran » sur 0..255."""
    return 255 - (255 - a) * (255 - b) / 255


def _bruit(h: int, w: int, graine: int) -> np.ndarray:
    return np.random.default_rng(graine).standard_normal((h, w)).astype(np.float32)


# ------------------------------------------------------------------ rétro
def demi_teinte(t: np.ndarray, p: dict) -> np.ndarray:
    """Trame de points ronds, comme l'imprimerie : en noir et blanc, ou en quatre encres (cyan, magenta, jaune, noir)
    chacune avec son angle."""
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    s = float(p["taille"])
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    lisse = _flou(rgb, s / 3)

    def trame(encre: np.ndarray, angle: float) -> np.ndarray:
        """encre 0..1 (1 = plein) -> couverture 0..1 (points ronds, bords adoucis)."""
        a = math.radians(angle)
        ca, sa = math.cos(a), math.sin(a)
        u, v = x * ca + y * sa, -x * sa + y * ca
        cu, cv = (np.floor(u / s) + 0.5) * s, (np.floor(v / s) + 0.5) * s
        cx, cy = cu * ca - cv * sa, cu * sa + cv * ca          # centre de la cellule, dans l'image
        ix = np.clip(np.round(cx), 0, w - 1).astype(np.int32)
        iy = np.clip(np.round(cy), 0, h - 1).astype(np.int32)
        valeur = encre[iy, ix]
        rayon = np.sqrt(np.clip(valeur, 0, 1)) * s * 0.72      # 72 % : les points pleins se touchent
        d = np.hypot(u - cu, v - cv)
        return np.clip(rayon - d + 0.5, 0, 1)

    if int(p["mode"]) == 0:
        g = trame(1 - _gris(lisse) / 255, float(p["angle"]))
        res = np.repeat((255 * (1 - g))[..., None], 3, axis=2)
    else:
        c, m, j = (1 - lisse[..., i] / 255 for i in range(3))
        k = np.minimum(np.minimum(c, m), j)
        res = np.full((h, w, 3), 255, np.float32)
        base = float(p["angle"])
        for encre, angle, couleur in ((c - k, base - 30, (0, 174, 239)), (m - k, base + 30, (236, 0, 140)),
                                      (j - k, base - 45, (255, 242, 0)), (k, base, (0, 0, 0))):
            cov = trame(np.clip(encre / np.maximum(1 - k, 1e-3) if couleur != (0, 0, 0) else encre, 0, 1), angle)
            res = res * (1 - cov[..., None]) + res * np.array(couleur, np.float32) / 255 * cov[..., None]
    return _sortie(res, t)


def vhs(t: np.ndarray, p: dict) -> np.ndarray:
    """Cassette vidéo : couleurs décalées (rouge et bleu), flou horizontal, lignes de balayage, bruit, couleurs un
    peu passées."""
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    force = p["force"] / 100
    d = max(1, int(round(w * 0.006 * force)))
    res = rgb.copy()
    res[:, d:, 0] = rgb[:, :-d, 0]                      # rouge vers la droite
    res[:, :-d, 2] = rgb[:, d:, 2]                      # bleu vers la gauche
    k = max(1, int(round(w * 0.002 * (1 + 3 * force))))
    res = _flou_horizontal(res, k)
    gris = _gris(res)[..., None]
    res = gris + (res - gris) * (1 - 0.25 * force)      # couleurs un peu passées
    res = res * (0.92 + 0.08 * force) + 10 * force      # noirs relevés
    lignes = p["lignes"] / 100
    if lignes > 0:
        pas = max(2, h // 240)
        rangée = (np.arange(h) // max(1, pas // 2)) % 2
        res = res * (1 - 0.22 * lignes * rangée)[:, None, None]
    bruit = p["bruit"] / 100
    if bruit > 0:
        res = res + _bruit(h, w, 7)[..., None] * 18 * bruit
        bandes = np.random.default_rng(3).random(h) < 0.004 * bruit
        decal = np.random.default_rng(4).integers(-3 * d - 2, 3 * d + 3, h)
        for yy in np.where(bandes)[0]:
            res[yy] = np.roll(res[yy], int(decal[yy]), axis=0)
    return _sortie(res, t)


def _flou_horizontal(f: np.ndarray, k: int) -> np.ndarray:
    p = np.pad(f, [(0, 0), (k + 1, k), (0, 0)], mode="edge").astype(np.float64)
    c = np.cumsum(p, axis=1)
    return ((c[:, 2 * k + 1:] - c[:, :-2 * k - 1]) / (2 * k + 1)).astype(np.float32)


def pellicule(t: np.ndarray, p: dict) -> np.ndarray:
    """Photo argentique ancienne : couleurs passées vers le sépia, grain, rayures verticales, poussières, coins
    assombris."""
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    age = p["age"] / 100
    g = _gris(rgb)
    sepia = np.stack([g * 1.07 + 18, g * 0.95 + 8, g * 0.78], axis=-1)
    res = rgb * (1 - age) + sepia * age
    res = 18 * age + res * (1 - 0.14 * age)             # noirs passés, blancs ternis
    grain = p["grain"] / 100
    if grain > 0:
        n = _flou(_bruit(h, w, 11), 0.6)
        res = res + n[..., None] * 26 * grain
    ray = p["rayures"] / 100
    if ray > 0:
        rng = np.random.default_rng(5)
        voile = np.zeros((h, w), np.float32)
        for _ in range(int(3 + 9 * ray)):                # rayures fines verticales
            x0 = int(rng.integers(0, w))
            large = max(1, w // 900)
            y0, y1 = sorted(rng.integers(0, h, 2))
            voile[y0:y1 + h // 4, x0:x0 + large] += rng.choice([-1, 1]) * rng.uniform(0.4, 1)
        for _ in range(int(40 * ray * (w * h) / 1e6) + 3):   # poussières
            cx, cy = int(rng.integers(0, w)), int(rng.integers(0, h))
            r = max(1, int(rng.uniform(0.5, 2.5) * max(w, h) / 1200))
            voile[max(0, cy - r):cy + r, max(0, cx - r):cx + r] += rng.choice([-1, 1]) * 0.9
        res = res + voile[..., None] * 90 * ray
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.hypot((x + 0.5) / w * 2 - 1, (y + 0.5) / h * 2 - 1) / math.sqrt(2)
    res = res * (1 - 0.45 * age * np.clip(d - 0.35, 0, 1) ** 1.5 / 0.65 ** 1.5)[..., None]
    return _sortie(res, t)


def pixel_art(t: np.ndarray, p: dict) -> np.ndarray:
    """Gros pixels carrés et peu de couleurs, comme un vieux jeu vidéo."""
    from PIL import Image
    h, w = t.shape[:2]
    s = int(p["taille"])
    pw, ph = max(1, round(w / s)), max(1, round(h / s))
    petit = Image.fromarray(_u8(t[..., :3]), "RGB").resize((pw, ph), Image.BOX)
    n = int(p["couleurs"])
    petit = petit.quantize(colors=n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    grand = petit.resize((w, h), Image.NEAREST)
    return _sortie(np.asarray(grand, np.float32), t)


# ------------------------------------------------------------------ peinture
def aquarelle(t: np.ndarray, p: dict) -> np.ndarray:
    """Aquarelle : couleurs lissées en aplats doux (filtre qui garde les bords), bords de taches plus foncés, grain
    du papier."""
    import cv2
    h, w = t.shape[:2]
    force = p["force"] / 100
    img = _u8(t[..., :3])
    echelle = max(w, h) / 1000
    res = cv2.edgePreservingFilter(img, flags=cv2.RECURS_FILTER, sigma_s=(15 + 60 * force) * max(1, echelle),
                                   sigma_r=0.3 + 0.3 * force)
    res = cv2.edgePreservingFilter(res, flags=cv2.RECURS_FILTER, sigma_s=10 * max(1, echelle), sigma_r=0.25)
    res = res.astype(np.float32)
    pas = 255 / (6 + 10 * (1 - force))                   # aplats : teintes un peu regroupées
    res = res * 0.7 + np.round(res / pas) * pas * 0.3
    res = _flou(res, 0.8 + 1.5 * force * max(1, echelle))   # couleur qui « bave » un peu
    bords = np.abs(res - _flou(res, 3 * max(1, echelle))).sum(axis=2, keepdims=True)
    res = res - np.clip(bords * 0.15, 0, 18)             # pigment accumulé aux bords des taches (léger)
    papier = p["papier"] / 100
    if papier > 0:
        grain = _flou(_bruit(h, w, 21), 1.2) * 0.7 + _flou(_bruit(h, w, 22), 6) * 2.2
        res = res * (1 + grain[..., None] * 0.035 * papier)
        res = res + (255 - res) * 0.08 * papier          # papier blanc qui transparaît
    return _sortie(res, t)


def huile(t: np.ndarray, p: dict) -> np.ndarray:
    """Peinture à l'huile (filtre de Kuwahara) : chaque point prend la couleur du coin le plus uni autour de lui,
    ce qui donne des touches de pinceau ; un léger relief imite l'épaisseur de la peinture."""
    from .filtres import boite
    rgb = t[..., :3].astype(np.float32)
    r = int(p["rayon"])
    q = max(1, r // 2)
    moy = boite(rgb, q)
    lum = _gris(rgb)
    m1, m2 = boite(lum, q), boite(lum * lum, q)
    var = m2 - m1 * m1
    h, w = lum.shape

    def decale(a, dy, dx):
        pad = [(abs(dy), abs(dy)), (abs(dx), abs(dx))] + [(0, 0)] * (a.ndim - 2)
        b = np.pad(a, pad, mode="edge")
        return b[abs(dy) + dy:abs(dy) + dy + h, abs(dx) + dx:abs(dx) + dx + w]
    meilleur = np.full((h, w), np.inf, np.float32)
    res = np.zeros_like(rgb)
    for dy in (-q, q):
        for dx in (-q, q):
            v, m = decale(var, dy, dx), decale(moy, dy, dx)
            prend = v < meilleur
            meilleur = np.where(prend, v, meilleur)
            res = np.where(prend[..., None], m, res)
    relief = p["relief"] / 100
    if relief > 0:
        l2 = _gris(res)
        gy, gx = np.gradient(_flou(l2, 1))
        res = res + ((gx - gy) * 0.9 * relief)[..., None]
    return _sortie(res, t)


def croquis(t: np.ndarray, p: dict) -> np.ndarray:
    """Croquis au crayon : « densité couleur − » entre l'image et son négatif flou (traits sur fond blanc) ; en
    gris ou en crayons de couleur."""
    rgb = t[..., :3].astype(np.float32)
    g = _gris(rgb)
    flou = _flou(255 - g, float(p["trait"]))
    dessin = np.clip(g * 255 / np.maximum(255 - flou, 1), 0, 255)
    c = p["contraste"] / 100
    dessin = 255 - (255 - dessin) * (1 + 2.5 * c)
    dessin = np.clip(dessin, 0, 255)
    if int(p["couleur"]) == 1:
        teinte = rgb + (255 - rgb) * 0.35
        res = teinte * dessin[..., None] / 255
    else:
        res = np.repeat(dessin[..., None], 3, axis=2)
    return _sortie(res, t)


def bd(t: np.ndarray, p: dict) -> np.ndarray:
    """Bande dessinée : couleurs lissées réduites à quelques teintes, contours noirs."""
    import cv2
    img = _u8(t[..., :3])
    lisse = img
    for _ in range(3):
        lisse = cv2.bilateralFilter(lisse, 9, 60, 7)
    n = int(p["niveaux"])
    f = lisse.astype(np.float32)
    pas = 255 / max(1, n - 1)
    hsv = cv2.cvtColor(lisse, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 2] = np.round(hsv[..., 2] / pas) * pas
    hsv[..., 1] = np.clip(hsv[..., 1] * 1.25, 0, 255)
    f = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    ep = int(p["traits"])
    if ep > 0:
        gris = cv2.medianBlur(cv2.cvtColor(lisse, cv2.COLOR_RGB2GRAY), 5)
        traits = cv2.Canny(gris, 40, 110)
        if ep > 1:
            traits = cv2.dilate(traits, np.ones((ep, ep), np.uint8))
        n, etiq, stats, _c = cv2.connectedComponentsWithStats(traits, connectivity=8)
        petits = stats[:, cv2.CC_STAT_AREA] < 12 * ep * ep      # miettes isolées : pas de trait
        petits[0] = False
        traits[petits[etiq]] = 0
        traits = cv2.GaussianBlur(traits, (3, 3), 0)
        f = f * (1 - traits[..., None].astype(np.float32) / 255)
    return _sortie(f, t)


# ------------------------------------------------------------------ miniature
def miniature(t: np.ndarray, p: dict) -> np.ndarray:
    """Effet miniature (tilt-shift) : une bande nette, le reste de plus en plus flou, couleurs plus vives : la
    scène ressemble à une maquette."""
    h = t.shape[0]
    rgb = t[..., :3].astype(np.float32)
    centre = p["position"] / 100 * h
    demi = p["largeur"] / 200 * h
    y = np.arange(h, dtype=np.float32)
    d = np.clip((np.abs(y - centre) - demi) / max(1.0, h * 0.35), 0, 1)        # 0 dans la bande, 1 loin
    rayon = float(p["flou"])
    niveaux = [rgb] + [_flou(rgb, rayon * k / 3) for k in (1, 2, 3)]
    pos = d * 3
    i0 = np.clip(np.floor(pos).astype(int), 0, 2)
    fr = (pos - i0)[:, None, None]
    pile = np.stack(niveaux)                                                    # 4, h, w, 3
    rangs = np.arange(h)
    a, b = pile[i0, rangs], pile[i0 + 1, rangs]
    res = a * (1 - fr) + b * fr
    s = p["saturation"] / 100
    if s > 0:
        g = _gris(res)[..., None]
        res = g + (res - g) * (1 + 0.8 * s)
        res = (res - 128) * (1 + 0.15 * s) + 128
    return _sortie(res, t)


# ------------------------------------------------------------------ lumière
def reflet(t: np.ndarray, p: dict) -> np.ndarray:
    """Reflet d'objectif : halo autour de la source, étoile, anneaux de couleur alignés vers le centre de l'image."""
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    cx, cy = p["cx"] / 100 * w, p["cy"] / 100 * h
    force = p["force"] / 100
    taille = p["taille"] / 100 * max(w, h)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    lum = np.zeros((h, w, 3), np.float32)
    d = np.hypot(x - cx, y - cy)
    lum += np.exp(-(d / (taille * 0.08)) ** 2)[..., None] * np.array([255, 250, 235])          # cœur
    lum += np.exp(-d / (taille * 0.35))[..., None] * np.array([255, 190, 120]) * 0.55          # halo chaud
    a = np.arctan2(y - cy, x - cx)
    etoile = (np.abs(np.cos(3 * a)) ** 40) * np.exp(-d / (taille * 0.5))
    lum += etoile[..., None] * np.array([255, 235, 210]) * 0.5
    vx, vy = w / 2 - cx, h / 2 - cy
    for k, (pos, r, coul, op) in enumerate(((0.5, 0.05, (120, 200, 255), 0.35), (0.85, 0.09, (150, 255, 170), 0.22),
                                            (1.25, 0.03, (255, 160, 220), 0.45), (1.6, 0.14, (120, 160, 255), 0.18),
                                            (1.9, 0.06, (255, 220, 130), 0.3))):
        gx, gy = cx + vx * pos, cy + vy * pos
        dd = np.hypot(x - gx, y - gy) / (taille * r * 1.6)
        disque = np.clip(1.15 - dd, 0, 1) ** 0.7
        anneau = np.exp(-((dd - 1) / 0.08) ** 2) * 0.6
        lum += (disque * 0.6 + anneau)[..., None] * np.array(coul, np.float32) * op
    res = _ecran(rgb, np.clip(lum * force, 0, 255))
    return _sortie(res, t)


def rayons(t: np.ndarray, p: dict) -> np.ndarray:
    """Rayons de soleil : les parties claires de l'image sont étirées depuis la source de lumière (flou radial vers
    la source), puis ajoutées en mode Écran."""
    import cv2
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    seuil = float(p["seuil"])
    clair = np.clip((_gris(rgb) - seuil) / max(1.0, 255 - seuil), 0, 1)
    source = (clair[..., None] * (rgb * 0.5 + np.array([255, 235, 200], np.float32) * 0.5)).astype(np.float32)
    echelle = max(1, int(max(w, h) / 900))
    if echelle > 1:
        petit = cv2.resize(source, (w // echelle, h // echelle), interpolation=cv2.INTER_AREA)
    else:
        petit = source
    ph, pw = petit.shape[:2]
    cx, cy = p["cx"] / 100 * pw, p["cy"] / 100 * ph
    longueur = p["longueur"] / 100
    n = 32
    acc = np.zeros_like(petit)
    for i in range(n):
        s = 1 + longueur * 1.2 * i / n
        m = np.float32([[s, 0, cx * (1 - s)], [0, s, cy * (1 - s)]])
        acc += cv2.warpAffine(petit, m, (pw, ph), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT) \
            * (1 - i / n)
    acc /= n / 2
    if echelle > 1:
        acc = cv2.resize(acc, (w, h), interpolation=cv2.INTER_LINEAR)
    res = _ecran(rgb, np.clip(acc * 5 * p["force"] / 100, 0, 255))
    return _sortie(res, t)


def fuites(t: np.ndarray, p: dict) -> np.ndarray:
    """Fuites de lumière (pellicule voilée) : grandes taches de couleur chaude qui viennent d'un bord, en mode
    Écran."""
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    rng = np.random.default_rng(int(p["variante"]))
    teintes = [[(255, 120, 30), (255, 60, 20), (255, 200, 90)], [(255, 80, 140), (255, 140, 200), (200, 60, 255)],
               [(40, 140, 255), (90, 220, 255), (120, 90, 255)], [(255, 60, 40), (255, 210, 40), (60, 200, 255)]]
    couleurs = teintes[int(p["teinte"])]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = x / w, y / h
    cote = int(p["cote"])
    lum = np.zeros((h, w, 3), np.float32)
    for i in range(4):
        if cote == 0:
            px, py = rng.uniform(-0.15, 0.05), rng.uniform(0, 1)
        elif cote == 1:
            px, py = rng.uniform(0.95, 1.15), rng.uniform(0, 1)
        elif cote == 2:
            px, py = rng.uniform(0, 1), rng.uniform(-0.15, 0.05)
        elif cote == 3:
            px, py = rng.uniform(0, 1), rng.uniform(0.95, 1.15)
        else:
            px, py = float(rng.choice([-0.05, 1.05])), float(rng.choice([-0.05, 1.05]))
        rx, ry = rng.uniform(0.15, 0.45), rng.uniform(0.25, 0.7)
        d = ((nx - px) / rx) ** 2 + ((ny - py) / ry) ** 2
        tache = np.exp(-d * 1.6)
        lum += tache[..., None] * np.array(couleurs[i % len(couleurs)], np.float32) * rng.uniform(0.5, 0.9)
    res = _ecran(rgb, np.clip(lum * p["force"] / 100, 0, 255))
    return _sortie(res, t)


# ------------------------------------------------------------------ bordures
def bordure(t: np.ndarray, p: dict) -> np.ndarray:
    """Bordure dessinée dans l'image (la taille de l'image ne change pas) : Polaroid (bas plus large), cadre simple,
    coins arrondis (transparents), bords déchirés, passe-partout (cadre + fin liseré), pellicule (bandes perforées)."""
    h, w = t.shape[:2]
    rgb = t[..., :3].astype(np.float32)
    alpha = t[..., 3].astype(np.float32)
    style = int(p["style"])
    e = max(1.0, p["epaisseur"] / 100 * min(w, h))
    couleur = np.array([(250, 250, 248), (12, 12, 12), (243, 236, 218)][int(p["couleur"])], np.float32)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    if style == 2:                                       # coins arrondis : seulement la transparence
        r = e * 2
        dx = np.maximum(np.maximum(r - x, x - (w - 1 - r)), 0)
        dy = np.maximum(np.maximum(r - y, y - (h - 1 - r)), 0)
        dedans = np.clip(r - np.hypot(dx, dy) + 0.5, 0, 1)
        return _sortie(rgb, t, alpha * dedans)
    if style == 0:                                       # Polaroid : bas trois fois plus large
        g, d, haut, bas = e, e, e, e * 3.2
    elif style == 5:
        g = d = e * 0.4
        haut = bas = e * 1.6
    else:
        g = d = haut = bas = e
    cadre = np.maximum.reduce([np.clip(g - x, 0, 1), np.clip(x - (w - 1 - d), 0, 1),
                               np.clip(haut - y, 0, 1), np.clip(y - (h - 1 - bas), 0, 1)])
    if style == 3:                                       # bords déchirés : limite irrégulière
        rng = np.random.default_rng(9)

        def bord(n):
            v = np.cumsum(rng.standard_normal(n)) * 0.6
            v = v - np.linspace(v[0], v[-1], n)
            return v * e * 0.08 + rng.standard_normal(n) * e * 0.05
        bx, by = bord(h), bord(w)
        dist = np.minimum.reduce([x - (g + bx[:, None]), (w - 1 - d + bx[::-1, None]) - x,
                                  y - (haut + by[None, :]), (h - 1 - bas + by[None, ::-1]) - y])
        cadre = np.clip(0.5 - dist, 0, 1)
        ombre = np.clip(1 - np.abs(dist) / (e * 0.15), 0, 1) * (dist > 0)
        rgb = rgb * (1 - 0.25 * ombre[..., None])
    res = rgb * (1 - cadre[..., None]) + couleur * cadre[..., None]
    if style == 4:                                       # passe-partout : liseré fin, en biais, autour de la photo
        bord_int = np.minimum.reduce([x - g, (w - 1 - d) - x, y - haut, (h - 1 - bas) - y])
        lisere = np.clip(1 - np.abs(bord_int + e * 0.06) / max(1.0, e * 0.03), 0, 1)
        res = res * (1 - lisere[..., None] * 0.35)
    if style == 5:                                       # perforations de pellicule
        pas = max(4.0, haut * 1.4)
        trou_l, trou_h = pas * 0.5, haut * 0.45
        mx = (x % pas) < trou_l
        for y0 in ((haut - trou_h) / 2, h - bas + (bas - trou_h) / 2):
            dans = mx & (y >= y0) & (y < y0 + trou_h)
            res = np.where(dans[..., None], np.array([235, 235, 230], np.float32) if couleur.sum() < 100
                           else np.array([20, 20, 20], np.float32), res)
    a = np.maximum(alpha, cadre * 255)
    return _sortie(res, t, a)


FONCTIONS = {"demi_teinte": demi_teinte, "vhs": vhs, "pellicule": pellicule, "pixel_art": pixel_art,
             "aquarelle": aquarelle, "huile": huile, "croquis": croquis, "bd": bd, "miniature": miniature,
             "reflet": reflet, "rayons": rayons, "fuites": fuites, "bordure": bordure}
