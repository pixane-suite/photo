"""Analyse de la zone à effacer, avant Effacer (IA) : ce qui empêcherait un effacement propre.

- Ombre : une zone plus sombre que le fond tout autour, de même teinte (une ombre assombrit sans changer la couleur),
  collée à la zone peinte. L'IA l'effacerait mal : elle laisserait une tache sombre sans objet.
- Bord oublié : les pixels juste autour de la zone peinte ressemblent encore à l'objet (ils diffèrent nettement du
  fond un peu plus loin) : l'objet n'est pas entièrement couvert, l'IA le redessinerait.

Calcul sur une copie réduite (au plus 700 px) autour de la zone : quelques dixièmes de seconde."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .selection_auto import etiquettes
from .styles import dilater, flou

TAILLE_CALCUL = 700


@dataclass
class Analyse:
    ombre: np.ndarray | None = None     # (h, w) bool, pleine taille : l'ombre trouvée (hors de la zone peinte)
    elargir: int = 0                    # px (pleine taille) à ajouter autour de la zone pour couvrir le bord oublié
    part_ombre: float = 0.0             # surface de l'ombre / surface de la zone peinte

    def vide(self) -> bool:
        return self.ombre is None and self.elargir == 0


def _reduire(a: np.ndarray, k: int) -> np.ndarray:
    if k == 1:
        return a.astype(np.float32)
    h, w = a.shape[:2]
    h2, w2 = h // k, w // k
    a = a[:h2 * k, :w2 * k].astype(np.float32)
    return a.reshape(h2, k, w2, k, *a.shape[2:]).mean(axis=(1, 3))


def _grossir(m: np.ndarray) -> np.ndarray:
    """Zone (bool) agrandie d'exactement 1 px (8 voisins)."""
    r = m.copy()
    r[1:] |= m[:-1]
    r[:-1] |= m[1:]
    r[:, 1:] |= r[:, :-1].copy()
    r[:, :-1] |= r[:, 1:].copy()
    return r


def _fond_local(rgb: np.ndarray, poids: np.ndarray, sigma: float) -> np.ndarray:
    """Couleur moyenne du fond autour de chaque pixel, calculée seulement sur les pixels de poids 1."""
    p = flou(poids, sigma)
    res = np.empty_like(rgb)
    for c in range(3):
        res[..., c] = flou(rgb[..., c] * poids, sigma) / np.maximum(p, 1e-4)
    return res


def analyser(rgb: np.ndarray, masque: np.ndarray) -> Analyse:
    """rgb (H, W, 3) uint8, masque (H, W) bool (zone peinte) -> ce qui gênerait l'effacement."""
    H, W = masque.shape
    ys, xs = np.nonzero(masque)
    if len(ys) < 20:
        return Analyse()
    taille = math.sqrt(len(ys))
    marge = int(max(20, taille * 1.5))
    y0, y1 = max(0, ys.min() - marge), min(H, ys.max() + 1 + marge)
    x0, x1 = max(0, xs.min() - marge), min(W, xs.max() + 1 + marge)
    k = max(1, int(math.ceil(max(y1 - y0, x1 - x0) / TAILLE_CALCUL)))
    img = _reduire(rgb[y0:y1, x0:x1], k)
    m = _reduire(masque[y0:y1, x0:x1].astype(np.float32), k) > 0.3
    if m.sum() < 10:
        return Analyse()
    t = taille / k                                       # taille de la zone, en px réduits
    res = Analyse()

    # ---- bord oublié : autour de la zone, des pixels qui ressemblent à l'objet (l'intérieur de la zone, près du
    # bord) plus qu'au fond (un peu plus loin), anneau par anneau de 1 px
    zone = m.astype(np.float32)
    interieur = m & ~(dilater(1 - zone, 3.0) > 0.5)                  # 3 px à l'intérieur du bord
    interieur = m & ~interieur if interieur.any() else m
    loin = (dilater(zone, max(14.0, t * 0.3)) > 0.5) & ~(dilater(zone, max(10.0, t * 0.2)) > 0.5)
    sig = max(3.0, t * 0.15)
    objet = _fond_local(img, interieur.astype(np.float32), sig)
    fond = _fond_local(img, loin.astype(np.float32), sig)
    d_objet = np.linalg.norm(img - objet, axis=2)
    d_fond = np.linalg.norm(img - fond, axis=2)
    ecart = np.linalg.norm(objet - fond, axis=2)
    comme_objet = (d_objet < d_fond) & (ecart > 30)                  # objet et fond bien distincts à cet endroit
    prec = m
    oublie = 0
    mince = int(max(3, min(12, t * 0.12)))                           # un bord oublié est mince
    fini = False
    for e in range(1, mince + 2):                                    # anneaux d'exactement 1 px (réduits)
        d = _grossir(prec)
        anneau = d & ~prec
        prec = d
        if not anneau.any():
            break
        part = float(comme_objet[anneau].mean())
        if part < 0.15:                                              # le fond revient tout autour : bord fini
            fini = True
            break
        if part < 0.35 and e == 1:                                   # trop peu de bord ressemble à l'objet
            break
        oublie = e
        m_couvert = d
    if not fini or oublie > mince:                                   # l'objet continue (zone qui le coupe) :
        oublie = 0                                                   # ce n'est pas un bord oublié
    if oublie:
        res.elargir = int(math.ceil(oublie * k)) + 2                 # + 2 px de sécurité
        m = _grossir(m_couvert)
        zone = m.astype(np.float32)

    # ---- ombre : plus sombre que le fond local, même teinte, collée à la zone
    proche = (dilater(zone, max(8.0, t * 0.9)) > 0.5) & ~m
    tres_loin = (dilater(zone, max(16.0, t * 1.4)) > 0.5) & ~(dilater(zone, max(12.0, t * 1.0)) > 0.5)
    if proche.any() and tres_loin.any():
        ref = _fond_local(img, tres_loin.astype(np.float32), max(6.0, t * 0.5))
        lum = img.sum(axis=2) + 1.0
        lum_ref = ref.sum(axis=2) + 1.0
        rapport = lum / lum_ref
        teinte = np.abs(img / lum[..., None] - ref / lum_ref[..., None]).sum(axis=2)
        candidat = proche & (rapport < 0.82) & (rapport > 0.15) & (teinte < 0.09)
        if candidat.any():
            lab, tailles = etiquettes(candidat)
            colle = (dilater(zone, 3.0) > 0.5) & candidat
            gardes = np.unique(lab[colle])
            gardes = gardes[gardes >= 0]
            ombre = np.isin(lab, gardes) if len(gardes) else np.zeros_like(candidat)
            part = float(ombre.sum()) / float(m.sum())
            # une vraie ombre : pas démesurée, lisse (pas plus de texture que le fond), plutôt d'un côté de l'objet
            lisse = decalee = False
            if 0.04 < part < 1.2:
                gris = img.mean(axis=2)
                texture = np.abs(np.diff(gris, axis=0))[:, :-1] + np.abs(np.diff(gris, axis=1))[:-1, :]
                o2, f2 = ombre[:-1, :-1], tres_loin[:-1, :-1]
                if o2.any() and f2.any():
                    t_ombre = float(np.median(texture[o2]) / max(1.0, float(np.median(lum[:-1, :-1][o2]) / 3)))
                    t_fond = float(np.median(texture[f2]) / max(1.0, float(np.median(lum[:-1, :-1][f2]) / 3)))
                    lisse = t_ombre <= t_fond * 1.3 + 0.01
                oy, ox = np.nonzero(ombre)
                my, mx = np.nonzero(m)
                decalee = math.hypot(oy.mean() - my.mean(), ox.mean() - mx.mean()) > t * 0.25
            if 0.04 < part < 1.2 and lisse and decalee:
                # bords adoucis puis remis à la taille de la photo
                o = dilater(ombre.astype(np.float32), 1.5) > 0.5
                pleine = np.zeros((H, W), bool)
                grand = np.repeat(np.repeat(o, k, axis=0), k, axis=1)
                hh, ww = min(grand.shape[0], y1 - y0), min(grand.shape[1], x1 - x0)
                pleine[y0:y0 + hh, x0:x0 + ww] = grand[:hh, :ww]
                pleine &= ~masque
                res.ombre = pleine
                res.part_ombre = part
    return res
