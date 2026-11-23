"""Filtres (menu Filtres) : flou gaussien, flou de mouvement, flou radial, flou de l'objectif, flou de surface,
réduction du bruit, netteté, vignette.

Calcul pur sur des tableaux RGBA uint8 (couleurs non prémultipliées), ou float32 sur la même échelle 0..255 pour un
calque 16 bits (le résultat est alors rendu en float, sans arrondi : voir appliquer_calque). Les flous travaillent en couleurs
prémultipliées : un bord transparent ne fait pas de halo sombre. `appliquer_calque` pose le résultat sur le calque,
seulement dans la sélection (bords doux) s'il y en a une.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageFilter
from PySide6.QtGui import QImage

from .langue import tr

# type -> liste de (clé, libellé, min, max, défaut, unité)
FILTRES = {
    "flou": [("rayon", "Rayon", 1, 250, 6, " px")],
    "mouvement": [("angle", "Angle", -180, 180, 0, "°"), ("distance", "Distance", 2, 500, 30, " px")],
    "radial": [("quantite", "Quantité", 1, 100, 15, ""), ("zoom", "Méthode", 0, 1, 1, ""),
               ("cx", "Centre horizontal", 0, 100, 50, " %"), ("cy", "Centre vertical", 0, 100, 50, " %")],
    "objectif": [("rayon", "Rayon", 1, 200, 12, " px"), ("reflets", "Reflets lumineux", 0, 100, 40, " %"),
                 ("seuil", "Seuil des reflets", 150, 255, 220, "")],
    "surface": [("rayon", "Rayon", 1, 100, 6, " px"), ("seuil", "Seuil", 2, 255, 18, "")],
    "bruit": [("force", "Force", 1, 100, 40, ""), ("details", "Garder les détails", 0, 100, 40, " %"),
              ("couleur", "Bruit de couleur", 0, 100, 60, " %")],
    "nettete": [("quantite", "Quantité", 1, 500, 120, " %"), ("rayon", "Rayon", 1, 50, 2, " px"),
                ("seuil", "Seuil", 0, 50, 2, "")],
    "vignette": [("force", "Force (− assombrit, + éclaircit)", -100, 100, -45, ""),
                 ("taille", "Taille du centre", 0, 100, 50, " %"), ("douceur", "Douceur", 0, 100, 60, " %"),
                 ("rond", "Rond (0 = suit le cadre)", 0, 100, 40, " %")],
    "correction": [("deformation", "Déformation (− corrige un coussin, + corrige un tonneau)", -100, 100, 0, ""),
                   ("vignetage", "Vignetage (+ éclaircit les coins sombres)", -100, 100, 0, ""),
                   ("franges", "Franges de couleur (rouge / cyan sur les bords)", -100, 100, 0, "")],
}


def noms() -> dict:
    return {"flou": tr("Flou gaussien"), "mouvement": tr("Flou de mouvement"), "radial": tr("Flou radial"),
            "objectif": tr("Flou de l'objectif"), "surface": tr("Flou de surface"), "bruit": tr("Réduction du bruit"),
            "nettete": tr("Netteté"), "vignette": tr("Vignette"), "correction": tr("Correction de l'objectif")}


def libelles() -> dict:
    """Libellés (écrits en entier pour la traduction)."""
    return {"Rayon": tr("Rayon"), "Angle": tr("Angle"), "Distance": tr("Distance"), "Force": tr("Force"),
            "Garder les détails": tr("Garder les détails"), "Bruit de couleur": tr("Bruit de couleur"),
            "Quantité": tr("Quantité"), "Seuil": tr("Seuil"),
            "Force (− assombrit, + éclaircit)": tr("Force (− assombrit, + éclaircit)"),
            "Taille du centre": tr("Taille du centre"), "Douceur": tr("Douceur"),
            "Rond (0 = suit le cadre)": tr("Rond (0 = suit le cadre)"),
            "Méthode": tr("Méthode"),
            "Centre horizontal": tr("Centre horizontal"), "Centre vertical": tr("Centre vertical"),
            "Reflets lumineux": tr("Reflets lumineux"), "Seuil des reflets": tr("Seuil des reflets"),
            "Déformation (− corrige un coussin, + corrige un tonneau)":
                tr("Déformation (− corrige un coussin, + corrige un tonneau)"),
            "Vignetage (+ éclaircit les coins sombres)": tr("Vignetage (+ éclaircit les coins sombres)"),
            "Franges de couleur (rouge / cyan sur les bords)": tr("Franges de couleur (rouge / cyan sur les bords)")}


def choix(type_: str, cle: str) -> list[str] | None:
    """Réglages à choisir dans une liste (valeur = place dans la liste) plutôt qu'avec un curseur."""
    if (type_, cle) == ("radial", "zoom"):
        return [tr("Rotation"), tr("Zoom")]
    return None


def defauts(type_: str) -> dict:
    return {r[0]: r[4] for r in FILTRES[type_]}


# ------------------------------------------------------------------ outils
def _premul(t: np.ndarray) -> np.ndarray:
    f = t.astype(np.float32)
    f[..., :3] *= f[..., 3:4] / 255
    return f


def _fin(v, t: np.ndarray) -> np.ndarray:
    """Résultat 0..255 : arrondi en uint8 ; gardé en float (16 / 32 bits) si l'entrée t était en float, sans
    plafond (en 32 bits, une couleur peut dépasser le blanc ; en 16 bits, appliquer_calque la ramène)."""
    if t.dtype.kind == "f":
        return np.maximum(np.asarray(v, np.float32), 0)
    return np.clip(np.round(v), 0, 255).astype(np.uint8)


def _depremul(f: np.ndarray, t: np.ndarray | None = None) -> np.ndarray:
    a = f[..., 3:4]
    seuil = 0.5 if t is None or t.dtype.kind != "f" else 0.002
    rgb = np.where(a > seuil, f[..., :3] * 255 / np.maximum(a, 1e-3), 0)
    v = np.concatenate([rgb, a], axis=-1)
    return _fin(v, t) if t is not None else np.clip(np.round(v), 0, 255).astype(np.uint8)


def boite(a: np.ndarray, r: int) -> np.ndarray:
    """Moyenne sur un carré de côté 2r+1 (bords répétés), en temps constant quel que soit r."""
    if r < 1:
        return a.astype(np.float32)
    p = np.pad(a.astype(np.float64), [(r + 1, r)] + [(r + 1, r)] + [(0, 0)] * (a.ndim - 2), mode="edge")
    c = np.cumsum(p, axis=0)
    c = c[2 * r + 1:] - c[:-2 * r - 1]
    c = np.cumsum(c, axis=1)
    c = c[:, 2 * r + 1:] - c[:, :-2 * r - 1]
    return (c / (2 * r + 1) ** 2).astype(np.float32)


def _flou_pil(f: np.ndarray, rayon: float) -> np.ndarray:
    """Flou gaussien d'un tableau float (h, w[, c]) : trois flous en boîte de suite (très proche d'une gaussienne,
    en temps constant quel que soit le rayon)."""
    sigma = max(0.3, float(rayon))
    r = max(1, int(round((np.sqrt(12 * sigma * sigma / 3 + 1) - 1) / 2)))
    res = f.astype(np.float32)
    for _ in range(3):
        res = boite(res, r)
    return res


flou_flottant = _flou_pil


# ------------------------------------------------------------------ filtres
def flou_gaussien(t: np.ndarray, p: dict) -> np.ndarray:
    """Pillow, en couleurs prémultipliées (mode « RGBa ») : rapide, sans halo au bord des zones transparentes.
    En 16 bits (t en float) : trois flous en boîte, en couleurs prémultipliées."""
    if t.dtype.kind == "f":
        return _depremul(_flou_pil(_premul(t), float(p["rayon"])), t)
    im = Image.fromarray(np.ascontiguousarray(t), "RGBA").convert("RGBa")
    return np.asarray(im.filter(ImageFilter.GaussianBlur(float(p["rayon"]))).convert("RGBA")).copy()


def flou_mouvement(t: np.ndarray, p: dict) -> np.ndarray:
    """L'image est tournée pour que le mouvement soit horizontal, floutée en ligne, puis remise droite."""
    h, w = t.shape[:2]
    f = _premul(t)
    d = max(2, int(p["distance"]))
    angle = float(p["angle"])
    couches = []
    for k in range(4):
        im = Image.fromarray(f[..., k], "F").rotate(-angle, Image.BILINEAR, expand=True)
        a = np.asarray(im, np.float32)
        r = d // 2
        pad = np.pad(a.astype(np.float64), [(0, 0), (r + 1, r)], mode="edge")
        c = np.cumsum(pad, axis=1)
        a = ((c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)).astype(np.float32)
        im = Image.fromarray(a, "F").rotate(angle, Image.BILINEAR, expand=True)
        W, H = im.size
        x0, y0 = (W - w) // 2, (H - h) // 2
        couches.append(np.asarray(im, np.float32)[y0:y0 + h, x0:x0 + w])
    res = np.stack(couches, axis=-1)
    if np.all(t[..., 3] == 255):          # photo opaque : les bords tournés ne doivent pas devenir transparents
        res[..., :3] = res[..., :3] * 255 / np.maximum(res[..., 3:4], 1e-3)
        res[..., 3] = 255
    return _depremul(res, t)


def _opaque(t: np.ndarray, res: np.ndarray) -> np.ndarray:
    """Photo opaque : les bords floutés ne doivent pas devenir transparents (res prémultiplié, float)."""
    if np.all(t[..., 3] == 255):
        res[..., :3] = res[..., :3] * 255 / np.maximum(res[..., 3:4], 1e-3)
        res[..., 3] = 255
    return res


def flou_radial(t: np.ndarray, p: dict) -> np.ndarray:
    """Comme Photoshop : rotation (les points tournent autour du centre) ou zoom (ils filent vers le centre).
    Moyenne de copies tournées ou agrandies autour du centre choisi."""
    h, w = t.shape[:2]
    f = _premul(t)
    q = p["quantite"] / 100
    cx, cy = w * p["cx"] / 100, h * p["cy"] / 100
    zoom = bool(p.get("zoom", 1))
    loin = max(math.hypot(cx - x, cy - y) for x in (0, w) for y in (0, h))
    longueur = loin * (q / 2 if zoom else math.radians(60 * q))     # trajet du point le plus loin, en pixels
    passes = int(min(8, max(3, math.ceil(math.log2(max(2.0, longueur / 1.5))))))
    n = 2 ** passes
    m = 0 if zoom else int(math.ceil(longueur)) + 2       # rotation : bords prolongés (sinon coins vides)
    if m:
        f = np.pad(f, [(m, m), (m, m), (0, 0)], mode="edge")
        cx, cy, w, h = cx + m, cy + m, w + 2 * m, h + 2 * m
    # copies doublées à chaque passe : après k passes, moyenne de 2^k copies régulièrement espacées
    res = [np.ascontiguousarray(f[..., k]) for k in range(4)]
    for i in range(passes):
        part = 2 ** i / n
        for k in range(4):
            im = Image.fromarray(res[k], "F")
            if zoom:
                s_ = (1 - q / 2) ** part
                a_ = (s_, 0, cx * (1 - s_), 0, s_, cy * (1 - s_))
                autre = np.asarray(im.transform((w, h), Image.AFFINE, a_, Image.BILINEAR), np.float32)
            else:
                autre = np.asarray(im.rotate(60 * q * part, Image.BILINEAR, center=(cx, cy)), np.float32)
            res[k] = (res[k] + autre) / 2
    if not zoom:                                     # le flou est centré sur la position d'origine
        res = [np.asarray(Image.fromarray(c, "F").rotate(-30 * q * (n - 1) / n, Image.BILINEAR, center=(cx, cy)),
                          np.float32) for c in res]
    res = np.stack(res, axis=-1)
    if m:
        res = np.ascontiguousarray(res[m:-m, m:-m])
    return _depremul(_opaque(t, res), t)


def _disque(r: int) -> np.ndarray:
    y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
    d = np.clip(r + 0.5 - np.sqrt(x * x + y * y), 0, 1)          # bord adouci d'un pixel
    return d / d.sum()


def _convoluer(f: np.ndarray, noyau: np.ndarray) -> np.ndarray:
    """Convolution (h, w, c) par un noyau (k, k), par transformée de Fourier (bords répétés)."""
    r = noyau.shape[0] // 2
    p = np.pad(f, [(r, r), (r, r), (0, 0)], mode="edge")
    H, W = p.shape[:2]
    taille = (H + 2 * r, W + 2 * r)
    K = np.fft.rfft2(noyau, taille)
    out = np.empty_like(f)
    for c in range(f.shape[2]):
        g = np.fft.irfft2(np.fft.rfft2(p[..., c], taille) * K, taille)
        out[..., c] = g[2 * r:2 * r + f.shape[0], 2 * r:2 * r + f.shape[1]]
    return out


def flou_objectif(t: np.ndarray, p: dict) -> np.ndarray:
    """Flou d'un vrai objectif : chaque point devient un petit disque (et non une tache floue comme le flou
    gaussien) ; les points très clairs (au-dessus du seuil) deviennent des reflets ronds bien visibles (bokeh)."""
    r = max(1, int(p["rayon"]))
    f = _premul(t) / 255
    rgb = f[..., :3]
    seuil = p["seuil"] / 255
    gain = p["reflets"] / 100 * 12
    y = rgb.max(axis=-1, keepdims=True)
    fort = np.clip((y - seuil) / max(1e-3, 1 - seuil), 0, 1) * gain       # lumière « gonflée » des reflets
    f2 = np.concatenate([rgb * (1 + fort), f[..., 3:4]], axis=-1).astype(np.float32)
    res = _convoluer(f2, _disque(r)) * 255
    res[..., :3] = np.minimum(res[..., :3], res[..., 3:4])
    return _depremul(_opaque(t, res), t)


def flou_surface(t: np.ndarray, p: dict) -> np.ndarray:
    """Comme le flou de surface de Photoshop : lisse les zones unies (peau, ciel) en gardant les bords nets ; le
    seuil dit à partir de quelle différence de couleur un bord est gardé."""
    f = t[..., :3].astype(np.float32) / 255
    r = max(1, int(p["rayon"]))
    eps = (p["seuil"] / 255) ** 2
    out = t.copy()
    res = np.stack([_guide(f[..., k], f[..., k], r, eps) for k in range(3)], axis=-1)
    out[..., :3] = _fin(res * 255, t)
    return out


def _guide(I: np.ndarray, P: np.ndarray, r: int, eps: float) -> np.ndarray:
    """Filtre guidé (He et al.) : lisse P en suivant les bords de I."""
    mI, mP = boite(I, r), boite(P, r)
    cov = boite(I * P, r) - mI * mP
    var = boite(I * I, r) - mI * mI
    a = cov / (var + eps)
    b = mP - a * mI
    return boite(a, r) * I + boite(b, r)


def reduire_bruit(t: np.ndarray, p: dict) -> np.ndarray:
    """Clarté : filtre guidé sur elle-même (lisse le grain, garde les bords). Couleur : bruit de couleur lissé plus
    fort (l'œil y est peu sensible)."""
    f = t[..., :3].astype(np.float32) / 255
    y = f @ np.array([0.299, 0.587, 0.114], np.float32)
    cb, cr = f[..., 2] - y, f[..., 0] - y
    force = p["force"] / 100
    r = max(1, round(1 + 4 * force))
    eps = (0.004 + 0.05 * force) ** 2
    y2 = _guide(y, y, r, eps)
    y2 = y2 + (y - y2) * (p["details"] / 100) * 0.6
    rc = max(1, round(2 + 8 * p["couleur"] / 100))
    k = p["couleur"] / 100
    cb2 = cb + (_guide(y, cb, rc, 0.01) - cb) * k
    cr2 = cr + (_guide(y, cr, rc, 0.01) - cr) * k
    g = (y2 - 0.299 * (cr2 + y2) - 0.114 * (cb2 + y2)) / 0.587
    rgb = np.stack([cr2 + y2, g, cb2 + y2], axis=-1)
    out = t.copy()
    out[..., :3] = _fin(rgb * 255, t)
    return out


def nettete(t: np.ndarray, p: dict) -> np.ndarray:
    if t.dtype.kind == "f":                 # 16 bits : masque flou (comme UnsharpMask de Pillow), sans arrondi
        f = t[..., :3].astype(np.float32)
        ecart = f - _flou_pil(f, float(p["rayon"]))
        ecart = np.where(np.abs(ecart) >= int(p["seuil"]), ecart, 0)
        out = t.copy()
        out[..., :3] = _fin(f + ecart * int(p["quantite"]) / 100, t)
        return out
    im = Image.fromarray(np.ascontiguousarray(t[..., :3]), "RGB").filter(
        ImageFilter.UnsharpMask(radius=float(p["rayon"]), percent=int(p["quantite"]), threshold=int(p["seuil"])))
    out = t.copy()
    out[..., :3] = np.asarray(im)
    return out


def vignette(t: np.ndarray, p: dict) -> np.ndarray:
    h, w = t.shape[:2]
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (x + 0.5) / w * 2 - 1, (y + 0.5) / h * 2 - 1
    rond = p["rond"] / 100
    if rond < 1:            # forme : du rectangle (suit le cadre) au cercle
        e = 2 + 10 * (1 - rond) ** 2
        d = (np.abs(nx) ** e + np.abs(ny) ** e) ** (1 / e)
    else:
        d = np.hypot(nx, ny) / math.sqrt(2) * 1.25
    centre = 0.2 + 0.8 * p["taille"] / 100
    douceur = 0.05 + 0.95 * p["douceur"] / 100
    v = np.clip((d - centre * (1 - douceur * 0.5)) / (douceur * 0.9 + 1e-3), 0, 1)
    v = v * v * (3 - 2 * v)                                 # transition douce
    force = p["force"] / 100
    f = t[..., :3].astype(np.float32)
    if force < 0:
        f = f * (1 + force * v)[..., None]
    else:
        f = f + (255 - f) * (force * v)[..., None]
    out = t.copy()
    out[..., :3] = _fin(f, t)
    return out


def _bilineaire(c: np.ndarray, sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
    """Valeurs de c (h, w[, n]) lues aux points (sx, sy), entre les pixels ; bords prolongés."""
    h, w = c.shape[:2]
    sx = np.clip(sx, 0, w - 1)
    sy = np.clip(sy, 0, h - 1)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1, y1 = np.minimum(x0 + 1, w - 1), np.minimum(y0 + 1, h - 1)
    fx, fy = sx - x0, sy - y0
    if c.ndim == 3:
        fx, fy = fx[..., None], fy[..., None]
    c = c.astype(np.float32)
    haut = c[y0, x0] * (1 - fx) + c[y0, x1] * fx
    bas = c[y1, x0] * (1 - fx) + c[y1, x1] * fx
    return haut * (1 - fy) + bas * fy


def correction_objectif(t: np.ndarray, p: dict) -> np.ndarray:
    """Filtre > Correction de l'objectif : déformation en tonneau ou en coussin (l'image est agrandie juste assez
    pour qu'aucun coin ne reste vide), vignetage (coins sombres), franges de couleur (rouge / cyan) sur les bords.
    Coordonnées relatives à la diagonale : même résultat sur l'aperçu réduit et sur la vraie image."""
    h, w = t.shape[:2]
    k = -p["deformation"] / 100 * 0.35                     # + corrige un tonneau : les bords sont rapprochés
    vig = p["vignetage"] / 100
    fr = p["franges"] / 100 * 0.006
    cx, cy, demi = (w - 1) / 2, (h - 1) / 2, math.hypot(w, h) / 2
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = (x - cx) / demi, (y - cy) / demi
    r2 = nx * nx + ny * ny
    echelle = 1.0
    if k:
        # zoom pour ne rien laisser de vide : le bord de l'image doit lire des pixels de l'image
        bx = np.concatenate([np.linspace(-cx, cx, 64), np.full(64, cx), np.linspace(-cx, cx, 64), np.full(64, -cx)])
        by = np.concatenate([np.full(64, -cy), np.linspace(-cy, cy, 64), np.full(64, cy), np.linspace(-cy, cy, 64)])
        bx, by = bx / demi, by / demi
        for _ in range(4):
            ux, uy = bx * echelle, by * echelle
            f = 1 + k * (ux * ux + uy * uy)
            m = max(np.abs(ux * f).max() * demi / max(cx, 1), np.abs(uy * f).max() * demi / max(cy, 1))
            echelle = echelle / m if m > 1 else echelle
            if m <= 1.0001:
                break
    ux, uy = nx * echelle, ny * echelle
    f = 1 + k * (ux * ux + uy * uy)
    out = t.copy()
    a = t.astype(np.float32)
    if k or fr:
        canaux = []
        for i, d in ((0, fr), (1, 0.0), (2, -fr)):            # rouge et bleu un peu plus ou moins écartés
            g = f * (1 + d)
            canaux.append(_bilineaire(a[..., i], cx + ux * g * demi, cy + uy * g * demi))
        alpha = _bilineaire(a[..., 3], cx + ux * f * demi, cy + uy * f * demi)
        rgb = np.stack(canaux, -1)
    else:
        rgb, alpha = a[..., :3], a[..., 3]
    if vig:
        g = 1 + vig * np.clip(r2, 0, 1) * 1.2
        rgb = rgb * g[..., None] if vig > 0 else rgb * np.maximum(g, 0)[..., None]
    out[..., :3] = _fin(rgb, t)
    out[..., 3] = _fin(alpha, t)
    return out


# ------------------------------------------------------------------ teinte d'une photo (restauration IA)
def _ycbcr(rgb: np.ndarray):
    f = rgb[..., :3].astype(np.float32)
    y = 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]
    return y, 0.564 * (f[..., 2] - y), 0.713 * (f[..., 0] - y)


def garder_teinte(original: np.ndarray, resultat: np.ndarray) -> np.ndarray:
    """Lumière et détails du résultat, teinte de l'original (adoucie pour ne pas reprendre les taches) :
    une restauration ne peut pas coloriser. Tableaux RGBA de même taille ; l'alpha du résultat est gardé."""
    y, _, _ = _ycbcr(resultat)
    _, cb, cr = _ycbcr(original)
    sigma = max(2.0, max(original.shape[:2]) / 250)
    cb, cr = _flou_pil(cb, sigma), _flou_pil(cr, sigma)
    r = y + cr / 0.713
    b = y + cb / 0.564
    g = (y - 0.299 * r - 0.114 * b) / 0.587
    out = resultat.copy()
    for i, c in enumerate((r, g, b)):
        out[..., i] = np.clip(np.round(c), 0, 255).astype(np.uint8)
    return out


FONCTIONS = {"flou": flou_gaussien, "mouvement": flou_mouvement, "radial": flou_radial, "objectif": flou_objectif,
             "surface": flou_surface, "bruit": reduire_bruit, "nettete": nettete,
             "vignette": vignette, "correction": correction_objectif}


def appliquer_calque(img: QImage, calcul, selection: QImage | None, seize: str | None = None) -> QImage:
    """calcul : tableau RGBA -> tableau RGBA. Résultat posé dans la sélection (avec ses bords doux) s'il y en a une.
    Calque 16 bits : seize = « entier » (calcul reçoit du uint16, ex. les réglages), « flottant » (float32 sur
    l'échelle 0..255, ex. les filtres) ; None : calcul en 8 bits (pont, voir profondeur.py).
    Calque 32 bits : « entier » -> float32 sur l'échelle 0..1 (ajustements.appliquer_rgba en 32 bits),
    « flottant » -> float32 sur l'échelle 0..255 ; les valeurs peuvent dépasser le blanc."""
    from .document import FORMAT_CALQUE, FORMAT_IMAGE, masque, qimage_rgba, tableau
    from .profondeur import est_16, est_32, qimage16, qimage32, tab16, tab32
    if seize and est_32(img):
        t = tab32(img)
        echelle = 1.0 if seize == "entier" else 255.0
        res = np.asarray(calcul(t * echelle if echelle != 1 else t), np.float32) / echelle
        if selection is not None:
            m = masque(selection)
            if m.any():
                w = m.astype(np.float32)[..., None] / 255
                res = t + (res - t) * w
        res = np.maximum(res, 0)
        res[..., 3] = np.clip(res[..., 3], 0, 1)
        return qimage32(res)
    if seize and est_16(img):
        t = tab16(img)
        res = np.asarray(calcul(t if seize == "entier" else t.astype(np.float32) / 257))
        res = res.astype(np.float32) * (1 if res.dtype == np.uint16 else 257)
        if selection is not None:
            m = masque(selection)
            if m.any():
                w = m.astype(np.float32)[..., None] / 255
                res = t + (res - t) * w
        return qimage16(np.clip(np.round(res), 0, 65535).astype(np.uint16))
    t = tableau(img.convertToFormat(FORMAT_IMAGE))
    res = calcul(t)
    if selection is not None:
        m = masque(selection)
        if m.any():
            w = m.astype(np.float32)[..., None] / 255
            res = np.clip(np.round(t + (res.astype(np.float32) - t) * w), 0, 255).astype(np.uint8)
    return qimage_rgba(res).convertToFormat(FORMAT_CALQUE)
