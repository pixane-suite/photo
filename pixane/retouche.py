"""Retouche à la main sur un calque : pinceau de couleur, tampon (copier une zone sur une autre) et pinceaux de
retouche comme Photoshop : Densité − (éclaircir), Densité + (assombrir), Éponge (saturer / désaturer), Goutte d'eau
(flouter), Netteté, Doigt (étaler la couleur), Historique (repeindre l'état d'avant : un « tampon » sans décalage).

Un coup de pinceau est d'abord dessiné dans un « trait » (masque gris de la taille du calque : blanc = touché), puis
posé sur l'image
d'origine du calque avec l'opacité choisie : repasser au même endroit pendant un même coup ne fonce pas la couleur
(comme Photoshop). Seule la partie touchée est recalculée à chaque mouvement.

Le coup se fait dans la profondeur du calque (8, 16 ou 32 bits, voir profondeur.py) : en 16 bits sans arrondi à
256 nuances, en 32 bits en gardant les couleurs plus claires que le blanc (le tampon les recopie).
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QRadialGradient

from .pointe import Placement, Pointe, Reglages, dessiner, texture_grise, texture_zone

PEINTURE, TAMPON, GOMME = "peinture", "tampon", "gomme"
ECLAIRCIR, ASSOMBRIR, EPONGE, GOUTTE, NETTETE, DOIGT = ("eclaircir", "assombrir", "eponge", "goutte", "nettete",
                                                       "doigt")
MELANGEUR = "melangeur"         # pinceau mélangeur : la couleur du pinceau se mélange à celle de la toile
FILTRES_PINCEAU = (ECLAIRCIR, ASSOMBRIR, EPONGE, GOUTTE, NETTETE)    # calculés d'après l'image d'avant le coup
GAMMES = ("ombres", "moyens", "lumieres")
_LUM_BVR = np.array([0.114, 0.587, 0.299], np.float32)               # pixels Qt : ordre B, V, R


def _vue(img: QImage, zone: QRect) -> np.ndarray:
    """Pixels (h, w, 4) float32 d'une zone d'une image prémultipliée (ordre B, V, R, A) : 0..1, au-delà de 1 en
    32 bits. ARGB32 (8 bits), RGBA64 (16 bits) ou RGBA32FPx4 (32 bits)."""
    from .profondeur import bits, tab32
    c = img.copy(zone)
    if bits(c) > 8:
        return np.ascontiguousarray(tab32(c, premul=True)[..., [2, 1, 0, 3]])
    c = c.convertToFormat(QImage.Format_ARGB32_Premultiplied)
    h, w, ligne = c.height(), c.width(), c.bytesPerLine()
    brut = np.frombuffer(c.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)
    return brut[:, : w * 4].reshape(h, w, 4).astype(np.float32) / 255


def _qimage(a: np.ndarray, b: int = 8) -> QImage:
    """Pixels (h, w, 4) float32 B, V, R, A prémultipliés -> QImage de profondeur b (8, 16, 32)."""
    if b > 8:
        from .profondeur import en_bits, qimage32
        t = a[..., [2, 1, 0, 3]].astype(np.float32)
        t[..., 3] = np.clip(t[..., 3], 0, 1)
        t[..., :3] = np.maximum(t[..., :3], 0) if b == 32 else np.clip(t[..., :3], 0, 1)
        return en_bits(qimage32(t, premul=True), b)
    a = np.ascontiguousarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    h, w = a.shape[:2]
    return QImage(a.data, w, h, 4 * w, QImage.Format_ARGB32_Premultiplied).copy()


class Trait:
    """Un coup de pinceau ou de tampon sur l'image d'un calque (8, 16 ou 32 bits : le coup garde sa profondeur)."""

    def __init__(self, mode: str, base: QImage, taille: float, durete: float, opacite: float,
                 couleur: QColor | None = None, source: QImage | None = None, decalage: QPointF | None = None,
                 pointe: Pointe | None = None, reglages: Reglages | None = None, fond: QColor | None = None,
                 texture: np.ndarray | None = None, double: Pointe | None = None, graine: int | None = None,
                 origine: QPoint | None = None, gamme: str = "moyens", saturer: bool = False):
        """pointe : forme du pinceau (None : rond, réglé par durete). reglages : espacement, dispersion, texture…
        (voir pointe.Reglages). texture : motif (h, w, 4) ; double : deuxième forme. mode GOMME : efface.
        origine : place de `base` dans l'image (trait dessiné seul dans son rectangle : la texture reste alignée)."""
        self.origine = QPoint(origine) if origine is not None else QPoint(0, 0)
        self.gamme = gamme if gamme in GAMMES else "moyens"   # Densité − / + : tons touchés
        self.saturer = bool(saturer)            # Éponge : saturer (sinon désaturer)
        self._flou = None                       # Goutte d'eau, Netteté : image floutée (calculée au premier besoin)
        self._tampon_doigt = None               # Doigt : couleur « emportée » par le doigt
        self._differer = False                  # tracer() : composer une seule fois, à la fin
        self.miroirs = []                       # symétrie : fonctions point -> point reflété (chaque touche est
        #                                         aussi posée à ces endroits)
        self.net = False                        # crayon : bord net, sans lissage (pixel par pixel)
        self.melange = 0.5                      # pinceau mélangeur : part de la toile reprise à chaque touche
        self.mode = mode
        from .profondeur import bits, format_de
        self._b = bits(base)                    # profondeur du calque : le coup se fait dans la même
        base = base if base.format() == format_de(base) else base.convertToFormat(format_de(base))
        self.base = base                        # image du calque avant le coup (jamais modifiée)
        self.image = base.copy()                # résultat en cours
        self.taille = max(1.0, float(taille))
        self.durete = max(0.0, min(1.0, durete))
        self.opacite = max(0.0, min(1.0, opacite))
        self.couleur = QColor(couleur) if couleur is not None else QColor(0, 0, 0)
        self.source = source                    # tampon : image où l'on copie (photo visible au début du coup)
        self.decalage = decalage or QPointF()   # tampon : source = point peint + décalage
        self.masque = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
        self.masque.fill(QColor(0, 0, 0))     # opaque : en mode « Éclaircir », le plus clair gagne (maximum)
        self._dernier: QPointF | None = None
        self._reste = 0.0                       # distance déjà parcourue depuis la dernière touche
        self.formes = pointe is not None or reglages is not None or mode == GOMME   # sinon : rond d'avant
        if self.formes:                         # moteur à formes : touches tamponnées dans une couche
            self.reglages = reglages or Reglages()
            self.pointe = pointe or Pointe([_rond(self.durete)], 0.08)
            self.couche = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
            self.couche.fill(Qt.transparent)
            self.placement = Placement(self.pointe, self.reglages, self.taille, self.couleur, fond, graine)
            self.texture = (texture_grise(texture, self.reglages.texture_echelle)
                            if texture is not None and self.reglages.texture else None)
            self.double = None
            if double is not None and self.reglages.double:
                self.double = QImage(base.size(), QImage.Format_ARGB32_Premultiplied)
                self.double.fill(Qt.transparent)
                r2 = Reglages(espacement=self.reglages.double_espacement, dispersion=self.reglages.double_dispersion,
                              deux_axes=True, pression_taille=False)
                self.placement_double = Placement(double, r2, self.taille * self.reglages.double_taille,
                                                  QColor(255, 255, 255), graine=None if graine is None else graine + 1)

    # ------------------------------------------------------------------ dessin du masque
    def _touche(self, p: QPainter, c: QPointF):
        r = self.taille / 2
        if self.net:                                # crayon : pixels entiers, sans lissage
            p.setBrush(QColor(255, 255, 255))
            n = max(1, int(round(self.taille)))
            x0, y0 = int(math.floor(c.x() - n / 2 + 0.5)), int(math.floor(c.y() - n / 2 + 0.5))
            if n <= 2:
                p.fillRect(QRect(x0, y0, n, n), QColor(255, 255, 255))
            else:
                p.drawEllipse(QRect(x0, y0, n, n))
            return
        if self.durete >= 0.99:
            p.setBrush(QColor(255, 255, 255))
        else:
            g = QRadialGradient(c, r)
            g.setColorAt(0, QColor(255, 255, 255))
            g.setColorAt(self.durete, QColor(255, 255, 255))
            g.setColorAt(1, QColor(0, 0, 0))
            p.setBrush(g)
        p.drawEllipse(c, r, r)

    def ajouter(self, pt: QPointF, pression: float = 1.0) -> QRect:
        """Prolonge le coup jusqu'au point ; renvoie la zone de l'image modifiée. pression : tablette (0..1)."""
        if self.mode in (DOIGT, MELANGEUR):
            zone = self._ajouter_doigt(pt)
            if self.miroirs:                        # chaque reflet garde sa propre « charge » de couleur
                principal = (self._dernier, self._reste, self._tampon_doigt)
                etats = self.__dict__.setdefault("_etats_miroirs", {})
                for k, m in enumerate(self.miroirs):
                    self._dernier, self._reste, self._tampon_doigt = etats.get(k, (None, 0.0, None))
                    zone = zone.united(self._ajouter_doigt(m(pt)))
                    etats[k] = (self._dernier, self._reste, self._tampon_doigt)
                self._dernier, self._reste, self._tampon_doigt = principal
            return zone
        if self.formes:
            return self._ajouter_formes(pt, pression)
        p = QPainter(self.masque)
        p.setRenderHint(QPainter.Antialiasing, not self.net)
        p.setPen(Qt.NoPen)
        p.setCompositionMode(QPainter.CompositionMode_Lighten)     # le plus opaque gagne (pas d'accumulation)
        pas = max(1.0, self.taille * 0.08) if not self.net else max(0.5, self.taille * 0.25)
        zone = QRectF(pt, pt)
        centres = []
        if self._dernier is None:
            centres.append(pt)
        else:
            a = self._dernier
            d = math.hypot(pt.x() - a.x(), pt.y() - a.y())
            t = pas - self._reste
            while t <= d:
                centres.append(a + (pt - a) * (t / d))
                t += pas
            self._reste = d - (t - pas)
            zone = QRectF(a, pt).normalized()
        for c in centres:
            self._touche(p, c)
            for m in self.miroirs:
                self._touche(p, m(c))
        p.end()
        self._dernier = pt
        r = self.taille / 2 + 2
        zones = [zone] + [QRectF(m(zone.topLeft()), m(zone.bottomRight())).normalized() for m in self.miroirs]
        rect = QRect()
        for z in zones:
            z = z.adjusted(-r, -r, r, r).toAlignedRect().intersected(self.image.rect())
            if not z.isEmpty():
                if not self._differer:
                    self._composer(z)
                rect = rect.united(z)
        return rect

    def tracer(self, points) -> None:
        """Tout un trait d'un coup (points : [(QPointF, pression)]) : même résultat que des ajouter() successifs,
        mais l'image n'est composée qu'une fois (calque de pinceau redessiné)."""
        self._differer = True
        try:
            for pt, pression in points:
                self.ajouter(pt, pression)
        finally:
            self._differer = False
        tout = self.image.rect()
        if self.formes:
            self._composer_formes(tout)
        else:
            self._composer(tout)

    # ------------------------------------------------------------------ moteur à formes
    def _ajouter_formes(self, pt: QPointF, pression: float) -> QRect:
        touches = self.placement.ajouter(pt, pression)
        if touches and self.miroirs:                # symétrie : chaque touche aussi à ses reflets
            from dataclasses import replace
            reflets = []
            for t in touches:
                for m in self.miroirs:
                    q = m(QPointF(t.x, t.y))
                    retourne = (q.x() != t.x) != (q.y() != t.y)      # un seul axe : la forme est retournée
                    reflets.append(replace(t, x=q.x(), y=q.y(), angle=(-t.angle if retourne else t.angle + 180)))
            touches = list(touches) + reflets
        zone = QRectF()
        if touches:
            p = QPainter(self.couche)
            p.setRenderHint(QPainter.Antialiasing)
            couleur = self.mode == PEINTURE
            for t in touches:
                if self.reglages.pression_opacite:            # pression -> opacité : portée par la touche
                    t.flux *= max(0.0, min(1.0, pression))
                if self.reglages.var_opacite:
                    t.flux *= 1 - self.placement.hasard.random() * self.reglages.var_opacite
                zone = zone.united(dessiner(p, self.pointe, t, couleur))
            p.end()
        if self.double is not None:
            p = QPainter(self.double)
            p.setRenderHint(QPainter.Antialiasing)
            for t in self.placement_double.ajouter(pt, pression):
                zone = zone.united(dessiner(p, self.placement_double.pointe, t, False))
            p.end()
        zone = zone.toAlignedRect().intersected(self.image.rect())
        if not zone.isEmpty() and not self._differer:
            if self.miroirs and touches:
                r = int(max(t.taille for t in touches)) + 4
                morceaux = [QRect(int(t.x) - r, int(t.y) - r, 2 * r, 2 * r).intersected(self.image.rect())
                            for t in touches]
                for z in _regrouper(morceaux):
                    self._composer_formes(z)
            else:
                self._composer_formes(zone)
        return zone

    def _composer_formes(self, zone: QRect):
        couche = _vue(self.couche, zone)
        a = couche[..., 3]
        facteur = np.ones_like(a)
        if self.texture is not None:
            tex = texture_zone(self.texture, zone.x() + self.origine.x(), zone.y() + self.origine.y(),
                               zone.width(), zone.height())
            if self.reglages.texture_inverser:
                tex = 1 - tex
            facteur *= 1 - self.reglages.texture_force * (1 - tex)
        if self.double is not None:
            facteur *= _vue(self.double, zone)[..., 3]
        base = _vue(self.base, zone)
        k = (facteur * self.opacite)[..., None]
        if self.mode == GOMME:
            res = base * (1 - a[..., None] * k)
        elif self.mode == PEINTURE:
            res = couche * k + base * (1 - a[..., None] * k)
        else:                                                   # tampon : la source à travers la couche
            src = QImage(zone.size(), self.image.format())
            src.fill(Qt.transparent)
            pp = QPainter(src)
            pp.drawImage(QPointF(-zone.x(), -zone.y()) - self.decalage, self.source)
            pp.end()
            s = _vue(src, QRect(0, 0, zone.width(), zone.height()))
            m = a[..., None] * k
            res = s * m + base * (1 - m)
        p = QPainter(self.image)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(zone.topLeft(), _qimage(res, self._b))
        p.end()

    # ------------------------------------------------------------------ Doigt
    def _pastille(self) -> np.ndarray:
        """Forme du doigt (2r+1)² : 1 au centre, bord adouci selon la dureté."""
        r = max(1, int(round(self.taille / 2)))
        y, x = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float32)
        d = np.sqrt(x * x + y * y) / r
        dur = min(0.98, self.durete)
        return np.clip((1 - d) / max(1e-3, 1 - dur), 0, 1)

    def _ajouter_doigt(self, pt: QPointF) -> QRect:
        """Comme le doigt de Photoshop : à chaque touche, la couleur emportée (mélange de ce qui a été touché avant)
        est étalée sous le doigt, puis se mélange à ce qui s'y trouve. Force = l'opacité de la barre."""
        r = max(1, int(round(self.taille / 2)))
        forme = self._pastille()[..., None]
        pas = max(1.0, self.taille * 0.12)
        points = [pt]
        if self._dernier is not None:
            a = self._dernier
            d = math.hypot(pt.x() - a.x(), pt.y() - a.y())
            points, t = [], pas - self._reste
            while t <= d:
                points.append(a + (pt - a) * (t / d))
                t += pas
            self._reste = d - (t - pas)
        self._dernier = pt
        zone = QRect()
        force = self.opacite
        melangeur = self.mode == MELANGEUR
        if melangeur:                                  # couleur du pinceau, prémultipliée, dans l'ordre B, V, R, A
            c0, al = self.couleur, self.couleur.alphaF()
            peinture = np.array([c0.blueF() * al, c0.greenF() * al, c0.redF() * al, al], np.float32)
        for c in points:
            rect = QRect(int(round(c.x())) - r, int(round(c.y())) - r, 2 * r + 1, 2 * r + 1)
            dessous = _vue(self.image, rect)               # hors de l'image : transparent
            if melangeur:
                if self._tampon_doigt is None:             # le pinceau arrive chargé de sa couleur
                    self._tampon_doigt = np.broadcast_to(peinture, dessous.shape).copy()
                # la charge se mêle à la toile : « mélange » = part de la toile reprise ; la charge s'épuise
                charge = self._tampon_doigt * (1 - self.melange) + dessous * self.melange
                nouveau = dessous + (charge - dessous) * forme * force
                self._tampon_doigt = charge * 0.92 + peinture * 0.08      # un peu de couleur fraîche à chaque pas
            elif self._tampon_doigt is None:
                self._tampon_doigt = dessous
                continue
            else:
                nouveau = dessous + (self._tampon_doigt - dessous) * forme * force
                self._tampon_doigt = self._tampon_doigt * force + nouveau * (1 - force)
            p = QPainter(self.image)
            p.setCompositionMode(QPainter.CompositionMode_Source)
            p.drawImage(rect.topLeft(), _qimage(nouveau, self._b))
            p.end()
            zone = zone.united(rect)
        return zone.intersected(self.image.rect())

    # ------------------------------------------------------------------ Densité, Éponge, Goutte d'eau, Netteté
    def _flou_zone(self, zone: QRect) -> np.ndarray:
        if self._flou is None and self._b > 8:          # 16 / 32 bits : flou en flottant (prémultiplié)
            from .filtres import flou_flottant
            self._flou = flou_flottant(_vue(self.base, self.base.rect()), max(1.0, self.taille / 14)).astype(np.float32)
        if self._flou is not None and self._flou.dtype == np.float32:
            x, y, w, h = zone.x(), zone.y(), zone.width(), zone.height()
            return self._flou[y:y + h, x:x + w]
        if self._flou is None:                          # une fois par coup : flou de tout le calque d'avant
            from PIL import Image, ImageFilter
            b = self.base
            h, w, ligne = b.height(), b.width(), b.bytesPerLine()
            brut = np.frombuffer(b.constBits(), np.uint8, count=h * ligne).reshape(h, ligne)[:, :w * 4]
            im = Image.frombuffer("RGBA", (w, h), np.ascontiguousarray(brut).tobytes(), "raw", "RGBA", 0, 1)
            rayon = max(1.0, self.taille / 14)
            self._flou = np.asarray(im.filter(ImageFilter.GaussianBlur(rayon))).reshape(h, w, 4)
        x, y, w, h = zone.x(), zone.y(), zone.width(), zone.height()
        return self._flou[y:y + h, x:x + w].astype(np.float32) / 255

    def _filtrer(self, base: np.ndarray, m: np.ndarray, zone: QRect) -> np.ndarray:
        """base : (h, w, 4) prémultiplié 0..1 ; m : (h, w) force sous le pinceau (masque × opacité)."""
        a = base[..., 3:4]
        coul = np.where(a > 1e-4, base[..., :3] / np.maximum(a, 1e-4), 0)
        w = m[..., None]
        hdr = self._b == 32                             # couleurs au-delà du blanc possibles
        if self.mode in (ECLAIRCIR, ASSOMBRIR):
            l = np.clip(coul @ _LUM_BVR, 0, 1)
            poids = {"ombres": (1 - l) ** 2, "moyens": 4 * l * (1 - l), "lumieres": l ** 2}[self.gamme][..., None]
            k = w * poids
            coul = coul + np.maximum(1 - coul, 0) * k * 0.6 if self.mode == ECLAIRCIR else coul * (1 - k * 0.6)
        elif self.mode == EPONGE:
            y = (coul @ _LUM_BVR)[..., None]
            coul = y + (coul - y) * (1 + w * 0.9 if self.saturer else 1 - w * 0.9)
        else:
            flou = self._flou_zone(zone)
            if self.mode == GOUTTE:
                return base + (flou - base) * w
            res = base + (base - flou) * w * 1.6               # Netteté : masque flou, sous le pinceau
            if hdr:
                res[..., :3] = np.maximum(res[..., :3], 0)
            else:
                res[..., :3] = np.minimum(np.clip(res[..., :3], 0, 1), base[..., 3:4])
            res[..., 3] = base[..., 3]
            return res
        out = base.copy()
        out[..., :3] = (np.maximum(coul, 0) if hdr else np.clip(coul, 0, 1)) * a
        return out

    # ------------------------------------------------------------------ rendu
    def _composer(self, zone: QRect):
        """Recalcule la zone : image d'origine + (couleur ou copie) à travers le masque, avec l'opacité."""
        if self.mode in FILTRES_PINCEAU:
            gris = self.masque.copy(zone).convertToFormat(QImage.Format_Grayscale8)
            g = np.frombuffer(gris.constBits(), np.uint8, count=gris.height() * gris.bytesPerLine())
            g = g.reshape(gris.height(), gris.bytesPerLine())[:, :gris.width()].astype(np.float32) / 255
            res = self._filtrer(_vue(self.base, zone), g * self.opacite, zone)
            p = QPainter(self.image)
            p.setCompositionMode(QPainter.CompositionMode_Source)
            p.drawImage(zone.topLeft(), _qimage(res, self._b))
            p.end()
            return
        pose = QImage(zone.size(), self.image.format())
        if self.mode == PEINTURE:
            pose.fill(self.couleur)
        else:
            pose.fill(Qt.transparent)
            pp = QPainter(pose)
            pp.drawImage(QPointF(-zone.x(), -zone.y()) - self.decalage, self.source)   # pixel p <- source(p + décalage)
            pp.end()
        gris = self.masque.copy(zone).convertToFormat(QImage.Format_Grayscale8)
        alpha = QImage(gris.constBits(), gris.width(), gris.height(), gris.bytesPerLine(), QImage.Format_Alpha8).copy()
        pp = QPainter(pose)
        pp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        pp.drawImage(0, 0, alpha)
        pp.end()
        p = QPainter(self.image)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(zone.topLeft(), self.base, zone)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        p.setOpacity(self.opacite)
        p.drawImage(zone.topLeft(), pose)
        p.end()


_ronds: dict = {}


def _regrouper(rects: list) -> list:
    """Rectangles qui se chevauchent réunis (moins de recompositions, sans couvrir toute l'image)."""
    res: list = []
    for r in rects:
        if r.isEmpty():
            continue
        fusion = True
        while fusion:
            fusion = False
            for i, q in enumerate(res):
                if q.intersects(r):
                    r = r.united(res.pop(i))
                    fusion = True
                    break
        res.append(r)
    return res


def _rond(durete: float) -> np.ndarray:
    """Forme ronde (pinceau par défaut dans le moteur à formes), gardée en mémoire par dureté."""
    from .pointe import forme_ronde
    cle = round(durete, 2)
    if cle not in _ronds:
        _ronds[cle] = forme_ronde(cle)
    return _ronds[cle]
