"""Barre contextuelle (comme la « barre des tâches contextuelle » de Photoshop) : une petite barre flottante sur la
photo, avec les actions utiles à ce moment. Avec une sélection : sous la sélection, Effacer, Remplir, Modifier,
Améliorer le contour, Inverser, Désélectionner. Sans sélection : en bas de la photo, Sélectionner le sujet,
Supprimer l'arrière-plan, Agrandir, Upscale. Affichage > Barre contextuelle la montre ou la cache."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QToolButton

from .document import masque
from .langue import tr


class BarreContextuelle(QFrame):
    def __init__(self, fenetre):
        super().__init__(fenetre.canevas)
        self.f = fenetre
        self.setObjectName("barreContextuelle")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        self.lay = QHBoxLayout(self)
        self.lay.setContentsMargins(4, 2, 4, 2)
        self.lay.setSpacing(2)
        self.actif = True
        self._cle = None
        self._genre = None
        self._boite = None
        self.minuteur = QTimer(self)
        self.minuteur.setInterval(250)
        self.minuteur.timeout.connect(self.verifier)
        self.minuteur.start()
        self.hide()

    def _actions(self, avec_selection: bool):
        f = self.f
        if avec_selection:
            return [f.a_effacer, f.a_remplir, f.a_modifier, f.a_contour, f.a_inverser, f.a_rien]
        return [f.a_sujet, f.a_arriere_plan, f.a_agrandir, f.a_upscale]

    def _remplir(self, genre: str):
        while self.lay.count():
            w = self.lay.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.deleteLater()
        f = self.f
        courts = {id(f.a_modifier): tr("Modifier"), id(f.a_contour): tr("Contour"), id(f.a_inverser): tr("Inverser"),
                  id(f.a_sujet): tr("Sujet"), id(f.a_arriere_plan): tr("Sans arrière-plan"),
                  id(f.a_agrandir): tr("Agrandir")}
        for a in self._actions(genre == "sel"):
            b = QToolButton(self)
            b.setDefaultAction(a)
            b.setAutoRaise(True)
            b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if not a.icon().isNull() else Qt.ToolButtonTextOnly)
            b.setText(courts.get(id(a), a.text().replace("&", "").rstrip("…")))
            b.setToolTip(a.text().replace("&", ""))
            self.lay.addWidget(b)
            b.show()
        self.adjustSize()
        self._genre = genre

    def verifier(self):
        f = self.f
        c = f.canevas
        doc = f.doc
        occupe = (doc is None or not self.actif or c._trait is not None or c._trace is not None or c._plus is not None
                  or c.transfo is not None or c.cadre is not None or c.persp is not None or c.comparer
                  or c.style_ouvert or bool(QApplication.mouseButtons()))
        if occupe:
            self.hide()
            self._cle = None
            return
        vide = doc.selection_vide()
        cle = (id(doc), doc.selection.cacheKey(), vide, c.zoom, c.decalage.x(), c.decalage.y(), c.angle_vue,
               c.width(), c.height())
        if cle == self._cle and self.isVisible():
            return
        self._cle = cle
        genre = "rien" if vide else "sel"
        if genre != self._genre:
            self._remplir(genre)
        if vide:
            r = QRect(0, 0, doc.image.width(), doc.image.height())
        else:
            a = masque(doc.selection)
            pas = max(1, max(a.shape) // 600)
            petit = a[::pas, ::pas] > 20
            ys, xs = np.nonzero(petit)
            if not len(xs):
                self.hide()
                return
            r = QRect(int(xs.min() * pas), int(ys.min() * pas), int((xs.max() - xs.min() + 1) * pas),
                      int((ys.max() - ys.min() + 1) * pas))
        bas = c._transfo_vue().map(c.vers_ecran(QPointF(r.center().x(), r.bottom())))
        x = int(bas.x() - self.width() / 2)
        y = int(bas.y() + 14)
        if y + self.height() > c.height() - 8:                 # pas de place dessous : au-dessus du bas du canevas
            y = c.height() - self.height() - 8
        x = max(8, min(c.width() - self.width() - 8, x))
        y = max(8, y)
        self.move(x, y)
        self.show()
        self.raise_()
