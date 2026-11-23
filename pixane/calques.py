"""Panneau Calques : liste (œil, vignette, masque, nom), mode de fusion, opacité, boutons nouveau / groupe / masque /
réglage / dupliquer / style / monter / descendre / fusionner / aplatir / supprimer. Chaque action passe par
`demande(etat, texte)` pour être annulable.

Groupes : leurs calques sont décalés vers la droite ; la flèche du groupe le replie. Masque : clic sur sa vignette =
les outils de peinture travaillent sur le masque (cadre de couleur autour) ; clic sur la vignette du calque = sur
les pixels ; Maj+clic sur le masque = le désactiver / réactiver.
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QInputDialog,
                               QLabel, QListWidget, QListWidgetItem, QMenu, QSlider, QToolButton, QVBoxLayout, QWidget)

from . import ajustements, calque_forme, calque_pinceau, calque_remplissage
from .composition import GROUPES_MODES, MODES, noms_modes, parents
from .document import Document
from .langue import tr

VIGNETTE = QSize(60, 34)           # case de la vignette ; l'image y garde sa forme (sans bandes vides)
RETRAIT = 16                       # décalage d'un niveau de groupe


def damier(taille: QSize, case: int = 5) -> QPixmap:
    pm = QPixmap(taille)
    pm.fill(QColor(235, 235, 235))
    p = QPainter(pm)
    for y in range(0, taille.height(), case):
        for x in range(0, taille.width(), case):
            if (x // case + y // case) % 2:
                p.fillRect(x, y, case, case, QColor(200, 200, 200))
    p.end()
    return pm


class Vignette(QLabel):
    clique = Signal(bool)          # Maj enfoncée ?

    def __init__(self):
        super().__init__()
        self.setFixedSize(VIGNETTE.width() + 4, VIGNETTE.height() + 4)
        self.setAlignment(Qt.AlignCenter)
        self.choisie = False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clique.emit(bool(e.modifiers() & Qt.ShiftModifier))
        super().mousePressEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.choisie:
            p = QPainter(self)
            p.setPen(QPen(self.palette().highlight().color(), 2))
            p.drawRect(self.rect().adjusted(1, 1, -1, -1))
            p.end()


class LigneCalque(QWidget):
    """Une ligne de la liste : retrait, flèche (groupe), œil, vignette, masque, nom, cadenas."""
    oeil_clique = Signal()
    cadenas_clique = Signal()
    fleche_cliquee = Signal()
    vignette_cliquee = Signal(bool)
    masque_clique = Signal(bool)

    def __init__(self, icones):
        super().__init__()
        self.icones = icones            # fonction nom -> QIcon (couleurs du thème)
        self.index = 0
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 6, 3)
        lay.setSpacing(6)
        self.retrait = QWidget()
        self.retrait.setFixedWidth(0)
        self.fleche = QToolButton()
        self.fleche.setAutoRaise(True)
        self.fleche.setFixedWidth(18)
        self.fleche.clicked.connect(self.fleche_cliquee)
        self.oeil = QToolButton()
        self.oeil.setAutoRaise(True)
        self.oeil.setToolTip(tr("Afficher / masquer le calque"))
        self.oeil.clicked.connect(self.oeil_clique)
        self.vignette = Vignette()
        self.vignette.clique.connect(self.vignette_cliquee)
        self.masque = Vignette()
        self.masque.setToolTip(tr("Masque du calque : clic = peindre le masque (noir cache, blanc montre) ; "
                                  "Maj+clic = le désactiver / réactiver"))
        self.masque.clique.connect(self.masque_clique)
        self.nom = QLabel()
        self.details = QLabel()
        self.details.setObjectName("discret")
        textes = QVBoxLayout()
        textes.setSpacing(0)
        textes.addWidget(self.nom)
        textes.addWidget(self.details)
        self.cadenas = QToolButton()
        self.cadenas.setAutoRaise(True)
        self.cadenas.clicked.connect(self.cadenas_clique)
        lay.addWidget(self.retrait)
        lay.addWidget(self.fleche)
        lay.addWidget(self.oeil)
        lay.addWidget(self.vignette)
        lay.addWidget(self.masque)
        lay.addLayout(textes, 1)
        lay.addWidget(self.cadenas)

    def marquer(self, oui: bool):
        """Calque choisi en plus du calque actif (Ctrl+clic) : fond surligné, plus discret que le calque actif."""
        self.setObjectName("ligneCalque")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("#ligneCalque { background: rgba(70, 140, 230, 70); border-radius: 3px; }" if oui else "")

    def remplir(self, c, vignette: QPixmap, vignette_masque: QPixmap | None, niveau: int, cible_masque: bool,
                choisi: bool, visible_en_vrai: bool):
        ecrete = getattr(c, "ecretage", False)
        self.retrait.setFixedWidth(niveau * RETRAIT + (RETRAIT if ecrete else 0))   # écrêté : décalé, comme Photoshop
        self.fleche.setVisible(c.groupe)
        if c.groupe:
            self.fleche.setText("▾" if c.ouvert else "▸")
            self.fleche.setToolTip(tr("Replier le groupe") if c.ouvert else tr("Déplier le groupe"))
        self.oeil.setIcon(self.icones("oeil" if c.visible else "oeil_ferme"))
        self.cadenas.setIcon(self.icones("cadenas" if c.verrou else "cadenas_ouvert"))
        self.cadenas.setToolTip(tr("Calque verrouillé : cliquer pour le déverrouiller") if c.verrou else
                                tr("Verrouiller le calque (protège contre les modifications)"))
        effet = self.cadenas.graphicsEffect()
        if effet is None:
            effet = QGraphicsOpacityEffect(self.cadenas)
            self.cadenas.setGraphicsEffect(effet)
        effet.setOpacity(1.0 if c.verrou else 0.35)        # cadenas ouvert discret
        self.nom.setText(("↳ " if ecrete else "") + c.nom)
        self.nom.setEnabled(visible_en_vrai)
        details = []
        if c.groupe:
            details.append(tr("groupe"))
        elif c.reglage is not None:
            details.append(tr("réglage : {quoi}", quoi=ajustements.nom(c.reglage["type"]).lower()))
        elif c.texte is not None:
            details.append(tr("texte"))
        elif calque_pinceau.valide(c) is not None:
            details.append(tr("pinceau modifiable"))
        elif calque_forme.valide(c) is not None:
            details.append(tr("forme modifiable"))
        elif calque_remplissage.valide(c) is not None:
            details.append(tr("remplissage"))
        if ecrete:
            details.append(tr("écrêté"))
        if c.style is not None and not c.style.vide():
            details.append(tr("fx · style"))
        if c.mode != "normal":
            details.append(noms_modes().get(c.mode, c.mode).lower())
        if c.opacite < 0.999:
            details.append(tr("opacité {n} %", n=round(c.opacite * 100)))
        if c.masque is not None and not c.masque_actif:
            details.append(tr("masque désactivé"))
        self.details.setText(" · ".join(details))
        self.details.setVisible(bool(details))
        self.vignette.setPixmap(vignette)
        self.vignette.choisie = choisi and not (cible_masque and vignette_masque is not None) and \
            vignette_masque is not None
        self.vignette.update()
        self.masque.setVisible(vignette_masque is not None)
        if vignette_masque is not None:
            self.masque.setPixmap(vignette_masque)
            self.masque.choisie = choisi and cible_masque
            self.masque.update()


class PanneauCalques(QWidget):
    demande = Signal(object, str)      # (nouvel état, texte pour Annuler)
    style_demande = Signal()           # double-clic sur un calque (hors du nom) ou bouton fx
    pixelliser_demande = Signal(str)   # clic droit > Pixelliser : "texte", "forme", "style", "dynamique", "tout"
    texte_demande = Signal()           # double-clic sur un calque de texte (hors du nom) : éditer le texte
    reglage_demande = Signal(str)      # nouveau calque de réglage (type) ; "" = modifier celui choisi
    refus = Signal(str)                # action impossible : message dans la barre d'état

    def __init__(self, icones):
        super().__init__()
        self.icones = icones
        self.doc: Document | None = None
        self._vignettes: dict = {}
        self._avant_opacite = None
        self._indexes: list[int] = []   # index du calque de chaque ligne (du haut vers le bas)
        # calques choisis (Ctrl+clic, Maj+clic, comme Photoshop) : le calque actif en fait toujours partie
        self.choisis: set[int] = set()
        self._vu = (None, 0)            # (document, nombre de calques) : la liste des choisis repart à zéro
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(6)

        haut = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.setToolTip(tr("Mode de fusion : comment le calque se mélange à ce qui est dessous"))
        noms = noms_modes()
        for k, groupe in enumerate(GROUPES_MODES):
            if k:
                self.mode.insertSeparator(self.mode.count())
            for m in groupe:
                self.mode.addItem(noms[m], m)
        self.mode.activated.connect(self._mode_choisi)
        haut.addWidget(self.mode, 1)
        lay.addLayout(haut)

        self.liste = QListWidget()
        self.liste.setObjectName("calques")
        self.liste.setIconSize(VIGNETTE)
        self.liste.setFocusPolicy(Qt.NoFocus)      # un clic ici laisse les flèches à l'image (outil Déplacer)
        self.liste.currentRowChanged.connect(self._ligne_choisie)
        self.liste.itemDoubleClicked.connect(self._double_clic)
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)          # clic droit : menu du calque
        self.liste.customContextMenuRequested.connect(self._menu_contextuel)
        # glisser un calque à la souris pour changer sa place (comme Photoshop)
        self._glisse = None                 # {"depart": point, "rang": ligne prise, "actif": en cours ?}
        self.liste.viewport().installEventFilter(self)
        self._trait = QFrame(self.liste.viewport())
        self._trait.setFixedHeight(3)
        self._trait.setStyleSheet("background: #f97316; border: none")
        self._trait.hide()
        lay.addWidget(self.liste, 1)

        opacite = QHBoxLayout()
        opacite.addWidget(QLabel(tr("Opacité")))
        self.curseur = QSlider(Qt.Horizontal)
        self.curseur.setRange(0, 100)
        self.curseur.sliderPressed.connect(self._opacite_debut)
        self.curseur.valueChanged.connect(self._opacite_change)
        self.curseur.sliderReleased.connect(self._opacite_fin)
        self.valeur = QLabel("100 %")
        self.valeur.setMinimumWidth(42)
        opacite.addWidget(self.curseur, 1)
        opacite.addWidget(self.valeur)
        lay.addLayout(opacite)

        # deux rangées : sur une seule, les 11 boutons étaient tassés et les icônes paraissaient minuscules
        rangees = (QHBoxLayout(), QHBoxLayout())
        for r in rangees:
            r.setSpacing(2)
        self.boutons = {}
        # bulles d'aide : tr("Nouveau calque vide"), tr("Fusionner avec le calque du dessous"),
        # tr("Aplatir l'image (un seul calque)") ; les autres sont déjà traduites ailleurs
        for nom, aide, action in (("calque_nouveau", "Nouveau calque vide", self.nouveau),
                                  ("groupe", tr("Nouveau groupe (Ctrl+G : mettre le calque dans un groupe)"),
                                   self.nouveau_groupe),
                                  ("masque", tr("Ajouter un masque (d'après la sélection s'il y en a une)"),
                                   self.ajouter_masque),
                                  ("reglage", tr("Nouveau calque de remplissage ou de réglage"), self._menu_reglage),
                                  ("dupliquer", tr("Dupliquer le calque"), self.dupliquer),
                                  ("style", tr("Style du calque (ombre, contour, lueur…)"), self.style_demande.emit),
                                  ("monter", tr("Monter le calque"), lambda: self.deplacer(+1)),
                                  ("descendre", tr("Descendre le calque"), lambda: self.deplacer(-1)),
                                  ("fusionner", "Fusionner avec le calque du dessous", self.fusionner),
                                  ("aplatir", "Aplatir l'image (un seul calque)", self.aplatir),
                                  ("supprimer", tr("Supprimer le calque"), self.supprimer)):
            b = QToolButton()
            b.setAutoRaise(True)
            b.setToolTip(tr(aide))
            b.setIconSize(QSize(22, 22))
            b.clicked.connect(action)
            self.boutons[nom] = b
            rangees[0 if len(self.boutons) <= 6 else 1].addWidget(b)
        for r in rangees:
            r.addStretch(1)
            lay.addLayout(r)
        self.appliquer_icones()
        self.rafraichir()

    # ---------------------------------------------------------- document
    def definir_document(self, doc: Document | None):
        if self.doc is not None:
            try:
                self.doc.calques_changes.disconnect(self.rafraichir)
            except (RuntimeError, TypeError):
                pass
        self.doc = doc
        self._vignettes.clear()
        if doc is not None:
            doc.calques_changes.connect(self.rafraichir)
        self.rafraichir()

    def appliquer_icones(self):
        for nom, b in self.boutons.items():
            b.setIcon(self.icones(nom))
        self.rafraichir()

    def _vignette(self, img: QImage, masque: bool = False) -> QPixmap:
        cle = (img.cacheKey(), masque)
        if cle not in self._vignettes:
            # la vignette a la forme de l'image (damier seulement sous l'image : pas de bandes vides autour)
            petit = img.scaled(VIGNETTE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            taille = petit.size().expandedTo(QSize(4, 4))
            if masque:
                pm = QPixmap(taille)
                pm.fill(QColor(0, 0, 0))
            else:
                pm = damier(taille)
            p = QPainter(pm)
            p.drawImage(0, 0, petit)
            p.setPen(QColor(128, 128, 128, 140))           # fin bord : on voit où s'arrête l'image
            p.drawRect(0, 0, taille.width() - 1, taille.height() - 1)
            p.end()
            if len(self._vignettes) > 300:
                self._vignettes.clear()
            self._vignettes[cle] = pm
        return self._vignettes[cle]

    def _vignette_icone(self, nom: str) -> QPixmap:
        cle = ("icone", nom)
        if cle not in self._vignettes:
            pm = QPixmap(VIGNETTE)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            self.icones(nom).paint(p, (VIGNETTE.width() - 26) // 2, (VIGNETTE.height() - 26) // 2, 26, 26)
            p.end()
            self._vignettes[cle] = pm
        return self._vignettes[cle]

    def _lignes(self) -> list[int]:
        """Index des calques montrés (du haut vers le bas) : ceux d'un groupe replié sont cachés."""
        doc = self.doc
        res = []
        for i in range(len(doc.calques) - 1, -1, -1):
            if all(g.ouvert for g in parents(doc.calques, i)):
                res.append(i)
        return res

    def rafraichir(self):
        doc = self.doc
        self._indexes = self._lignes() if doc else []
        n = len(self._indexes)
        self.liste.blockSignals(True)
        while self.liste.count() > n:
            self.liste.takeItem(self.liste.count() - 1)
        while self.liste.count() < n:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, VIGNETTE.height() + 10))
            self.liste.addItem(item)
            ligne = LigneCalque(self.icones)
            ligne.oeil_clique.connect(lambda l=ligne: self._oeil(l))
            ligne.cadenas_clique.connect(lambda l=ligne: self._cadenas(l))
            ligne.fleche_cliquee.connect(lambda l=ligne: self._plier(l))
            ligne.vignette_cliquee.connect(lambda maj, l=ligne: self._vignette_cliquee(l, maj))
            ligne.masque_clique.connect(lambda maj, l=ligne: self._masque_clique(l, maj))
            self.liste.setItemWidget(item, ligne)
        if doc and doc.calque_actif.masque is None:
            doc.cible_masque = False
        if doc is None or self._vu != (doc, len(doc.calques)):
            self.choisis = set()
            self._vu = (doc, len(doc.calques)) if doc else (None, 0)
        if doc:
            self.choisis = {i for i in self.choisis if 0 <= i < len(doc.calques)}
            if doc.actif not in self.choisis:
                self.choisis = {doc.actif}
        for rang, index in enumerate(self._indexes):
            c = doc.calques[index]
            ligne = self.liste.itemWidget(self.liste.item(rang))
            ligne.index = index
            if c.groupe:
                vig = self._vignette_icone("dossier")
            elif c.reglage is not None:
                vig = self._vignette_icone("reglage_calque")
            else:
                vig = self._vignette(c.image)
            vm = self._vignette(c.masque, True) if c.masque is not None else None
            from .composition import visible_en_vrai
            ligne.remplir(c, vig, vm, len(parents(doc.calques, index)), doc.cible_masque, index == doc.actif,
                          visible_en_vrai(doc.calques, index))
            ligne.marquer(index in self.choisis and index != doc.actif)
        if doc:
            if doc.actif in self._indexes:
                self.liste.setCurrentRow(self._indexes.index(doc.actif))
            if not self.curseur.isSliderDown():
                self.curseur.blockSignals(True)
                self.curseur.setValue(round(doc.calque_actif.opacite * 100))
                self.curseur.blockSignals(False)
            self.valeur.setText(f"{self.curseur.value()} %")
            k = self.mode.findData(doc.calque_actif.mode)
            self.mode.setCurrentIndex(max(0, k))
        self.liste.blockSignals(False)
        for nom, b in self.boutons.items():
            b.setEnabled(bool(doc))
        verrou = bool(doc) and doc.calque_actif.verrou
        if doc:
            c = doc.calque_actif
            self.boutons["supprimer"].setEnabled(doc.etat_supprimer_choisis(self.choisis) is not None)
            self.boutons["aplatir"].setEnabled(len(doc.calques) > 1 and not any(x.verrou for x in doc.calques))
            plusieurs = len(self.choisis) > 1
            self.boutons["fusionner"].setEnabled((doc.etat_fusionner_choisis(self.choisis) if plusieurs
                                                  else doc.etat_fusionner_bas()) is not None)
            self.boutons["fusionner"].setToolTip(tr("Fusionner les {n} calques choisis (Ctrl+E)", n=len(self.choisis))
                                                 if plusieurs else tr("Fusionner avec le calque du dessous (Ctrl+E)"))
            self.boutons["supprimer"].setToolTip(tr("Supprimer les {n} calques choisis", n=len(self.choisis))
                                                 if plusieurs else tr("Supprimer le calque"))
            self.boutons["monter"].setEnabled(doc.etat_deplacer(doc.actif, doc.actif + 1) is not None)
            self.boutons["descendre"].setEnabled(doc.etat_deplacer(doc.actif, doc.actif - 1) is not None)
            self.boutons["masque"].setEnabled(c.masque is None and not verrou)
            self.boutons["style"].setEnabled(not c.special)
        self.curseur.setEnabled(bool(doc) and not verrou)
        self.mode.setEnabled(bool(doc) and not verrou and not (doc and doc.calque_actif.reglage is not None))
        self.curseur.setToolTip(tr("Calque verrouillé") if verrou else "")

    # ---------------------------------------------------------- glisser un calque
    def _rang_cible(self, y: float) -> int:
        """Place visée (0 = tout en haut) d'après la hauteur de la souris : au-dessus ou en dessous de la ligne
        survolée selon sa moitié."""
        n = self.liste.count()
        for rang in range(n):
            r = self.liste.visualItemRect(self.liste.item(rang))
            if y < r.center().y():
                return rang
        return n

    def eventFilter(self, obj, ev):
        if obj is not self.liste.viewport() or self.doc is None:
            return False
        t = ev.type()
        if t == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            it = self.liste.itemAt(ev.position().toPoint())
            if it is not None and self._choisir_avec_touches(self.liste.row(it), ev.modifiers()):
                self._glisse = None
                return True
            self._glisse = {"depart": ev.position(), "rang": self.liste.row(it), "actif": False} if it else None
        elif t == QEvent.MouseMove and self._glisse is not None and ev.buttons() & Qt.LeftButton:
            g = self._glisse
            if not g["actif"] and (ev.position() - g["depart"]).manhattanLength() >=                     QApplication.startDragDistance():
                g["actif"] = True
                self.liste.setCursor(Qt.ClosedHandCursor)
            if g["actif"]:
                cible = self._rang_cible(ev.position().y())
                n = self.liste.count()
                if cible < n:
                    y = self.liste.visualItemRect(self.liste.item(cible)).top()
                else:
                    y = self.liste.visualItemRect(self.liste.item(n - 1)).bottom()
                self._trait.setGeometry(0, max(0, y - 1), self.liste.viewport().width(), 3)
                self._trait.show()
                self._trait.raise_()
                return True
        elif t == QEvent.MouseButtonRelease and self._glisse is not None:
            g, self._glisse = self._glisse, None
            self._trait.hide()
            self.liste.unsetCursor()
            if g["actif"]:
                self.deposer(g["rang"], self._rang_cible(ev.position().y()))
                return True
        return False

    def deposer(self, rang: int, cible: int):
        """Calque de la ligne « rang » posé avant la ligne « cible » (lignes du haut vers le bas) : il avance d'une
        place à la fois (règles de Monter / Descendre : entre dans un groupe ouvert, sort d'un groupe), une seule
        entrée dans Annuler."""
        doc = self.doc
        if not (0 <= rang < len(self._indexes)) or cible in (rang, rang + 1):
            return
        index = self._indexes[rang]
        sens = 1 if cible < rang else -1                  # vers le haut de la liste = index plus grand
        voulu = cible if sens > 0 else cible - 1          # ligne où le calque doit arriver
        sauve = (doc.calques, doc.actif)
        etat = None
        try:
            doc.actif = index
            for _ in range(2 * len(doc.calques) + 2):
                e = doc.etat_deplacer(doc.actif, doc.actif + sens)
                if e is None:
                    break
                etat = e
                doc.calques, doc.actif = e[0], e[1]
                lignes = self._lignes()
                if doc.actif not in lignes:
                    break
                ici = lignes.index(doc.actif)
                if (sens > 0 and ici <= voulu) or (sens < 0 and ici >= voulu):
                    # un pas de plus qui ne change pas la ligne : il entre dans le groupe juste au-dessus
                    e2 = doc.etat_deplacer(doc.actif, doc.actif + sens)
                    if sens > 0 and e2 is not None:
                        doc.calques, doc.actif = e2[0], e2[1]
                        lignes2 = self._lignes()
                        if doc.actif in lignes2 and lignes2.index(doc.actif) == ici:
                            etat = e2
                    break
        finally:
            doc.calques, doc.actif = sauve
            doc._fusion = None
        if etat is not None:
            self.demande.emit(etat, tr("Déplacer le calque"))

    # ---------------------------------------------------------- plusieurs calques, menu du clic droit
    def _choisir_avec_touches(self, rang: int, touches) -> bool:
        """Ctrl+clic : ajoute ou retire le calque des choisis ; Maj+clic : tous ceux entre le calque actif et celui-ci.
        Clic simple : ce calque seul. -> True si le clic est traité ici (Ctrl ou Maj)."""
        doc = self.doc
        if not (0 <= rang < len(self._indexes)):
            return False
        index = self._indexes[rang]
        if touches & Qt.ControlModifier:
            if index in self.choisis and len(self.choisis) > 1:
                self.choisis.discard(index)
                if doc.actif == index:
                    doc.actif = max(self.choisis)
            else:
                self.choisis.add(index)
                doc.actif = index
        elif touches & Qt.ShiftModifier:
            depart = self._indexes.index(doc.actif) if doc.actif in self._indexes else rang
            a, b = sorted((depart, rang))
            self.choisis = set(self._indexes[a:b + 1])
            doc.actif = index
        else:
            self.choisis = {index}
            return False
        doc.cible_masque = False
        doc.calques_changes.emit()
        return True

    def _menu_contextuel(self, pos):
        menu = self.menu_calque(pos)
        if menu is not None:
            menu.exec(self.liste.viewport().mapToGlobal(pos))

    def menu_calque(self, pos) -> QMenu | None:
        """Menu du clic droit à l'endroit `pos` de la liste (sur un calque, sur plusieurs choisis, ou dans le vide)."""
        doc = self.doc
        if doc is None:
            return None
        it = self.liste.itemAt(pos)
        menu = QMenu(self)
        if it is not None:
            index = self._indexes[self.liste.row(it)]
            if index not in self.choisis:                 # clic droit hors des choisis : ce calque seul
                self.choisis = {index}
                doc.actif = index
                doc.calques_changes.emit()
            c = doc.calque_actif
            n = len(self.choisis)
            if n > 1:
                a = menu.addAction(tr("Fusionner les {n} calques choisis", n=n), self.fusionner)
                a.setShortcut("Ctrl+E")
                a.setEnabled(doc.etat_fusionner_choisis(self.choisis) is not None)
                a = menu.addAction(tr("Supprimer les {n} calques choisis", n=n), self.supprimer)
                a.setEnabled(doc.etat_supprimer_choisis(self.choisis) is not None)
                menu.addSeparator()
                menu.addAction(tr("Afficher les calques choisis"), lambda: self._visibles(True))
                menu.addAction(tr("Masquer les calques choisis"), lambda: self._visibles(False))
            else:
                menu.addAction(tr("Renommer…"), self.renommer)
                menu.addAction(tr("Dupliquer le calque"), self.dupliquer).setShortcut("Ctrl+J")
                a = menu.addAction(tr("Supprimer le calque"), self.supprimer)
                a.setEnabled(doc.etat_supprimer_choisis(self.choisis) is not None)
                menu.addSeparator()
                a = menu.addAction(tr("Fusionner avec le calque du dessous"), self.fusionner)
                a.setShortcut("Ctrl+E")
                a.setEnabled(doc.etat_fusionner_bas() is not None)
                a = menu.addAction(tr("Aplatir l'image"), self.aplatir)
                a.setEnabled(len(doc.calques) > 1 and not any(x.verrou for x in doc.calques))
                menu.addSeparator()
                menu.addAction(tr("Grouper les calques"), self.grouper).setShortcut("Ctrl+G")
                if c.groupe:
                    menu.addAction(tr("Dégrouper"), self.degrouper).setShortcut("Ctrl+Shift+G")
                if not c.special:
                    menu.addAction(tr("Style du calque…"), self.style_demande.emit).setShortcut("Ctrl+Alt+F")
                if self.peut_ecreter():
                    menu.addAction(tr("Retirer le masque d'écrêtage") if c.ecretage else
                                   tr("Créer un masque d'écrêtage"), self.ecreter).setShortcut("Ctrl+Alt+G")
                if c.masque is None and not c.verrou:
                    menu.addAction(tr("Ajouter un masque (d'après la sélection s'il y en a une)"),
                                   lambda: self.ajouter_masque())
                if (c.texte is not None or calque_pinceau.valide(c) is not None
                        or calque_forme.valide(c) is not None or calque_remplissage.valide(c) is not None) \
                        and not c.verrou:
                    menu.addAction(tr("Convertir en image"), lambda: self.demande.emit(
                        doc.etat_en_pixels(doc.actif), tr("Convertir en image")))
                if not c.verrou and not c.groupe and c.reglage is None:
                    sous = menu.addMenu(tr("Pixelliser"))
                    for quoi, texte, ok in (
                            ("texte", tr("Texte"), c.texte is not None),
                            ("forme", tr("Forme, pinceau, remplissage"),
                             c.forme is not None or c.pinceau is not None or c.remplissage is not None),
                            ("style", tr("Style du calque"), c.style is not None and not c.style.vide()),
                            ("dynamique", tr("Objet dynamique"), c.origine is not None)):
                        sous.addAction(texte, lambda q=quoi: self.pixelliser_demande.emit(q)).setEnabled(ok)
                    sous.addSeparator()
                    sous.addAction(tr("Calque entier"), lambda: self.pixelliser_demande.emit("tout"))
                menu.addSeparator()
                menu.addAction(tr("Masquer le calque") if c.visible else tr("Afficher le calque"),
                               lambda: self._visibles(not c.visible))
                menu.addAction(tr("Déverrouiller le calque") if c.verrou else tr("Verrouiller le calque"),
                               lambda: self.demande.emit(doc.etat_calque_modifie(doc.actif, verrou=not c.verrou),
                                                         tr("Déverrouiller le calque") if c.verrou
                                                         else tr("Verrouiller le calque")))
            menu.addSeparator()
        menu.addAction(tr("Nouveau calque"), self.nouveau).setShortcut("Ctrl+Shift+N")
        menu.addAction(tr("Nouveau groupe"), self.nouveau_groupe)
        return menu

    def _visibles(self, oui: bool):
        doc = self.doc
        calques = [replace(c, visible=oui) if i in self.choisis else c for i, c in enumerate(doc.calques)]
        self.demande.emit(doc.etat_avec(calques), tr("Afficher le calque") if oui else tr("Masquer le calque"))

    # ---------------------------------------------------------- actions
    def _ligne_choisie(self, rang: int):
        """Changer de calque actif n'est pas une retouche : pas d'entrée dans Annuler."""
        if self.doc and 0 <= rang < len(self._indexes):
            nouveau = self._indexes[rang]
            if nouveau != self.doc.actif:
                self.doc.cible_masque = False
            self.doc.actif = nouveau
            self.doc.calques_changes.emit()        # panneau, canevas et panneau Texte suivent

    def _choisir(self, index: int):
        if self.doc.actif != index:
            self.doc.actif = index
        self.doc.calques_changes.emit()

    def _vignette_cliquee(self, ligne: LigneCalque, _maj: bool):
        self.doc.cible_masque = False
        self._choisir(ligne.index)

    def _masque_clique(self, ligne: LigneCalque, maj: bool):
        c = self.doc.calques[ligne.index]
        if maj and c.masque is not None:
            texte = tr("Réactiver le masque") if not c.masque_actif else tr("Désactiver le masque")
            self.demande.emit(self.doc.etat_calque_modifie(ligne.index, masque_actif=not c.masque_actif), texte)
            return
        self.doc.actif = ligne.index
        self.doc.cible_masque = True
        self.doc.calques_changes.emit()

    def _oeil(self, ligne: LigneCalque):
        c = self.doc.calques[ligne.index]
        texte = tr("Masquer le calque") if c.visible else tr("Afficher le calque")
        self.demande.emit(self.doc.etat_calque_modifie(ligne.index, visible=not c.visible), texte)

    def _cadenas(self, ligne: LigneCalque):
        c = self.doc.calques[ligne.index]
        texte = tr("Déverrouiller le calque") if c.verrou else tr("Verrouiller le calque")
        self.demande.emit(self.doc.etat_calque_modifie(ligne.index, verrou=not c.verrou), texte)

    def _plier(self, ligne: LigneCalque):
        """Replier / déplier un groupe : simple affichage, sans entrée dans Annuler."""
        from dataclasses import replace
        c = self.doc.calques[ligne.index]
        calques = list(self.doc.calques)
        calques[ligne.index] = replace(c, ouvert=not c.ouvert)
        self.doc.calques = tuple(calques)
        self.doc.actif = ligne.index
        self.doc.calques_changes.emit()

    def _mode_choisi(self, _k: int):
        if not self.doc:
            return
        m = self.mode.currentData()
        if m and m != self.doc.calque_actif.mode:
            self.demande.emit(self.doc.etat_calque_modifie(self.doc.actif, mode=m), tr("Mode de fusion"))

    def _opacite_debut(self):
        self._avant_opacite = self.doc.etat()

    def _opacite_change(self, v: int):
        self.valeur.setText(f"{v} %")
        if not self.doc:
            return
        etat = self.doc.etat_calque_modifie(self.doc.actif, opacite=v / 100)
        if self.curseur.isSliderDown():
            self.doc.appliquer_etat(etat)              # aperçu en direct ; l'entrée Annuler est créée au lâcher
        else:
            self.demande.emit(etat, tr("Opacité du calque"))

    def _opacite_fin(self):
        if self._avant_opacite is not None:
            apres = self.doc.etat()
            avant, self._avant_opacite = self._avant_opacite, None
            self.doc.appliquer_etat(avant)
            self.demande.emit(apres, tr("Opacité du calque"))

    def nouveau(self):
        self.demande.emit(self.doc.etat_nouveau_calque(), tr("Nouveau calque"))

    def nouveau_groupe(self):
        self.demande.emit(self.doc.etat_nouveau_groupe(), tr("Nouveau groupe"))

    def grouper(self):
        """Ctrl+G : les calques choisis (Ctrl+clic, Maj+clic) dans un même nouveau groupe."""
        self.demande.emit(self.doc.etat_grouper(set(self.choisis) | {self.doc.actif}), tr("Grouper"))

    def peut_ecreter(self) -> bool:
        """Masque d'écrêtage possible : calque de pixels (ou texte) avec un calque juste en dessous, dans le même
        groupe."""
        doc = self.doc
        if doc is None or not doc.calques:
            return False
        i = doc.actif
        c = doc.calques[i]
        if c.special or c.verrou or i == 0:
            return False
        return doc.calques[i - 1].dans == c.dans

    def ecreter(self):
        """Ctrl+Alt+G : le calque ne se voit que dans les pixels du calque juste en dessous (ex. une photo dans les
        lettres d'un texte) ; encore une fois : retiré."""
        doc = self.doc
        if not self.peut_ecreter():
            return
        c = doc.calques[doc.actif]
        self.demande.emit(doc.etat_calque_modifie(doc.actif, ecretage=not c.ecretage),
                          tr("Retirer le masque d'écrêtage") if c.ecretage else tr("Créer un masque d'écrêtage"))

    def degrouper(self):
        etat = self.doc.etat_degrouper()
        if etat:
            self.demande.emit(etat, tr("Dégrouper"))

    def ajouter_masque(self, quoi: str | None = None):
        if quoi is None:
            quoi = "blanc" if self.doc.selection_vide() else "selection"
        etat = self.doc.etat_ajouter_masque(quoi)
        if etat:
            self.demande.emit(etat, tr("Ajouter un masque"))
            self.doc.cible_masque = True
            self.doc.calques_changes.emit()

    def _menu_reglage(self):
        menu = QMenu(self)
        # comme Photoshop : les calques de remplissage d'abord, puis les calques de réglage
        for g, nom in calque_remplissage.noms_genres().items():
            menu.addAction(nom + "…", lambda *_, g=g: self.reglage_demande.emit("remplissage:" + g))
        menu.addSeparator()
        for t in ajustements.TYPES:
            menu.addAction(ajustements.nom(t), lambda *_, t=t: self.reglage_demande.emit(t))
        b = self.boutons["reglage"]
        menu.exec(b.mapToGlobal(b.rect().bottomLeft()))

    def dupliquer(self):
        self.demande.emit(self.doc.etat_dupliquer(), tr("Dupliquer le calque"))

    def deplacer(self, sens: int):
        etat = self.doc.etat_deplacer(self.doc.actif, self.doc.actif + sens)
        if etat:
            self.demande.emit(etat, tr("Monter le calque") if sens > 0 else tr("Descendre le calque"))

    def fusionner(self):
        """Plusieurs calques choisis : ils sont fusionnés ensemble ; sinon, avec le calque du dessous (Ctrl+E)."""
        if self.doc is None:
            return
        plusieurs = len(self.choisis) > 1
        etat = self.doc.etat_fusionner_choisis(self.choisis) if plusieurs else self.doc.etat_fusionner_bas()
        if etat:
            self.demande.emit(etat, tr("Fusionner les calques"))
        elif plusieurs:
            self.refus.emit(tr("Impossible de fusionner : un des calques choisis est verrouillé, est un groupe ou un "
                               "calque de réglage."))

    def aplatir(self):
        etat = self.doc.etat_aplatir()
        if etat:
            self.demande.emit(etat, tr("Aplatir l'image"))

    def supprimer(self):
        etat = self.doc.etat_supprimer_choisis(self.choisis or {self.doc.actif})
        if etat:
            self.demande.emit(etat, tr("Supprimer les calques") if len(self.choisis) > 1 else tr("Supprimer le calque"))

    def _double_clic(self, item):
        """Comme Photoshop : double-clic sur le nom = renommer ; ailleurs : éditer le texte (calque de texte), réglage
        (calque de réglage) ou style (le style d'un texte reste au bouton fx)."""
        ligne = self.liste.itemWidget(item)
        p = ligne.nom.mapFromGlobal(QCursor.pos()) if ligne is not None else None
        largeur = ligne.nom.fontMetrics().horizontalAdvance(ligne.nom.text()) + 10 if ligne is not None else 0
        if p is not None and 0 <= p.y() < ligne.nom.height() and p.x() < largeur:
            self.renommer()
        elif self.doc and self.doc.calque_actif.texte is not None:
            self.texte_demande.emit()
        elif self.doc and (self.doc.calque_actif.reglage is not None
                           or calque_remplissage.valide(self.doc.calque_actif) is not None):
            self.reglage_demande.emit("")             # calque de réglage ou de remplissage : sa fenêtre
        elif self.doc and not self.doc.calque_actif.groupe:
            self.style_demande.emit()

    def renommer(self):
        if not self.doc:
            return
        c = self.doc.calque_actif
        nom, ok = QInputDialog.getText(self, tr("Renommer le calque"), tr("Nom :"), text=c.nom)
        if ok and nom.strip() and nom.strip() != c.nom:
            self.demande.emit(self.doc.etat_calque_modifie(self.doc.actif, nom=nom.strip()), tr("Renommer le calque"))
