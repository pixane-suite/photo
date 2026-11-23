"""Outil Yeux rouges : la pupille rougie par le flash redevient sombre (sans IA, immédiat).

Dans le cadre (ou autour du clic) : les pixels nettement rouges (rouge bien plus fort que le vert et le bleu) ; on
garde la tache d'un seul tenant la plus proche du centre, ses petits trous bouchés (le reflet blanc du flash reste
tel quel : il n'est pas rouge). Le rouge y est remplacé par la moyenne du vert et du bleu, assombrie ; le bord est
adouci pour ne pas laisser de cerne.
"""
from __future__ import annotations

import numpy as np

from .selection_auto import boucher_trous, etiquettes

SEUIL = 1.45          # rouge / moyenne(vert, bleu) au-delà duquel un pixel est « rouge yeux »
ASSOMBRIR = 0.75      # la pupille corrigée garde 75 % de la clarté du vert et du bleu


def rougeur(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., k].astype(np.float32) for k in range(3))
    return r / ((g + b) / 2 + 12.0)


def _flou(a: np.ndarray, n: int = 1) -> np.ndarray:
    for _ in range(n):
        p = np.pad(a, 1, mode="edge")
        a = (p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:] + p[1:-1, :-2] + p[1:-1, 1:-1] + p[1:-1, 2:] + p[2:, :-2]
             + p[2:, 1:-1] + p[2:, 2:]) / 9.0
    return a


def zone_rouge(rgb: np.ndarray, centre: tuple[int, int] | None = None) -> np.ndarray:
    """Masque (bool) de la pupille rouge dans ce morceau d'image ; vide s'il n'y a pas de rouge yeux."""
    h, w = rgb.shape[:2]
    m = (rougeur(rgb) > SEUIL) & (rgb[..., 0] > 50)
    if not m.any():
        return m
    num, tailles = etiquettes(m)
    if len(tailles) == 0:
        return np.zeros_like(m)
    cx, cy = centre if centre is not None else (w // 2, h // 2)
    yy, xx = np.mgrid[0:h, 0:w]
    meilleur, score = -1, None
    for k, t in enumerate(tailles):
        if t < 4:
            continue
        sel = num == k
        d = np.hypot(xx[sel] - cx, yy[sel] - cy).min()
        s = d - np.sqrt(t) * 0.5              # proche du centre, et pas une miette
        if score is None or s < score:
            meilleur, score = k, s
    if meilleur < 0:
        return np.zeros_like(m)
    return boucher_trous(num == meilleur)


def corriger(rgba: np.ndarray, x0: int, y0: int, x1: int, y1: int,
             centre: tuple[int, int] | None = None) -> tuple[np.ndarray, int]:
    """Corrige la pupille trouvée dans le rectangle (x0, y0, x1, y1) ; rend (image corrigée, pixels changés)."""
    H, W = rgba.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return rgba, 0
    morceau = rgba[y0:y1, x0:x1]
    c = None if centre is None else (centre[0] - x0, centre[1] - y0)
    m = zone_rouge(morceau[..., :3], c)
    n = int(m.sum())
    if n == 0:
        return rgba, 0
    # bord adouci : la zone un peu grossie puis floutée ; dans le cœur, correction pleine
    poids = np.clip(_flou(_flou(m.astype(np.float32)) > 0.05, 1).astype(np.float32) * 1.0, 0, 1)
    poids = np.maximum(poids, m.astype(np.float32))
    # seuls les pixels encore rougeâtres changent vraiment (le reflet blanc et l'iris restent)
    r = rougeur(morceau[..., :3])
    poids *= np.clip((r - 1.05) / 0.4, 0, 1)
    f = morceau[..., :3].astype(np.float32)
    gb = (f[..., 1] + f[..., 2]) / 2 * ASSOMBRIR
    sombre = np.stack([gb, f[..., 1] * ASSOMBRIR, f[..., 2] * ASSOMBRIR], -1)
    nouveau = f + (sombre - f) * poids[..., None]
    sortie = rgba.copy()
    sortie[y0:y1, x0:x1, :3] = np.clip(nouveau + 0.5, 0, 255).astype(np.uint8)
    return sortie, n
