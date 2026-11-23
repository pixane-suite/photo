"""Partie « fenêtre » des outils ajoutés (voir outils_plus.py) : leurs boutons dans la boîte à outils, leurs options
dans la barre du haut, et ce qu'ils font une fois le geste fini (Pièce, Déplacer un objet, Redresser avec la règle).
Fenetre (fenetre.py) hérite de FenetrePlusMixin."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QSlider, QToolButton, QWidget)

from .langue import tr
from .outils_plus import (CRAYON, DEPLACER_IA, ECHANTILLONS, ELLIPSE_SEL, LASSO_MAG, LOUPE, MELANGEUR, PIECE,
                          PIPETTE, REGLE, ROTATION_VUE, angle_pour_redresser, appliquer_piece)


def outils_plus():
    """(outil, texte, raccourci, icône) des outils ajoutés, pour la boîte à outils."""
    return (
        (ELLIPSE_SEL, tr("Sélection elliptique (Maj : ajouter, Alt : retirer)"), "", "ellipse_sel"),
        (LASSO_MAG, tr("Lasso magnétique : suis le bord de l'objet, le trait s'y colle"), "", "lasso_mag"),
        (PIECE, tr("Pièce : entoure un défaut, puis glisse-le sur une partie saine qui le remplace"), "", "piece"),
        (DEPLACER_IA, tr("Déplacer un objet (IA) : glisse l'objet sélectionné ; sa place d'origine est "
                         "reconstruite"), "", "deplacer_ia"),
        (PIPETTE, tr("Pipette : prend une couleur de la photo"), "I", "pipette"),
        (REGLE, tr("Règle : mesure une distance et un angle ; peut redresser la photo"), "", "regle"),
        (LOUPE, tr("Loupe : clic pour agrandir, Alt+clic pour réduire, cadre pour zoomer dessus"), "Z", "loupe"),
        (ROTATION_VUE, tr("Rotation de la vue : tourne l'affichage (pas la photo) ; double-clic : vue droite"),
         "Shift+H", "rotation_vue"),
        (CRAYON, tr("Crayon : trait net, sans bord adouci (pixel art)"), "N", "crayon"),
        (MELANGEUR, tr("Pinceau mélangeur : la couleur du pinceau se mêle à celle de la toile"), "", "melangeur"),
    )


def aides() -> dict:
    return {
        ELLIPSE_SEL: tr("Sélection elliptique : glisse pour tracer l'ellipse. Maj : ajouter, Alt : retirer. Un simple clic "
                     "désélectionne."),
        LASSO_MAG: tr("Lasso magnétique : clique au bord de l'objet, puis suis ce bord : le trait s'y colle. Clic = point "
                   "d'ancrage ; double-clic, Entrée ou clic sur le départ pour fermer ; Retour arrière enlève le "
                   "dernier ancrage ; Échap abandonne."),
        PIECE: tr("Pièce : entoure le défaut (ou garde ta sélection), puis glisse-le sur une partie saine : elle le "
               "remplace, raccordée à la lumière autour."),
        DEPLACER_IA: tr("Déplacer un objet (IA) : sélectionne l'objet, puis glisse-le ; il part dans un nouveau calque et "
                     "l'IA reconstruit le fond à sa place d'origine (propositions au choix)."),
        PIPETTE: tr("Pipette : clic (ou glisser) sur la photo ; la couleur devient celle du pinceau. Choisis en haut la "
                 "taille de l'échantillon."),
        REGLE: tr("Règle : glisse d'un point à un autre (Maj : par 15°) ; la longueur et l'angle s'affichent. « Redresser » "
               "tourne la photo pour rendre la ligne droite. Échap efface la règle."),
        LOUPE: tr("Loupe : clic pour agrandir, Alt+clic pour réduire, ou tire un cadre sur la partie à voir en grand."),
        ROTATION_VUE: tr("Rotation de la vue : glisse pour tourner l'affichage, comme une feuille sur la table (Maj : par "
                      "15°). La photo ne change pas. Double-clic : vue droite."),
        CRAYON: tr("Crayon : trait net, pixel par pixel, sans bord adouci ; idéal en pixel art (taille 1 à quelques px)."),
        MELANGEUR: tr("Pinceau mélangeur : peins ; la couleur du pinceau se mêle à celle de la toile et s'épuise peu à peu. "
                   "« Mélange » en haut : part de la toile reprise."),
    }


class FenetrePlusMixin:

    # ---------------------------------------------------------- barre du haut
    def _options_plus(self, tout):
        c = self.canevas
        self.opt_pipette = QWidget()
        lay = QHBoxLayout(self.opt_pipette)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Échantillon")))
        self.opt_pipette_ech = QComboBox()
        for n in ECHANTILLONS:
            self.opt_pipette_ech.addItem(tr("1 pixel") if n == 1 else tr("Moyenne {n} × {n}", n=n), n)
        i = self.opt_pipette_ech.findData(int(self.reglages.value("pipette_echantillon", 1) or 1))
        self.opt_pipette_ech.setCurrentIndex(max(0, i))
        c.echantillon = self.opt_pipette_ech.currentData()

        def echantillon(*_):
            c.echantillon = self.opt_pipette_ech.currentData()
            self.reglages.setValue("pipette_echantillon", c.echantillon)
        self.opt_pipette_ech.currentIndexChanged.connect(echantillon)
        lay.addWidget(self.opt_pipette_ech)
        self.opt_pipette_calque = QCheckBox(tr("Calque choisi seulement"))
        self.opt_pipette_calque.setToolTip(tr("Coché : la couleur du calque choisi ; sinon, l'image telle qu'on la "
                                              "voit"))
        self.opt_pipette_calque.toggled.connect(lambda v: setattr(c, "pipette_calque", v))
        lay.addWidget(self.opt_pipette_calque)
        tout.addWidget(self.opt_pipette)

        self.opt_symetrie = QToolButton()               # petit bouton à menu : la barre du haut reste étroite
        self.opt_symetrie.setPopupMode(QToolButton.InstantPopup)
        self.opt_symetrie.setAutoRaise(True)
        self._icone(self.opt_symetrie, "sym_h")
        menu = QMenu(self.opt_symetrie)
        groupe = QActionGroup(self.opt_symetrie)
        self._actions_symetrie = {}
        for cle, texte in (("", tr("Aucune")), ("v", tr("Gauche ↔ droite")), ("h", tr("Haut ↔ bas")),
                           ("vh", tr("Les deux (4 traits)"))):
            a = menu.addAction(texte)
            a.setCheckable(True)
            a.setChecked(cle == "")
            groupe.addAction(a)
            a.triggered.connect(lambda _=False, k=cle: self.definir_symetrie(k))
            self._actions_symetrie[cle] = a
        self.opt_symetrie.setMenu(menu)
        self.opt_symetrie.setToolTip(tr("Peinture en symétrie : chaque trait est aussi peint en miroir, de l'autre "
                                        "côté du milieu de l'image"))
        tout.addWidget(self.opt_symetrie)

        self.opt_melangeur = QWidget()
        lay = QHBoxLayout(self.opt_melangeur)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Mélange")))
        self.opt_melange = QSlider(Qt.Horizontal)
        self.opt_melange.setRange(0, 100)
        self.opt_melange.setValue(int(self.reglages.value("melange", 50) or 50))
        self.opt_melange.setFixedWidth(110)
        self.opt_melange.setToolTip(tr("0 % : surtout la couleur du pinceau ; 100 % : surtout celle de la toile"))
        c.melange = self.opt_melange.value() / 100

        def melange(v):
            c.melange = v / 100
            self.reglages.setValue("melange", v)
        self.opt_melange.valueChanged.connect(melange)
        lay.addWidget(self.opt_melange)
        tout.addWidget(self.opt_melangeur)

        self.opt_regle = QWidget()
        lay = QHBoxLayout(self.opt_regle)
        lay.setContentsMargins(0, 0, 0, 0)
        self.texte_regle = QLabel(tr("Glisse sur la photo pour mesurer."))
        lay.addWidget(self.texte_regle)
        self.b_redresser_regle = QPushButton(tr("Redresser"))
        self.b_redresser_regle.setToolTip(tr("Tourne la photo pour que la ligne de la règle devienne horizontale "
                                             "(ou verticale)"))
        self.b_redresser_regle.clicked.connect(self.redresser_avec_regle)
        lay.addWidget(self.b_redresser_regle)
        b = QPushButton(tr("Effacer"))
        b.clicked.connect(self._effacer_regle)
        lay.addWidget(b)
        tout.addWidget(self.opt_regle)
        c.regle_changee.connect(self._maj_regle)
        self._maj_regle()

        self.opt_vue = QWidget()
        lay = QHBoxLayout(self.opt_vue)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Angle de la vue")))
        self.opt_angle_vue = QDoubleSpinBox()
        self.opt_angle_vue.setRange(-180, 180)
        self.opt_angle_vue.setSuffix(" °")
        self.opt_angle_vue.setDecimals(0)
        self.opt_angle_vue.valueChanged.connect(
            lambda v: c.definir_angle_vue(v) if abs(v - c.angle_vue) > 0.4 else None)
        lay.addWidget(self.opt_angle_vue)
        b = QPushButton(tr("Vue droite"))
        b.clicked.connect(lambda: c.definir_angle_vue(0))
        lay.addWidget(b)
        tout.addWidget(self.opt_vue)

        for w in (self.opt_pipette, self.opt_symetrie, self.opt_melangeur, self.opt_regle, self.opt_vue):
            w.hide()
        c.piece_glissee.connect(self._piece)
        c.objet_deplace.connect(self._deplacer_objet)

    def definir_symetrie(self, cle: str):
        self.canevas.symetrie = cle
        self._actions_symetrie[cle].setChecked(True)
        self.opt_symetrie.setText(tr("Symétrie"))
        self.opt_symetrie.setToolButtonStyle(Qt.ToolButtonTextBesideIcon if cle else Qt.ToolButtonIconOnly)
        if cle:
            self.statusBar().showMessage(tr("Symétrie : {quoi}", quoi=self._actions_symetrie[cle].text()), 5000)

    def _visibilite_plus(self, outil: str):
        from .canevas import OUTILS_FILTRE, PEINTURE
        self.opt_pipette.setVisible(outil == PIPETTE)
        self.opt_symetrie.setVisible(outil in (PEINTURE, CRAYON, MELANGEUR) + OUTILS_FILTRE)
        self.opt_melangeur.setVisible(outil == MELANGEUR)
        self.opt_regle.setVisible(outil == REGLE)
        self.opt_vue.setVisible(outil == ROTATION_VUE)
        if outil == ROTATION_VUE:
            self.opt_angle_vue.blockSignals(True)
            self.opt_angle_vue.setValue(round(self.canevas.angle_vue))
            self.opt_angle_vue.blockSignals(False)
        if outil != LASSO_MAG:
            self.canevas.annuler_magnetique()
        a = aides()
        if outil in a:
            self.statusBar().showMessage(a[outil], 12000)

    # ---------------------------------------------------------- règle
    def _maj_regle(self):
        r = self.canevas.regle
        ok = r is not None and (r[1] - r[0]).manhattanLength() > 2
        self.texte_regle.setText(self.canevas.texte_regle() if ok else tr("Glisse sur la photo pour mesurer."))
        self.b_redresser_regle.setEnabled(ok)

    def _effacer_regle(self):
        self.canevas.regle = None
        self._maj_regle()
        self.canevas.update()

    def redresser_avec_regle(self):
        r = self.canevas.regle
        if not self.doc or r is None or not self._verifier_verrou(tr("Redresser"), tous=True):
            return
        angle = angle_pour_redresser(*r)
        if abs(angle) < 0.05:
            self.statusBar().showMessage(tr("La ligne est déjà droite."), 5000)
            return
        from .fenetre import CommandeEtat
        avant = self.doc.etat()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            apres = self.doc.etat_redresse(angle, True)
        finally:
            QApplication.restoreOverrideCursor()
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Redresser")))
        self._effacer_regle()

    # ---------------------------------------------------------- Pièce
    def _piece(self, dx: int, dy: int):
        doc = self.doc
        if not doc or doc.selection_vide() or not self._verifier_verrou(tr("Pièce")):
            return
        c = doc.calque_actif
        if c.special:
            self.statusBar().showMessage(tr("Choisis un calque d'image pour l'outil Pièce."), 6000)
            return
        from .fenetre import CommandeEtat
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            img = appliquer_piece(c.image, doc.selection, dx, dy)
        finally:
            QApplication.restoreOverrideCursor()
        if c.texte is not None:                          # un texte touché devient des pixels
            apres = doc.etat_calque_modifie(doc.actif, image=img, texte=None)
        else:
            apres = doc.etat_calque_modifie(doc.actif, image=img)
        self.historique.push(CommandeEtat(doc, doc.etat(), apres, tr("Pièce")))

    # ---------------------------------------------------------- Déplacer un objet (IA)
    def _deplacer_objet(self, dx: int, dy: int):
        doc = self.doc
        if not doc or doc.selection_vide() or not self._verifier_verrou(tr("Déplacer un objet")):
            return
        from . import recettes
        from .fenetre import CommandeEtat
        img, place = doc.pixels_choisis()
        nouvelle_place = QPoint(place.x() + dx, place.y() + dy)
        nom = doc.calque_actif.nom

        def poser():
            if doc is self.doc:
                self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_coller(img, nouvelle_place,
                                                                                    tr("{nom} déplacé", nom=nom)),
                                                  tr("Déplacer un objet")))
        self.statusBar().showMessage(tr("L'IA reconstruit le fond à la place d'origine ; l'objet sera ensuite posé "
                                        "à sa nouvelle place, dans un nouveau calque."), 10000)
        self._lancer(tr("Déplacer un objet"), True, lambda n: recettes.effacer(n), remplir_trous=True,
                     variante=lambda n, force: recettes.variante(n, force, nb=recettes.NB_EFFACER), ensuite=poser)
