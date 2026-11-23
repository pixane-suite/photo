"""Panneau Texte : réglages du calque de texte choisi (ou du prochain texte si aucun n'est choisi).

Chaque changement est envoyé par `modifie(texte, champ)` ; la fenêtre en fait une entrée d'Annuler
(les changements successifs d'un même réglage sont regroupés).
"""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QEvent, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction as QAction_
from PySide6.QtGui import (QColor, QCursor, QFont, QFontMetrics, QPainter, QPixmap, QSyntaxHighlighter,
                           QKeySequence, QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox,
                               QFontComboBox, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QMessageBox,
                               QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QStyle, QStyledItemDelegate,
                               QToolButton, QVBoxLayout, QWidget)

from .calques import damier
from .langue import tr
from .texte import CENTRE, CHAMPS_LETTRE, DROITE, GAUCHE, JUSTIFIE, Texte, avec_style_texte, forme, style_texte


class BoutonCouleur(QToolButton):
    """Pastille de couleur ; un clic ouvre le choix de couleur (avec la transparence). Pendant le choix, apercu
    donne chaque couleur essayée (pour la montrer tout de suite sur la photo), puis "" quand la fenêtre se ferme ;
    change seulement à OK."""
    change = Signal(str)
    apercu = Signal(str)

    def __init__(self, titre: str):
        super().__init__()
        self.titre = titre
        self.couleur = "#ffffffff"
        self.setIconSize(QSize(34, 16))
        self.setToolTip(titre)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._choisir)
        self.definir(self.couleur)

    def definir(self, couleur: str):
        self.couleur = couleur
        pm = damier(QSize(34, 16), 4)
        p = QPainter(pm)
        p.fillRect(pm.rect(), QColor(couleur))
        p.setPen(QColor(0, 0, 0, 90))
        p.drawRect(pm.rect().adjusted(0, 0, -1, -1))
        p.end()
        self.setIcon(pm)

    def _choisir(self):
        d = QColorDialog(QColor(self.couleur), self)
        d.setWindowTitle(self.titre)
        d.setOption(QColorDialog.ShowAlphaChannel)
        d.currentColorChanged.connect(lambda c: c.isValid() and self.apercu.emit(c.name(QColor.HexArgb)))
        ok = d.exec()
        c = d.currentColor()
        self.apercu.emit("")
        if ok and c.isValid():
            self.definir(c.name(QColor.HexArgb))
            self.change.emit(self.couleur)


def _reglages():
    import os
    from PySide6.QtCore import QSettings
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


EXEMPLE_MAX = 24          # caractères de l'exemple montré dans la liste des polices


class ApercuPolices(QStyledItemDelegate):
    """Liste des polices : le nom (police normale) puis un exemple écrit dans la police, avec le texte tapé ou
    sélectionné (ses premiers caractères), sinon « Aa Bb Cc 123 »."""

    def __init__(self, exemple, parent=None):
        super().__init__(parent)
        self.exemple = exemple            # fonction -> texte de l'exemple
        self.echelle = 1.0                # taille de la liste : petite 1, moyenne 1,5, grande 2,2

    def sizeHint(self, option, index):
        return QSize(int(420 * self.echelle), int(max(30, option.fontMetrics.height() + 14) * self.echelle))

    def paint(self, p: QPainter, option, index):
        p.save()
        if option.state & QStyle.State_Selected:
            p.fillRect(option.rect, option.palette.highlight())
            couleur = option.palette.highlightedText().color()
        else:
            couleur = option.palette.text().color()
        famille = index.data(Qt.DisplayRole) or ""
        r = option.rect.adjusted(8, 0, -8, 0)
        largeur_nom = min(int(190 * min(self.echelle, 1.4)), r.width() // 2)
        p.setPen(couleur)
        f_nom = QFont(option.font)
        if self.echelle > 1 and f_nom.pointSizeF() > 0:
            f_nom.setPointSizeF(f_nom.pointSizeF() * min(self.echelle, 1.4))
        p.setFont(f_nom)
        nom = QFontMetrics(f_nom).elidedText(famille, Qt.ElideRight, largeur_nom - 10)
        p.drawText(QRect(r.x(), r.y(), largeur_nom, r.height()), Qt.AlignVCenter | Qt.AlignLeft, nom)
        police = QFont(famille)
        police.setPixelSize(int(max(14, option.fontMetrics.height() + 4) * self.echelle))
        p.setFont(police)
        zone = QRect(r.x() + largeur_nom, r.y(), r.width() - largeur_nom, r.height())
        texte = QFontMetrics(police).elidedText(self.exemple(), Qt.ElideRight, zone.width())
        p.drawText(zone, Qt.AlignVCenter | Qt.AlignLeft, texte)
        p.restore()


class Soulignement(QSyntaxHighlighter):
    """Mots mal orthographiés soulignés en rouge dans la case du texte (comme un traitement de texte)."""

    def __init__(self, document, langue):
        super().__init__(document)
        self.langue = langue              # fonction -> langue du texte choisi
        self.format = QTextCharFormat()
        self.format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.format.setUnderlineColor(QColor(220, 40, 40))
        self.attente = None               # minuterie : dictionnaire en train de se charger
        self.fini = False
        app = QApplication.instance()
        if app is not None:               # à la fermeture : détaché avant que Qt ne détruise la case (sinon Qt
            app.aboutToQuit.connect(self.detacher)       # appelait encore highlightBlock pendant la destruction)

    def detacher(self):
        self.fini = True
        if self.attente is not None:
            self.attente.stop()
        self.setDocument(None)

    def highlightBlock(self, texte: str):
        if self.fini:
            return
        from . import orthographe as o
        langue = self.langue()
        if not texte or not o.verifiable(langue):
            return
        if not o.pret(langue):           # premier usage : chargé en fond (environ 1 s), puis soulignement
            if self.attente is None:
                o.precharger(langue)
                self.attente = QTimer(self)        # détruite avec le soulignement (pas d'appel après coup)
                self.attente.timeout.connect(lambda: self._verifier_pret(langue))
                self.attente.start(300)
            return
        for a, b in o.fautes(texte, langue):
            self.setFormat(a, b - a, self.format)

    def _verifier_pret(self, langue):
        from . import orthographe as o
        if o.pret(langue):
            self.attente.stop()
            self.attente = None
            self.rehighlight()


TAILLES_LISTE = {"petite": (1.0, 460, 10), "moyenne": (1.5, 640, 14), "grande": (2.2, 880, 16)}


class ChoixPolice(QFontComboBox):
    """Liste des polices qui prévient quand elle se referme (fin de l'aperçu sur la photo) ; filtre par style
    (styles_polices) et taille de la liste, appliqués à l'ouverture."""
    fermee = Signal()

    def __init__(self):
        super().__init__()
        self.style_filtre = ""            # "" : toutes
        self.taille_liste = "petite"

    def showPopup(self):
        echelle, largeur, lignes = TAILLES_LISTE.get(self.taille_liste, TAILLES_LISTE["petite"])
        d = self.itemDelegate()
        if isinstance(d, ApercuPolices):
            d.echelle = echelle
        self.view().setMinimumWidth(largeur)
        self.setMaxVisibleItems(lignes)
        vue = self.view()
        if self.style_filtre:
            from .styles_polices import oublier, style_de
            if self.count() != getattr(self, "_nb_vu", self.count()):
                oublier()                 # police ajoutée ou retirée pendant que Pixane tourne : relire leur style
            self._nb_vu = self.count()
        for i in range(self.count()):
            vue.setRowHidden(i, bool(self.style_filtre) and style_de(self.itemText(i)) != self.style_filtre)
        super().showPopup()

    def hidePopup(self):
        super().hidePopup()
        self.fermee.emit()


def _titre(texte: str) -> QLabel:
    l = QLabel(f"<b>{texte}</b>")
    l.setContentsMargins(0, 8, 0, 0)
    return l


class PanneauTexte(QScrollArea):
    modifie = Signal(object, str)        # (nouveau Texte, nom du réglage changé)
    apercu_texte = Signal(object)        # texte essayé (couleur en train d'être choisie) ; None : fin de l'essai
    selection_lettres = Signal(int, int)  # lettres sélectionnées dans la saisie (début, fin), à montrer sur la photo
    apercu_police = Signal(str)          # police survolée dans la liste ("" : liste fermée, retour au texte)
    tracer = Signal(bool)                # « Dessiner un tracé » enfoncé / relâché

    def __init__(self, icones):
        super().__init__()
        self.icones = icones
        self.defaut = Texte(texte="")    # réglages du prochain texte
        self.t = self.defaut
        self.lie = False                 # vrai si les réglages affichés sont ceux d'un calque de texte
        self._remplissage = False
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(6)
        self.aide = QLabel()
        self.aide.setObjectName("discret")
        self.aide.setWordWrap(True)
        lay.addWidget(self.aide)

        self.saisie = QPlainTextEdit()
        self.saisie.setFixedHeight(76)
        self.saisie.setPlaceholderText(tr("Écris ton texte ici"))
        self.saisie.textChanged.connect(lambda: self._changer("texte", self.saisie.toPlainText()))
        self.saisie.cursorPositionChanged.connect(self._montrer_lettres)
        self.saisie.selectionChanged.connect(self._montrer_lettres)
        self.saisie.installEventFilter(self)
        self.soulignement = Soulignement(self.saisie.document(), lambda: self.t.langue)
        self.saisie.setContextMenuPolicy(Qt.CustomContextMenu)
        self.saisie.customContextMenuRequested.connect(self._menu_saisie)
        pal = self.saisie.palette()              # la sélection reste visible quand on règle à côté
        for role in (pal.ColorRole.Highlight, pal.ColorRole.HighlightedText):
            pal.setColor(pal.ColorGroup.Inactive, role, pal.color(pal.ColorGroup.Active, role))
        self.saisie.setPalette(pal)
        self.saisie.setToolTip(tr("Sélectionne des lettres pour ne changer qu'elles (police, taille, couleur…). "
                                  "Alt+flèches : resserrer ou écarter les deux lettres autour du curseur."))
        lay.addWidget(self.saisie)
        self.portee = QLabel()
        self.portee.setObjectName("discret")
        self.portee.setWordWrap(True)
        lay.addWidget(self.portee)

        # ---- caractères
        lay.addWidget(_titre(tr("Caractères")))
        self.police = ChoixPolice()
        form_liste = self._formulaire(lay)
        self.style_police = QComboBox()
        for cle, nom in (("", tr("Toutes")), ("serif", tr("Avec empattements")), ("sans", tr("Sans empattements")),
                         ("manuscrite", tr("Manuscrites")), ("fantaisie", tr("Fantaisie")),
                         ("fixe", tr("Chasse fixe"))):
            self.style_police.addItem(nom, cle)
        self.style_police.setToolTip(tr("Ne montrer dans la liste des polices que celles de ce style (lu dans "
                                        "chaque police ; quelques polices de fantaisie peuvent être mal rangées)"))
        form_liste.addRow(tr("Style :"), self.style_police)
        self.taille_liste = QComboBox()
        for cle, nom in (("petite", tr("Petite")), ("moyenne", tr("Moyenne")), ("grande", tr("Grande"))):
            self.taille_liste.addItem(nom, cle)
        self.taille_liste.setToolTip(tr("Taille de la liste des polices et de leur aperçu"))
        form_liste.addRow(tr("Liste :"), self.taille_liste)
        reg = _reglages()
        self._choisir_liste(self.style_police, reg.value("police_style_filtre", "", type=str))
        self._choisir_liste(self.taille_liste, reg.value("police_taille_liste", "petite", type=str))
        self.police.style_filtre = self.style_police.currentData()
        self.police.taille_liste = self.taille_liste.currentData()

        def _style(_i):
            self.police.style_filtre = self.style_police.currentData()
            _reglages().setValue("police_style_filtre", self.police.style_filtre)

        def _taille(_i):
            self.police.taille_liste = self.taille_liste.currentData()
            _reglages().setValue("police_taille_liste", self.police.taille_liste)
        self.style_police.currentIndexChanged.connect(_style)
        self.taille_liste.currentIndexChanged.connect(_taille)
        self.police.setItemDelegate(ApercuPolices(self.exemple_police, self.police))
        # survoler une police dans la liste la montre tout de suite sur le texte de la photo (sans rien changer)
        # (seulement liste ouverte, et pas quand le panneau se remplit : en changeant de calque de texte, l'ancienne
        # police revenait sur le nouveau texte)
        self.police.highlighted.connect(
            lambda i: None if self._remplissage or not self.police.view().isVisible()
            else self.apercu_police.emit(self.police.itemText(i)))
        self.police.fermee.connect(lambda: self.apercu_police.emit(""))
        self.police.setToolTip(tr("La liste montre chaque police avec le début de ton texte (ou de la partie "
                                  "sélectionnée)"))
        self.police.currentFontChanged.connect(lambda f: self._changer("police", f.family()))
        lay.addWidget(self.police)
        ligne = QHBoxLayout()
        self.taille = self._entier(4, 5000, " px", "taille")
        self.taille.setToolTip(tr("Taille des lettres, en pixels de la photo"))
        self.couleur = BoutonCouleur(tr("Couleur du texte"))
        self.couleur.change.connect(lambda c: self._changer("couleur", c))
        self.couleur.apercu.connect(lambda c: self._apercu("couleur", c))
        self.bouton_glyphes = QToolButton()
        self.bouton_glyphes.setText("Ω")
        self.bouton_glyphes.setFixedSize(30, 28)
        self.bouton_glyphes.setToolTip(tr("Glyphes : tous les caractères de la police (symboles, flèches, lettres "
                                          "accentuées…), un clic les insère dans le texte"))
        self.bouton_glyphes.clicked.connect(self.ouvrir_glyphes)
        self._glyphes = None
        ligne.addWidget(self.taille, 1)
        ligne.addWidget(self.bouton_glyphes)
        ligne.addWidget(self.couleur)
        lay.addLayout(ligne)

        ligne = QHBoxLayout()
        ligne.setSpacing(2)
        self.styles = {}
        for champ, lettre, aide, style in (("gras", tr("G|gras"), tr("Gras"), "bold"),
                                           ("italique", tr("I|italique"), tr("Italique"), "italic"),
                                           ("souligne", tr("S|souligné"), tr("Souligné"), "underline"),
                                           ("barre", tr("B|barré"), tr("Barré"), "strike")):
            b = QToolButton()
            b.setText(lettre)
            b.setCheckable(True)
            b.setToolTip(aide)
            b.setFixedSize(30, 28)
            f = QFont(b.font())
            f.setBold(style == "bold")
            f.setItalic(style == "italic")
            f.setUnderline(style == "underline")
            f.setStrikeOut(style == "strike")
            b.setFont(f)
            b.toggled.connect(lambda oui, c=champ: self._changer(c, oui))
            self.styles[champ] = b
            ligne.addWidget(b)
        ligne.addSpacing(10)
        self.alignements = {}
        groupe = QButtonGroup(self)
        for valeur, nom, aide in ((GAUCHE, "aligner_gauche", tr("Aligner à gauche")),
                                  (CENTRE, "aligner_centre", tr("Centrer")),
                                  (DROITE, "aligner_droite", tr("Aligner à droite")),
                                  (JUSTIFIE, "aligner_justifie", tr("Justifier (texte en cadre)"))):
            b = QToolButton()
            b.setCheckable(True)
            b.setToolTip(aide)
            b.setFixedSize(30, 28)
            b.clicked.connect(lambda _=False, v=valeur: self._changer("alignement", v))
            groupe.addButton(b)
            self.alignements[valeur] = (b, nom)
            ligne.addWidget(b)
        ligne.addStretch(1)
        lay.addLayout(ligne)

        form = self._formulaire(lay)
        self.lettres = self._entier(-50, 300, " %", "lettres")
        self.lettres.setToolTip(tr("Espace ajouté entre les lettres, en % de la taille"))
        form.addRow(tr("Lettres"), self.lettres)
        self.interligne = QDoubleSpinBox()
        self.interligne.setRange(0.5, 5.0)
        self.interligne.setSingleStep(0.1)
        self.interligne.setDecimals(2)
        self.interligne.setSuffix(" ×")
        self.interligne.setToolTip(tr("Écart entre les lignes, × la taille des lettres"))
        self.interligne.valueChanged.connect(lambda v: self._changer("interligne", v))
        form.addRow(tr("Lignes"), self.interligne)
        self.echelle_h = self._entier(10, 1000, " %", "echelle_h")
        self.echelle_h.setToolTip(tr("Largeur des lettres (étirer ou serrer)"))
        form.addRow(tr("Largeur"), self.echelle_h)
        self.echelle_v = self._entier(10, 1000, " %", "echelle_v")
        self.echelle_v.setToolTip(tr("Hauteur des lettres (étirer ou tasser)"))
        form.addRow(tr("Hauteur"), self.echelle_v)
        self.casse = self._liste("casse", (("normale", tr("Comme tapé")), ("majuscules", tr("TOUT EN MAJUSCULES")),
                                           ("minuscules", tr("tout en minuscules")),
                                           ("petites_capitales", tr("Petites capitales")),
                                           ("titre", tr("Première Lettre En Majuscule"))))
        form.addRow(tr("Casse"), self.casse)
        self.position = self._liste("position", (("normale", tr("Normale")), ("exposant", tr("Exposant")),
                                                 ("indice", tr("Indice"))))
        form.addRow(tr("Position"), self.position)
        self.ligne_base = self._entier(-300, 300, " %", "ligne_base")
        self.ligne_base.setToolTip(tr("Monter (positif) ou descendre (négatif) les lettres, en % de la taille"))
        form.addRow(tr("Ligne de base"), self.ligne_base)
        self.crenage = self._liste("crenage", ((True, tr("De la police")), (False, tr("Aucun"))))
        self.crenage.setToolTip(tr("Crénage : espaces corrigés par la police entre certaines paires (AV, To…)"))
        form.addRow(tr("Crénage"), self.crenage)
        self.crenage_ici = QSpinBox()
        self.crenage_ici.setRange(-1000, 1000)
        self.crenage_ici.setSingleStep(20)
        self.crenage_ici.setSuffix(" ‰")
        self.crenage_ici.setKeyboardTracking(False)
        self.crenage_ici.setToolTip(tr("Espace entre les deux lettres autour du curseur, en millièmes de la "
                                       "taille (aussi Alt+flèches dans le texte)"))
        self.crenage_ici.valueChanged.connect(self._crenage_ici)
        form.addRow(tr("Ici"), self.crenage_ici)
        self.opentype = {}
        ligne = QHBoxLayout()
        for champ, nom, aide in (("ligatures", tr("Ligatures"), tr("fi, fl, ff… liés (si la police en a)")),
                                 ("fractions", tr("Fractions"), tr("1/2 devient ½ (si la police le permet)")),
                                 ("chiffres_anciens", tr("Chiffres anciens"),
                                  tr("Chiffres de hauteurs variées, comme dans les livres (si la police en a)"))):
            c = QCheckBox(nom)
            c.setToolTip(aide)
            c.toggled.connect(lambda oui, ch=champ: self._changer(ch, oui))
            self.opentype[champ] = c
            if champ == "chiffres_anciens":           # deux par ligne : le panneau reste étroit
                ligne.addStretch(1)
                lay.addLayout(ligne)
                ligne = QHBoxLayout()
            ligne.addWidget(c)
        self.lissage = QCheckBox(tr("Bords lissés"))
        self.lissage.setToolTip(tr("Décoché : lettres aux bords nets, pixel par pixel (sans lissage)"))
        self.lissage.toggled.connect(lambda oui: self._changer("lissage", oui))
        ligne.addWidget(self.lissage)
        ligne.addStretch(1)
        lay.addLayout(ligne)

        # ---- paragraphe
        lay.addWidget(_titre(tr("Paragraphe")))
        self.vertical = QCheckBox(tr("Texte vertical"))
        self.vertical.setToolTip(tr("Lettres les unes sous les autres ; chaque ligne devient une colonne"))
        self.vertical.toggled.connect(lambda oui: self._changer("vertical", oui))
        lay.addWidget(self.vertical)
        ligne = QHBoxLayout()
        self.langue_texte = self._liste("langue", (("", tr("Langue de Pixane Photo")), ("fr", "Français"),
                                                   ("en", "English")))
        self.langue_texte.setToolTip(tr("Langue du texte : pour l'orthographe et la césure"))
        ligne.addWidget(QLabel(tr("Langue")))
        ligne.addWidget(self.langue_texte, 1)
        lay.addLayout(ligne)
        self.cadre = QCheckBox(tr("Texte en cadre"))
        self.cadre.setToolTip(tr("Les lignes se coupent toutes seules à la largeur du cadre"))
        self.cadre.toggled.connect(self._cadre_coche)
        lay.addWidget(self.cadre)
        form = self._formulaire(lay)
        self.cadre_l = self._entier(1, 20000, " px", "cadre_l")
        form.addRow(tr("Largeur du cadre"), self.cadre_l)
        self.cadre_h = self._entier(0, 20000, " px", "cadre_h")
        self.cadre_h.setSpecialValueText(tr("auto"))
        self.cadre_h.setToolTip(tr("Ce qui dépasse du cadre est caché ; 0 = selon le texte"))
        form.addRow(tr("Hauteur du cadre"), self.cadre_h)
        self.cesure = QCheckBox(tr("Césure"))
        self.cesure.setToolTip(tr("Coupe les mots longs en fin de ligne, avec un tiret (texte en cadre ; option "
                                  "Affichage > Orthographe et césure)"))
        self.cesure.toggled.connect(lambda oui: self._changer("cesure", oui))
        form.addRow("", self.cesure)
        self.retrait = self._entier(-500, 2000, " %", "retrait")
        self.retrait.setToolTip(tr("Alinéa de la première ligne de chaque paragraphe, en % de la taille"))
        form.addRow(tr("Retrait"), self.retrait)
        self.espace_paragraphe = self._entier(0, 1000, " %", "espace_paragraphe")
        self.espace_paragraphe.setToolTip(tr("Espace ajouté entre les paragraphes, en % de la taille"))
        form.addRow(tr("Entre paragraphes"), self.espace_paragraphe)

        # ---- disposition
        lay.addWidget(_titre(tr("Disposition")))
        form = self._formulaire(lay)
        self.angle = self._entier(-180, 180, "°", "angle")
        self.angle.setToolTip(tr("Rotation (aussi avec la poignée ronde au-dessus du texte)"))
        form.addRow(tr("Rotation"), self.angle)
        self.courbe = self._entier(-360, 360, "°", "courbe")
        self.courbe.setToolTip(tr("Texte en arc : positif = en voûte, négatif = en creux, 360 = cercle complet"))
        form.addRow(tr("Courbe"), self.courbe)
        ligne = QHBoxLayout()
        ligne.setSpacing(4)
        self.bouton_trace = QPushButton(tr("Dessiner un tracé"))
        self.bouton_trace.setCheckable(True)
        self.bouton_trace.setToolTip(tr("Puis glisse sur la photo : le texte suit la ligne dessinée"))
        self.bouton_trace.toggled.connect(self.tracer.emit)
        self.retirer_trace = QPushButton(tr("Retirer"))
        self.retirer_trace.setToolTip(tr("Le texte quitte son tracé (redevient droit)"))
        self.retirer_trace.clicked.connect(lambda: self._changer("trace", ()))
        ligne.addWidget(self.bouton_trace, 1)
        ligne.addWidget(self.retirer_trace)
        form.addRow(ligne)
        self.trace_debut = self._entier(0, 100, " %", "trace_debut")
        self.trace_debut.setToolTip(tr("Où le texte commence le long du tracé"))
        form.addRow(tr("Départ"), self.trace_debut)
        self.deformation = self._liste("deformation", (
            ("aucune", tr("Aucune")), ("arc", tr("Arc")), ("arc_inferieur", tr("Arc inférieur")),
            ("arc_superieur", tr("Arc supérieur")), ("arche", tr("Arche")), ("renflement", tr("Renflement")),
            ("drapeau", tr("Drapeau")), ("vague", tr("Vague")), ("poisson", tr("Poisson")),
            ("montee", tr("Montée")), ("oeil_de_poisson", tr("Œil de poisson")), ("gonflement", tr("Gonflement")),
            ("compression", tr("Compression")), ("torsion", tr("Torsion"))))
        self.deformation.setToolTip(tr("Déformer le texte (comme dans Photoshop)"))
        form.addRow(tr("Déformation"), self.deformation)
        self.flexion = self._entier(-100, 100, " %", "flexion")
        form.addRow(tr("Force"), self.flexion)
        self.distorsion_h = self._entier(-100, 100, " %", "distorsion_h")
        self.distorsion_h.setToolTip(tr("Perspective : un côté plus grand que l'autre"))
        form.addRow(tr("Distorsion horiz."), self.distorsion_h)
        self.distorsion_v = self._entier(-100, 100, " %", "distorsion_v")
        self.distorsion_v.setToolTip(tr("Perspective : le haut plus large que le bas, ou l'inverse"))
        form.addRow(tr("Distorsion vert."), self.distorsion_v)

        # ---- effets
        self.effets = {}
        for cle, titre, reglages in (
                ("contour", tr("Contour"), (("contour_epaisseur", tr("Épaisseur"), 1, 100, " %"),)),
                ("ombre", tr("Ombre portée"), (("ombre_distance", tr("Distance"), 0, 300, " %"),
                                               ("ombre_direction", tr("Direction"), 0, 359, "°"),
                                               ("ombre_flou", tr("Flou"), 0, 300, " %"))),
                ("fond", tr("Fond"), (("fond_marge", tr("Marge"), 0, 300, " %"),
                                      ("fond_arrondi", tr("Arrondi"), 0, 200, " %")))):
            ligne = QHBoxLayout()
            case = QCheckBox(titre)
            case.setStyleSheet("font-weight: bold")
            case.toggled.connect(lambda oui, c=cle: self._changer(c, oui))
            couleur = BoutonCouleur(tr("Couleur : {effet}", effet=titre))
            couleur.change.connect(lambda c, ch=cle + "_couleur": self._changer(ch, c))
            couleur.apercu.connect(lambda c, ch=cle + "_couleur": self._apercu(ch, c))
            ligne.addWidget(case, 1)
            ligne.addWidget(couleur)
            lay.addSpacing(6)
            lay.addLayout(ligne)
            form = self._formulaire(lay)
            cases = {}
            for champ, nom, mini, maxi, suffixe in reglages:
                s = self._entier(mini, maxi, suffixe, champ)
                if suffixe == " %":
                    s.setToolTip(tr("En % de la taille des lettres"))
                form.addRow(nom, s)
                cases[champ] = s
            self.effets[cle] = (case, couleur, cases)
        # ---- styles de texte
        lay.addWidget(_titre(tr("Styles de texte")))
        ligne = QHBoxLayout()
        ligne.setSpacing(4)
        self.copier_style = QPushButton(tr("Copier"))
        self.copier_style.setToolTip(tr("Retient police, couleur, effets et réglages de ce texte"))
        self.copier_style.clicked.connect(self._copier_style)
        self.coller_style = QPushButton(tr("Coller"))
        self.coller_style.setToolTip(tr("Donne à ce texte le style copié (son texte et sa place ne changent pas)"))
        self.coller_style.clicked.connect(lambda: self._appliquer_style(self._style_copie))
        ligne.addWidget(self.copier_style)
        ligne.addWidget(self.coller_style)
        lay.addLayout(ligne)
        self._style_copie = None
        ligne = QHBoxLayout()
        ligne.setSpacing(4)
        self.styles_enr = QComboBox()
        self.styles_enr.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.styles_enr.setMinimumContentsLength(8)
        self.styles_enr.setToolTip(tr("Styles enregistrés : en choisir un l'applique au texte"))
        self.styles_enr.activated.connect(self._style_choisi)
        self.enregistrer_style = QToolButton()
        self.enregistrer_style.setText("+")
        self.enregistrer_style.setFixedSize(28, 26)
        self.enregistrer_style.setToolTip(tr("Enregistrer le style de ce texte sous un nom"))
        self.enregistrer_style.clicked.connect(self._enregistrer_style)
        self.supprimer_style = QToolButton()
        self.supprimer_style.setText("−")
        self.supprimer_style.setFixedSize(28, 26)
        self.supprimer_style.setToolTip(tr("Supprimer le style choisi dans la liste"))
        self.supprimer_style.clicked.connect(self._supprimer_style)
        ligne.addWidget(self.styles_enr, 1)
        ligne.addWidget(self.enregistrer_style)
        ligne.addWidget(self.supprimer_style)
        lay.addLayout(ligne)
        self._remplir_styles()

        note = QLabel(tr("Transparence : curseur Opacité du panneau Calques, ou la couleur (canal alpha)."))
        note.setObjectName("discret")
        note.setWordWrap(True)
        lay.addSpacing(6)
        lay.addWidget(note)
        lay.addStretch(1)
        self.setWidget(w)
        self.appliquer_icones()
        self.afficher(None)

    # ---------------------------------------------------------- construction
    @staticmethod
    def _formulaire(lay) -> QFormLayout:
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(4)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        lay.addLayout(form)
        return form

    def _entier(self, mini: int, maxi: int, suffixe: str, champ: str) -> QSpinBox:
        s = QSpinBox()
        s.setRange(mini, maxi)
        s.setSuffix(suffixe)
        s.setKeyboardTracking(False)
        s.valueChanged.connect(lambda v: self._changer(champ, float(v)))
        return s

    def _liste(self, champ: str, choix) -> QComboBox:
        c = QComboBox()
        c.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)    # étroite (liste ouverte : tout)
        c.setMinimumContentsLength(10)
        for valeur, nom in choix:
            c.addItem(nom, valeur)
        c.currentIndexChanged.connect(lambda _i: self._changer(champ, c.currentData()))
        return c

    @staticmethod
    def _choisir_liste(c: QComboBox, valeur):
        i = c.findData(valeur)
        c.setCurrentIndex(max(0, i))

    def appliquer_icones(self):
        for b, nom in self.alignements.values():
            b.setIcon(self.icones(nom))

    def exemple_police(self) -> str:
        """Exemple de la liste des polices : la partie sélectionnée du texte, sinon le texte, sinon un modèle."""
        choisi = self.saisie.textCursor().selectedText() or self.saisie.toPlainText()
        choisi = " ".join(choisi.replace("\u2029", " ").split())          # une seule ligne
        if len(choisi) > EXEMPLE_MAX:
            choisi = choisi[:EXEMPLE_MAX].rstrip() + "…"
        return choisi or tr("Aa Bb Cc 123")

    # ---------------------------------------------------------- affichage
    def afficher(self, t: Texte | None, verrou: bool = False):
        """Montre les réglages du calque de texte `t`, ou ceux du prochain texte (t = None)."""
        self.lie = t is not None
        self.t = t if t is not None else self.defaut
        t = self.t
        self._remplissage = True
        try:
            if self.saisie.toPlainText() != (t.texte if self.lie else ""):
                self.saisie.setPlainText(t.texte if self.lie else "")
            self.saisie.setEnabled(self.lie and not verrou)
            self.police.setCurrentFont(QFont(t.police))
            self.taille.setValue(round(t.taille))
            self.couleur.definir(t.couleur)
            for champ, b in self.styles.items():
                b.setChecked(getattr(t, champ))
            for valeur, (b, _) in self.alignements.items():
                b.setChecked(valeur == t.alignement)
            self.interligne.setValue(t.interligne)
            self.angle.setValue(round(t.angle))
            self.courbe.setValue(round(t.courbe))
            self._choisir_liste(self.crenage, t.crenage)
            for champ, c in self.opentype.items():
                c.setChecked(getattr(t, champ))
            self.lissage.setChecked(t.lissage)
            self.vertical.setChecked(t.vertical)
            self.cadre.setChecked(t.cadre_l > 0)
            self.cadre_l.setValue(round(t.cadre_l) if t.cadre_l > 0 else 1)
            self.cadre_h.setValue(round(t.cadre_h))
            self.retrait.setValue(round(t.retrait))
            self.cesure.setChecked(t.cesure)
            self._choisir_liste(self.langue_texte, t.langue)
            self.espace_paragraphe.setValue(round(t.espace_paragraphe))
            self._choisir_liste(self.deformation, t.deformation)
            self.trace_debut.setValue(round(t.trace_debut))
            self.flexion.setValue(round(t.flexion))
            self.distorsion_h.setValue(round(t.distorsion_h))
            self.distorsion_v.setValue(round(t.distorsion_v))
            for cle, (case, couleur, cases) in self.effets.items():
                case.setChecked(getattr(t, cle))
                couleur.definir(getattr(t, cle + "_couleur"))
                for champ, s in cases.items():
                    s.setValue(round(getattr(t, champ)))
        finally:
            self._remplissage = False
        self._montrer_lettres()
        for w in (self.cadre_l, self.cadre_h):
            w.setEnabled(self.t.cadre_l > 0 and not self.t.vertical)
        self.cesure.setEnabled(self.t.cadre_l > 0 and not self.t.vertical and self._ortho_active())
        self.flexion.setEnabled(self.t.deformation != "aucune")
        self.bouton_trace.setEnabled(self.lie and not verrou)
        if not self.lie and self.bouton_trace.isChecked():
            self.bouton_trace.setChecked(False)
        self.coller_style.setEnabled(self._style_copie is not None and not verrou)
        self.retirer_trace.setEnabled(self.lie and bool(self.t.trace))
        self.trace_debut.setEnabled(self.lie and bool(self.t.trace))
        self.courbe.setEnabled(not self.t.trace)
        self.taille.setEnabled(self.lie)       # sans texte choisi, la taille est calculée d'après la photo
        self.angle.setEnabled(self.lie)
        if verrou:
            self.aide.setText(tr("Ce calque de texte est verrouillé : clique sur son cadenas pour le modifier."))
        elif self.lie:
            self.aide.setText(tr("Le texte s'applique au fur et à mesure, rien à valider. Glisse-le pour le "
                                 "déplacer, la poignée ronde le tourne. Clique ailleurs pour un autre texte."))
        else:
            self.aide.setText(tr("Clique sur la photo pour écrire un texte, ou sur un texte existant pour le "
                                 "modifier. Les réglages ci-dessous serviront pour le prochain texte."))

    def choisir_lettres(self, a: int, b: int):
        """Lettres choisies à la souris sur la photo : la même sélection dans la case (et la case prend la main)."""
        if not self.lie:
            return
        n = len(self.saisie.toPlainText())
        c = self.saisie.textCursor()
        c.setPosition(max(0, min(a, n)))
        c.setPosition(max(0, min(b, n)), QTextCursor.KeepAnchor)
        self.saisie.setTextCursor(c)
        self.saisie.setFocus()

    def commencer_saisie(self):
        """Nouveau texte : on peut taper tout de suite (le texte proposé est sélectionné)."""
        self.saisie.setFocus()
        self.saisie.selectAll()

    # ---------------------------------------------------------- changements
    PAS_DEFAUT = ("texte", "x", "y", "angle", "taille", "courbe", "cadre_l", "cadre_h", "deformation", "flexion",
                  "distorsion_h", "distorsion_v", "trace", "trace_debut", "styles", "crenages")

    def _selection(self) -> tuple[int, int]:
        """Lettres sélectionnées dans la saisie (début, fin) ; (0, 0) sans sélection."""
        if not self.lie:
            return 0, 0
        c = self.saisie.textCursor()
        a, b = sorted((c.anchor(), c.position()))
        return (a, b) if b > a else (0, 0)

    def _montrer_lettres(self):
        """Réglages de caractère montrés : ceux des lettres sélectionnées, sinon ceux du texte entier."""
        t = self.t
        a, b = self._selection()
        self.selection_lettres.emit(a, b)
        st = t.style_de(a) if b > a else t.style_de(-1)
        pos = self.saisie.textCursor().position()
        avant = self._remplissage
        self._remplissage = True
        try:
            self.police.setCurrentFont(QFont(st["police"]))
            self.taille.setValue(round(st["taille"]))
            self.couleur.definir(st["couleur"])
            for champ, bt in self.styles.items():
                bt.setChecked(bool(st[champ]))
            self.lettres.setValue(round(st["lettres"]))
            self.echelle_h.setValue(round(st["echelle_h"]))
            self.echelle_v.setValue(round(st["echelle_v"]))
            self._choisir_liste(self.casse, st["casse"])
            self._choisir_liste(self.position, st["position"])
            self.ligne_base.setValue(round(st["ligne_base"]))
            self.crenage_ici.setValue(round(t.crenage_a(pos)))
        finally:
            self._remplissage = avant
        self.crenage_ici.setEnabled(self.lie and b <= a and 0 < pos < len(t.texte))
        if b > a:
            self.portee.setText(tr("Réglages de caractère : seulement les {n} lettres sélectionnées.", n=b - a))
        elif t.styles and self.lie:
            self.portee.setText(tr("Certaines lettres ont leur propre style : un réglage ici les change toutes."))
        else:
            self.portee.setText("")
        self.portee.setVisible(bool(self.portee.text()))

    def _changer(self, champ: str, valeur):
        if self._remplissage:
            return
        t = self.t
        a, b = self._selection()
        if champ in CHAMPS_LETTRE and b > a:              # style par lettre : seulement la sélection
            nouveau = t.avec_style(a, b, **{champ: valeur})
            if nouveau == t:
                return
            self.t = nouveau
            self._montrer_lettres()
            self.modifie.emit(self.t, champ + "@lettres")
            return
        if champ == "texte":
            nouveau = t.avec_texte(valeur)
        elif champ in CHAMPS_LETTRE:                      # tout le texte, lettres à style propre comprises
            nouveau = replace(t, **{champ: valeur}).avec_style(0, len(t.texte), **{champ: valeur})
        else:
            nouveau = replace(t, **{champ: valeur})
        if nouveau == t:
            return
        self.t = nouveau
        if champ not in self.PAS_DEFAUT:
            self.defaut = replace(self.defaut, **{champ: valeur})      # le prochain texte reprend ce style
        if champ == "langue":
            self.soulignement.rehighlight()
        if champ in ("cadre_l", "vertical", "deformation", "trace"):
            self.afficher(self.t if self.lie else None)
        else:
            self._montrer_lettres()
        if self.lie:
            self.modifie.emit(self.t, champ)

    def _apercu(self, champ: str, valeur: str):
        """Couleur essayée dans la fenêtre de couleur : le texte de la photo la montre (sans rien changer)."""
        if not self.lie:
            return
        if not valeur:
            self.apercu_texte.emit(None)
            return
        t = self.t
        a, b = self._selection()
        if champ in CHAMPS_LETTRE and b > a:
            essai = t.avec_style(a, b, **{champ: valeur})
        elif champ in CHAMPS_LETTRE:
            essai = replace(t, **{champ: valeur}).avec_style(0, len(t.texte), **{champ: valeur})
        else:
            essai = replace(t, **{champ: valeur})
        self.apercu_texte.emit(essai)

    def _cadre_coche(self, oui: bool):
        """Texte en cadre : le cadre prend la largeur actuelle du texte (on la change ensuite)."""
        if self._remplissage:
            return
        if oui:
            largeur = forme(replace(self.t, cadre_l=0.0, courbe=0.0, deformation="aucune"))[1].width()
            self._changer("cadre_l", float(max(round(largeur) + 2, round(self.t.taille * 2))))
        else:
            self._changer("cadre_l", 0.0)

    def _crenage_ici(self, valeur: int):
        if self._remplissage or not self.lie:
            return
        self._regler_crenage(self.saisie.textCursor().position(), float(valeur))

    def _regler_crenage(self, pos: int, valeur: float):
        if not (0 < pos < len(self.t.texte)):
            return
        nouveau = self.t.avec_crenage(pos, valeur)
        if nouveau != self.t:
            self.t = nouveau
            self._montrer_lettres()
            self.modifie.emit(self.t, "crenages")

    # ---------------------------------------------------------- orthographe
    @staticmethod
    def _ortho_active() -> bool:
        try:
            from . import orthographe
            return orthographe.active() and orthographe.disponible()
        except Exception:
            return False

    def option_orthographe(self):
        """Option ou langues de l'orthographe changées (menu Affichage) : soulignement et césure à jour."""
        self.soulignement.rehighlight()
        self.afficher(self.t if self.lie else None, not self.saisie.isEnabled() and self.lie)

    def _menu_saisie(self, pos):
        """Clic droit dans la case du texte : sur un mot souligné, les suggestions, Ignorer, Ajouter au dictionnaire ;
        puis le menu habituel (couper, copier, coller…)."""
        from . import orthographe as o
        menu = self.saisie.createStandardContextMenu()
        curseur = self.saisie.cursorForPosition(pos)
        texte = self.saisie.toPlainText()
        span = o.mot_a(texte, curseur.position())
        langue = self.t.langue
        if self.lie and self.saisie.isEnabled() and span and o.verifiable(langue) and o.pret(langue):
            mot = texte[span[0]:span[1]]
            if not o.correct(mot, langue):
                QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
                try:
                    props = o.suggestions(mot, langue)
                finally:
                    QApplication.restoreOverrideCursor()
                premiere = menu.actions()[0] if menu.actions() else None
                actions = []
                for s in props:
                    a = QAction_(s, menu)
                    f = a.font()
                    f.setBold(True)
                    a.setFont(f)
                    a.triggered.connect(lambda _=False, s=s, sp=span: self._remplacer_mot(sp, s))
                    actions.append(a)
                if not props:
                    a = QAction_(tr("(aucune suggestion)"), menu)
                    a.setEnabled(False)
                    actions.append(a)
                a = QAction_(tr("Ignorer « {mot} »", mot=mot), menu)
                a.triggered.connect(lambda: (o.ignorer_mot(mot), self.soulignement.rehighlight()))
                actions.append(a)
                a = QAction_(tr("Ajouter « {mot} » au dictionnaire", mot=mot), menu)
                a.triggered.connect(lambda: (o.ajouter_mot(mot), self.soulignement.rehighlight()))
                actions.append(a)
                sep = QAction_(menu)
                sep.setSeparator(True)
                actions.append(sep)
                menu.insertActions(premiere, actions)
        menu.exec(self.saisie.mapToGlobal(pos))

    def _remplacer_mot(self, span, nouveau: str):
        c = self.saisie.textCursor()
        c.setPosition(span[0])
        c.setPosition(span[1], QTextCursor.KeepAnchor)
        c.insertText(nouveau)
        self.saisie.setTextCursor(c)

    # ---------------------------------------------------------- glyphes
    def ouvrir_glyphes(self):
        from .glyphes import FenetreGlyphes
        from .fenetre import reglages
        import json
        if self._glyphes is None:
            try:
                recents = json.loads(reglages().value("glyphes_recents", "[]"))
            except ValueError:
                recents = []
            self._glyphes = FenetreGlyphes(self.window(), [c for c in recents if isinstance(c, str)])
            self._glyphes.choisi.connect(self._inserer_glyphe)
        a, _b = self._selection()
        st = self.t.style_de(a) if self.lie else self.t.style_de(-1)
        self._glyphes.montrer_police(st["police"], bool(st["gras"]), bool(st["italique"]))
        self._glyphes.show()
        self._glyphes.raise_()

    def _inserer_glyphe(self, ch: str):
        from .fenetre import reglages
        import json
        reglages().setValue("glyphes_recents", json.dumps(self._glyphes.recents, ensure_ascii=False))
        if not self.lie or not self.saisie.isEnabled():
            QMessageBox.information(self.window(), tr("Glyphes"),
                                    tr("Choisis d'abord un texte (ou clique sur la photo pour en écrire un)."))
            return
        self.saisie.insertPlainText(ch)

    # ---------------------------------------------------------- styles de texte
    def _styles_enregistres(self) -> dict:
        from .fenetre import reglages
        import json
        try:
            d = json.loads(reglages().value("styles_texte", "{}"))
        except ValueError:
            d = {}
        return d if isinstance(d, dict) else {}

    def _remplir_styles(self):
        d = self._styles_enregistres()
        self.styles_enr.clear()
        self.styles_enr.addItem(tr("Styles enregistrés…") if d else tr("Aucun style enregistré"), None)
        for nom in sorted(d, key=str.lower):
            self.styles_enr.addItem(nom, nom)
        self.supprimer_style.setEnabled(bool(d))

    def _copier_style(self):
        self._style_copie = style_texte(self.t)
        self.coller_style.setEnabled(True)

    def _appliquer_style(self, style: dict | None):
        if style is None:
            return
        nouveau = avec_style_texte(self.t, style)
        if nouveau == self.t:
            return
        self.t = nouveau
        self.defaut = avec_style_texte(self.defaut, style)       # le prochain texte aussi
        self.afficher(self.t if self.lie else None)
        if self.lie:
            self.modifie.emit(self.t, "style")

    def _style_choisi(self, i: int):
        nom = self.styles_enr.itemData(i)
        if nom is not None:
            self._appliquer_style(self._styles_enregistres().get(nom))
        self.styles_enr.setCurrentIndex(0)

    def _enregistrer_style(self):
        from .fenetre import reglages
        import json
        nom, ok = QInputDialog.getText(self.window(), tr("Enregistrer le style"), tr("Nom du style :"))
        nom = nom.strip()
        if not ok or not nom:
            return
        d = self._styles_enregistres()
        if nom in d and QMessageBox.question(self.window(), tr("Enregistrer le style"),
                                             tr("Le style « {nom} » existe déjà. Le remplacer ?", nom=nom)) \
                != QMessageBox.Yes:
            return
        d[nom] = style_texte(self.t)
        reglages().setValue("styles_texte", json.dumps(d, ensure_ascii=False))
        self._remplir_styles()

    def _supprimer_style(self):
        from .fenetre import reglages
        import json
        nom = self.styles_enr.currentData()
        d = self._styles_enregistres()
        if nom is None:
            if not d:
                return
            nom, ok = QInputDialog.getItem(self.window(), tr("Supprimer un style"), tr("Style à supprimer :"),
                                           sorted(d, key=str.lower), 0, False)
            if not ok:
                return
        d.pop(nom, None)
        reglages().setValue("styles_texte", json.dumps(d, ensure_ascii=False))
        self._remplir_styles()

    def eventFilter(self, objet, ev):
        """Alt+flèches dans la saisie : crénage à la main entre les deux lettres autour du curseur.
        Ctrl+Z / Ctrl+Y dans la saisie, quand elle n'a rien à annuler (ex. un texte posé par erreur d'un clic) : ils
        vont à l'historique de l'image (le texte posé est retiré), au lieu de ne rien faire."""
        if objet is self.saisie and ev.type() == QEvent.ShortcutOverride:
            doc = self.saisie.document()
            if (ev.matches(QKeySequence.Undo) and not doc.isUndoAvailable()) or \
                    (ev.matches(QKeySequence.Redo) and not doc.isRedoAvailable()):
                return True                      # pas accepté : le raccourci de la fenêtre (Annuler) s'en charge
        if objet is self.saisie and ev.type() == QEvent.KeyPress and ev.modifiers() & Qt.AltModifier \
                and ev.key() in (Qt.Key_Left, Qt.Key_Right) and self.lie and self.saisie.isEnabled():
            pas = 20.0 * (5 if ev.modifiers() & Qt.ControlModifier else 1)
            pos = self.saisie.textCursor().position()
            self._regler_crenage(pos, self.t.crenage_a(pos) + (pas if ev.key() == Qt.Key_Right else -pas))
            return True
        return super().eventFilter(objet, ev)
