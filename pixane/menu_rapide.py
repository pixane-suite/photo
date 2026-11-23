"""Menu rapide (comme la palette ronde de Krita) : clic droit sur la photo. Une couronne avec les 8 derniers outils
utilisés, au milieu la couleur du pinceau entourée des dernières couleurs. Un clic choisit ; Échap ou clic à côté
ferme."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from .langue import tr

RAYON = 130            # rayon extérieur
INTERIEUR = 70         # rayon du disque des couleurs


class MenuRapide(QWidget):
    outil_choisi = Signal(str)
    couleur_choisie = Signal(str)

    def __init__(self, outils, icones, couleur: QColor, couleurs: list[str], parent=None):
        """outils : [(clé, nom)] ; icones : clé -> QIcon ; couleurs : dernières couleurs (#rrggbb)."""
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setFixedSize(2 * RAYON + 4, 2 * RAYON + 4)
        self.outils = list(outils)[:8]
        self.icones = icones
        self.couleur = QColor(couleur)
        self.couleurs = [c for c in couleurs if QColor(c).isValid()][:8]
        self.survol = None

    def ouvrir(self, global_pos):
        self.move(global_pos.x() - self.width() // 2, global_pos.y() - self.height() // 2)
        self.show()
        self.setFocus()

    def _centre(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    def _place_outil(self, i: int) -> QPointF:
        a = -math.pi / 2 + i * 2 * math.pi / max(1, len(self.outils))
        r = (RAYON + INTERIEUR) / 2
        return self._centre() + QPointF(r * math.cos(a), r * math.sin(a))

    def _place_couleur(self, i: int) -> QPointF:
        a = -math.pi / 2 + i * 2 * math.pi / max(1, len(self.couleurs))
        r = INTERIEUR * 0.62
        return self._centre() + QPointF(r * math.cos(a), r * math.sin(a))

    def _sous(self, p: QPointF):
        for i in range(len(self.outils)):
            if (p - self._place_outil(i)).manhattanLength() < 26:
                return ("outil", i)
        for i in range(len(self.couleurs)):
            if (p - self._place_couleur(i)).manhattanLength() < 16:
                return ("couleur", i)
        return None

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = self._centre()
        pal = self.palette()
        fond = QColor(pal.window().color())
        fond.setAlpha(235)
        anneau = QPainterPath()
        anneau.addEllipse(c, RAYON, RAYON)
        trou = QPainterPath()
        trou.addEllipse(c, INTERIEUR, INTERIEUR)
        p.setPen(QPen(pal.mid().color(), 1))
        p.setBrush(fond)
        p.drawPath(anneau.subtracted(trou))
        p.setBrush(QColor(pal.base().color()))
        p.drawEllipse(c, INTERIEUR - 4, INTERIEUR - 4)
        for i, (cle, _nom) in enumerate(self.outils):
            q = self._place_outil(i)
            if self.survol == ("outil", i):
                p.setPen(Qt.NoPen)
                p.setBrush(pal.highlight().color())
                p.drawEllipse(q, 22, 22)
            ic = self.icones.get(cle)
            if ic is not None:
                ic.paint(p, QRectF(q.x() - 13, q.y() - 13, 26, 26).toRect())
        for i, coul in enumerate(self.couleurs):
            q = self._place_couleur(i)
            p.setPen(QPen(pal.highlight().color() if self.survol == ("couleur", i) else pal.mid().color(), 2))
            p.setBrush(QColor(coul))
            p.drawEllipse(q, 11, 11)
        p.setPen(QPen(pal.text().color(), 1.5))
        p.setBrush(self.couleur)
        p.drawEllipse(c, 16, 16)
        if self.survol is not None and self.survol[0] == "outil":
            nom = self.outils[self.survol[1]][1].split(" : ")[0].split(" (")[0]
            p.setPen(pal.text().color())
            p.drawText(QRectF(c.x() - INTERIEUR, c.y() + 18, 2 * INTERIEUR, 40), Qt.AlignHCenter | Qt.TextWordWrap,
                       nom)
        p.end()

    def mouseMoveEvent(self, e):
        s = self._sous(e.position())
        if s != self.survol:
            self.survol = s
            self.update()

    def mouseReleaseEvent(self, e):
        s = self._sous(e.position())
        if s is None:
            if (e.position() - self._centre()).manhattanLength() > RAYON * 1.3:
                self.close()
            return
        if s[0] == "outil":
            self.outil_choisi.emit(self.outils[s[1]][0])
        else:
            self.couleur_choisie.emit(self.couleurs[s[1]])
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)


__all__ = ["MenuRapide", "tr"]
