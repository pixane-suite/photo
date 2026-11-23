"""Confort de l'interface : panneaux déplaçables (menu Fenêtre), espaces de travail, panneaux Navigateur, Info et
Deuxième image, écran d'accueil, rechercher une commande (Ctrl+F), plein écran (F11), raccourcis clavier
personnalisables, photo suivante / précédente du dossier, plans de travail, et la photo rechargée quand son fichier
change sur le disque. Fenetre (fenetre.py) hérite de InterfacePlusMixin ; _interface_plus() est appelé à la fin de la
construction de la fenêtre."""
from __future__ import annotations

import base64
import json
import re
import unicodedata
from pathlib import Path

from PySide6.QtCore import QByteArray, QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QImage, QImageReader, QKeySequence, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDockWidget,
                               QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QKeySequenceEdit,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
                               QSlider, QTableWidget, QTableWidgetItem, QToolBar, QVBoxLayout, QWidget)

from .langue import tr

LARGEUR = 290


def sans_accents(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def tri_naturel(nom: str):
    return [int(m) if m.isdigit() else m.lower() for m in re.split(r"(\d+)", nom)]


# ====================================================================== panneau Navigateur
class Navigateur(QWidget):
    """Vignette de toute la photo ; le cadre rouge montre la partie visible. Cliquer ou glisser déplace la vue ; la
    glissière règle le zoom."""

    def __init__(self, fenetre):
        super().__init__()
        self.f = fenetre
        self.setMinimumHeight(190)
        self._pm = None
        self._cle = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addStretch(1)
        ligne = QHBoxLayout()
        self.zoom = QSlider(Qt.Horizontal)
        self.zoom.setRange(0, 1000)
        self.zoom.valueChanged.connect(self._zoom_glisse)
        self.texte_zoom = QLabel("100 %")
        self.texte_zoom.setMinimumWidth(56)
        ligne.addWidget(QLabel(tr("Zoom")))
        ligne.addWidget(self.zoom, 1)
        ligne.addWidget(self.texte_zoom)
        lay.addLayout(ligne)
        self._attente = QTimer(self)
        self._attente.setSingleShot(True)
        self._attente.setInterval(80)
        self._attente.timeout.connect(self.rafraichir)
        fenetre.canevas.vue_peinte.connect(lambda: self._attente.start() if self.isVisible() else None)

    @staticmethod
    def _pos(zoom: float) -> int:
        import math
        return int(round((math.log2(max(0.01, min(64, zoom))) + 6.64) / (6 + 6.64) * 1000))

    @staticmethod
    def _zoom(pos: int) -> float:
        return 2 ** (pos / 1000 * (6 + 6.64) - 6.64)

    def _zoom_glisse(self, v):
        c = self.f.canevas
        if self.f.doc is None or abs(self._pos(c.zoom) - v) <= 1:
            return
        c.definir_zoom(self._zoom(v), QPointF(c.width() / 2, c.height() / 2))

    def _zone(self) -> QRectF:
        return QRectF(6, 6, self.width() - 12, self.height() - 50)

    def _echelle(self):
        img = self.f.doc.image
        z = self._zone()
        k = min(z.width() / img.width(), z.height() / img.height())
        x0 = z.x() + (z.width() - img.width() * k) / 2
        y0 = z.y() + (z.height() - img.height() * k) / 2
        return k, x0, y0

    def rafraichir(self):
        c = self.f.canevas
        if self.f.doc is not None:
            self.zoom.blockSignals(True)
            self.zoom.setValue(self._pos(c.zoom))
            self.zoom.blockSignals(False)
            self.texte_zoom.setText(f"{round(c.zoom * 100)} %")
        self.update()

    def paintEvent(self, _e):
        doc = self.f.doc
        p = QPainter(self)
        if doc is None:
            p.setPen(self.palette().mid().color())
            p.drawText(self._zone(), Qt.AlignCenter, tr("Aucune image"))
            return
        img = doc.image
        k, x0, y0 = self._echelle()
        cle = (id(doc), img.cacheKey(), self.width(), self.height())
        if cle != self._cle:
            self._cle = cle
            self._pm = QPixmap.fromImage(img.scaled(max(1, round(img.width() * k)), max(1, round(img.height() * k)),
                                                    Qt.KeepAspectRatio, Qt.SmoothTransformation))
        p.drawPixmap(QPointF(x0, y0), self._pm)
        c = self.f.canevas
        inv, _ok = c._transfo_vue().inverted()
        coins = [c.vers_image(inv.map(QPointF(x, y))) for x, y in ((0, 0), (c.width(), 0), (c.width(), c.height()),
                                                                     (0, c.height()))]
        poly = QPolygonF([QPointF(x0 + q.x() * k, y0 + q.y() * k) for q in coins])
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(230, 40, 40), 2))
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(poly)

    def _aller(self, pos: QPointF):
        if self.f.doc is None:
            return
        k, x0, y0 = self._echelle()
        pt = QPointF((pos.x() - x0) / k, (pos.y() - y0) / k)
        c = self.f.canevas
        c.decalage = QPointF(c.width() / 2, c.height() / 2) - pt * c.zoom
        c._ajuste = False
        c.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._aller(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._aller(e.position())


# ====================================================================== panneau Info
class PanneauInfo(QWidget):
    """Sous la souris : position, couleur (RVB, TSV, hexadécimal) ; la sélection ; la taille de l'image."""

    def __init__(self, fenetre):
        super().__init__()
        self.f = fenetre
        g = QFormLayout(self)
        g.setContentsMargins(10, 8, 10, 8)
        self.pastille = QLabel()
        self.pastille.setFixedSize(34, 20)
        self.champs = {}
        for cle, nom in (("pos", tr("Position")), ("rvb", tr("RVB")), ("tsv", tr("TSV")), ("hex", tr("Hexa")),
                         ("sel", tr("Sélection")), ("img", tr("Image")), ("zoom", tr("Zoom"))):
            lab = QLabel("—")
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.champs[cle] = lab
            g.addRow(nom, lab)
        g.addRow(tr("Couleur"), self.pastille)
        self.minuteur = QTimer(self)
        self.minuteur.setInterval(120)
        self.minuteur.timeout.connect(self.rafraichir)
        self.minuteur.start()
        self._sel = None

    def rafraichir(self):
        if not self.isVisible():
            return
        doc = self.f.doc
        if doc is None:
            for lab in self.champs.values():
                lab.setText("—")
            return
        from PySide6.QtGui import QCursor
        c = self.f.canevas
        pos = c.mapFromGlobal(QCursor.pos())
        pt = c.vers_image(c.derotation(QPointF(pos)))
        x, y = int(pt.x()), int(pt.y())
        img = doc.image
        if 0 <= x < img.width() and 0 <= y < img.height() and c.rect().contains(pos):
            col = QColor(img.pixelColor(x, y))
            self.champs["pos"].setText(f"x {x}   y {y}")
            self.champs["rvb"].setText(f"{col.red()}, {col.green()}, {col.blue()}" +
                                       (f"   α {col.alpha()}" if col.alpha() < 255 else ""))
            h, s, v = col.hsvHue(), col.hsvSaturation(), col.value()
            self.champs["tsv"].setText(f"{max(0, h)}°, {round(s / 2.55)} %, {round(v / 2.55)} %")
            self.champs["hex"].setText(col.name().upper())
            self.pastille.setStyleSheet(f"background: {col.name()}; border: 1px solid #888")
        else:
            for k in ("pos", "rvb", "tsv", "hex"):
                self.champs[k].setText("—")
        cle = doc.selection.cacheKey()
        if cle != self._sel:
            self._sel = cle
            if doc.selection_vide():
                self.champs["sel"].setText(tr("aucune"))
            else:
                import numpy as np
                from .document import masque
                a = masque(doc.selection) > 20
                ys, xs = np.nonzero(a)
                self.champs["sel"].setText(f"{xs.max() - xs.min() + 1} × {ys.max() - ys.min() + 1} px  "
                                           f"(x {xs.min()}, y {ys.min()})")
        self.champs["img"].setText(f"{img.width()} × {img.height()} px · {round(doc.dpi)} dpi · "
                                   f"{doc.profondeur} bits")
        self.champs["zoom"].setText(f"{round(c.zoom * 100)} %" +
                                    (f" · {tr('vue tournée de {a}°', a=round(c.angle_vue))}" if c.angle_vue else ""))


# ====================================================================== panneau Deuxième image
class VueSimple(QWidget):
    """Une image à regarder (pas à modifier) : molette = zoom, glisser = se déplacer."""

    def __init__(self):
        super().__init__()
        self.image = None
        self.zoom = 1.0
        self.decalage = QPointF(0, 0)
        self._glisse = None
        self.setMinimumHeight(200)

    def montrer(self, img, zoom=None):
        nouvelle = self.image is None or img is None or img.size() != self.image.size()
        self.image = img
        if zoom is not None:
            self.zoom = zoom
        elif nouvelle and img is not None:
            self.zoom = min(self.width() / img.width(), self.height() / img.height()) * 0.95
        if nouvelle and img is not None:
            self.decalage = QPointF((self.width() - img.width() * self.zoom) / 2,
                                    (self.height() - img.height() * self.zoom) / 2)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().dark())
        if self.image is None:
            p.setPen(self.palette().text().color())
            p.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, tr("Ouvre une deuxième image pour la voir ici."))
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1)
        p.translate(self.decalage)
        p.scale(self.zoom, self.zoom)
        p.drawImage(0, 0, self.image)

    def wheelEvent(self, e):
        if self.image is None:
            return
        f = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
        pos = e.position()
        self.decalage = pos - (pos - self.decalage) * f
        self.zoom *= f
        self.update()

    def mousePressEvent(self, e):
        self._glisse = e.position()

    def mouseMoveEvent(self, e):
        if self._glisse is not None:
            self.decalage += e.position() - self._glisse
            self._glisse = e.position()
            self.update()

    def mouseReleaseEvent(self, _e):
        self._glisse = None


class PanneauDeuxieme(QWidget):
    def __init__(self, fenetre):
        super().__init__()
        self.f = fenetre
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        ligne = QHBoxLayout()
        self.liste = QComboBox()
        self.liste.activated.connect(lambda _i: self._montrer())
        ligne.addWidget(self.liste, 1)
        self.meme_zoom = QCheckBox(tr("Même zoom"))
        self.meme_zoom.setToolTip(tr("La deuxième image suit le zoom de la photo"))
        self.meme_zoom.toggled.connect(lambda _v: self._montrer())
        ligne.addWidget(self.meme_zoom)
        lay.addLayout(ligne)
        self.vue = VueSimple()
        lay.addWidget(self.vue, 1)
        self._docs = []
        t = QTimer(self)
        t.setInterval(500)
        t.timeout.connect(self._verifier)
        t.start()
        self._cle = None

    def _verifier(self):
        if not self.isVisible():
            return
        docs = [d for d in self.f.documents if d is not self.f.doc]
        noms = [self.f._nom_onglet(d) for d in docs]
        if [id(d) for d in docs] != [id(d) for d in self._docs]:
            choisi = self._docs[self.liste.currentIndex()] if 0 <= self.liste.currentIndex() < len(self._docs) \
                else None
            self._docs = docs
            self.liste.clear()
            self.liste.addItems(noms)
            if choisi in docs:
                self.liste.setCurrentIndex(docs.index(choisi))
        self._montrer()

    def _montrer(self):
        k = self.liste.currentIndex()
        img = self._docs[k].image if 0 <= k < len(self._docs) else None
        cle = (id(img) if img is not None else None, img.cacheKey() if img is not None else None,
               self.meme_zoom.isChecked() and self.f.canevas.zoom)
        if cle == self._cle:
            return
        self._cle = cle
        self.vue.montrer(img, self.f.canevas.zoom if self.meme_zoom.isChecked() else None)


# ====================================================================== écran d'accueil
class Accueil(QWidget):
    """Sans photo ouverte : Nouvelle image, Ouvrir, Coller, et les derniers fichiers en vignettes."""
    ouvrir_fichier = Signal(str)

    def __init__(self, fenetre):
        super().__init__(fenetre.canevas)
        self.f = fenetre
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("accueil")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(40, 30, 40, 30)
        titre = QLabel("<span style='font-size:22pt; font-weight:600'>Pixane Photo</span>")
        lay.addWidget(titre, 0, Qt.AlignHCenter)
        sous = QLabel(tr("Ouvre une photo pour commencer, ou glisse-la ici."))
        sous.setObjectName("discret")
        lay.addWidget(sous, 0, Qt.AlignHCenter)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        for texte, action in ((tr("Nouvelle image…"), fenetre.a_nouvelle), (tr("Ouvrir…"), fenetre.a_ouvrir),
                              (tr("Depuis le presse-papiers"), fenetre.a_nouvelle_pp)):
            b = QPushButton(texte)
            b.setMinimumHeight(34)
            b.clicked.connect(action.trigger)
            boutons.addWidget(b)
        boutons.addStretch(1)
        lay.addLayout(boutons)
        lay.addSpacing(16)
        self.titre_recents = QLabel(tr("Fichiers récents"))
        self.titre_recents.setObjectName("discret")
        lay.addWidget(self.titre_recents)
        self.recents = QListWidget()
        self.recents.setViewMode(QListWidget.IconMode)
        self.recents.setIconSize(QSize(150, 110))
        self.recents.setGridSize(QSize(180, 150))
        self.recents.setResizeMode(QListWidget.Adjust)
        self.recents.setMovement(QListWidget.Static)
        self.recents.setWordWrap(True)
        self.recents.setFrameShape(QListWidget.NoFrame)
        self.recents.itemActivated.connect(lambda it: self.ouvrir_fichier.emit(it.data(Qt.UserRole)))
        self.recents.itemClicked.connect(lambda it: self.ouvrir_fichier.emit(it.data(Qt.UserRole)))
        lay.addWidget(self.recents, 1)
        self._liste = None
        self.setAcceptDrops(False)                    # glisser une photo : c'est la fenêtre qui l'ouvre

    def remplir(self):
        liste = [c for c in self.f._recents() if Path(c).exists()][:12]
        if liste == self._liste:
            return
        self._liste = liste
        self.recents.clear()
        self.titre_recents.setVisible(bool(liste))
        for chemin in liste:
            it = QListWidgetItem(Path(chemin).name)
            it.setData(Qt.UserRole, chemin)
            it.setToolTip(chemin)
            lecteur = QImageReader(chemin)
            taille = lecteur.size()
            if taille.isValid():
                lecteur.setScaledSize(taille.scaled(150, 110, Qt.KeepAspectRatio))
            img = lecteur.read()
            if not img.isNull():
                it.setIcon(QPixmap.fromImage(img))
            self.recents.addItem(it)

    def placer(self):
        self.setGeometry(self.parentWidget().rect())


# ====================================================================== rechercher une commande
class RechercheCommande(QDialog):
    """Ctrl+F : taper quelques lettres ; toutes les commandes des menus (et les outils) qui correspondent ; Entrée
    lance celle choisie."""

    def __init__(self, commandes, parent):
        super().__init__(parent, Qt.Popup)
        self.commandes = commandes                    # [(chemin lisible, QAction)]
        self.setMinimumSize(560, 380)
        lay = QVBoxLayout(self)
        self.champ = QLineEdit()
        self.champ.setPlaceholderText(tr("Rechercher une commande (ex. « flou », « recadrer », « calque »)…"))
        self.champ.textChanged.connect(self._filtrer)
        self.champ.returnPressed.connect(self._lancer)
        lay.addWidget(self.champ)
        self.liste = QListWidget()
        self.liste.itemActivated.connect(lambda _it: self._lancer())
        lay.addWidget(self.liste, 1)
        self.champ.installEventFilter(self)
        self._filtrer("")

    def eventFilter(self, obj, e):
        from PySide6.QtCore import QEvent
        if obj is self.champ and e.type() == QEvent.KeyPress and e.key() in (Qt.Key_Down, Qt.Key_Up):
            r = self.liste.currentRow() + (1 if e.key() == Qt.Key_Down else -1)
            self.liste.setCurrentRow(max(0, min(self.liste.count() - 1, r)))
            return True
        return super().eventFilter(obj, e)

    def _filtrer(self, texte):
        mots = sans_accents(texte).split()
        self.liste.clear()
        for chemin, a in self.commandes:
            cible = sans_accents(chemin)
            if all(m in cible for m in mots):
                raccourci = a.shortcut().toString(QKeySequence.NativeText)
                it = QListWidgetItem(chemin + (f"    ({raccourci})" if raccourci else ""))
                it.setData(Qt.UserRole, a)
                if not a.isEnabled():
                    it.setFlags(it.flags() & ~Qt.ItemIsEnabled)
                self.liste.addItem(it)
        for i in range(self.liste.count()):
            if self.liste.item(i).flags() & Qt.ItemIsEnabled:
                self.liste.setCurrentRow(i)
                break

    def _lancer(self):
        it = self.liste.currentItem()
        if it is None or not it.flags() & Qt.ItemIsEnabled:
            return
        a = it.data(Qt.UserRole)
        self.accept()
        QTimer.singleShot(0, a.trigger)


# ====================================================================== raccourcis personnalisables
class DialogueRaccourcis(QDialog):
    def __init__(self, commandes, defauts: dict, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Raccourcis clavier"))
        self.resize(720, 560)
        self.commandes = commandes                  # [(chemin, QAction)]
        self.defauts = defauts                      # objectName -> raccourci d'origine
        self.nouveaux = {a.objectName(): a.shortcut().toString() for _c, a in commandes}
        lay = QVBoxLayout(self)
        self.filtre = QLineEdit()
        self.filtre.setPlaceholderText(tr("Chercher une commande…"))
        self.filtre.textChanged.connect(self._filtrer)
        lay.addWidget(self.filtre)
        self.table = QTableWidget(len(commandes), 2)
        self.table.setHorizontalHeaderLabels([tr("Commande"), tr("Raccourci")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for i, (chemin, a) in enumerate(commandes):
            self.table.setItem(i, 0, QTableWidgetItem(chemin))
            self.table.setItem(i, 1, QTableWidgetItem(a.shortcut().toString(QKeySequence.NativeText)))
        self.table.currentCellChanged.connect(lambda r, *_: self._ligne(r))
        lay.addWidget(self.table, 1)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Nouveau raccourci :")))
        self.saisie = QKeySequenceEdit()
        self.saisie.setMaximumSequenceLength(1) if hasattr(self.saisie, "setMaximumSequenceLength") else None
        self.saisie.editingFinished.connect(self._saisi)
        ligne.addWidget(self.saisie, 1)
        b = QPushButton(tr("Aucun"))
        b.clicked.connect(lambda: self._poser(""))
        ligne.addWidget(b)
        b = QPushButton(tr("D'origine"))
        b.clicked.connect(self._origine)
        ligne.addWidget(b)
        lay.addLayout(ligne)
        self.alerte = QLabel()
        self.alerte.setObjectName("discret")
        self.alerte.setWordWrap(True)
        lay.addWidget(self.alerte)
        bas = QHBoxLayout()
        b = QPushButton(tr("Tout remettre d'origine"))
        b.clicked.connect(self._tout_origine)
        bas.addWidget(b)
        bas.addStretch(1)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        bas.addWidget(boutons)
        lay.addLayout(bas)

    def _filtrer(self, t):
        mots = sans_accents(t).split()
        for i, (chemin, _a) in enumerate(self.commandes):
            self.table.setRowHidden(i, not all(m in sans_accents(chemin) for m in mots))

    def _ligne(self, r):
        if 0 <= r < len(self.commandes):
            self.saisie.setKeySequence(QKeySequence(self.nouveaux[self.commandes[r][1].objectName()]))
            self.alerte.clear()

    def _poser(self, seq: str):
        r = self.table.currentRow()
        if not (0 <= r < len(self.commandes)):
            return
        nom = self.commandes[r][1].objectName()
        if seq:
            for i, (chemin, a) in enumerate(self.commandes):
                if i != r and self.nouveaux[a.objectName()] == seq:     # déjà pris : l'autre commande le perd
                    self.nouveaux[a.objectName()] = ""
                    self.table.item(i, 1).setText("")
                    self.alerte.setText(tr("« {r} » était le raccourci de « {c} » : il lui est retiré.",
                                           r=QKeySequence(seq).toString(QKeySequence.NativeText), c=chemin))
        self.nouveaux[nom] = seq
        self.table.item(r, 1).setText(QKeySequence(seq).toString(QKeySequence.NativeText))
        self.saisie.setKeySequence(QKeySequence(seq))

    def _saisi(self):
        self._poser(self.saisie.keySequence().toString())

    def _origine(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.commandes):
            self._poser(self.defauts.get(self.commandes[r][1].objectName(), ""))

    def _tout_origine(self):
        for i, (_c, a) in enumerate(self.commandes):
            seq = self.defauts.get(a.objectName(), "")
            self.nouveaux[a.objectName()] = seq
            self.table.item(i, 1).setText(QKeySequence(seq).toString(QKeySequence.NativeText))
        self.alerte.setText(tr("Tous les raccourcis sont revenus à ceux d'origine."))


# ====================================================================== plans de travail
class DialoguePlans(QDialog):
    """Image > Plans de travail… : des zones nommées de la même image (ex. « Instagram », « Bannière »), montrées en
    pointillés bleus, exportées d'un coup, chacune dans son fichier."""

    def __init__(self, fenetre):
        super().__init__(fenetre)
        self.f = fenetre
        self.doc = fenetre.doc
        self.setWindowTitle(tr("Plans de travail"))
        self.resize(620, 420)
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Chaque plan est une zone nommée de l'image. Ajoute un plan d'après la sélection (ou toute "
                         "l'image), règle sa place et sa taille, puis exporte tous les plans d'un coup."))
        aide.setWordWrap(True)
        aide.setObjectName("discret")
        lay.addWidget(aide)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr("Nom"), "x", "y", tr("Largeur"), tr("Hauteur")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        self.table.itemChanged.connect(self._lu)
        lay.addWidget(self.table, 1)
        ligne = QHBoxLayout()
        b = QPushButton(tr("Ajouter un plan"))
        b.setToolTip(tr("D'après la sélection, ou toute l'image sans sélection"))
        b.clicked.connect(self.ajouter)
        ligne.addWidget(b)
        b = QPushButton(tr("Supprimer"))
        b.clicked.connect(self.supprimer)
        ligne.addWidget(b)
        ligne.addStretch(1)
        self.format = QComboBox()
        for ext in ("png", "jpg", "webp"):
            self.format.addItem(ext.upper(), ext)
        ligne.addWidget(self.format)
        b = QPushButton(tr("Exporter tous les plans…"))
        b.clicked.connect(self.exporter)
        ligne.addWidget(b)
        lay.addLayout(ligne)
        boutons = QDialogButtonBox(QDialogButtonBox.Close)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        self._remplir()

    def _remplir(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.doc.plans))
        for i, plan in enumerate(self.doc.plans):
            for j, v in enumerate(plan):
                self.table.setItem(i, j, QTableWidgetItem(str(v)))
        self.table.blockSignals(False)
        self.f.canevas.update()

    def _lu(self, it):
        i, j = it.row(), it.column()
        plan = self.doc.plans[i]
        if j == 0:
            plan[0] = it.text().strip() or plan[0]
        else:
            try:
                plan[j] = max(1 if j > 2 else -100000, int(float(it.text())))
            except ValueError:
                pass
        self.doc.modifie = True
        self._remplir()

    def ajouter(self):
        import numpy as np
        from .document import masque
        doc = self.doc
        if doc.selection_vide():
            r = [0, 0, doc.image.width(), doc.image.height()]
        else:
            a = masque(doc.selection) > 20
            ys, xs = np.nonzero(a)
            r = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
        noms = {p[0] for p in doc.plans}
        k = len(doc.plans) + 1
        while tr("Plan {n}", n=k) in noms:
            k += 1
        doc.plans.append([tr("Plan {n}", n=k)] + r)
        doc.modifie = True
        self._remplir()

    def supprimer(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.doc.plans):
            self.doc.plans.pop(r)
            self.doc.modifie = True
            self._remplir()

    def exporter(self, dossier: str | None = None):
        if not self.doc.plans:
            return
        if not dossier:
            dossier = QFileDialog.getExistingDirectory(self, tr("Dossier où exporter les plans"),
                                                       self.f.reglages.value("dossier", ""))
        if not dossier:
            return
        ext = self.format.currentData()
        faits = []
        for nom, x, y, w, h in self.doc.plans:
            img = self.doc.image.copy(x, y, w, h)
            propre = re.sub(r'[\\/:*?"<>|]+', "_", nom).strip() or "plan"
            chemin = Path(dossier) / f"{propre}.{ext}"
            if ext == "jpg":                              # pas de transparence en JPEG : fond blanc
                fond = QImage(img.size(), QImage.Format_RGB32)
                fond.fill(Qt.white)
                p = QPainter(fond)
                p.drawImage(0, 0, img)
                p.end()
                img = fond
            img.save(str(chemin), quality=95)
            faits.append(chemin.name)
        self.f.statusBar().showMessage(tr("{n} plans exportés : {noms}", n=len(faits), noms=", ".join(faits)), 10000)
        return faits


# ====================================================================== la fenêtre
class InterfacePlusMixin:

    def _interface_plus(self):
        self._docks_principaux = [d for d in self.findChildren(QDockWidget)]
        for d in self._docks_principaux:
            d.setObjectName("dock_" + sans_accents(d.windowTitle()).replace(" ", "_"))
        for b in self.findChildren(QToolBar):
            b.setObjectName("barre_" + sans_accents(b.windowTitle()).replace(" ", "_"))
        self.dock_navigateur = self._nouveau_dock(tr("NAVIGATEUR"), Navigateur(self))
        self.dock_info = self._nouveau_dock(tr("INFO"), PanneauInfo(self))
        self.dock_deuxieme = self._nouveau_dock(tr("DEUXIÈME IMAGE"), PanneauDeuxieme(self))
        self.dock_deuxieme.setMinimumWidth(LARGEUR)
        self.dock_deuxieme.setMaximumWidth(16777215)
        self.dock_deuxieme.widget().setMinimumWidth(0)
        for d in (self.dock_navigateur, self.dock_info, self.dock_deuxieme):
            d.hide()
        self._menu_fenetre()
        self._menus_plus()
        self._defauts_raccourcis = {a.objectName(): a.shortcut().toString() for _c, a in self._commandes()}
        self._appliquer_raccourcis()
        self._etat_defaut = self.saveState()
        self._verrouiller_panneaux(self.reglages.value("panneaux_verrouilles", False, type=bool))
        etat = self.reglages.value("etat_fenetre", "")
        if etat:
            self.restoreState(QByteArray(base64.b64decode(etat)))
        self.accueil = Accueil(self)
        self.accueil.ouvrir_fichier.connect(self.charger)
        self._minuteur_interface = QTimer(self)
        self._minuteur_interface.setInterval(300)
        self._minuteur_interface.timeout.connect(self._maj_accueil)
        self._minuteur_interface.start()
        self._minuteur_fichiers = QTimer(self)
        self._minuteur_fichiers.setInterval(2000)
        self._minuteur_fichiers.timeout.connect(self._fichiers_changes)
        self._minuteur_fichiers.start()
        self._question_fichier = False
        self._maj_accueil()

    def _nouveau_dock(self, titre: str, contenu: QWidget) -> QDockWidget:
        d = QDockWidget(titre, self)
        d.setObjectName("dock_" + sans_accents(titre).replace(" ", "_"))
        d.setWidget(contenu)
        d.setFixedWidth(LARGEUR)
        self.addDockWidget(Qt.RightDockWidgetArea, d)
        self.tabifyDockWidget(self.dock_calques, d)
        self.dock_calques.raise_()
        return d

    # ---------------------------------------------------------- menu Fenêtre, espaces de travail
    def _menu_fenetre(self):
        aide = next((a for a in self.menuBar().actions() if a.text().replace("&", "") == tr("Aide")), None)
        m = QMenu(tr("Fe&nêtre"), self)
        self.m_fenetre = m
        if aide is not None:
            self.menuBar().insertMenu(aide, m)
        else:
            self.menuBar().addMenu(m)
        for d in self._docks_principaux + [self.dock_navigateur, self.dock_info, self.dock_deuxieme]:
            if d is getattr(self, "dock_texte", None):
                continue
            a = d.toggleViewAction()
            a.setText(d.windowTitle().capitalize())
            m.addAction(a)
        m.addSeparator()
        self.a_verrou_panneaux = self._action(m, tr("Verrouiller les panneaux"), None, None, "a_verrou_panneaux")
        self.a_verrou_panneaux.setCheckable(True)
        self.a_verrou_panneaux.setChecked(self.reglages.value("panneaux_verrouilles", False, type=bool))
        self.a_verrou_panneaux.setToolTip(tr("Décoché : les panneaux se déplacent par leur titre (vers un autre "
                                             "bord, ou flottants), se ferment, se rangent en onglets"))
        self.a_verrou_panneaux.toggled.connect(self._verrouiller_panneaux)
        self.m_espaces = m.addMenu(tr("Espace de travail"))
        self.m_espaces.aboutToShow.connect(self._remplir_espaces)
        m.addSeparator()
        self._action(m, tr("Plein écran"), "F11", self.plein_ecran, "a_plein_ecran")

    def _verrouiller_panneaux(self, v: bool):
        self.reglages.setValue("panneaux_verrouilles", v)
        f = (QDockWidget.NoDockWidgetFeatures if v else
             QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        for d in self.findChildren(QDockWidget):
            d.setFeatures(f)

    def _espaces(self) -> dict:
        try:
            return json.loads(self.reglages.value("espaces", "{}") or "{}")
        except ValueError:
            return {}

    ESPACES_PRETS = {
        "essentiel": ("Essentiel", ["dock_intelligence_artificielle", "dock_calques"]),
        "photo": ("Retouche photo", ["dock_intelligence_artificielle", "dock_calques", "dock_info",
                                     "dock_navigateur"]),
        "peinture": ("Peinture", ["dock_calques", "dock_nuancier", "dock_navigateur"]),
    }

    def _remplir_espaces(self):
        m = self.m_espaces
        m.clear()
        for cle, (nom, _docks) in self.ESPACES_PRETS.items():
            m.addAction(tr(nom), lambda c=cle: self.espace_pret(c))
        perso = self._espaces()
        if perso:
            m.addSeparator()
            for nom in sorted(perso):
                m.addAction(nom, lambda n=nom: self.espace_perso(n))
        m.addSeparator()
        m.addAction(tr("Enregistrer l'espace actuel…"), self.enregistrer_espace)
        if perso:
            sous = m.addMenu(tr("Supprimer un espace"))
            for nom in sorted(perso):
                sous.addAction(nom, lambda n=nom: self.supprimer_espace(n))
        m.addAction(tr("Revenir à la disposition d'origine"), self.espace_origine)

    def espace_pret(self, cle: str):
        self.restoreState(self._etat_defaut)
        _nom, visibles = self.ESPACES_PRETS[cle]
        for d in self.findChildren(QDockWidget):
            if d is getattr(self, "dock_texte", None):
                continue
            d.setVisible(d.objectName() in visibles)
        for nom in visibles:                              # premier panneau d'onglets montré devant
            d = self.findChild(QDockWidget, nom)
            if d is not None and nom != "dock_intelligence_artificielle":
                d.raise_()
                break

    def espace_perso(self, nom: str):
        e = self._espaces().get(nom)
        if e:
            self.restoreState(QByteArray(base64.b64decode(e)))

    def enregistrer_espace(self, nom: str | None = None):
        if nom is None:
            nom, ok = QInputDialog.getText(self, tr("Espace de travail"), tr("Nom de cet espace de travail :"))
            if not ok:
                return
        nom = nom.strip()
        if not nom:
            return
        e = self._espaces()
        e[nom] = base64.b64encode(bytes(self.saveState())).decode()
        self.reglages.setValue("espaces", json.dumps(e))
        self.statusBar().showMessage(tr("Espace de travail « {nom} » enregistré (menu Fenêtre).", nom=nom), 6000)

    def supprimer_espace(self, nom: str):
        e = self._espaces()
        e.pop(nom, None)
        self.reglages.setValue("espaces", json.dumps(e))

    def espace_origine(self):
        self.restoreState(self._etat_defaut)
        for d in (self.dock_navigateur, self.dock_info, self.dock_deuxieme):
            d.hide()

    def _sauver_interface(self):
        if hasattr(self, "_etat_defaut"):
            self.reglages.setValue("etat_fenetre", base64.b64encode(bytes(self.saveState())).decode())

    def plein_ecran(self):
        if self.isFullScreen():
            self.showMaximized() if getattr(self, "_etait_agrandie", False) else self.showNormal()
        else:
            self._etait_agrandie = self.isMaximized()
            self.showFullScreen()
            self.statusBar().showMessage(tr("Plein écran : F11 pour revenir."), 5000)

    # ---------------------------------------------------------- autres menus
    def _menus_plus(self):
        menus = {a.text().replace("&", ""): a.menu() for a in self.menuBar().actions() if a.menu() is not None}
        m = menus.get(tr("Fichier"))
        if m is not None:
            avant = next((a for a in m.actions() if a.text() == tr("Quitter")), None)
            for texte, cle, sens, raccourci in ((tr("Photo suivante du dossier"), "a_photo_suivante", 1,
                                                 "Ctrl+Alt+PgDown"),
                                                (tr("Photo précédente du dossier"), "a_photo_precedente", -1,
                                                 "Ctrl+Alt+PgUp")):
                a = QAction(texte, self)
                a.setShortcut(QKeySequence(raccourci))
                a.setToolTip(tr("Ouvre la photo suivante (ou précédente) du même dossier ; la photo actuelle est "
                                "fermée si elle n'a pas changé"))
                a.triggered.connect(lambda _=False, s=sens: self.photo_du_dossier(s))
                setattr(self, cle, a)
                m.insertAction(avant, a)
            m.insertSeparator(avant)
        m = menus.get(tr("Édition"))
        if m is not None:
            m.addSeparator()
            self._action(m, tr("Rechercher une commande…"), "Ctrl+F", self.rechercher_commande, "a_chercher_commande")
            self._action(m, tr("Raccourcis clavier…"), "Ctrl+Alt+K", self.raccourcis_clavier, "a_raccourcis_clavier")
        m = menus.get(tr("Image"))
        if m is not None:
            m.addSeparator()
            self._action(m, tr("Plans de travail…"), None, self.plans_de_travail, "a_plans")

    # ---------------------------------------------------------- commandes (recherche, raccourcis)
    def _commandes(self) -> list:
        """[(chemin lisible, QAction)] : toutes les commandes des menus et les outils, chacune une fois."""
        res, vus = [], set()

        def parcourir(menu, chemin):
            for a in menu.actions():
                if a.isSeparator():
                    continue
                texte = a.text().replace("&", "").split("|")[0]
                if a.menu() is not None:
                    parcourir(a.menu(), chemin + [texte])
                elif texte and id(a) not in vus:
                    vus.add(id(a))
                    res.append((" > ".join(chemin + [texte]), a))
        for a in self.menuBar().actions():
            if a.menu() is not None:
                parcourir(a.menu(), [a.text().replace("&", "")])
        for o, a in self._actions_outils.items():
            if id(a) not in vus:
                vus.add(id(a))
                res.append((tr("Outils") + " > " + a.text().split(" : ")[0], a))
        for n, v in list(vars(self).items()):
            if isinstance(v, QAction) and n.startswith("a_") and not v.objectName():
                v.setObjectName(n)
        for o, a in self._actions_outils.items():
            a.setObjectName("outil_" + o)
        for chemin, a in res:
            if not a.objectName():
                a.setObjectName("menu_" + sans_accents(chemin))
        return res

    def rechercher_commande(self):
        d = RechercheCommande(self._commandes(), self)
        geo = self.geometry()
        d.move(geo.x() + (geo.width() - d.minimumWidth()) // 2, geo.y() + 80)
        self._recherche_commande = d
        d.show()
        d.champ.setFocus()

    def _appliquer_raccourcis(self):
        try:
            perso = json.loads(self.reglages.value("raccourcis", "{}") or "{}")
        except ValueError:
            perso = {}
        for _c, a in self._commandes():
            if a.objectName() in perso:
                a.setShortcut(QKeySequence(perso[a.objectName()]))

    def raccourcis_clavier(self):
        commandes = self._commandes()
        d = DialogueRaccourcis(commandes, self._defauts_raccourcis, self)
        if d.exec():
            perso = {nom: seq for nom, seq in d.nouveaux.items() if seq != self._defauts_raccourcis.get(nom, "")}
            self.reglages.setValue("raccourcis", json.dumps(perso))
            for _c, a in commandes:
                a.setShortcut(QKeySequence(d.nouveaux[a.objectName()]))
                if a in self._actions_outils.values():
                    t = a.toolTip().split("  (")[0].split("\n")[0]
                    s = a.shortcut().toString(QKeySequence.NativeText)
                    a.setToolTip(f"{t}  ({s})" if s else t)
        d.deleteLater()

    # ---------------------------------------------------------- écran d'accueil
    def _maj_accueil(self):
        sans = self.doc is None
        if sans:
            self.accueil.placer()
            self.accueil.remplir()
            if not self.accueil.isVisible():
                self.accueil.show()
                self.accueil.raise_()
        elif self.accueil.isVisible():
            self.accueil.hide()

    # ---------------------------------------------------------- photo suivante / précédente du dossier
    def photo_du_dossier(self, sens: int = 1):
        doc = self.doc
        if doc is None or doc.chemin is None:
            self.statusBar().showMessage(tr("Cette photo n'a pas encore de fichier : rien à suivre."), 5000)
            return
        from .document import EXTENSIONS_LECTURE
        exts = {e.lstrip("*").lower() for e in EXTENSIONS_LECTURE.split()}
        dossier = Path(doc.chemin).parent
        fichiers = sorted((p for p in dossier.iterdir() if p.is_file() and p.suffix.lower() in exts),
                          key=lambda p: tri_naturel(p.name))
        if len(fichiers) < 2:
            self.statusBar().showMessage(tr("Pas d'autre photo dans ce dossier."), 5000)
            return
        noms = [p.name.lower() for p in fichiers]
        i = noms.index(Path(doc.chemin).name.lower()) if Path(doc.chemin).name.lower() in noms else -1
        suivant = fichiers[(i + sens) % len(fichiers)]
        ancien = doc
        self.charger(str(suivant))
        if self.doc is not ancien and not ancien.modifie and ancien in self.documents:
            self.fermer_onglet(self.documents.index(ancien))
            k = self.documents.index(self.doc) if self.doc in self.documents else -1
            if k >= 0:
                self.barre_onglets.setCurrentIndex(k)
        self.statusBar().showMessage(tr("{nom}  ({i} / {n} dans le dossier)", nom=suivant.name,
                                        i=fichiers.index(suivant) + 1, n=len(fichiers)), 5000)

    # ---------------------------------------------------------- fichier changé sur le disque
    def noter_fichier(self, doc):
        try:
            doc._mtime_connu = Path(doc.chemin).stat().st_mtime
        except (OSError, TypeError):
            pass

    def _fichiers_changes(self):
        if self._question_fichier:
            return
        for doc in list(self.documents):
            if doc.chemin is None:
                continue
            try:
                mt = Path(doc.chemin).stat().st_mtime
            except OSError:
                continue
            connu = getattr(doc, "_mtime_connu", None)
            if connu is None:
                doc._mtime_connu = mt
                continue
            if mt == connu:
                continue
            doc._mtime_connu = mt
            self._question_fichier = True
            try:
                texte = tr("Le fichier « {nom} » a été modifié par un autre programme. Le recharger ?",
                           nom=Path(doc.chemin).name)
                if doc.modifie:
                    texte += "\n\n" + tr("Attention : tes changements dans Pixane seront perdus.")
                r = QMessageBox.question(self, tr("Fichier modifié"), texte, QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.Yes)
            finally:
                self._question_fichier = False
            if r == QMessageBox.Yes:
                self.recharger(doc)
            return

    def recharger(self, doc):
        chemin = str(doc.chemin)
        k = self.documents.index(doc)
        doc.modifie = False
        if hasattr(self, "_recuperation"):
            self._recuperation.oublier(doc)
        self.fermer_onglet(k)
        self.charger(chemin)
        self.statusBar().showMessage(tr("Rechargé : {nom}", nom=Path(chemin).name), 5000)

    # ---------------------------------------------------------- plans de travail
    def plans_de_travail(self):
        if not self.doc:
            return
        d = DialoguePlans(self)
        self._dialogue_plans = d
        d.exec()
        self.canevas.update()


__all__ = ["InterfacePlusMixin", "Navigateur", "PanneauInfo", "PanneauDeuxieme", "Accueil", "RechercheCommande",
           "DialogueRaccourcis", "DialoguePlans"]
