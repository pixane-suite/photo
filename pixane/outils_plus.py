"""Outils ajoutés à la boîte à outils (partie « canevas ») : pipette, sélection elliptique, lasso magnétique, outil
Pièce, déplacer un objet (IA), loupe, rotation de la vue, règle, crayon, pinceau mélangeur, et la peinture en
symétrie. Les constantes sont ici ; Canevas (canevas.py) hérite de CanevasPlusMixin.

Rotation de la vue : seule la vue tourne (comme le « Faire pivoter l'affichage » de Photoshop), jamais la photo.
Tout le dessin du canevas est fait dans le repère non tourné, puis tourné autour du centre du canevas ; les positions
de la souris sont « dé-tournées » avant d'arriver aux outils (voir event()).
"""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QEvent, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPainterPath, QPen, QTransform

from .langue import tr

PIPETTE = "pipette"
ELLIPSE_SEL = "ellipse_sel"
LASSO_MAG = "lasso_mag"
PIECE = "piece"
DEPLACER_IA = "deplacer_ia"
LOUPE = "loupe"
ROTATION_VUE = "rotation_vue"
REGLE = "regle"
CRAYON = "crayon"
MELANGEUR = "melangeur"

ECHANTILLONS = (1, 3, 5, 11, 31)       # pipette : carré moyenné (px)
SYMETRIES = ("", "v", "h", "vh")       # aucune, axe vertical (gauche ↔ droite), horizontal, les deux


def angle_regle(a: QPointF, b: QPointF) -> float:
    """Angle de la règle en degrés (0 = horizontale vers la droite ; positif : descend vers la droite)."""
    return math.degrees(math.atan2(b.y() - a.y(), b.x() - a.x()))


def angle_pour_redresser(a: QPointF, b: QPointF) -> float:
    """Rotation (sens des aiguilles, en degrés) qui rend la ligne horizontale, ou verticale si elle est plus proche
    de la verticale."""
    t = angle_regle(a, b)
    t = (t + 90) % 180 - 90                      # -90..90 : le sens du tracé ne compte pas
    if abs(t) <= 45:
        return -t
    return (90 - t) if t > 0 else (-90 - t)


def couleur_moyenne(img: QImage, x: int, y: int, cote: int) -> QColor | None:
    """Couleur moyenne d'un carré de côté `cote` autour de (x, y) (pixels opaques comptés selon leur opacité)."""
    if not (0 <= x < img.width() and 0 <= y < img.height()):
        return None
    if cote <= 1:
        c = QColor(img.pixelColor(x, y))
        c.setAlpha(255)
        return c
    r = cote // 2
    zone = img.copy(x - r, y - r, cote, cote).convertToFormat(QImage.Format_RGBA8888)
    a = np.frombuffer(zone.constBits(), np.uint8).reshape(zone.height(), zone.bytesPerLine() // 4, 4)
    a = a[:, :zone.width()].astype(np.float32)
    poids = a[..., 3:4] / 255
    if poids.sum() <= 0:
        return None
    rgb = (a[..., :3] * poids).sum((0, 1)) / poids.sum()
    return QColor(*(int(round(v)) for v in rgb))


class Ciseaux:
    """Lasso magnétique : chemin qui colle aux bords entre deux points (« ciseaux intelligents » d'OpenCV), sur une
    version réduite de l'image pour rester rapide."""

    def __init__(self, image: QImage):
        import cv2
        self.echelle = min(1.0, 1400 / max(image.width(), image.height()))
        petite = image if self.echelle >= 1 else image.scaled(
            max(1, round(image.width() * self.echelle)), max(1, round(image.height() * self.echelle)),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        petite = petite.convertToFormat(QImage.Format_RGB888)
        h, w = petite.height(), petite.width()
        rgb = np.frombuffer(petite.constBits(), np.uint8).reshape(h, petite.bytesPerLine())[:, :w * 3]
        self.taille = (w, h)
        self.outil = cv2.segmentation_IntelligentScissorsMB()
        self.outil.setEdgeFeatureCannyParameters(32, 100)
        self.outil.setGradientMagnitudeMaxLimit(200)
        self.outil.applyImage(np.ascontiguousarray(rgb.reshape(h, w, 3)))
        self.depart = None

    def _p(self, pt: QPointF) -> tuple[int, int]:
        w, h = self.taille
        return (min(w - 1, max(0, int(round(pt.x() * self.echelle)))),
                min(h - 1, max(0, int(round(pt.y() * self.echelle)))))

    def ancrer(self, pt: QPointF):
        self.depart = self._p(pt)
        self.outil.buildMap(self.depart)

    def chemin(self, pt: QPointF) -> list[QPointF]:
        """Points (image) du dernier ancrage jusqu'à pt, collés aux bords."""
        if self.depart is None:
            return [pt]
        c = self.outil.getContour(self._p(pt))
        k = 1 / self.echelle
        return [QPointF((x + 0.5) * k, (y + 0.5) * k) for x, y in c.reshape(-1, 2)]


class CanevasPlusMixin:
    """Partie canevas des outils ajoutés. Les méthodes _presser_plus / _glisser_plus / _lacher_plus renvoient True
    quand elles ont traité le geste."""

    def _init_plus(self):
        self.angle_vue = 0.0                  # rotation de l'affichage (degrés, sens des aiguilles)
        self.symetrie = ""                    # peinture en symétrie : "", "v", "h", "vh"
        self.echantillon = 1                  # pipette : côté du carré moyenné
        self.pipette_calque = False           # pipette : dans le calque choisi (sinon l'image visible)
        self.melange = 0.5                    # pinceau mélangeur : part de la toile reprise
        self.regle: tuple[QPointF, QPointF] | None = None
        self._plus = None                     # geste en cours : (genre, données…)
        self._ciseaux: Ciseaux | None = None
        self._mag_points: list[QPointF] = []  # lasso magnétique : points validés (image)
        self._mag_ancres: list[int] = []      # index des ancrages dans _mag_points
        self._mag_suite: list[QPointF] = []   # chemin vers la souris (pas encore validé)

    # ---------------------------------------------------------- rotation de la vue
    def _transfo_vue(self) -> QTransform:
        c = QPointF(self.width() / 2, self.height() / 2)
        return QTransform().translate(c.x(), c.y()).rotate(self.angle_vue).translate(-c.x(), -c.y())

    def derotation(self, pos: QPointF) -> QPointF:
        """Position de la souris (widget) -> repère du dessin (avant rotation de la vue)."""
        if not self.angle_vue:
            return QPointF(pos)
        inv, _ok = self._transfo_vue().inverted()
        return inv.map(QPointF(pos))

    def definir_angle_vue(self, angle: float):
        self.angle_vue = ((angle + 180) % 360) - 180
        if abs(self.angle_vue) < 0.01:
            self.angle_vue = 0.0
        self.update()
        self.message.emit(tr("Vue tournée de {a}° (la photo ne change pas). Double-clic avec l'outil Rotation de la "
                             "vue, ou Affichage > Vue droite, pour la remettre droite.", a=round(self.angle_vue))
                          if self.angle_vue else tr("Vue droite."))

    def event(self, e):
        if self.angle_vue and e.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseMove,
                                           QEvent.MouseButtonDblClick):
            e2 = QMouseEvent(e.type(), self.derotation(e.position()), e.scenePosition(), e.globalPosition(),
                             e.button(), e.buttons(), e.modifiers(), e.pointingDevice())
            ok = super().event(e2)
            e.setAccepted(e2.isAccepted())
            return ok
        return super().event(e)

    # ---------------------------------------------------------- symétrie
    def miroirs(self) -> list:
        """Fonctions point -> point reflété, d'après la symétrie choisie (axes au milieu de l'image)."""
        if not self.symetrie or self.doc is None:
            return []
        w, h = self.doc.image.width(), self.doc.image.height()
        res = []
        if "v" in self.symetrie:
            res.append(lambda q: QPointF(w - q.x(), q.y()))
        if "h" in self.symetrie:
            res.append(lambda q: QPointF(q.x(), h - q.y()))
        if self.symetrie == "vh":
            res.append(lambda q: QPointF(w - q.x(), h - q.y()))
        return res

    # ---------------------------------------------------------- souris
    def _presser_plus(self, e, pos: QPointF) -> bool:
        pt = self.vers_image(pos)
        alt = bool(e.modifiers() & Qt.AltModifier)
        if self.outil == PIPETTE:
            self._plus = ("pipette",)
            self._prendre_couleur(pt)
            return True
        if self.outil == LOUPE:
            self._plus = ("loupe", pos, pos, alt)
            return True
        if self.outil == ROTATION_VUE:
            c = QPointF(self.width() / 2, self.height() / 2)
            souris = self._transfo_vue().map(pos)
            self._plus = ("rotation", math.degrees(math.atan2(souris.y() - c.y(), souris.x() - c.x())),
                          self.angle_vue)
            self.setCursor(Qt.ClosedHandCursor)
            return True
        if self.outil == REGLE:
            self._plus = ("regle",)
            self.regle = (pt, pt)
            self.update()
            return True
        if self.outil == LASSO_MAG:
            self._presser_magnetique(pt, e)
            return True
        if self.outil in (PIECE, DEPLACER_IA):
            sel = self.doc.selection
            x, y = int(pt.x()), int(pt.y())
            dedans = (not self.doc.selection_vide() and 0 <= x < sel.width() and 0 <= y < sel.height()
                      and QColor.fromRgba(sel.pixel(x, y)).alpha() > 127)
            if dedans:
                self._plus = ("glisse", pt, pt)
            elif self.outil == PIECE:
                self._plus = ("entourer", [pt])
            else:
                self.refus.emit(tr("Sélectionne d'abord l'objet (sélection d'objet, lasso…), puis glisse-le avec "
                                   "cet outil."))
            return True
        return False

    def _glisser_plus(self, e, pos: QPointF) -> bool:
        if self.outil == LASSO_MAG and self._ciseaux is not None and self._mag_points:
            pt = self.vers_image(pos)
            self._mag_suite = self._ciseaux.chemin(pt)
            # ancrage automatique tous les 60 px d'écran environ : le chemin reste stable
            if len(self._mag_suite) > 2:
                depart = self._mag_points[self._mag_ancres[-1]] if self._mag_ancres else self._mag_points[0]
                if QLineF(depart, pt).length() * self.zoom > 60:
                    self._ancrer_magnetique(pt)
            self.update()
            return True
        if self._plus is None:
            if self.outil in (PIPETTE, LOUPE, REGLE, LASSO_MAG):
                self.setCursor(Qt.CrossCursor)
            elif self.outil == ROTATION_VUE:
                self.setCursor(Qt.OpenHandCursor)
            return False
        genre = self._plus[0]
        pt = self.vers_image(pos)
        if genre == "pipette":
            self._prendre_couleur(pt)
        elif genre == "loupe":
            self._plus = ("loupe", self._plus[1], pos, self._plus[3])
        elif genre == "rotation":
            c = QPointF(self.width() / 2, self.height() / 2)
            souris = self._transfo_vue().map(pos)          # vraie position à l'écran (pos est « dé-tournée »)
            a = math.degrees(math.atan2(souris.y() - c.y(), souris.x() - c.x()))
            nouvel = self._plus[2] + (a - self._plus[1])
            if e.modifiers() & Qt.ShiftModifier:            # Maj : par pas de 15°
                nouvel = round(nouvel / 15) * 15
            self.angle_vue = ((nouvel + 180) % 360) - 180
        elif genre == "regle":
            a = self.regle[0]
            if e.modifiers() & Qt.ShiftModifier:                     # Maj : par pas de 15°
                t = math.radians(round(angle_regle(a, pt) / 15) * 15)
                d = QLineF(a, pt).length()
                pt = QPointF(a.x() + d * math.cos(t), a.y() + d * math.sin(t))
            self.regle = (a, pt)
            self.message.emit(self.texte_regle())
        elif genre == "entourer":
            if QLineF(pt, self._plus[1][-1]).length() * self.zoom >= 2:
                self._plus[1].append(pt)
        elif genre == "glisse":
            self._plus = ("glisse", self._plus[1], pt)
        self.update()
        return True

    def _lacher_plus(self) -> bool:
        if self._plus is None:
            return False
        geste, self._plus = self._plus, None
        genre = geste[0]
        if genre == "loupe":
            _g, a, b, alt = geste
            if QLineF(a, b).length() > 8 and not alt:                  # cadre : zoom pour le remplir
                r = QRectF(a, b).normalized()
                facteur = min(self.width() / r.width(), self.height() / r.height())
                centre = self.vers_image(r.center())
                self.definir_zoom(self.zoom * facteur, QPointF(self.width() / 2, self.height() / 2))
                self.decalage = QPointF(self.width() / 2, self.height() / 2) - centre * self.zoom
                self._signaler()
            else:
                self.definir_zoom(self.zoom / 2 if alt else self.zoom * 2, a)
        elif genre == "rotation":
            self.setCursor(Qt.OpenHandCursor)
            self.definir_angle_vue(self.angle_vue)
        elif genre == "regle":
            self.regle_changee.emit()
        elif genre == "entourer":
            points = geste[1]
            if len(points) > 2:
                avant = self.doc.etat()
                self.doc.selection.fill(0)
                chemin = QPainterPath(points[0])
                for q in points[1:]:
                    chemin.lineTo(q)
                chemin.closeSubpath()
                chemin.setFillRule(Qt.WindingFill)              # un tracé qui se croise reste plein
                p = self._peintre_selection()
                from .canevas import COULEUR_SELECTION
                p.fillPath(chemin, COULEUR_SELECTION)
                p.end()
                self.selection_modifiee.emit(avant, tr("Pièce : zone à réparer"))
                self.message.emit(tr("Zone à réparer entourée : glisse-la maintenant vers une partie saine de la "
                                     "photo, qui la remplacera."))
        elif genre == "glisse":
            _g, a, b = geste
            dx, dy = round(b.x() - a.x()), round(b.y() - a.y())
            if dx or dy:
                (self.piece_glissee if self.outil == PIECE else self.objet_deplace).emit(dx, dy)
        self.update()
        return True

    def _prendre_couleur(self, pt: QPointF):
        img = self.doc.calque_actif.image if self.pipette_calque else self.doc.image
        c = couleur_moyenne(img, int(pt.x()), int(pt.y()), self.echantillon)
        if c is not None:
            self.couleur_prise.emit(c.name())

    def texte_regle(self) -> str:
        if self.regle is None:
            return ""
        a, b = self.regle
        return tr("Règle : {l} px, angle {t}° (Δx {dx}, Δy {dy})", l=round(QLineF(a, b).length(), 1),
                  t=round(-angle_regle(a, b), 1), dx=round(b.x() - a.x()), dy=round(b.y() - a.y()))

    # ---------------------------------------------------------- lasso magnétique
    def _presser_magnetique(self, pt: QPointF, e):
        if self._ciseaux is None or not self._mag_points:
            self._ciseaux = Ciseaux(self.doc.image)
            self._mag_points, self._mag_ancres, self._mag_suite = [pt], [0], []
            self._ciseaux.ancrer(pt)
            self.message.emit(tr("Lasso magnétique : suis le bord de l'objet, le trait s'y colle ; clic = un point "
                                 "d'ancrage ; double-clic, Entrée ou clic sur le départ pour fermer ; Retour arrière "
                                 "enlève le dernier ancrage ; Échap abandonne."))
            self.update()
            return
        if QLineF(pt, self._mag_points[0]).length() * self.zoom < 10 and len(self._mag_points) > 3:
            self.finir_magnetique()
            return
        self._ancrer_magnetique(pt)

    def _ancrer_magnetique(self, pt: QPointF):
        suite = self._ciseaux.chemin(pt) if self._ciseaux is not None else [pt]
        self._mag_points.extend(suite[1:] if len(suite) > 1 else suite)
        self._mag_ancres.append(len(self._mag_points) - 1)
        self._mag_suite = []
        self._ciseaux.ancrer(self._mag_points[-1])
        self.update()

    def retirer_ancre_magnetique(self) -> bool:
        if not self._mag_points or len(self._mag_ancres) <= 1:
            self.annuler_magnetique()
            return True
        self._mag_ancres.pop()
        fin = self._mag_ancres[-1]
        del self._mag_points[fin + 1:]
        self._ciseaux.ancrer(self._mag_points[-1])
        self._mag_suite = []
        self.update()
        return True

    def annuler_magnetique(self):
        self._ciseaux, self._mag_points, self._mag_ancres, self._mag_suite = None, [], [], []
        self.update()

    def magnetique_en_cours(self) -> bool:
        return bool(self._mag_points)

    def finir_magnetique(self):
        """Ferme le lasso magnétique : la zone entourée devient la sélection (mode de la barre : nouvelle, ajouter,
        retirer)."""
        points = self._mag_points + self._mag_suite[1:]
        if len(points) < 3:
            self.annuler_magnetique()
            return
        retour = self._ciseaux.chemin(points[0]) if self._ciseaux is not None else []
        if self._ciseaux is not None:
            self._ciseaux.ancrer(points[-1])
            retour = self._ciseaux.chemin(points[0])
        points = points + retour[1:]
        avant = self.doc.etat()
        if self.mode_forme == "nouvelle":
            self.doc.selection.fill(0)
        chemin = QPainterPath(points[0])
        for q in points[1:]:
            chemin.lineTo(q)
        chemin.closeSubpath()
        chemin.setFillRule(Qt.WindingFill)              # un tracé qui se croise reste plein
        from .canevas import COULEUR_SELECTION
        self._soustraire = self.mode_forme == "retirer"
        p = self._peintre_selection()
        p.fillPath(chemin, COULEUR_SELECTION)
        p.end()
        self._soustraire = False
        self.annuler_magnetique()
        self.selection_modifiee.emit(avant, tr("Lasso magnétique"))

    # ---------------------------------------------------------- dessin
    def _dessiner_plus(self, p: QPainter):
        if self._plus is not None and self._plus[0] == "loupe":
            _g, a, b, _alt = self._plus
            if QLineF(a, b).length() > 8:
                p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
                p.setBrush(Qt.NoBrush)
                p.drawRect(QRectF(a, b).normalized())
        if self.outil == REGLE and self.regle is not None:
            a, b = (self.vers_ecran(q) for q in self.regle)
            for coul, ep in ((QColor(0, 0, 0, 160), 3), (QColor(255, 255, 255), 1)):
                p.setPen(QPen(coul, ep))
                p.drawLine(a, b)
                for q in (a, b):
                    p.drawLine(q + QPointF(-5, 0), q + QPointF(5, 0))
                    p.drawLine(q + QPointF(0, -5), q + QPointF(0, 5))
            texte = self.texte_regle().split(" : ", 1)[-1]
            p.setPen(QColor(255, 255, 255))
            fond = QRectF(b + QPointF(10, 8), b + QPointF(10 + 7 * len(texte), 28))
            p.fillRect(fond, QColor(0, 0, 0, 150))
            p.drawText(fond, Qt.AlignCenter, texte)
        if self.outil == LASSO_MAG and self._mag_points:
            chemin = QPainterPath(self.vers_ecran(self._mag_points[0]))
            for q in self._mag_points[1:] + self._mag_suite[1:]:
                chemin.lineTo(self.vers_ecran(q))
            for coul, style in ((QColor(0, 0, 0), Qt.SolidLine), (QColor(255, 255, 255), Qt.DashLine)):
                p.setPen(QPen(coul, 1, style))
                p.setBrush(Qt.NoBrush)
                p.drawPath(chemin)
            p.setPen(QPen(QColor(255, 255, 255), 1))
            for i in self._mag_ancres:
                q = self.vers_ecran(self._mag_points[i])
                p.fillRect(QRectF(q.x() - 2.5, q.y() - 2.5, 5, 5), self.couleur_accent)
        if self._plus is not None and self._plus[0] == "entourer":
            chemin = QPainterPath(self.vers_ecran(self._plus[1][0]))
            for q in self._plus[1][1:]:
                chemin.lineTo(self.vers_ecran(q))
            p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawPath(chemin)
        if self._plus is not None and self._plus[0] == "glisse":
            _g, a, b = self._plus
            d = (b - a) * self.zoom
            p.save()
            p.translate(self.decalage + d)
            p.scale(self.zoom, self.zoom)
            if self.outil == DEPLACER_IA:            # l'objet suit la souris
                img = self.doc.calque_actif.image.copy()
                pp = QPainter(img)
                pp.setCompositionMode(QPainter.CompositionMode_DestinationIn)
                pp.drawImage(0, 0, self.doc.selection)
                pp.end()
                p.setOpacity(0.85)
                p.drawImage(QPointF(0, 0), img)
            else:                                     # Pièce : la zone saine qui viendra, en transparence
                p.setOpacity(0.5)
                p.drawImage(QPointF(0, 0), self.doc.selection)
            p.restore()
            if self.outil == PIECE:
                self.message.emit(tr("Lâche sur une partie saine : elle remplacera la zone à réparer."))


def appliquer_piece(calque: QImage, selection: QImage, dx: int, dy: int) -> QImage:
    """Outil Pièce : la zone sélectionnée du calque est remplacée par la zone décalée de (dx, dy), raccordée à la
    lumière et aux couleurs autour (collage fondu de Poisson, OpenCV seamlessClone)."""
    import cv2
    from .document import FORMAT_CALQUE, FORMAT_IMAGE, masque, qimage_rgba, tableau
    t = tableau(calque.convertToFormat(FORMAT_IMAGE))
    m = masque(selection).astype(np.float32) / 255
    h, w = m.shape
    if not (m > 0.5).any():
        return calque
    marge = 12
    grand = np.pad(t, ((marge, marge), (marge, marge), (0, 0)), mode="reflect")
    source = np.roll(grand, (-dy, -dx), axis=(0, 1))          # la partie saine vient se poser sur la zone
    mm = np.pad(m, marge)
    binaire = (mm > 0.5).astype(np.uint8) * 255
    binaire = cv2.dilate(binaire, np.ones((5, 5), np.uint8))
    ys, xs = np.where(binaire > 0)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    y0, x0 = max(1, y0), max(1, x0)
    y1, x1 = min(binaire.shape[0] - 2, y1), min(binaire.shape[1] - 2, x1)
    binaire[:y0], binaire[y1 + 1:], binaire[:, :x0], binaire[:, x1 + 1:] = 0, 0, 0, 0
    centre = ((x0 + x1 + 1) // 2, (y0 + y1 + 1) // 2)
    src = np.ascontiguousarray(source[..., :3])
    dst = np.ascontiguousarray(grand[..., :3])
    try:
        fondu = cv2.seamlessClone(src, dst, binaire, centre, cv2.NORMAL_CLONE)
    except cv2.error:
        fondu = src                                           # zone trop au bord : simple copie
    fondu = fondu[marge:marge + h, marge:marge + w].astype(np.float32)
    doux = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None]
    res = t.astype(np.float32)
    res[..., :3] = res[..., :3] * (1 - doux) + fondu * doux
    return qimage_rgba(np.clip(np.round(res), 0, 255).astype(np.uint8)).convertToFormat(FORMAT_CALQUE)


__all__ = ["PIPETTE", "ELLIPSE_SEL", "LASSO_MAG", "PIECE", "DEPLACER_IA", "LOUPE", "ROTATION_VUE", "REGLE", "CRAYON",
           "MELANGEUR", "ECHANTILLONS", "SYMETRIES", "CanevasPlusMixin", "Ciseaux", "appliquer_piece",
           "angle_pour_redresser", "couleur_moyenne"]
