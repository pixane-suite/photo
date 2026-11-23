"""Régler une valeur en glissant sur son nom (comme les « scrubby sliders » de Photoshop) : partout dans Pixane,
le nom posé juste avant une case à chiffres ou une glissière devient une poignée. Glisser vers la droite augmente,
vers la gauche diminue ; Maj : 10 fois plus vite, Ctrl (ou Alt) : 10 fois plus fin. Le curseur devient une double
flèche au-dessus du nom."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QAbstractSlider, QAbstractSpinBox, QApplication, QDoubleSpinBox, QLabel, QSpinBox

PROPRIETE = "pixane_glisser"


def cible(label: QLabel):
    """Case ou glissière réglée par ce nom : son « buddy », ou le premier élément après lui dans sa mise en page."""
    b = label.buddy()
    if isinstance(b, (QSpinBox, QDoubleSpinBox, QAbstractSlider)):
        return b
    parent = label.parentWidget()
    lay = parent.layout() if parent is not None else None
    if lay is None:
        return None
    trouve = _apres(lay, label)
    if isinstance(trouve, (QSpinBox, QDoubleSpinBox, QAbstractSlider)) and trouve.isEnabled():
        return trouve
    return None


def _apres(lay, label):
    for i in range(lay.count()):
        it = lay.itemAt(i)
        if it.widget() is label:
            for j in range(i + 1, lay.count()):
                w = lay.itemAt(j).widget()
                if w is not None and not w.isHidden():
                    return w
            return None
        if it.layout() is not None:
            r = _apres(it.layout(), label)
            if r is not None:
                return r
    return None


class GlisserNoms(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._prise = None                        # (cible, x de départ, valeur de départ)

    def eventFilter(self, obj, e):
        if not isinstance(obj, QLabel) or obj.property(PROPRIETE) is False:
            return False
        t = e.type()
        if t == QEvent.Enter:
            if cible(obj) is not None and obj.text():
                obj.setCursor(Qt.SizeHorCursor)
            return False
        if t == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
            c = cible(obj)
            if c is None or not obj.text():
                return False
            self._prise = (c, e.globalPosition().x(), c.value())
            return True
        if t == QEvent.MouseMove and self._prise is not None:
            c, x0, v0 = self._prise
            dx = e.globalPosition().x() - x0
            m = QApplication.keyboardModifiers()
            facteur = 10 if m & Qt.ShiftModifier else 0.1 if m & (Qt.ControlModifier | Qt.AltModifier) else 1
            if isinstance(c, QAbstractSpinBox):
                pas = c.singleStep() if isinstance(c, (QSpinBox, QDoubleSpinBox)) else 1
            else:
                pas = max(1, (c.maximum() - c.minimum()) / 200)
            v = v0 + round(dx / 2) * pas * facteur
            if isinstance(c, QSpinBox) or isinstance(c, QAbstractSlider):
                v = int(round(v))
            c.setValue(max(c.minimum(), min(c.maximum(), v)))
            return True
        if t == QEvent.MouseButtonRelease and self._prise is not None:
            self._prise = None
            return True
        return False


def installer(app) -> GlisserNoms:
    f = GlisserNoms(app)
    app.installEventFilter(f)
    return f
