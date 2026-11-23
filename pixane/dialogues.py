"""Fenêtres : choix du résultat, barre Agrandir, réglages Upscale."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QImage, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QRadioButton, QSpinBox,
                               QSlider, QVBoxLayout, QWidget, QCheckBox)

from .langue import tr


class Apercu(QWidget):
    """Montre une proposition, zoomable : molette = zoom sous la souris, glisser = se déplacer, double-clic = ajusté
    / 100 %. Le zoom et l'endroit regardé sont gardés d'une image à l'autre (en proportion de l'image) : on compare
    toujours le même détail, même entre l'original et une proposition plus grande (Upscale)."""
    zoom_change = Signal()
    ZOOM_MAX = 16.0                       # échelle maximale (1 px de l'image = 16 px à l'écran)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(500, 350)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip(tr("Molette : zoomer · glisser : se déplacer · double-clic : ajuster / 100 %"))
        self._image: QImage | None = None
        self.facteur = 1.0                # 1 = image entière ajustée à la zone ; plus = zoomé
        self.centre = QPointF(0.5, 0.5)   # point de l'image au centre de la zone (0..1)
        self._glisse = None

    def montrer(self, image: QImage):
        self._image = image
        self._borner()
        self.update()

    def _ajuste(self) -> float:
        im = self._image
        if im is None or im.isNull():
            return 1.0
        return min(self.width() / im.width(), self.height() / im.height())

    def echelle(self) -> float:
        """Pixels d'écran par pixel de l'image."""
        return self._ajuste() * self.facteur

    def _borner(self):
        """Pas de zoom plus petit que l'image entière ; on ne sort pas de l'image."""
        im = self._image
        if im is None or im.isNull():
            return
        a = self._ajuste()
        self.facteur = max(1.0, min(self.facteur, max(1.0, self.ZOOM_MAX / a)))
        s = self.echelle()
        cx, cy = self.centre.x(), self.centre.y()
        demi_x = self.width() / 2 / (im.width() * s)
        demi_y = self.height() / 2 / (im.height() * s)
        cx = 0.5 if demi_x >= 0.5 else min(max(cx, demi_x), 1 - demi_x)
        cy = 0.5 if demi_y >= 0.5 else min(max(cy, demi_y), 1 - demi_y)
        self.centre = QPointF(cx, cy)

    def _vers_image(self, pos: QPointF) -> QPointF:
        """Point de la zone -> point de l'image (0..1)."""
        im, s = self._image, self.echelle()
        return QPointF(self.centre.x() + (pos.x() - self.width() / 2) / (im.width() * s),
                       self.centre.y() + (pos.y() - self.height() / 2) / (im.height() * s))

    def zoomer(self, facteur: float, pos: QPointF | None = None):
        """Nouveau facteur (1 = ajusté) ; pos : point de la zone qui reste sous la souris."""
        if self._image is None or self._image.isNull():
            return
        if pos is None:
            pos = QPointF(self.width() / 2, self.height() / 2)
        n = self._vers_image(pos)
        self.facteur = facteur
        self._borner()
        im, s = self._image, self.echelle()
        self.centre = QPointF(n.x() - (pos.x() - self.width() / 2) / (im.width() * s),
                              n.y() - (pos.y() - self.height() / 2) / (im.height() * s))
        self._borner()
        self._curseur()
        self.update()
        self.zoom_change.emit()

    def ajuster(self):
        self.zoomer(1.0)

    def cent_pour_cent(self, pos: QPointF | None = None):
        self.zoomer(1.0 / self._ajuste(), pos)

    def wheelEvent(self, e):
        crans = e.angleDelta().y() / 120
        if crans:
            self.zoomer(self.facteur * 1.25 ** crans, e.position())
        e.accept()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.facteur > 1.0:
            self._glisse = e.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._glisse is not None and self._image is not None:
            d = e.position() - self._glisse
            self._glisse = e.position()
            im, s = self._image, self.echelle()
            self.centre = QPointF(self.centre.x() - d.x() / (im.width() * s),
                                  self.centre.y() - d.y() / (im.height() * s))
            self._borner()
            self.update()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._glisse = None
        self._curseur()
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.facteur > 1.0:
            self.ajuster()
        elif self._ajuste() < 1.0:
            self.cent_pour_cent(e.position())
        else:
            self.zoomer(2.0, e.position())

    def _curseur(self):
        if self._glisse is None:
            self.setCursor(Qt.OpenHandCursor if self.facteur > 1.0 else Qt.ArrowCursor)

    def resizeEvent(self, e):
        self._borner()
        super().resizeEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#282828"))
        im = self._image
        if im is None or im.isNull():
            return
        s = self.echelle()
        w, h = im.width() * s, im.height() * s
        x = self.width() / 2 - self.centre.x() * w
        y = self.height() / 2 - self.centre.y() * h
        p.setRenderHint(QPainter.SmoothPixmapTransform, s < 2.0)    # zoom fort : pixels nets, comme Photoshop
        p.drawImage(QRectF(x, y, w, h), im)
        texte = f"{round(s * 100)} %"
        m = p.fontMetrics()
        cadre = QRectF(8, self.height() - m.height() - 12, m.horizontalAdvance(texte) + 12, m.height() + 4)
        p.fillRect(cadre, QColor(0, 0, 0, 140))
        p.setPen(QColor("#f0f0f0"))
        p.drawText(cadre, Qt.AlignCenter, texte)
        p.end()


class BoutonComparer(QPushButton):
    appuye = Signal(bool)

    def __init__(self):
        super().__init__(tr("Maintenir pour voir l'original"))

    def mousePressEvent(self, e):
        self.appuye.emit(True)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.appuye.emit(False)
        super().mouseReleaseEvent(e)


class ChoixResultat(QDialog):
    """Montre les propositions en vignettes ; on en garde une (comme Photoshop)."""
    autres_demandees = Signal()
    variante_demandee = Signal(int, int)       # (proposition choisie, glissière Proche 0 .. Libre 100)

    def __init__(self, titre: str, original: QImage, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("{titre} — choisis un résultat", titre=titre))
        self.resize(1100, 800)
        self.original = original
        self.images: list[QImage] = []
        self.apercu = Apercu()
        self.vignettes = QListWidget()
        self.vignettes.setViewMode(QListWidget.IconMode)
        self.vignettes.setIconSize(QSize(160, 120))
        self.vignettes.setFixedHeight(175)
        self.vignettes.setFlow(QListWidget.LeftToRight)
        self.vignettes.setWrapping(False)
        self.vignettes.currentRowChanged.connect(self._choisi)
        comparer = BoutonComparer()
        comparer.appuye.connect(self._comparer)
        self.bouton_autres = QPushButton(tr("Autres propositions"))
        self.bouton_autres.clicked.connect(self._autres)
        self.bouton_autres.setToolTip(tr("Nouvelles propositions, calculées à partir de l'image d'origine"))
        # « Partir de celle-ci » : variantes de la proposition choisie (montré par permettre_variantes)
        self.bouton_variante = QPushButton(tr("Partir de celle-ci"))
        self.bouton_variante.setToolTip(tr("Nouvelles propositions à partir de celle qui est choisie : l'IA garde sa "
                                           "forme générale et change les détails (réglage Proche ↔ Libre)"))
        self.bouton_variante.clicked.connect(self._variante)
        self.proche_libre = QSlider(Qt.Horizontal)
        self.proche_libre.setRange(0, 100)
        self.proche_libre.setFixedWidth(110)
        self.proche_libre.setToolTip(tr("Proche : petites retouches, presque la même image. Libre : la même idée, "
                                        "retravaillée davantage."))
        self.zone_variante = QWidget()
        lv = QHBoxLayout(self.zone_variante)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(4)
        lv.addWidget(self.bouton_variante)
        proche, libre = QLabel(tr("Proche")), QLabel(tr("Libre"))
        proche.setObjectName("discret")
        libre.setObjectName("discret")
        lv.addWidget(proche)
        lv.addWidget(self.proche_libre)
        lv.addWidget(libre)
        self.zone_variante.hide()
        garder = QPushButton(tr("Garder ce résultat"))
        garder.setDefault(True)
        gras = garder.font()
        gras.setBold(True)                     # le thème met ce bouton en gras : place pour tout le texte
        garder.setMinimumWidth(QFontMetrics(gras).horizontalAdvance(garder.text()) + 36)
        garder.clicked.connect(self.accept)
        annuler = QPushButton(tr("Annuler"))
        annuler.clicked.connect(self.reject)
        self.bouton_ajuster = QPushButton(tr("Ajuster"))
        self.bouton_ajuster.setToolTip(tr("Voir l'image entière (touche 0 ou double-clic)"))
        self.bouton_ajuster.clicked.connect(self.apercu.ajuster)
        self.bouton_100 = QPushButton("100 %")
        self.bouton_100.setToolTip(tr("Taille réelle : 1 pixel de l'image = 1 pixel de l'écran (touche 1)"))
        self.bouton_100.clicked.connect(lambda: self.apercu.cent_pour_cent())
        for touches, faire in ((("+", "="), lambda: self.apercu.zoomer(self.apercu.facteur * 1.25)),
                               (("-",), lambda: self.apercu.zoomer(self.apercu.facteur / 1.25)),
                               (("0",), self.apercu.ajuster), (("1",), lambda: self.apercu.cent_pour_cent())):
            for t in touches:
                QShortcut(QKeySequence(t), self, faire)
        self.etat = QLabel("")
        self.barre = QProgressBar()
        self.barre.setFixedWidth(220)
        self.barre.setFormat("%p %")
        self.barre.hide()
        bas = QHBoxLayout()
        bas.addWidget(comparer)
        bas.addWidget(self.bouton_autres)
        bas.addWidget(self.zone_variante)
        bas.addWidget(self.bouton_ajuster)
        bas.addWidget(self.bouton_100)
        bas.addWidget(self.barre)
        bas.addWidget(self.etat, 1)
        bas.addWidget(annuler)
        bas.addWidget(garder)
        lay = QVBoxLayout(self)
        lay.addWidget(self.apercu, 1)
        lay.addWidget(self.vignettes)
        lay.addLayout(bas)

    vue = None          # fonction image -> image montrée (ex. transparence de la photo remise)

    def ajouter(self, resultats: list[tuple[str, QImage]]):
        premier = len(self.images)
        for libelle, img in resultats:
            self.images.append(img)
            if self.vue is not None:
                img = self.vue(img)
            item = QListWidgetItem(QIcon(QPixmap.fromImage(img.scaled(160, 120, Qt.KeepAspectRatio,
                                                                      Qt.SmoothTransformation))), libelle)
            self.vignettes.addItem(item)
        if self.images:
            self.vignettes.setCurrentRow(premier if premier < len(self.images) else 0)
        self.occupe(False)

    def permettre_variantes(self, curseur: int = 50):
        """Montre « Partir de celle-ci » et la glissière Proche ↔ Libre (Effacer, Remplir, Agrandir)."""
        self.proche_libre.setValue(curseur)
        self.zone_variante.show()

    def occupe(self, oui: bool, texte: str = ""):
        self.bouton_autres.setEnabled(not oui)
        self.bouton_variante.setEnabled(not oui)
        self.etat.setText(texte)
        if not oui:
            self.barre.hide()

    def progression(self, info: dict):
        self.barre.show()
        regler_barre(self.barre, info)
        self.etat.setText(f"{info['etape']}  ·  {texte_progression(info)}")

    def _autres(self):
        self.occupe(True, tr("Calcul de nouvelles propositions…"))
        self.autres_demandees.emit()

    def _variante(self):
        ligne = self.vignettes.currentRow()
        if not 0 <= ligne < len(self.images):
            return
        self.occupe(True, tr("Calcul de variantes de la proposition {n}…", n=ligne + 1))
        self.variante_demandee.emit(ligne, self.proche_libre.value())

    def _choisi(self, ligne: int):
        if 0 <= ligne < len(self.images):
            img = self.images[ligne]
            self.apercu.montrer(self.vue(img) if self.vue is not None else img)

    def _comparer(self, oui: bool):
        if oui:
            self.apercu.montrer(self.original)
        else:
            self._choisi(self.vignettes.currentRow())

    def choix(self) -> QImage | None:
        ligne = self.vignettes.currentRow()
        return self.images[ligne] if 0 <= ligne < len(self.images) else None


class BarreAgrandir(QFrame):
    """Petite barre posée sur la photo pendant Agrandir.
    Ligne « Agrandir » : % ajoutés par côté (cadre extérieur). Ligne « Bord abîmé » : px du bord de la photo
    à jeter et faire redessiner par l'IA (cadre intérieur rouge). Les cases suivent le cadre, et l'inverse."""
    lancer = Signal()
    annuler = Signal()
    decrire = Signal()                          # bouton « Décrire » : description automatique (Qwen3.5)
    valeurs_changees = Signal(object, object)   # (ajout, bord abîmé) en px, (haut, bas, gauche, droite)

    COTES = (("haut", "Haut"), ("bas", "Bas"), ("gauche", "Gauche"), ("droite", "Droite"))   # noms traduits à l'affichage

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("panneau")
        self.taille = (1, 1)
        self.ajout = {}
        self.abime = {}
        colonne = QVBoxLayout(self)
        colonne.setContentsMargins(12, 6, 8, 8)
        colonne.setSpacing(4)
        aide = QLabel(tr("Cadre carré : tire vers l'extérieur pour agrandir.  Cadre rond rouge : tire vers "
                         "l'intérieur pour marquer un bord abîmé à refaire.  (Maj : les deux côtés)"))
        aide.setObjectName("discret")
        colonne.addWidget(aide)
        self.vide = None
        self.info_vide = QLabel(tr("Il y a du vide autour de la photo : le cadre part de la photo. Tire-le "
                                   "jusqu'où l'IA doit la prolonger : dans le vide (il s'arrête tout seul au bord "
                                   "de l'image), ou au-delà pour agrandir l'image."))
        self.info_vide.setWordWrap(True)
        self.info_vide.hide()
        colonne.addWidget(self.info_vide)
        bas = QHBoxLayout()
        bas.setSpacing(12)
        colonne.addLayout(bas)
        grille = QGridLayout()
        grille.setHorizontalSpacing(6)
        grille.setVerticalSpacing(4)
        bas.addLayout(grille)
        grille.addWidget(QLabel(tr("Agrandir")), 1, 0)
        grille.addWidget(QLabel(tr("Bord abîmé")), 2, 0)
        for i, (cle, nom) in enumerate(self.COTES):
            titre = QLabel(tr(nom))
            titre.setObjectName("discret")
            titre.setAlignment(Qt.AlignCenter)
            grille.addWidget(titre, 0, 1 + i)
            a = QSpinBox()
            a.setRange(0, 200)
            a.setSuffix(" %")
            a.setToolTip(tr("Ce que l'IA ajoute de ce côté, en % de la photo."))
            a.valueChanged.connect(self._case_changee)
            self.ajout[cle] = a
            grille.addWidget(a, 1, 1 + i)
            m = QSpinBox()
            m.setRange(0, 5000)
            m.setSuffix(" px")
            m.setToolTip(tr("Bande abîmée au bord de la photo : jetée puis redessinée par l'IA."))
            m.valueChanged.connect(self._case_changee)
            self.abime[cle] = m
            grille.addWidget(m, 2, 1 + i)
        droite = QVBoxLayout()
        droite.setSpacing(4)
        self.texte_taille = QLabel()
        self.texte_taille.setMinimumWidth(self.texte_taille.fontMetrics().horizontalAdvance("00000 × 00000 px"))
        self.texte_taille.setAlignment(Qt.AlignCenter)
        droite.addWidget(self.texte_taille)
        boutons = QHBoxLayout()
        b_annuler = QPushButton(tr("Annuler"))
        b_annuler.setAutoDefault(False)
        b_annuler.clicked.connect(self.annuler)
        self.b_lancer = QPushButton(tr("Lancer"))
        self.b_lancer.setObjectName("principal")
        self.b_lancer.setAutoDefault(False)
        self.b_lancer.clicked.connect(self.lancer)
        boutons.addWidget(b_annuler)
        boutons.addWidget(self.b_lancer)
        droite.addLayout(boutons)
        self.pleine = QCheckBox(tr("Pleine définition"))
        self.pleine.setToolTip(tr(
            "Après le choix d'une proposition, l'ajout est redessiné à la vraie taille de la photo, par morceaux : "
            "aussi net et détaillé que le reste, avec le même grain. Plus long (environ 30 s à 1 min par "
            "morceau de 1024 px). Sans effet sur une petite photo."))
        droite.addWidget(self.pleine)
        droite.addStretch()
        bas.addLayout(droite)
        # description facultative : écrite, ou faite par l'IA (« Décrire ») ; vide : l'IA devine d'après l'image
        ligne = QHBoxLayout()
        ligne.setSpacing(6)
        ligne.addWidget(QLabel(tr("Description")))
        self.texte = QLineEdit()
        self.texte.setPlaceholderText(tr("Facultatif : ce que l'IA doit ajouter (ex. foule, fumée, ciel nuageux). "
                                         "Vide : elle devine d'après l'image."))
        self.texte.setToolTip(tr("Guide ce que l'IA invente dans l'ajout : évite les objets ou personnages hors sujet. "
                                 "En français ou en anglais (traduit sur ce PC si le traducteur est installé)."))
        self.texte.setMinimumWidth(self.texte.fontMetrics().horizontalAdvance("x") * 60)
        ligne.addWidget(self.texte, 1)
        self.b_decrire = QPushButton(tr("Décrire (IA)"))
        self.b_decrire.setAutoDefault(False)
        self.b_decrire.setToolTip(tr("L'IA regarde la photo et écrit sa description (en anglais, modifiable) : "
                                     "style, scène, fond, lumière, couleurs. Demande le modèle Qwen3.5 2B."))
        self.b_decrire.clicked.connect(self.decrire)
        ligne.addWidget(self.b_decrire)
        colonne.addLayout(ligne)
        self._px = ((0, 0, 0, 0), (0, 0, 0, 0))
        parent.installEventFilter(self)
        self.hide()

    def ouvrir(self, largeur: int, hauteur: int, abime=(0, 0, 0, 0), vide=None):
        """vide : None, ou ((x0, y0, x1, y1) de la photo, (largeur, hauteur) de l'image) quand du vide transparent
        entoure la photo : le cadre part alors de la photo, les % sont ceux de la photo."""
        self.taille = (largeur, hauteur)
        self.vide = vide
        if vide is not None:
            x0, y0, x1, y1 = vide[0]
            self.taille = (x1 - x0, y1 - y0)
            largeur, hauteur = self.taille
        self.info_vide.setVisible(vide is not None)
        self.texte.clear()
        for c in self.abime.values():
            c.setMaximum(max(0, max(largeur, hauteur) - 32))
        self.definir_px((0, 0, 0, 0), abime)
        self.adjustSize()
        self._placer()
        self.show()
        self.raise_()

    def definir_px(self, ajout, abime):
        """Valeurs venant des cadres tirés à la souris."""
        self._px = (tuple(int(v) for v in ajout), tuple(int(v) for v in abime))
        w, h = self.taille
        for c, v, n in zip(self.ajout.values(), self._px[0], (h, h, w, w)):
            c.blockSignals(True)
            c.setValue(round(v * 100 / n))
            c.blockSignals(False)
        for c, v in zip(self.abime.values(), self._px[1]):
            c.blockSignals(True)
            c.setValue(v)
            c.blockSignals(False)
        self._maj_texte()

    def _case_changee(self):
        """Seule la case modifiée change (les autres gardent leur valeur exacte en px)."""
        w, h = self.taille
        ajout, abime = list(self._px[0]), list(self._px[1])
        for i, (c, n) in enumerate(zip(self.ajout.values(), (h, h, w, w))):
            if c is self.sender():
                ajout[i] = round(c.value() * n / 100)
        for i, c in enumerate(self.abime.values()):
            if c is self.sender():
                ajout_n = (h, h, w, w)[i]
                autre = abime[i ^ 1]
                abime[i] = min(c.value(), max(0, ajout_n - autre - 32))
        self._px = (tuple(ajout), tuple(abime))
        self._maj_texte()
        self.valeurs_changees.emit(*self._px)

    def _maj_texte(self):
        w, h = self.taille
        hh, bb, gg, dd = self._px[0]
        if self.vide is not None:                      # l'image ne rétrécit pas : elle grandit si le cadre dépasse
            (x0, y0, x1, y1), (W, H) = self.vide
            self.texte_taille.setText(f"{max(W, x1 + dd) - min(0, x0 - gg)} × {max(H, y1 + bb) - min(0, y0 - hh)} px")
        else:
            self.texte_taille.setText(f"{w + gg + dd} × {h + hh + bb} px")
        self.b_lancer.setEnabled(any(self._px[0]) or any(self._px[1]))

    def valeurs_px(self) -> tuple:
        """((ajout), (bord abîmé)), chacun (haut, bas, gauche, droite) en px."""
        return self._px

    def _placer(self):
        p = self.parentWidget()
        self.move(max(0, (p.width() - self.width()) // 2), 12)

    def eventFilter(self, objet, e):
        if e.type() == QEvent.Resize:
            self._placer()
        return False


class ReglagesUpscale(QDialog):
    def __init__(self, largeur: int, hauteur: int, parent=None, calque=None, cible: str = "image",
                 image_possible: bool = True, graphique: bool = False):
        """graphique : image faite surtout d'aplats (pochette, logo, affiche) : force douce proposée d'office.
        calque : None, ou (nom, (largeur, hauteur) de son contenu) : on peut alors ne traiter que ce calque.
        cible : choix de départ, « image », « net » (calque plus net à sa taille) ou « agrandi » (calque agrandi)."""
        super().__init__(parent)
        self.setWindowTitle(tr("Upscale"))
        self.taille = (largeur, hauteur)
        self.calque = calque
        self.cibles = {}
        cadre_cible = None
        if calque is not None:
            cadre_cible = QGroupBox(tr("Que faut-il traiter ?"))
            lc = QVBoxLayout(cadre_cible)
            groupe_c = QButtonGroup(self)
            for cle, texte in (("image", tr("Toute l'image : l'image entière et tous ses calques grandissent")),
                               ("net", tr("Le calque « {nom} » plus net, sans changer de taille",
                                          nom=calque[0])),
                               ("agrandi", tr("Le calque « {nom} » agrandi (l'image entière garde sa taille)",
                                              nom=calque[0]))):
                b = QRadioButton(texte)
                self.cibles[cle] = b
                groupe_c.addButton(b)
                lc.addWidget(b)
                b.toggled.connect(self._maj)
            self.cibles.get(cible, self.cibles["image"]).setChecked(True)
            if not image_possible:                  # un calque est verrouillé : toute l'image ne peut pas changer
                self.cibles["image"].setEnabled(False)
                self.cibles["image"].setToolTip(tr("Impossible : un calque est verrouillé (cadenas)."))
        self.net = QRadioButton(tr("Net (Flux redessine les détails, plus lent)"))
        self.rapide = QRadioButton(tr("Rapide (RealESRGAN seul, peut lisser)"))
        self.net.setChecked(True)
        groupe = QButtonGroup(self)
        groupe.addButton(self.net)
        groupe.addButton(self.rapide)
        self.facteur = QDoubleSpinBox()
        self.facteur.setRange(1.5, 4.0)
        self.facteur.setSingleStep(0.5)
        self.facteur.setValue(2.0)
        self.facteur.setPrefix("× ")
        self.force = QDoubleSpinBox()
        self.force.setRange(0.10, 0.60)
        self.force.setSingleStep(0.05)
        self.force.setValue(0.25 if graphique else 0.35)
        self.force.setToolTip(tr(
            "Force : la liberté laissée à Flux quand il redessine les détails (mode Net).\n"
            "0,10 à 0,25 : très fidèle à la photo, peu de détails ajoutés (visages, textes, logos).\n"
            "0,35 : bon équilibre, conseillé.\n"
            "0,45 à 0,60 : beaucoup de détails, mais l'IA en invente (un visage ou un texte peut changer un peu) ; "
            "pour paysages, végétation, tissus."))
        self.aide_force = QLabel(tr("Force : liberté laissée à l'IA pour redessiner les détails. 0,35 conseillé ; "
                                    "0,25 pour des visages, textes ou logos (plus fidèle) ; 0,45 pour des paysages "
                                    "ou des matières (plus de détails, un peu inventés)."))
        if graphique:
            self.aide_force.setText(tr("Image graphique (aplats, texte, logo) : force 0,25 proposée, pour que l'IA ne "
                                       "change pas les lettres. Les aplats sont protégés : rien n'y est inventé."))
        self.aide_force.setWordWrap(True)
        self.aide_force.setObjectName("discret")
        self.resultat = QLabel()
        self.facteur.valueChanged.connect(self._maj)
        self.net.toggled.connect(self._maj)
        form = QFormLayout()
        form.addRow(tr("Agrandir|facteur"), self.facteur)
        form.addRow(tr("Force (0,25 léger – 0,45 fort)"), self.force)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText(tr("Lancer"))
        boutons.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        if cadre_cible is not None:
            lay.addWidget(cadre_cible)
        lay.addWidget(self.net)
        lay.addWidget(self.rapide)
        lay.addLayout(form)
        lay.addWidget(self.aide_force)
        lay.addWidget(self.resultat)
        lay.addWidget(boutons)
        self._maj()

    def cible(self) -> str:
        return next((k for k, b in self.cibles.items() if b.isChecked()), "image")

    def _maj(self, *_):
        if not hasattr(self, "resultat"):            # fenêtre pas encore finie
            return
        self.force.setEnabled(self.net.isChecked())
        self.aide_force.setVisible(self.net.isChecked())
        cible = self.cible()
        self.facteur.setEnabled(cible != "net")
        if cible == "net":
            w, h = self.calque[1]
            self.resultat.setText(tr("Le calque garde sa taille : {largeur} × {hauteur} px", largeur=w, hauteur=h))
            return
        taille = self.calque[1] if cible == "agrandi" else self.taille
        w, h = (round(v * self.facteur.value()) for v in taille)
        if cible == "agrandi":
            self.resultat.setText(tr("Calque : {l0} × {h0} -> {largeur} × {hauteur} px (l'image entière reste en {fl} × {fh} "
                                     "px)", l0=taille[0], h0=taille[1], largeur=w, hauteur=h,
                                     fl=self.taille[0], fh=self.taille[1]))
        else:
            self.resultat.setText(tr("Taille finale : {largeur} × {hauteur} px", largeur=w, hauteur=h))

    def valeurs(self) -> dict:
        return {"net": self.net.isChecked(), "facteur": 2.0 if self.cible() == "net" else self.facteur.value(),
                "force": self.force.value(), "cible": self.cible()}


def duree(s: float) -> str:
    s = max(0, int(round(s or 0)))          # secondes entières (le temps restant peut être un nombre à virgule)
    return tr("{min} min {s} s", min=s // 60, s=f"{s % 60:02d}") if s >= 60 else tr("{s} s", s=s)


def texte_progression(info: dict) -> str:
    texte = tr("{duree} écoulées", duree=duree(info['secondes']))
    if info.get("restant") is not None:
        texte += tr("  —  encore environ {duree}", duree=duree(info['restant']))
    return texte


def regler_barre(barre: QProgressBar, info: dict):
    if info.get("fraction") is None:
        barre.setRange(0, 0)  # barre animée sans pourcentage
    else:
        barre.setRange(0, 1000)
        barre.setValue(int(info["fraction"] * 1000))


class Attente(QDialog):
    """Fenêtre « calcul en cours » : étape, barre de progression, temps, bouton Annuler."""
    annuler = Signal()

    def __init__(self, titre: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setModal(True)
        self.titre = QLabel(f"<b>{titre}</b>")
        self.etape = QLabel(tr("Envoi de l'image au moteur…"))
        self.barre = QProgressBar()
        self.barre.setTextVisible(True)
        self.barre.setFormat("%p %")
        self.barre.setRange(0, 0)
        self.temps = QLabel("")
        self.bouton = QPushButton(tr("Annuler"))
        self.bouton.setAutoDefault(False)
        self.bouton.clicked.connect(self._annuler)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        lay.addWidget(self.titre)
        lay.addWidget(self.etape)
        lay.addWidget(self.barre)
        lay.addWidget(self.temps)
        lay.addWidget(self.bouton, alignment=Qt.AlignRight)
        self.setFixedWidth(440)

    def maj(self, info: dict):
        self.etape.setText(info["etape"])
        regler_barre(self.barre, info)
        self.temps.setText(texte_progression(info))

    def _annuler(self):
        self.etape.setText(tr("Annulation…"))
        self.bouton.setEnabled(False)
        self.annuler.emit()

    def closeEvent(self, e):
        self._annuler()
        e.ignore()
