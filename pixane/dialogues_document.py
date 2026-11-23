"""Fenêtres du document : Nouvelle image (formats tout prêts, unités, résolution, mode, fond perdu), Taille de la
zone de travail, Exporter pour l'impression (CMJN)."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import formats as fmt
from .formats import Format, depuis_px, mm_vers_px, vers_px
from .langue import tr


def _boutons(d: QDialog, texte_ok: str) -> QDialogButtonBox:
    b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    b.button(QDialogButtonBox.Ok).setText(texte_ok)
    b.button(QDialogButtonBox.Cancel).setText(tr("Annuler"))
    b.accepted.connect(d.accept)
    b.rejected.connect(d.reject)
    return b


def _poids(w: int, h: int) -> str:
    o = w * h * 4
    return tr("{n} Mo", n=f"{o / 1024 ** 2:.1f}".replace(".", tr(",|décimale"))) if o >= 1024 ** 2 \
        else tr("{n} Ko", n=max(1, round(o / 1024)))


def _nombre(v: float, decimales: int = 2) -> str:
    s = f"{v:.{decimales}f}".rstrip("0").rstrip(".")
    return s.replace(".", tr(",|décimale"))


class ApercuFeuille(QWidget):
    """Petit aperçu d'une feuille : sa forme, son fond (damier si transparent), l'image posée dessus (ce qui sort de
    la feuille, donc rogné, est montré pâle avec un pointillé) et les repères (fond perdu, zone de sécurité)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(260, 190)
        self.feuille = (1, 1)
        self.fond = QColor(Qt.white)
        self.image = None             # (QImage réduite, x, y, largeur, hauteur) en pixels de la feuille
        self.reperes: list = []

    def definir(self, largeur: int, hauteur: int, fond: QColor, image=None, reperes=None):
        self.feuille = (max(1, largeur), max(1, hauteur))
        self.fond, self.image, self.reperes = QColor(fond), image, list(reperes or [])
        self.update()

    def paintEvent(self, _e):
        W, H = self.feuille
        x0, y0, x1, y1 = 0.0, 0.0, float(W), float(H)
        if self.image is not None:
            _im, ix, iy, iw, ih = self.image
            x0, y0, x1, y1 = min(x0, ix), min(y0, iy), max(x1, ix + iw), max(y1, iy + ih)
        k = min((self.width() - 12) / (x1 - x0), (self.height() - 12) / (y1 - y0))
        ox = (self.width() - (x1 - x0) * k) / 2 - x0 * k
        oy = (self.height() - (y1 - y0) * k) / 2 - y0 * k
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        feuille = QRectF(ox, oy, W * k, H * k)
        if self.fond.alpha() < 255:                       # damier sous un fond transparent
            p.save()
            p.setClipRect(feuille)
            case = 6
            for yy in range(int(feuille.top()), int(feuille.bottom()) + 1, case):
                for xx in range(int(feuille.left()), int(feuille.right()) + 1, case):
                    p.fillRect(xx, yy, case, case, QColor(205, 205, 205) if (xx // case + yy // case) % 2
                               else QColor(240, 240, 240))
            p.restore()
        p.fillRect(feuille, self.fond)
        if self.image is not None:
            im, ix, iy, iw, ih = self.image
            cible = QRectF(ox + ix * k, oy + iy * k, iw * k, ih * k)
            p.setOpacity(0.3)                             # partie qui sera rognée : pâle
            p.drawImage(cible, im)
            p.setOpacity(1.0)
            p.save()
            p.setClipRect(feuille)
            p.drawImage(cible, im)
            p.restore()
            if not feuille.contains(cible):
                p.setPen(QPen(QColor(220, 60, 60), 1, Qt.DashLine))
                p.drawRect(cible)
        p.setPen(QPen(QColor(0, 170, 220), 1, Qt.DashLine))
        for sens, v in self.reperes:
            if sens == "v":
                p.drawLine(int(ox + v * k), int(feuille.top()), int(ox + v * k), int(feuille.bottom()))
            else:
                p.drawLine(int(feuille.left()), int(oy + v * k), int(feuille.right()), int(oy + v * k))
        p.setPen(QPen(QColor(128, 128, 128), 1))
        p.drawRect(feuille)
        p.end()


def image_reduite(image: QImage | None, cote: int = 600) -> QImage | None:
    """Copie réduite (aperçus rapides)."""
    if image is None or image.isNull():
        return None
    if max(image.width(), image.height()) <= cote:
        return image.copy()
    return image.scaled(cote, cote, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class ChoixFond(QWidget):
    """Blanc, Transparent, Noir ou une couleur au choix."""
    change = Signal()

    def __init__(self, parent=None, transparent_d_abord: bool = False):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.liste = QComboBox()
        self.liste.addItem(tr("Blanc"), "#ffffffff")
        self.liste.addItem(tr("Transparent"), "#00000000")
        self.liste.addItem(tr("Noir"), "#ff000000")
        self.liste.addItem(tr("Couleur…"), "autre")
        self.couleur_autre = QColor("#3a5f8a")
        self.bouton = QToolButton()
        self.bouton.setFixedSize(26, 22)
        self.bouton.setToolTip(tr("Choisir la couleur"))
        self.bouton.clicked.connect(self._choisir)
        self.liste.currentIndexChanged.connect(self._actualiser)
        lay.addWidget(self.liste, 1)
        lay.addWidget(self.bouton)
        if transparent_d_abord:
            self.liste.setCurrentIndex(1)
        self._actualiser()

    def _choisir(self):
        c = QColorDialog.getColor(self.couleur_autre, self.window(), tr("Couleur du fond"),
                                  QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self.couleur_autre = c
            self.liste.setCurrentIndex(3)
            self._actualiser()

    def _actualiser(self):
        c = self.couleur()
        self.bouton.setStyleSheet(f"background:{c.name(QColor.HexArgb) if c.alpha() else 'transparent'};"
                                  "border:1px solid #888;border-radius:3px")
        self.bouton.setVisible(self.liste.currentData() == "autre")
        self.change.emit()

    def couleur(self) -> QColor:
        d = self.liste.currentData()
        return QColor(self.couleur_autre) if d == "autre" else QColor(d)

    def valeur(self) -> str:
        """La couleur choisie, #aarrggbb (#00000000 = transparent)."""
        return self.couleur().name(QColor.HexArgb)

    def definir(self, valeur: str):
        c = QColor(valeur)
        if not c.isValid():
            return
        if c.alpha() == 0:
            valeur = "#00000000"
        i = self.liste.findData(c.name(QColor.HexArgb) if c.alpha() else valeur)
        if i >= 0:
            self.liste.setCurrentIndex(i)
        else:
            self.couleur_autre = c
            self.liste.setCurrentIndex(self.liste.findData("autre"))
        self._actualiser()


class ChampLongueur(QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setRange(0.01, 300000)
        self.setKeyboardTracking(False)
        self.setMinimumWidth(110)


# ======================================================================== Nouvelle image
class NouvelleImage(QDialog):
    """Nouvelle image : formats tout prêts à gauche, réglages à droite (comme Photoshop)."""

    def __init__(self, largeur: int | None = None, hauteur: int | None = None, reglages=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Nouvelle image"))
        self.reglages = reglages
        self._unite = "px"
        self._bloque = False
        lay = QHBoxLayout(self)

        # ---- formats tout prêts
        gauche = QVBoxLayout()
        self.arbre = QTreeWidget()
        self.arbre.setHeaderHidden(True)
        self.arbre.setMinimumWidth(300)
        self.arbre.setSelectionMode(QAbstractItemView.SingleSelection)
        self.arbre.itemClicked.connect(self._format_clique)
        gauche.addWidget(QLabel(tr("Formats tout prêts")))
        gauche.addWidget(self.arbre, 1)
        b = QHBoxLayout()
        self.b_garder = QPushButton(tr("Enregistrer ce format…"))
        self.b_garder.clicked.connect(self._enregistrer_format)
        self.b_supprimer = QPushButton(tr("Supprimer"))
        self.b_supprimer.setToolTip(tr("Supprimer ce format enregistré"))
        self.b_supprimer.clicked.connect(self._supprimer_format)
        self.b_supprimer.setEnabled(False)
        b.addWidget(self.b_garder)
        b.addWidget(self.b_supprimer)
        gauche.addLayout(b)
        lay.addLayout(gauche, 1)

        # ---- réglages
        droite = QVBoxLayout()
        f = QFormLayout()
        self.nom = QLineEdit()
        self.nom.setPlaceholderText(tr("sans titre"))
        f.addRow(tr("Nom"), self.nom)
        self.largeur, self.hauteur = ChampLongueur(), ChampLongueur()
        self.unite = QComboBox()
        for u in fmt.UNITES:
            self.unite.addItem(fmt.nom_unite(u), u)
        ligne = QHBoxLayout()
        ligne.addWidget(self.largeur)
        ligne.addWidget(self.unite)
        f.addRow(tr("Largeur"), ligne)
        f.addRow(tr("Hauteur"), self.hauteur)
        orient = QHBoxLayout()
        self.b_portrait, self.b_paysage = QToolButton(), QToolButton()
        self.b_portrait.setText(tr("Portrait"))
        self.b_paysage.setText(tr("Paysage"))
        groupe = QButtonGroup(self)
        for bt in (self.b_portrait, self.b_paysage):
            bt.setCheckable(True)
            bt.setToolButtonStyle(Qt.ToolButtonTextOnly)
            bt.setMinimumWidth(90)
            groupe.addButton(bt)
            orient.addWidget(bt)
        orient.addStretch(1)
        self.b_portrait.clicked.connect(lambda: self._orienter(True))
        self.b_paysage.clicked.connect(lambda: self._orienter(False))
        f.addRow(tr("Orientation"), orient)
        self.dpi = QDoubleSpinBox()
        self.dpi.setRange(1, 10000)
        self.dpi.setDecimals(0)
        self.dpi.setSuffix(" " + tr("ppp"))
        self.dpi.setToolTip(tr("Points par pouce : 300 pour l'impression, 72 pour l'écran"))
        self.dpi.setKeyboardTracking(False)
        f.addRow(tr("Résolution"), self.dpi)
        self.mode = QComboBox()
        self.mode.addItem(tr("Couleurs RVB"), "rvb")
        self.mode.addItem(tr("Niveaux de gris"), "gris")
        self.bits = QComboBox()
        for b in (8, 16, 32):
            self.bits.addItem(tr("{n} bits par couche", n=b), b)
        self.bits.setToolTip(tr(
            "8 bits : 256 nuances par couleur, comme le JPEG, le PNG et le web.\n"
            "16 bits : 65 536 nuances (dégradés et réglages sans cassures).\n"
            "32 bits (HDR) : les couleurs peuvent être plus claires que le blanc.\n"
            "Modifiable ensuite : Image > Mode."))
        if reglages is not None:
            i = self.bits.findData(int(reglages.value("nouvelle_bits", 8)))
            self.bits.setCurrentIndex(max(0, i))
        lm = QHBoxLayout()
        lm.addWidget(self.mode, 1)
        lm.addWidget(self.bits)
        f.addRow(tr("Mode"), lm)
        self.fond = ChoixFond()
        f.addRow(tr("Fond"), self.fond)
        self.fond_perdu, self.marge = QDoubleSpinBox(), QDoubleSpinBox()
        for s, maxi in ((self.fond_perdu, 50), (self.marge, 100)):
            s.setRange(0, maxi)
            s.setDecimals(1)
            s.setSingleStep(0.5)
            s.setSuffix(" mm")
            s.setKeyboardTracking(False)
        self.fond_perdu.setToolTip(tr("Bande ajoutée tout autour, coupée par l'imprimeur : le fond doit déborder "
                                      "jusqu'au bord de l'image (en général 3 mm)"))
        self.marge.setToolTip(tr("Zone de sécurité, à l'intérieur du format fini : rien d'important (texte, visage) "
                                 "au-delà de cette ligne"))
        f.addRow(tr("Fond perdu"), self.fond_perdu)
        f.addRow(tr("Zone de sécurité"), self.marge)
        droite.addLayout(f)
        self.apercu = ApercuFeuille()
        droite.addWidget(self.apercu, 0, Qt.AlignHCenter)
        self.info = QLabel()
        self.info.setWordWrap(True)
        droite.addWidget(self.info)
        droite.addStretch(1)
        droite.addWidget(_boutons(self, tr("Créer")))
        lay.addLayout(droite, 1)

        for s in (self.largeur, self.hauteur, self.dpi, self.fond_perdu, self.marge):
            s.valueChanged.connect(self._actualiser)
        self.unite.currentIndexChanged.connect(self._unite_changee)
        self.fond.change.connect(self._actualiser)
        self._remplir_arbre()

        # ---- point de départ : presse-papiers, sinon le dernier format, sinon Full HD
        depart = None
        if largeur and hauteur:
            depart = Format(tr("Presse-papiers"), largeur, hauteur, "px", 72)
        elif reglages is not None:
            depart = fmt.dernier_format(reglages)
        self.appliquer_format(depart or Format("Full HD", 1920, 1080, "px", 72), garder_nom=True)
        self.resize(820, 520)

    # ---------------------------------------------------------- liste des formats
    def _remplir_arbre(self):
        self.arbre.clear()
        gras = QFont()
        gras.setBold(True)
        categories = list(fmt.formats())
        perso = fmt.formats_perso(self.reglages) if self.reglages is not None else []
        if perso:
            categories.insert(0, (tr("Mes formats"), perso))
        for nom, liste in categories:
            cat = QTreeWidgetItem([nom])
            cat.setFont(0, gras)
            cat.setFlags(Qt.ItemIsEnabled)
            cat.setData(0, Qt.UserRole + 1, nom == tr("Mes formats") and bool(perso))
            for f in liste:
                it = QTreeWidgetItem([f.nom])
                it.setData(0, Qt.UserRole, f)
                cat.addChild(it)
            self.arbre.addTopLevelItem(cat)
            cat.setExpanded(nom in (tr("Mes formats"), tr("Pochettes"), tr("Livres")))

    def _format_clique(self, it: QTreeWidgetItem, _col=0):
        f = it.data(0, Qt.UserRole)
        perso = it.parent() is not None and bool(it.parent().data(0, Qt.UserRole + 1))
        self.b_supprimer.setEnabled(perso)
        if f is not None:
            self.appliquer_format(f)

    def appliquer_format(self, f: Format, garder_nom: bool = False):
        self._bloque = True
        self._unite = f.unite
        self.unite.setCurrentIndex(fmt.UNITES.index(f.unite))
        self._decimales()
        self.dpi.setValue(f.dpi)
        self.largeur.setValue(f.largeur)
        self.hauteur.setValue(f.hauteur)
        self.fond_perdu.setValue(f.fond_perdu)
        self.marge.setValue(f.marge)
        if f.mode and self.mode.findData(f.mode) >= 0:
            self.mode.setCurrentIndex(self.mode.findData(f.mode))
        if f.fond:
            self.fond.definir(f.fond)
        self._bloque = False
        self._actualiser()

    def _decimales(self):
        d = 0 if self._unite == "px" else (3 if self._unite == "in" else 2)
        for s in (self.largeur, self.hauteur):
            s.setDecimals(d)
            s.setSuffix(" " + fmt.abrege_unite(self._unite))

    def _unite_changee(self):
        if self._bloque:
            return
        nouvelle = self.unite.currentData()
        dpi = self.dpi.value()
        wpx = vers_px(self.largeur.value(), self._unite, dpi) if self._unite != "px" else self.largeur.value()
        hpx = vers_px(self.hauteur.value(), self._unite, dpi) if self._unite != "px" else self.hauteur.value()
        self._bloque = True
        self._unite = nouvelle
        self._decimales()
        self.largeur.setValue(depuis_px(wpx, nouvelle, dpi))
        self.hauteur.setValue(depuis_px(hpx, nouvelle, dpi))
        self._bloque = False
        self._actualiser()

    def _orienter(self, portrait: bool):
        w, h = self.largeur.value(), self.hauteur.value()
        if (portrait and w > h) or (not portrait and h > w):
            self._bloque = True
            self.largeur.setValue(h)
            self.hauteur.setValue(w)
            self._bloque = False
        self._actualiser()

    def _actualiser(self):
        if self._bloque:
            return
        w, h = self.largeur.value(), self.hauteur.value()
        self.b_portrait.setChecked(h > w)
        self.b_paysage.setChecked(w > h)
        if w == h:
            for bt in (self.b_portrait, self.b_paysage):
                bt.group().setExclusive(False)
                bt.setChecked(False)
                bt.group().setExclusive(True)
        W, H = self.pixels()
        f = self.format_choisi()
        texte = tr("Image : {l} × {h} px", l=W, h=H)
        if f.fond_perdu:
            texte += " " + tr("(fond perdu compris)")
        if self._unite != "px":
            pw, ph = vers_px(w, self._unite, f.dpi), vers_px(h, self._unite, f.dpi)
            texte += "\n" + tr("Format fini : {l} × {h} cm", l=_nombre(pw / f.dpi * 2.54), h=_nombre(ph / f.dpi * 2.54))
        else:
            texte += "\n" + tr("À {dpi} ppp : {l} × {h} cm imprimés", dpi=round(f.dpi),
                               l=_nombre(W / f.dpi * 2.54), h=_nombre(H / f.dpi * 2.54))
        texte += "\n" + tr("Mémoire : {poids} par calque", poids=_poids(W, H))
        if W * H > 400_000_000:
            texte += "\n" + tr("Attention : image énorme, Pixane Photo risque d'être très lent.")
        self.info.setText(texte)
        if hasattr(self, "apercu"):
            self.apercu.definir(W, H, self.couleur(), reperes=self.reperes())

    # ---------------------------------------------------------- formats de l'utilisateur
    def _enregistrer_format(self):
        if self.reglages is None:
            return
        nom, ok = QInputDialog.getText(self, tr("Enregistrer ce format"), tr("Nom du format :"))
        if not ok or not nom.strip():
            return
        liste = [f for f in fmt.formats_perso(self.reglages) if f.nom != nom.strip()]
        liste.append(replace(self.format_choisi(), nom=nom.strip()))
        fmt.enregistrer_formats_perso(self.reglages, liste)
        self._remplir_arbre()

    def _supprimer_format(self):
        it = self.arbre.currentItem()
        f = it.data(0, Qt.UserRole) if it else None
        if f is None or self.reglages is None:
            return
        if QMessageBox.question(self, tr("Supprimer"), tr("Supprimer le format « {nom} » ?", nom=f.nom)) \
                != QMessageBox.Yes:
            return
        fmt.enregistrer_formats_perso(self.reglages, [g for g in fmt.formats_perso(self.reglages) if g.nom != f.nom])
        self.b_supprimer.setEnabled(False)
        self._remplir_arbre()

    # ---------------------------------------------------------- résultat
    def format_choisi(self) -> Format:
        return Format(self.nom.text().strip() or tr("sans titre"), self.largeur.value(), self.hauteur.value(),
                      self._unite, self.dpi.value(), self.fond_perdu.value(), self.marge.value(),
                      self.mode.currentData(), self.fond.valeur())

    def pixels(self) -> tuple[int, int]:
        return self.format_choisi().pixels()

    def couleur(self) -> QColor:
        return self.fond.couleur()

    def mode_couleur(self) -> str:
        return self.mode.currentData()

    def nom_document(self) -> str | None:
        return self.nom.text().strip() or None

    def reperes(self) -> list:
        """Repères posés tout seuls : bord du format fini (fond perdu) et zone de sécurité."""
        f = self.format_choisi()
        W, H = f.pixels()
        res = []
        for mm in ([f.fond_perdu] if f.fond_perdu else []) + ([f.fond_perdu + f.marge] if f.marge else []):
            d = mm_vers_px(mm, f.dpi)
            if 0 < d < min(W, H) / 2:
                res += [("v", float(d)), ("v", float(W - d)), ("h", float(d)), ("h", float(H - d))]
        return res

    def image(self):
        from PySide6.QtGui import QImage
        W, H = self.pixels()
        img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
        img.fill(self.couleur())
        return img

    def bits_choisis(self) -> int:
        return int(self.bits.currentData())

    def accept(self):
        if self.reglages is not None:
            fmt.retenir_dernier(self.reglages, replace(self.format_choisi(), nom=tr("Dernier format utilisé")))
            self.reglages.setValue("nouvelle_bits", self.bits_choisis())
        super().accept()


# ======================================================================== Taille de la zone de travail
class ZoneTravail(QDialog):
    """Agrandir (ou rogner) la feuille sans étirer l'image : nouvelle taille, point d'ancrage, couleur ajoutée."""

    def __init__(self, largeur: int, hauteur: int, dpi: float, parent=None, image: QImage | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Taille de la zone de travail"))
        self.w0, self.h0, self.dpi = largeur, hauteur, dpi
        self._image = image_reduite(image)
        self._unite = "px"
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("Taille actuelle : {l} × {h} px", l=largeur, h=hauteur)))
        f = QFormLayout()
        self.largeur, self.hauteur = ChampLongueur(), ChampLongueur()
        self.largeur.setRange(-300000, 300000)
        self.hauteur.setRange(-300000, 300000)
        self.unite = QComboBox()
        for u in fmt.UNITES:
            self.unite.addItem(fmt.nom_unite(u), u)
        self.unite.addItem(tr("pourcentage"), "%")
        ligne = QHBoxLayout()
        ligne.addWidget(self.largeur)
        ligne.addWidget(self.unite)
        f.addRow(tr("Largeur"), ligne)
        f.addRow(tr("Hauteur"), self.hauteur)
        self.relatif = QCheckBox(tr("Relative (ajouter à la taille actuelle)"))
        f.addRow("", self.relatif)
        # ancre : 3 × 3 boutons
        grille = QGridLayout()
        grille.setSpacing(2)
        self._ancres = QButtonGroup(self)
        for i in range(9):
            b = QToolButton()
            b.setCheckable(True)
            b.setFixedSize(28, 28)
            self._ancres.addButton(b, i)
            grille.addWidget(b, i // 3, i % 3)
        self._ancres.button(4).setChecked(True)
        self._ancres.idClicked.connect(self._fleches)
        g = QWidget()
        g.setLayout(grille)
        f.addRow(tr("Ancrage"), g)
        self.fond = ChoixFond()
        f.addRow(tr("Couleur ajoutée"), self.fond)
        lay.addLayout(f)
        self.apercu = ApercuFeuille()
        lay.addWidget(self.apercu, 0, Qt.AlignHCenter)
        self.info = QLabel()
        lay.addWidget(self.info)
        lay.addWidget(_boutons(self, tr("OK")))
        self.unite.currentIndexChanged.connect(self._unite_changee)
        self.relatif.toggled.connect(self._relatif)
        self._ancres.idClicked.connect(lambda _i: self._actualiser())
        self.fond.change.connect(self._actualiser)
        for s in (self.largeur, self.hauteur):
            s.valueChanged.connect(self._actualiser)
        self._decimales()
        self.largeur.setValue(largeur)
        self.hauteur.setValue(hauteur)
        self._fleches(4)
        self._actualiser()

    def _decimales(self):
        d = 0 if self._unite == "px" else (3 if self._unite == "in" else 1 if self._unite == "%" else 2)
        for s in (self.largeur, self.hauteur):
            s.setDecimals(d)
            s.setSuffix(" " + ("%" if self._unite == "%" else fmt.abrege_unite(self._unite)))

    def _vers_px(self, v: float, ref: int) -> int:
        if self._unite == "%":
            return round(ref * v / 100)
        if self._unite == "px":
            return round(v)
        return round(v * fmt.POUCES[self._unite] * self.dpi)

    def _depuis_px(self, px: float, ref: int) -> float:
        if self._unite == "%":
            return px * 100 / ref
        return depuis_px(px, self._unite, self.dpi)

    def _unite_changee(self):
        W, H = self.pixels()
        rel = self.relatif.isChecked()
        self._unite = self.unite.currentData()
        self._decimales()
        if rel:
            self.largeur.setValue(self._depuis_px(W - self.w0, self.w0))
            self.hauteur.setValue(self._depuis_px(H - self.h0, self.h0))
        else:
            self.largeur.setValue(self._depuis_px(W, self.w0))
            self.hauteur.setValue(self._depuis_px(H, self.h0))

    def _relatif(self, rel: bool):
        W, H = self.pixels(not rel)
        if rel:
            self.largeur.setValue(self._depuis_px(W - self.w0, self.w0))
            self.hauteur.setValue(self._depuis_px(H - self.h0, self.h0))
        else:
            self.largeur.setValue(self._depuis_px(W, self.w0))
            self.hauteur.setValue(self._depuis_px(H, self.h0))

    def _fleches(self, centre: int):
        fl = {(-1, -1): "↖", (0, -1): "↑", (1, -1): "↗", (-1, 0): "←", (1, 0): "→", (-1, 1): "↙", (0, 1): "↓",
              (1, 1): "↘"}
        cx, cy = centre % 3, centre // 3
        for i in range(9):
            dx, dy = i % 3 - cx, i // 3 - cy
            self._ancres.button(i).setText("●" if (dx, dy) == (0, 0) else fl.get((dx, dy), ""))

    def pixels(self, relatif: bool | None = None) -> tuple[int, int]:
        rel = self.relatif.isChecked() if relatif is None else relatif
        w = self._vers_px(self.largeur.value(), self.w0)
        h = self._vers_px(self.hauteur.value(), self.h0)
        if rel:
            w, h = self.w0 + w, self.h0 + h
        return max(1, w), max(1, h)

    def decalage(self) -> tuple[int, int]:
        """Place de l'ancienne image dans la nouvelle (selon l'ancrage)."""
        W, H = self.pixels()
        a = self._ancres.checkedId()
        fx, fy = (a % 3) / 2, (a // 3) / 2
        return round((W - self.w0) * fx), round((H - self.h0) * fy)

    def couleur(self) -> QColor:
        return self.fond.couleur()

    def _actualiser(self):
        W, H = self.pixels()
        self.info.setText(tr("Nouvelle taille : {l} × {h} px", l=W, h=H)
                          + ("" if W >= self.w0 and H >= self.h0 else "\n" + tr("L'image sera rognée.")))
        if hasattr(self, "apercu"):
            dx, dy = self.decalage()
            im = self._image
            if im is None:                            # sans image : un gris neutre à sa place
                im = QImage(4, 4, QImage.Format_ARGB32_Premultiplied)
                im.fill(QColor(150, 150, 150))
            self.apercu.definir(W, H, self.couleur(), (im, dx, dy, self.w0, self.h0))


# ======================================================================== Exporter pour l'impression
class ExportImpression(QDialog):
    """Format (TIFF, JPEG, PDF), profil CMJN de Windows, intention de rendu, compensation du point noir, résolution."""

    def __init__(self, dpi: float, reglages=None, parent=None):
        super().__init__(parent)
        from .impression import profils_cmjn
        self.setWindowTitle(tr("Exporter pour l'impression (CMJN)"))
        self.reglages = reglages
        lay = QVBoxLayout(self)
        intro = QLabel(tr("L'image est convertie en CMJN (les quatre encres de l'imprimeur) avec le profil choisi. "
                          "Demandez à votre imprimeur le profil qu'il utilise ; en Europe, c'est souvent "
                          "« Coated FOGRA39 » (papier couché)."))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        f = QFormLayout()
        self.format = QComboBox()
        self.format.addItem("TIFF (.tif)", ".tif")
        self.format.addItem("PDF (.pdf)", ".pdf")
        self.format.addItem("JPEG (.jpg)", ".jpg")
        f.addRow(tr("Format"), self.format)
        self.profil = QComboBox()
        for nom, chemin in profils_cmjn():
            self.profil.addItem(nom, chemin)
        f.addRow(tr("Profil CMJN"), self.profil)
        self.intention = QComboBox()
        self.intention.addItem(tr("Perceptive (photos)"), "perceptive")
        self.intention.addItem(tr("Colorimétrie relative (logos, aplats)"), "relative")
        f.addRow(tr("Intention de rendu"), self.intention)
        self.compensation = QCheckBox(tr("Compensation du point noir"))
        self.compensation.setChecked(True)
        f.addRow("", self.compensation)
        self.dpi = QSpinBox()
        self.dpi.setRange(1, 10000)
        self.dpi.setSuffix(" " + tr("ppp"))
        self.dpi.setValue(round(dpi))
        self.dpi.setToolTip(tr("Seulement noté dans le fichier : les pixels ne changent pas"))
        f.addRow(tr("Résolution"), self.dpi)
        self.qualite = QSpinBox()
        self.qualite.setRange(50, 100)
        self.qualite.setValue(95)
        f.addRow(tr("Qualité JPEG"), self.qualite)
        lay.addLayout(f)
        if not self.profil.count():
            lay.addWidget(QLabel(tr("Aucun profil CMJN trouvé dans Windows.")))
        lay.addWidget(_boutons(self, tr("Exporter…")))
        if reglages is not None:
            for combo, cle in ((self.format, "cmjn_format"), (self.profil, "cmjn_profil"),
                               (self.intention, "cmjn_intention")):
                i = combo.findData(reglages.value(cle, ""))
                if i >= 0:
                    combo.setCurrentIndex(i)
        self.format.currentIndexChanged.connect(lambda: self.qualite.setEnabled(self.format.currentData() != ".tif"))
        self.qualite.setEnabled(self.format.currentData() != ".tif")
        if not self.profil.count():
            self.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).setEnabled(False)

    def valeurs(self) -> dict:
        return {"ext": self.format.currentData(), "profil": self.profil.currentData(),
                "intention": self.intention.currentData(), "compensation": self.compensation.isChecked(),
                "dpi": self.dpi.value(), "qualite": self.qualite.value()}

    def accept(self):
        if self.reglages is not None:
            v = self.valeurs()
            self.reglages.setValue("cmjn_format", v["ext"])
            self.reglages.setValue("cmjn_profil", v["profil"])
            self.reglages.setValue("cmjn_intention", v["intention"])
        super().accept()
