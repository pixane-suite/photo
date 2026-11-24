"""Création : vectoriser (vtracer), panorama (OpenCV), GIF animé, photo d'identité (planche à imprimer), collage de
photos, double exposition, coller en perspective (point de fuite), retouche du visage et maquillage (IA, par Flux
Kontext comme « Modifier avec une consigne »), et les instantanés nommés de l'Historique.
Fenetre (fenetre.py) hérite de CreationMixin ; _creation() est appelé à la fin de la construction de la fenêtre."""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from PySide6.QtCore import QByteArray, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel,
                               QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSlider, QSpinBox, QVBoxLayout,
                               QWidget)

from .langue import tr

DPI = 300


def mm(v: float) -> int:
    return int(round(v / 25.4 * DPI))


def _rgba(img: QImage) -> np.ndarray:
    from .document import tableau
    return tableau(img.convertToFormat(QImage.Format_RGBA8888)).copy()


def _qimage(a: np.ndarray) -> QImage:
    from .document import qimage_rgba
    return qimage_rgba(np.ascontiguousarray(a))


def _png(img: QImage) -> bytes:
    from PySide6.QtCore import QBuffer
    b = QBuffer()
    b.open(QBuffer.WriteOnly)
    img.save(b, "PNG")
    return bytes(b.data())


def couvrir(img: QImage, w: int, h: int) -> QImage:
    """img agrandie ou réduite pour couvrir w × h, centrée, le dépassement coupé."""
    s = img.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return s.copy((s.width() - w) // 2, (s.height() - h) // 2, w, h)


# ====================================================================== vectoriser
def vectoriser_svg(img: QImage, couleurs: bool = True, details: int = 6, lisse: bool = True) -> str:
    """Image -> SVG (tracés). details 1..10 : plus haut = plus de couleurs et de petites formes gardées."""
    import vtracer
    details = max(1, min(10, int(details)))
    return vtracer.convert_raw_image_to_svg(
        _png(img), img_format="png", colormode="color" if couleurs else "binary",
        hierarchical="stacked", mode="spline" if lisse else "polygon",
        filter_speckle=max(1, 12 - details), color_precision=max(1, min(8, details - 1)),
        layer_difference=max(4, 40 - details * 3), corner_threshold=60, length_threshold=4.0, splice_threshold=45,
        path_precision=3)


def svg_vers_image(svg: str, w: int, h: int) -> QImage:
    from PySide6.QtSvg import QSvgRenderer
    rendu = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    rendu.render(p, QRectF(0, 0, w, h))
    p.end()
    return img


class DialogueVectoriser(QDialog):
    """Image > Vectoriser… : aperçu ; le résultat va dans un nouveau calque, et peut être enregistré en SVG."""

    def __init__(self, image: QImage, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Vectoriser"))
        self.image = image
        k = min(1.0, 700 / max(image.width(), image.height()))
        self.petite = image.scaled(max(1, round(image.width() * k)), max(1, round(image.height() * k)),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.svg = ""
        lay = QVBoxLayout(self)
        self.apercu = QLabel()
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setMinimumSize(420, 300)
        lay.addWidget(self.apercu, 1)
        f = QFormLayout()
        self.couleurs = QComboBox()
        self.couleurs.addItem(tr("En couleurs"), True)
        self.couleurs.addItem(tr("Noir et blanc (logo, dessin)"), False)
        f.addRow(tr("Mode"), self.couleurs)
        self.details = QSlider(Qt.Horizontal)
        self.details.setRange(1, 10)
        self.details.setValue(6)
        f.addRow(tr("Détails"), self.details)
        self.lisse = QCheckBox(tr("Courbes lisses (sinon : lignes droites)"))
        self.lisse.setChecked(True)
        f.addRow("", self.lisse)
        lay.addLayout(f)
        aide = QLabel(tr("Le dessin devient des formes vectorielles : il s'agrandit sans flou. Idéal pour un logo, "
                         "un dessin, un texte scanné. OK le pose dans un nouveau calque ; « Enregistrer le SVG… » "
                         "garde le fichier vectoriel."))
        aide.setWordWrap(True)
        aide.setObjectName("discret")
        lay.addWidget(aide)
        bas = QHBoxLayout()
        b = QPushButton(tr("Enregistrer le SVG…"))
        b.clicked.connect(self.enregistrer_svg)
        bas.addWidget(b)
        bas.addStretch(1)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        bas.addWidget(boutons)
        lay.addLayout(bas)
        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.setInterval(250)
        self._minuteur.timeout.connect(self._apercu)
        for s in (self.couleurs.currentIndexChanged, self.details.valueChanged, self.lisse.toggled):
            s.connect(lambda *_: self._minuteur.start())
        self._apercu()

    def reglages(self):
        return dict(couleurs=self.couleurs.currentData(), details=self.details.value(), lisse=self.lisse.isChecked())

    def _apercu(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            svg = vectoriser_svg(self.petite, **self.reglages())
            img = svg_vers_image(svg, self.petite.width(), self.petite.height())
        finally:
            QApplication.restoreOverrideCursor()
        pm = QPixmap(img.size())
        pm.fill(QColor(255, 255, 255))
        p = QPainter(pm)
        p.drawImage(0, 0, img)
        p.end()
        self.apercu.setPixmap(pm.scaled(self.apercu.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resultat(self) -> tuple[str, QImage]:
        if not self.svg:
            self.svg = vectoriser_svg(self.image, **self.reglages())
        return self.svg, svg_vers_image(self.svg, self.image.width(), self.image.height())

    def enregistrer_svg(self, chemin: str | None = None):
        if not chemin:
            chemin, _f = QFileDialog.getSaveFileName(self, tr("Enregistrer le SVG"), "", "SVG (*.svg)")
        if not chemin:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.svg = vectoriser_svg(self.image, **self.reglages())
            Path(chemin).write_text(self.svg, encoding="utf-8")
        finally:
            QApplication.restoreOverrideCursor()


# ====================================================================== panorama
def panorama(images: list[QImage], recadrer: bool = True) -> QImage | None:
    """Assemble des photos qui se chevauchent (Stitcher d'OpenCV). recadrer : les bords vides sont coupés (sinon :
    transparents). None si les photos ne se raccordent pas."""
    import cv2
    tab = []
    for img in images:
        a = _rgba(img)[..., :3]
        k = min(1.0, 2400 / max(a.shape[:2]))
        if k < 1:
            a = cv2.resize(a, (round(a.shape[1] * k), round(a.shape[0] * k)), interpolation=cv2.INTER_AREA)
        tab.append(cv2.cvtColor(a, cv2.COLOR_RGB2BGR))
    statut, res = None, None
    for mode in (cv2.Stitcher_PANORAMA, cv2.Stitcher_SCANS):
        s = cv2.Stitcher_create(mode)
        statut, res = s.stitch(tab)
        if statut == cv2.Stitcher_OK:
            break
    if statut != cv2.Stitcher_OK or res is None:
        return None
    rgb = cv2.cvtColor(res, cv2.COLOR_BGR2RGB)
    plein = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY) > 0
    plein = cv2.morphologyEx(plein.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
    if recadrer:
        y0, y1, x0, x1 = _plus_grand_rectangle(plein)
        rgb, plein = rgb[y0:y1, x0:x1], plein[y0:y1, x0:x1]
    out = np.dstack([rgb, np.where(plein, 255, 0).astype(np.uint8)])
    return _qimage(out)


def _plus_grand_rectangle(plein: np.ndarray):
    """Rectangle entièrement rempli, trouvé en rognant les bords (ligne ou colonne la plus vide d'abord)."""
    y0, y1, x0, x1 = 0, plein.shape[0], 0, plein.shape[1]
    while y1 - y0 > 10 and x1 - x0 > 10:
        z = plein[y0:y1, x0:x1]
        bords = {"h": 1 - z[0].mean(), "b": 1 - z[-1].mean(), "g": 1 - z[:, 0].mean(), "d": 1 - z[:, -1].mean()}
        cote, vide = max(bords.items(), key=lambda kv: kv[1])
        if vide <= 0:
            break
        if cote == "h":
            y0 += 1
        elif cote == "b":
            y1 -= 1
        elif cote == "g":
            x0 += 1
        else:
            x1 -= 1
    return y0, y1, x0, x1


# ====================================================================== GIF animé
def gif_anime(images: list[QImage], chemin: str | Path, duree_ms: int = 200, boucle: bool = True,
              largeur_max: int = 800, aller_retour: bool = False) -> int:
    """Chaque image = une vue du GIF ; renvoie le nombre de vues."""
    from PIL import Image
    vues = list(images) + (list(images[-2:0:-1]) if aller_retour and len(images) > 2 else [])
    pil = []
    for img in vues:
        if img.width() > largeur_max:
            img = img.scaledToWidth(largeur_max, Qt.SmoothTransformation)
        a = _rgba(img)
        im = Image.fromarray(a, "RGBA")
        fond = Image.new("RGBA", im.size, (255, 255, 255, 255))
        fond.alpha_composite(im)
        pil.append(fond.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT))
    pil[0].save(str(chemin), save_all=True, append_images=pil[1:], duration=max(20, int(duree_ms)),
                loop=0 if boucle else 1, optimize=True, disposal=2)
    return len(pil)


class DialogueGif(QDialog):
    def __init__(self, calques: list, parent):
        """calques : [(nom, QImage)] (de bas en haut)."""
        super().__init__(parent)
        self.setWindowTitle(tr("Exporter un GIF animé"))
        self.calques = calques
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Chaque calque coché devient une image de l'animation, du bas vers le haut de la liste des "
                         "calques."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.liste = QListWidget()
        for nom, _img in calques:
            it = QListWidgetItem(nom)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.liste.addItem(it)
        lay.addWidget(self.liste, 1)
        f = QFormLayout()
        self.duree = QSpinBox()
        self.duree.setRange(20, 10000)
        self.duree.setValue(250)
        self.duree.setSuffix(" ms")
        f.addRow(tr("Durée de chaque image"), self.duree)
        self.largeur = QSpinBox()
        self.largeur.setRange(32, 4000)
        self.largeur.setValue(min(800, max(img.width() for _n, img in calques)))
        self.largeur.setSuffix(" px")
        f.addRow(tr("Largeur maximale"), self.largeur)
        self.boucle = QCheckBox(tr("En boucle"))
        self.boucle.setChecked(True)
        f.addRow("", self.boucle)
        self.aller_retour = QCheckBox(tr("Aller-retour"))
        f.addRow("", self.aller_retour)
        lay.addLayout(f)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)

    def images(self) -> list[QImage]:
        return [img for i, (_n, img) in enumerate(self.calques) if self.liste.item(i).checkState() == Qt.Checked]


# ====================================================================== photo d'identité
FORMATS_IDENTITE = {     # clé : (nom, largeur mm, hauteur mm, hauteur de la tête mm, du haut de la tête au bord mm)
    "35x45": ("35 × 45 mm (Belgique, France, Europe)", 35, 45, 34, 4),
    "2x2": ("2 × 2 pouces, 51 × 51 mm (États-Unis)", 51, 51, 30, 8),
    "40x50": ("40 × 50 mm", 40, 50, 37, 5),
    "35x35": ("35 × 35 mm", 35, 35, 26, 4),
}


def points_par_defaut(img: QImage):
    """Sans repères : une tête supposée au centre, un peu au-dessus du milieu (photo de face)."""
    W, H = img.width(), img.height()
    t = min(H * 0.45, W * 0.6)
    return (W / 2, H * 0.42 - t / 2), (W / 2, H * 0.42 + t / 2)


def cadre_depuis_points(haut, menton, format_cle: str):
    """Rectangle (x, y, l, h) à découper : la tête (du haut des cheveux au menton) a la hauteur voulue par le
    format, et le haut de la tête est à la bonne distance du bord."""
    _n, lw, lh, tete, marge = FORMATS_IDENTITE[format_cle]
    (xh, yh), (xm, ym) = haut, menton
    tete_px = max(4.0, abs(ym - yh))
    echelle = tete_px / tete                            # px de la photo par mm
    cw, ch = lw * echelle, lh * echelle
    cx = (xh + xm) / 2
    return int(round(cx - cw / 2)), int(round(min(yh, ym) - marge * echelle)), int(round(cw)), int(round(ch))


def points_depuis_masques(tete: np.ndarray, visage: np.ndarray):
    """Haut de la tête (cheveux compris) et menton, d'après les masques de SAM ; None si rien de trouvé."""
    t = tete > 127
    v = visage > 127
    if v.sum() < 50:
        return None
    ys, xs = np.nonzero(v)
    cx = float(xs.mean())
    menton = (cx, float(ys.max()))
    if t.sum() >= 50:
        yt = np.nonzero(t)[0]
        haut = (cx, float(yt.min()))
    else:                                               # sans la tête : le front + un tiers du visage
        haut = (cx, float(ys.min() - (ys.max() - ys.min()) * 0.3))
    return haut, menton


def photo_identite(img: QImage, format_cle: str, cadre=None) -> QImage:
    """La photo d'identité à 300 dpi (le dehors de la photo, s'il y en a, est blanc)."""
    _n, lw, lh, _t, _h = FORMATS_IDENTITE[format_cle]
    if cadre is None:
        cadre = cadre_depuis_points(*points_par_defaut(img), format_cle)
    x, y, w, h = cadre
    res = QImage(mm(lw), mm(lh), QImage.Format_ARGB32_Premultiplied)
    res.fill(QColor(255, 255, 255))
    p = QPainter(res)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.drawImage(QRectF(0, 0, res.width(), res.height()), img, QRectF(x, y, w, h))
    p.end()
    return res


def planche(photo: QImage, largeur_mm=150, hauteur_mm=100, ecart_mm=2) -> tuple[QImage, int]:
    """Planche à imprimer (10 × 15 cm par défaut) remplie de copies, avec des traits de coupe gris."""
    W, H, e = mm(largeur_mm), mm(hauteur_mm), mm(ecart_mm)
    pw, ph = photo.width(), photo.height()
    nx, ny = max(1, (W - e) // (pw + e)), max(1, (H - e) // (ph + e))
    res = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    res.fill(QColor(255, 255, 255))
    p = QPainter(res)
    x0 = (W - nx * pw - (nx - 1) * e) // 2
    y0 = (H - ny * ph - (ny - 1) * e) // 2
    p.setPen(QPen(QColor(190, 190, 190), 1))
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + i * (pw + e), y0 + j * (ph + e)
            p.drawImage(x, y, photo)
            p.drawRect(x - 1, y - 1, pw + 1, ph + 1)
    p.end()
    return res, nx * ny


class DialogueIdentite(QDialog):
    """Deux points : le haut de la tête (cheveux compris) et le menton ; le cadre en découle, aux règles du format.
    « Trouver la tête (IA) » les pose avec SAM 3.1."""

    def __init__(self, image: QImage, parent, trouver=None):
        """trouver(rappel) : demande à l'IA les deux points ; rappel((haut, menton) ou None)."""
        super().__init__(parent)
        self.setWindowTitle(tr("Photo d'identité"))
        self.image = image
        self.points: list[list[float]] = []
        self._tenu = None
        lay = QVBoxLayout(self)
        ligne = QHBoxLayout()
        self.vue = QLabel()
        self.vue.setFixedSize(420, 420)
        self.vue.setAlignment(Qt.AlignCenter)
        self.vue.setCursor(Qt.CrossCursor)
        self.vue.mousePressEvent = self._presser
        self.vue.mouseMoveEvent = self._glisser
        self.vue.mouseReleaseEvent = lambda _e: setattr(self, "_tenu", None)
        ligne.addWidget(self.vue)
        self.resultat_vue = QLabel()
        self.resultat_vue.setFixedSize(200, 260)
        self.resultat_vue.setAlignment(Qt.AlignCenter)
        ligne.addWidget(self.resultat_vue)
        lay.addLayout(ligne)
        haut = QHBoxLayout()
        self.b_ia = QPushButton(tr("Trouver la tête (IA)"))
        self.b_ia.setToolTip(tr("L'IA pose les deux points (SAM 3.1, quelques secondes) ; tu peux les corriger "
                                "ensuite en les glissant"))
        self.b_ia.setEnabled(trouver is not None)
        self.b_ia.clicked.connect(lambda: trouver(self.poser_points))
        haut.addWidget(self.b_ia)
        b = QPushButton(tr("Recommencer"))
        b.clicked.connect(self.recommencer)
        haut.addWidget(b)
        haut.addStretch(1)
        lay.addLayout(haut)
        f = QFormLayout()
        self.format = QComboBox()
        for cle, (nom, *_r) in FORMATS_IDENTITE.items():
            self.format.addItem(tr(nom), cle)
        self.format.currentIndexChanged.connect(self._dessiner)
        f.addRow(tr("Format"), self.format)
        self.sortie = QComboBox()
        self.sortie.addItem(tr("Une photo"), "photo")
        self.sortie.addItem(tr("Planche à imprimer 10 × 15 cm"), "planche")
        self.sortie.setCurrentIndex(1)
        f.addRow(tr("Résultat"), self.sortie)
        lay.addLayout(f)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setObjectName("discret")
        lay.addWidget(self.info)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        self._dessiner()

    def recommencer(self):
        self.points = []
        self._dessiner()

    def poser_points(self, pts):
        if pts is None:
            QMessageBox.information(self, tr("Photo d'identité"), tr(
                "Aucune tête trouvée : clique sur le haut de la tête, puis sur le menton."))
            return
        self.points = [list(pts[0]), list(pts[1])]
        self._dessiner()

    def _echelle(self) -> float:
        return min(420 / self.image.width(), 420 / self.image.height())

    def _vers_image(self, e):
        k = self._echelle()
        pm = self.vue.pixmap()
        dx = (self.vue.width() - pm.width()) / 2 if pm else 0
        dy = (self.vue.height() - pm.height()) / 2 if pm else 0
        return [(e.position().x() - dx) / k, (e.position().y() - dy) / k]

    def _presser(self, e):
        pt = self._vers_image(e)
        if len(self.points) < 2:
            self.points.append(pt)
            self._tenu = len(self.points) - 1
        else:                                         # le point le plus proche suit la souris
            d = [(q[0] - pt[0]) ** 2 + (q[1] - pt[1]) ** 2 for q in self.points]
            self._tenu = d.index(min(d))
            self.points[self._tenu] = pt
        self._dessiner()

    def _glisser(self, e):
        if self._tenu is not None:
            self.points[self._tenu] = self._vers_image(e)
            self._dessiner()

    def haut_menton(self):
        if len(self.points) == 2:
            a, b = sorted(self.points, key=lambda q: q[1])
            return tuple(a), tuple(b)
        return points_par_defaut(self.image)

    def cadre(self):
        return cadre_depuis_points(*self.haut_menton(), self.format.currentData())

    def _dessiner(self):
        n = len(self.points)
        self.info.setText(
            tr("Clique sur le haut de la tête (cheveux compris).") if n == 0 else
            tr("Clique maintenant sur le menton.") if n == 1 else
            tr("Le cadre rouge suit les règles du format (taille de la tête, marge au-dessus). Glisse un point pour "
               "le corriger. Fond uni et clair conseillé ; regard vers l'objectif, sans sourire."))
        img = self.image
        k = self._echelle()
        pm = QPixmap.fromImage(img.scaled(round(img.width() * k), round(img.height() * k), Qt.KeepAspectRatio,
                                          Qt.SmoothTransformation))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        x, y, w, h = self.cadre()
        p.setPen(QPen(QColor(255, 60, 60), 2))
        p.drawRect(QRectF(x * k, y * k, w * k, h * k))
        for i, (px, py) in enumerate(self.points):
            p.setPen(QPen(QColor(0, 0, 0), 2))
            p.setBrush(QColor(0, 200, 255) if i == 0 else QColor(255, 200, 0))
            p.drawEllipse(QPointF(px * k, py * k), 5, 5)
        if len(self.points) == 2:
            (hx, hy), (mx, my) = self.haut_menton()
            p.setPen(QPen(QColor(0, 200, 255), 1, Qt.DashLine))
            p.drawLine(QPointF(0, hy * k), QPointF(pm.width(), hy * k))
            p.drawLine(QPointF(0, my * k), QPointF(pm.width(), my * k))
        p.end()
        self.vue.setPixmap(pm)
        self.resultat_vue.setPixmap(QPixmap.fromImage(self.resultat_photo()).scaled(
            self.resultat_vue.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resultat_photo(self) -> QImage:
        return photo_identite(self.image, self.format.currentData(), self.cadre())

    def resultat(self) -> tuple[QImage, str]:
        photo = self.resultat_photo()
        if self.sortie.currentData() == "planche":
            img, n = planche(photo)
            return img, tr("Planche d'identité ({n} photos)", n=n)
        return photo, tr("Photo d'identité")


# ====================================================================== collage
def collage(images: list[QImage], colonnes: int, largeur: int, hauteur: int, espace: int, fond: QColor,
            arrondi: int = 0):
    """[(QImage du calque à la taille du collage, nom)] + le fond : chaque photo couvre sa case (grille)."""
    n = len(images)
    colonnes = max(1, min(colonnes, n))
    lignes = (n + colonnes - 1) // colonnes
    cw = (largeur - espace * (colonnes + 1)) / colonnes
    ch = (hauteur - espace * (lignes + 1)) / lignes
    calques = []
    from PySide6.QtGui import QPainterPath
    for k, img in enumerate(images):
        i, j = k % colonnes, k // colonnes
        dernier = j == lignes - 1 and n % colonnes
        decal = (colonnes - n % colonnes) * (cw + espace) / 2 if dernier else 0     # dernière ligne centrée
        x = espace + i * (cw + espace) + decal
        y = espace + j * (ch + espace)
        case = couvrir(img, max(1, int(cw)), max(1, int(ch)))
        c = QImage(largeur, hauteur, QImage.Format_ARGB32_Premultiplied)
        c.fill(Qt.transparent)
        p = QPainter(c)
        p.setRenderHint(QPainter.Antialiasing)
        if arrondi:
            ch_ = QPainterPath()
            ch_.addRoundedRect(QRectF(int(x), int(y), case.width(), case.height()), arrondi, arrondi)
            p.setClipPath(ch_)
        p.drawImage(int(x), int(y), case)
        p.end()
        calques.append(c)
    f = QImage(largeur, hauteur, QImage.Format_ARGB32_Premultiplied)
    f.fill(fond)
    return f, calques


class DialogueCollage(QDialog):
    def __init__(self, parent, chemins: list[str] | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Nouveau collage de photos"))
        self.resize(620, 560)
        lay = QVBoxLayout(self)
        haut = QHBoxLayout()
        b = QPushButton(tr("Ajouter des photos…"))
        b.clicked.connect(self._ajouter)
        haut.addWidget(b)
        b = QPushButton(tr("Retirer"))
        b.clicked.connect(lambda: [self.liste.takeItem(self.liste.row(i)) for i in self.liste.selectedItems()]
                          and self._apercu())
        haut.addWidget(b)
        haut.addStretch(1)
        lay.addLayout(haut)
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.IconMode)
        self.liste.setIconSize(QSize(90, 70))
        self.liste.setDragDropMode(QAbstractItemView.InternalMove)
        self.liste.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.liste.setMaximumHeight(130)
        self.liste.model().rowsMoved.connect(lambda *_: self._apercu())
        lay.addWidget(self.liste)
        f = QFormLayout()
        self.colonnes = QSpinBox()
        self.colonnes.setRange(1, 10)
        self.colonnes.setValue(3)
        f.addRow(tr("Colonnes"), self.colonnes)
        taille = QHBoxLayout()
        self.largeur = QSpinBox()
        self.largeur.setRange(100, 20000)
        self.largeur.setValue(3000)
        self.hauteur = QSpinBox()
        self.hauteur.setRange(100, 20000)
        self.hauteur.setValue(2000)
        for w in (self.largeur, self.hauteur):
            w.setSuffix(" px")
            taille.addWidget(w)
        f.addRow(tr("Taille"), taille)
        self.espace = QSpinBox()
        self.espace.setRange(0, 500)
        self.espace.setValue(30)
        self.espace.setSuffix(" px")
        f.addRow(tr("Espace"), self.espace)
        self.arrondi = QSpinBox()
        self.arrondi.setRange(0, 300)
        self.arrondi.setSuffix(" px")
        f.addRow(tr("Coins arrondis"), self.arrondi)
        self.fond = QColor(255, 255, 255)
        self.b_fond = QPushButton()
        self.b_fond.clicked.connect(self._choisir_fond)
        f.addRow(tr("Fond"), self.b_fond)
        lay.addLayout(f)
        self.apercu = QLabel()
        self.apercu.setAlignment(Qt.AlignCenter)
        self.apercu.setMinimumHeight(200)
        lay.addWidget(self.apercu, 1)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)
        for w in (self.colonnes, self.largeur, self.hauteur, self.espace, self.arrondi):
            w.valueChanged.connect(lambda *_: self._apercu())
        self.images: dict[str, QImage] = {}
        self._maj_fond()
        if chemins:
            self.ajouter(chemins)

    def _maj_fond(self):
        self.b_fond.setStyleSheet(f"background: {self.fond.name()}; min-height: 22px")

    def _choisir_fond(self):
        c = QColorDialog.getColor(self.fond, self, tr("Couleur du fond"))
        if c.isValid():
            self.fond = c
            self._maj_fond()
            self._apercu()

    def _ajouter(self):
        from .document import EXTENSIONS_LECTURE
        chemins, _f = QFileDialog.getOpenFileNames(self, tr("Photos du collage"), "",
                                                   tr("Images") + f" ({EXTENSIONS_LECTURE})")
        self.ajouter(chemins)

    def ajouter(self, chemins):
        from .document import Document
        for ch in chemins:
            try:
                img = QImage(Document.ouvrir(ch).image)
            except Exception:                         # noqa: BLE001 — fichier illisible : passé
                continue
            self.images[ch] = img
            it = QListWidgetItem(Path(ch).name)
            it.setData(Qt.UserRole, ch)
            it.setIcon(QPixmap.fromImage(img.scaled(90, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self.liste.addItem(it)
        n = self.liste.count()
        if n:
            self.colonnes.setValue(max(1, round(n ** 0.5 + 0.49)) if n > 2 else n)
        self._apercu()

    def choisies(self) -> list[tuple[str, QImage]]:
        return [(self.liste.item(i).data(Qt.UserRole), self.images[self.liste.item(i).data(Qt.UserRole)])
                for i in range(self.liste.count())]

    def resultat(self, reduit: float = 1.0):
        imgs = [img for _c, img in self.choisies()]
        if not imgs:
            return None
        k = reduit
        return collage(imgs, self.colonnes.value(), int(self.largeur.value() * k), int(self.hauteur.value() * k),
                       int(self.espace.value() * k), self.fond, int(self.arrondi.value() * k))

    def _apercu(self):
        k = min(1.0, 520 / self.largeur.value(), 260 / self.hauteur.value())
        r = self.resultat(k)
        if r is None:
            self.apercu.setText(tr("Ajoute au moins deux photos."))
            return
        fond, calques = r
        p = QPainter(fond)
        for c in calques:
            p.drawImage(0, 0, c)
        p.end()
        self.apercu.setPixmap(QPixmap.fromImage(fond))


# ====================================================================== double exposition
def double_exposition(taille: QSize, seconde: QImage, silhouette: np.ndarray | None, base: QImage,
                      douceur: float = 8.0):
    """(image du calque, masque du calque) : la seconde photo couvre l'image ; elle n'apparaît que dans la
    silhouette (la sélection) ; sans sélection, dans les zones sombres de la photo (silhouette sur fond clair)."""
    import cv2
    w, h = taille.width(), taille.height()
    img = couvrir(seconde, w, h)
    if silhouette is None:
        g = cv2.cvtColor(_rgba(base)[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32)
        m = np.clip((235 - g) / 120, 0, 1)                    # sombre = sujet
    else:
        m = silhouette.astype(np.float32) / 255
    if douceur > 0:
        m = cv2.GaussianBlur(m, (0, 0), douceur)
    m8 = np.clip(m * 255, 0, 255).astype(np.uint8)
    masque = QImage(np.ascontiguousarray(m8).data, w, h, w, QImage.Format_Grayscale8).copy()
    return img, masque


# ====================================================================== retouche du visage, maquillage (IA)
VISAGE = [
    ("sourire", "Sourire naturel", "make the person smile naturally"),
    ("yeux", "Yeux bien ouverts", "make the person's eyes naturally open"),
    ("regard", "Regard vers l'objectif", "make the person look straight at the camera"),
    ("peau", "Peau plus lisse", "smooth the skin slightly and remove small blemishes, keep natural skin texture"),
    ("cernes", "Sans cernes", "remove the dark circles under the eyes"),
    ("jeune", "Plus jeune (environ 10 ans)", "make the person look about ten years younger"),
    ("age", "Plus âgé (environ 15 ans)", "make the person look about fifteen years older"),
    ("dents", "Dents plus blanches", "whiten the teeth naturally"),
]
MAQUILLAGE = [
    ("naturel", "Maquillage naturel", "apply a light natural make-up"),
    ("levres", "Rouge à lèvres", "apply {couleur} lipstick"),
    ("paupieres", "Fard à paupières", "apply {couleur} eyeshadow"),
    ("eyeliner", "Eye-liner et mascara", "apply black eyeliner and mascara"),
    ("blush", "Blush", "apply a soft pink blush on the cheeks"),
    ("soiree", "Maquillage de soirée", "apply an elegant evening make-up"),
]
COULEURS_MAQUILLAGE = [("rouge", "red"), ("rose", "pink"), ("nude", "nude"), ("prune", "plum"), ("corail", "coral"),
                       ("bordeaux", "burgundy"), ("doré", "golden"), ("bleu", "blue"), ("vert", "green")]
GARDER = "Keep the same person and identity, the same pose, expression otherwise unchanged, lighting and background."


def consigne_visage(choix: list[str], liste, couleur: str = "red") -> str:
    parties = [en.format(couleur=couleur) for cle, _fr, en in liste if cle in choix]
    if not parties:
        return ""
    return ", ".join(parties).capitalize() + ". " + GARDER


class DialogueVisage(QDialog):
    def __init__(self, parent, maquillage: bool = False):
        super().__init__(parent)
        self.maquillage = maquillage
        self.liste = MAQUILLAGE if maquillage else VISAGE
        self.setWindowTitle(tr("Maquillage (IA)") if maquillage else tr("Retouche du visage (IA)"))
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Coche ce qui doit changer ; la personne, la pose et le fond restent les mêmes. Avec une "
                         "sélection, seule la zone choisie change. Modèle Flux Kontext (environ 1 min par "
                         "proposition)."))
        aide.setWordWrap(True)
        aide.setObjectName("discret")
        lay.addWidget(aide)
        self.cases = {}
        for cle, fr, _en in self.liste:
            c = QCheckBox(tr(fr))
            self.cases[cle] = c
            lay.addWidget(c)
        self.couleur = QComboBox()
        for fr, en in COULEURS_MAQUILLAGE:
            self.couleur.addItem(tr(fr), en)
        if maquillage:
            f = QFormLayout()
            f.addRow(tr("Couleur (rouge à lèvres, fard)"), self.couleur)
            lay.addLayout(f)
        f = QFormLayout()
        self.nb = QSpinBox()
        self.nb.setRange(1, 4)
        self.nb.setValue(2)
        f.addRow(tr("Propositions"), self.nb)
        lay.addLayout(f)
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)

    def consigne(self) -> str:
        return consigne_visage([k for k, c in self.cases.items() if c.isChecked()], self.liste,
                               self.couleur.currentData())


# ====================================================================== la fenêtre
from .retouche_plus import RetouchePlusMixin  # noqa: E402


class CreationMixin(RetouchePlusMixin):

    def _creation(self):
        menus = {a.text().replace("&", ""): a.menu() for a in self.menuBar().actions() if a.menu() is not None}

        def ajouter(menu_nom, texte, fonction, cle, avant=None):
            m = menus.get(tr(menu_nom))
            if m is None:
                return
            a = QAction(texte, self)
            a.triggered.connect(fonction)
            setattr(self, cle, a)
            cible = next((x for x in m.actions() if x.text() == avant), None) if avant else None
            m.insertAction(cible, a) if cible is not None else m.addAction(a)
        imprimer = tr("Imprimer…")
        ajouter("Fichier", tr("Nouveau collage de photos…"), self.nouveau_collage, "a_collage", imprimer)
        ajouter("Fichier", tr("Assembler un panorama…"), self.assembler_panorama, "a_panorama", imprimer)
        ajouter("Fichier", tr("Exporter un GIF animé…"), self.exporter_gif, "a_gif", imprimer)
        ajouter("Image", tr("Photo d'identité…"), self.photo_identite, "a_identite")
        ajouter("Image", tr("Vectoriser…"), self.vectoriser, "a_vectoriser")
        ajouter("Édition", tr("Coller en perspective…"), self.coller_perspective, "a_coller_persp")
        ajouter("Calque", tr("Double exposition…"), self.double_exposition, "a_double_expo")
        ajouter("IA", tr("Retouche du visage (IA)…"), lambda: self.ia_visage(False), "a_ia_visage",
                tr("Retouche portrait…"))
        ajouter("IA", tr("Maquillage (IA)…"), lambda: self.ia_visage(True), "a_ia_maquillage",
                tr("Retouche portrait…"))
        self._persp_coller = None
        self._retouche_plus(ajouter)
        self._instantanes_ui()

    # ---------------------------------------------------------- vectoriser
    def vectoriser(self):
        if not self.doc:
            return
        actif = self.doc.calque_actif
        img = self.doc.image if actif.special or actif.groupe else actif.image
        d = DialogueVectoriser(img, self)
        if d.exec():
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                _svg, rendu = d.resultat()
            finally:
                QApplication.restoreOverrideCursor()
            from .fenetre import CommandeEtat
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(),
                                              self.doc.etat_nouveau_calque(rendu, tr("Vectorisé")), tr("Vectoriser")))
        d.deleteLater()

    # ---------------------------------------------------------- panorama
    def assembler_panorama(self, chemins=None):
        from .document import EXTENSIONS_LECTURE, Document
        if not chemins:
            chemins, _f = QFileDialog.getOpenFileNames(self, tr("Photos du panorama (qui se chevauchent)"),
                                                       self.reglages.value("dossier", ""),
                                                       tr("Images") + f" ({EXTENSIONS_LECTURE})")
        if not chemins:
            return None
        if len(chemins) < 2:
            QMessageBox.information(self, tr("Panorama"), tr("Choisis au moins deux photos qui se chevauchent."))
            return None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            images = [QImage(Document.ouvrir(c).image) for c in chemins]
            res = panorama(images)
        finally:
            QApplication.restoreOverrideCursor()
        if res is None:
            QMessageBox.information(self, tr("Panorama"), tr(
                "Ces photos ne se raccordent pas : il faut qu'elles se chevauchent (environ un tiers), prises du "
                "même endroit en tournant."))
            return None
        doc = Document(res)
        self._installer_document(doc)
        self.statusBar().showMessage(tr("Panorama de {n} photos : {l} × {h} px.", n=len(chemins), l=res.width(),
                                        h=res.height()), 8000)
        return doc

    # ---------------------------------------------------------- GIF animé
    def exporter_gif(self, chemin: str | None = None, d=None):
        if not self.doc:
            return None
        calques = [(c.nom, c.image) for c in self.doc.calques if not c.special and not c.groupe]
        if len(calques) < 2:
            QMessageBox.information(self, tr("GIF animé"), tr(
                "Il faut au moins deux calques : chacun devient une image de l'animation."))
            return None
        if d is None:
            d = DialogueGif(calques, self)
            if not d.exec():
                return None
        if not chemin:
            chemin, _f = QFileDialog.getSaveFileName(self, tr("Exporter un GIF animé"), "", "GIF (*.gif)")
        if not chemin:
            return None
        n = gif_anime(d.images(), chemin, d.duree.value(), d.boucle.isChecked(), d.largeur.value(),
                      d.aller_retour.isChecked())
        self.statusBar().showMessage(tr("GIF animé de {n} images enregistré : {chemin}", n=n, chemin=chemin), 8000)
        return n

    # ---------------------------------------------------------- photo d'identité
    def photo_identite(self, d=None):
        if not self.doc:
            return None
        if d is None:
            d = DialogueIdentite(self.doc.image, self, self._trouver_tete)
            if not d.exec():
                return None
        from .document import Document
        img, nom = d.resultat()
        doc = Document(img.convertToFormat(QImage.Format_RGB32))
        doc.dpi = float(DPI)
        self._installer_document(doc)
        self.statusBar().showMessage(tr("{nom} à {dpi} dpi : imprime-la à 100 % (sans « ajuster à la page »).",
                                        nom=nom, dpi=DPI), 10000)
        return doc

    def _trouver_tete(self, rappel):
        """Bouton « Trouver la tête (IA) » : SAM 3.1 cherche la tête et le visage."""
        from . import recettes
        if not self._sam_present(tr("Photo d'identité")):
            return
        self._carte_ia(tr("Recherche de la tête"), recettes.tete,
                       lambda cartes: rappel(points_depuis_masques(cartes[0], cartes[1]) if len(cartes) >= 2
                                             else None), toutes=True, vide_ok=True)

    # ---------------------------------------------------------- collage
    def nouveau_collage(self, d=None):
        if d is None:
            d = DialogueCollage(self)
            if not d.exec():
                return None
        r = d.resultat()
        if r is None or len(d.choisies()) < 1:
            return None
        from .document import Calque, Document
        fond, calques = r
        noms = [Path(c).stem for c, _i in d.choisies()]
        doc = Document(calques=[Calque(tr("Fond"), fond.convertToFormat(QImage.Format_ARGB32_Premultiplied))] +
                       [Calque(n, c) for n, c in zip(noms, calques)])
        self._installer_document(doc)
        self.statusBar().showMessage(tr("Collage de {n} photos : chacune est dans son calque (Déplacer, "
                                        "Transformer pour l'ajuster).", n=len(calques)), 10000)
        return doc

    # ---------------------------------------------------------- double exposition
    def double_exposition(self, chemin: str | None = None):
        if not self.doc:
            return None
        from .document import EXTENSIONS_LECTURE, Document, masque
        autres = [d for d in self.documents if d is not self.doc]
        seconde = None
        if chemin:
            seconde = QImage(Document.ouvrir(chemin).image)
        else:
            choix = [self._nom_onglet(d) for d in autres] + [tr("Un fichier…")]
            nom, ok = QInputDialog.getItem(self, tr("Double exposition"), tr(
                "Deuxième photo (elle apparaîtra dans la silhouette : la sélection, ou les zones sombres de la photo "
                "sur fond clair) :"), choix, 0, False)
            if not ok:
                return None
            if nom == tr("Un fichier…"):
                chemin, _f = QFileDialog.getOpenFileName(self, tr("Deuxième photo"), self.reglages.value("dossier", ""),
                                                         tr("Images") + f" ({EXTENSIONS_LECTURE})")
                if not chemin:
                    return None
                seconde = QImage(Document.ouvrir(chemin).image)
            else:
                seconde = autres[choix.index(nom)].image
        doc = self.doc
        sil = None if doc.selection_vide() else masque(doc.selection).copy()
        img, m = double_exposition(doc.image.size(), seconde, sil, doc.image)
        from .document import Calque
        from .fenetre import CommandeEtat
        from .composition import FORMAT_MASQUE
        c = Calque(doc.nom_libre(tr("Double exposition")), img.convertToFormat(QImage.Format_ARGB32_Premultiplied),
                   mode="ecran", masque=m.convertToFormat(FORMAT_MASQUE))
        self.historique.push(CommandeEtat(doc, doc.etat(), doc.inserer(c), tr("Double exposition")))
        self.statusBar().showMessage(tr("Double exposition : nouveau calque en mode Superposition, avec un masque "
                                        "(peins le masque, ou change le mode et l'opacité, pour ajuster)."), 10000)
        return c

    # ---------------------------------------------------------- coller en perspective (point de fuite)
    def coller_perspective(self, image: QImage | None = None):
        c = self.canevas
        if not self.doc or c.transfo is not None or c.cadre is not None or c.persp is not None:
            return
        if image is None:
            image = QApplication.clipboard().image()
        if image is None or image.isNull():
            QMessageBox.information(self, tr("Coller en perspective"), tr(
                "Copie d'abord une image (Ctrl+C dans Pixane ou ailleurs), puis pose ses 4 coins sur la surface vue "
                "de biais (un mur, un écran, une affiche)."))
            return
        self._persp_coller = image
        c.commencer_persp()
        self.opt_pinceau.hide()
        self.opt_persp.show()
        self.options.adjustSize()
        self.statusBar().showMessage(tr("Tire les 4 coins sur la surface vue de biais ; l'image collée suivra sa "
                                        "perspective. Entrée ou double-clic pour coller, Échap pour annuler."), 20000)

    def _coller_persp_fini(self, coins) -> bool:
        """Appelé par _valider_persp : l'image copiée est posée dans le quadrilatère (nouveau calque)."""
        img = self._persp_coller
        self._persp_coller = None
        if img is None:
            return False
        import cv2
        doc = self.doc
        w, h = doc.image.width(), doc.image.height()
        src = np.float32([[0, 0], [img.width(), 0], [img.width(), img.height()], [0, img.height()]])
        dst = np.float32([[q.x(), q.y()] for q in coins])
        M = cv2.getPerspectiveTransform(src, dst)
        a = _rgba(img)
        pre = a.astype(np.float32)
        pre[..., :3] *= pre[..., 3:4] / 255                       # prémultiplié : bords propres
        res = cv2.warpPerspective(pre, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(0, 0, 0, 0))
        al = np.clip(res[..., 3:4], 1e-3, 255)
        res[..., :3] = np.where(res[..., 3:4] > 0, res[..., :3] * 255 / al, 0)
        out = np.clip(np.round(res), 0, 255).astype(np.uint8)
        from .fenetre import CommandeEtat
        self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_nouveau_calque(_qimage(out),
                                                                                   tr("Collé en perspective")),
                                          tr("Coller en perspective")))
        return True

    # ---------------------------------------------------------- visage, maquillage (IA)
    def ia_visage(self, maquillage: bool = False, consigne: str | None = None, nb: int = 2):
        titre = tr("Maquillage (IA)") if maquillage else tr("Retouche du visage (IA)")
        if not self.doc or not self._verifier_verrou(titre):
            return None
        from . import recettes
        if not recettes.restauration_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Flux Kontext (11,9 Go), qui n'est pas installé. Menu IA > Installer "
                "le moteur IA permet de l'ajouter (case « Flux Kontext »)."))
            return None
        if consigne is None:
            d = DialogueVisage(self, maquillage)
            if not d.exec():
                return None
            consigne, nb = d.consigne(), d.nb.value()
            if not consigne:
                return None
        self._modifier_avec(titre, consigne, nb)
        return consigne

    def _modifier_avec(self, titre: str, consigne: str, nb: int):
        """Comme Modifier avec une consigne, sans la fenêtre de consigne."""
        from . import modifier_ia, recettes
        from .document import FORMAT_IMAGE, masque, tableau
        doc = self.doc
        zone = None if doc.selection_vide() else masque(doc.selection).copy()
        prep = modifier_ia.preparer(doc, zone, self.a_ia_nouveau_calque.isChecked())
        visible = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
        self._lancer(titre, False, lambda nom: recettes.restaurer(nom, prep.taille, nb=nb, texte=consigne),
                     png=prep.png, apres=lambda img: modifier_ia.image_complete(prep, img),
                     placer=lambda image: modifier_ia.etat(doc, prep, image, titre),
                     vue=lambda img: modifier_ia.vue(prep, img, visible), nom_calque=titre,
                     suffixe=tr("_modifie"), duree="kontext")

    # ---------------------------------------------------------- instantanés nommés (panneau Historique)
    def _instantanes_ui(self):
        dock = getattr(self, "dock_historique", None)
        if dock is None:
            return
        lay = dock.widget().layout()
        titre = QLabel(tr("Instantanés"))
        titre.setObjectName("discret")
        self.liste_instantanes = QListWidget()
        self.liste_instantanes.setMaximumHeight(110)
        self.liste_instantanes.setToolTip(tr("Double-clic : revenir à cet instantané (Ctrl+Z annule ce retour)"))
        self.liste_instantanes.itemDoubleClicked.connect(lambda it: self.revenir_instantane(
            self.liste_instantanes.row(it)))
        ligne = QHBoxLayout()
        b = QPushButton(tr("Nouvel instantané…"))
        b.setToolTip(tr("Garde l'état actuel de l'image sous un nom, pour y revenir plus tard"))
        b.clicked.connect(lambda: self.nouvel_instantane())
        ligne.addWidget(b)
        b = QPushButton(tr("Supprimer"))
        b.clicked.connect(self.supprimer_instantane)
        ligne.addWidget(b)
        k = max(0, lay.count() - 1)
        lay.insertWidget(k, titre)
        lay.insertWidget(k + 1, self.liste_instantanes)
        lay.insertLayout(k + 2, ligne)
        self._vu_instantanes = None
        t = QTimer(self)
        t.setInterval(400)
        t.timeout.connect(self._maj_instantanes)
        t.start()

    def _maj_instantanes(self):
        doc = self.doc
        liste = getattr(doc, "instantanes", []) if doc is not None else []
        cle = (id(doc), tuple(n for n, _e in liste))
        if cle == self._vu_instantanes:
            return
        self._vu_instantanes = cle
        self.liste_instantanes.clear()
        for nom, _e in liste:
            self.liste_instantanes.addItem(nom)

    def nouvel_instantane(self, nom: str | None = None):
        doc = self.doc
        if doc is None:
            return
        if not hasattr(doc, "instantanes"):
            doc.instantanes = []
        if nom is None:
            nom, ok = QInputDialog.getText(self, tr("Instantané"), tr("Nom de cet instantané :"),
                                           text=tr("Instantané {n}", n=len(doc.instantanes) + 1))
            if not ok:
                return
        doc.instantanes.append((nom.strip() or tr("Instantané {n}", n=len(doc.instantanes) + 1), doc.etat()))
        self._maj_instantanes()

    def revenir_instantane(self, k: int):
        doc = self.doc
        liste = getattr(doc, "instantanes", [])
        if not (0 <= k < len(liste)):
            return
        from .fenetre import CommandeEtat
        nom, etat = liste[k]
        self.historique.push(CommandeEtat(doc, doc.etat(), etat, tr("Revenir à « {nom} »", nom=nom)))

    def supprimer_instantane(self):
        doc = self.doc
        k = self.liste_instantanes.currentRow()
        if doc is not None and 0 <= k < len(getattr(doc, "instantanes", [])):
            doc.instantanes.pop(k)
            self._maj_instantanes()


__all__ = ["CreationMixin", "vectoriser_svg", "panorama", "gif_anime", "photo_identite", "planche", "collage",
           "double_exposition", "consigne_visage", "io", "QPointF", "QWidget"]
