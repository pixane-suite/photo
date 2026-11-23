"""Filigrane / signature : un texte (« © chrypox ») ou un logo (PNG transparent) posé sur les images exportées.
Réglé une fois dans Fichier > Filigrane… (aperçu sur l'image ouverte) ; ajouté à l'export (Exporter sous, Exporter
pour le web, Traitement par lot) si la case est cochée. Le document lui-même n'est jamais touché.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QSlider,
                               QToolButton, QVBoxLayout)

from .langue import tr

POSITIONS = ["haut_gauche", "haut", "haut_droite", "gauche", "centre", "droite", "bas_gauche", "bas", "bas_droite"]
DEFAUT = {"genre": "texte", "texte": "©", "police": "Segoe UI", "gras": True, "couleur": "#ffffff", "image": "",
          "position": "bas_droite", "mosaique": False, "taille": 18, "opacite": 60, "marge": 3, "angle": 0,
          "ombre": True, "actif": False}


def charger(reglages) -> dict:
    try:
        d = json.loads(reglages.value("filigrane", "") or "{}")
    except (ValueError, TypeError):
        d = {}
    r = dict(DEFAUT)
    r.update({k: v for k, v in d.items() if k in DEFAUT})
    return r


def enregistrer(reglages, f: dict):
    reglages.setValue("filigrane", json.dumps(f, ensure_ascii=False))


def _motif(f: dict, largeur: int) -> QImage | None:
    """Le filigrane seul (texte ou logo), à sa taille dans une image de cette largeur ; None s'il n'y a rien."""
    cible = max(8.0, largeur * f["taille"] / 100)                # largeur du filigrane
    if f["genre"] == "image":
        logo = QImage(f["image"]) if f["image"] and Path(f["image"]).is_file() else QImage()
        if logo.isNull():
            return None
        return logo.scaledToWidth(max(1, int(cible)), Qt.SmoothTransformation).convertToFormat(
            QImage.Format_ARGB32_Premultiplied)
    texte = (f["texte"] or "").strip()
    if not texte:
        return None
    police = QFont(f["police"] or "Segoe UI")
    police.setBold(bool(f["gras"]))
    police.setPixelSize(100)
    largeur_100 = max(1.0, QFontMetricsF(police).horizontalAdvance(texte))
    police.setPixelSize(max(4, int(100 * cible / largeur_100)))
    m = QFontMetricsF(police)
    w, h = int(m.horizontalAdvance(texte) + m.height() * 0.4) + 4, int(m.height() * 1.2) + 4
    img = QImage(w, h, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    chemin = QPainterPath()
    chemin.addText(QPointF(m.height() * 0.2 + 2, m.ascent() + m.height() * 0.1 + 2), police, texte)
    if f["ombre"]:                                    # ombre douce : le texte se lit sur le clair comme sur le foncé
        ombre = QColor(0, 0, 0, 110) if QColor(f["couleur"]).lightness() > 110 else QColor(255, 255, 255, 110)
        p.setPen(QPen(ombre, max(1.5, m.height() * 0.06), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(ombre)
        p.drawPath(chemin.translated(max(1, m.height() * 0.03), max(1, m.height() * 0.03)))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(f["couleur"]))
    p.drawPath(chemin)
    p.end()
    return img


def appliquer_qimage(img: QImage, f: dict) -> QImage:
    """Copie de img avec le filigrane."""
    res = img.convertToFormat(QImage.Format_ARGB32_Premultiplied).copy()
    W, H = res.width(), res.height()
    motif = _motif(f, W)
    if motif is None:
        return res
    if f["angle"]:
        motif = motif.transformed(QTransform().rotate(-f["angle"]), Qt.SmoothTransformation)
    p = QPainter(res)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    p.setOpacity(max(0.0, min(1.0, f["opacite"] / 100)))
    mw, mh = motif.width(), motif.height()
    if f["mosaique"]:                                  # répété sur toute l'image, en quinconce
        pas_x, pas_y = mw * 1.8, mh * 3
        y, rang = -mh / 2, 0
        while y < H:
            x = -mw / 2 + (pas_x / 2 if rang % 2 else 0)
            while x < W:
                p.drawImage(QPointF(x, y), motif)
                x += pas_x
            y += pas_y
            rang += 1
    else:
        marge = min(W, H) * f["marge"] / 100
        i = POSITIONS.index(f["position"]) if f["position"] in POSITIONS else 8
        col, lig = i % 3, i // 3
        x = (marge, (W - mw) / 2, W - mw - marge)[col]
        y = (marge, (H - mh) / 2, H - mh - marge)[lig]
        p.drawImage(QPointF(x, y), motif)
    p.end()
    return res


def appliquer(im: Image.Image, f: dict) -> Image.Image:
    """Image Pillow (RGB ou RGBA) -> même image avec le filigrane (même mode)."""
    from .document import pil_vers_qimage, qimage_vers_pil
    mode = im.mode
    res = qimage_vers_pil(appliquer_qimage(pil_vers_qimage(im.convert("RGBA")), f))
    return res.convert(mode) if mode != res.mode else res


class DialogueFiligrane(QDialog):
    """Fichier > Filigrane… : texte ou logo, place (9 positions ou mosaïque), taille, opacité, angle ; aperçu sur
    l'image ouverte."""

    def __init__(self, fenetre, image: QImage | None):
        super().__init__(fenetre)
        self.setWindowTitle(tr("Filigrane"))
        self.reglages = fenetre.reglages
        self.f = charger(self.reglages)
        self.image = (image if image is not None and not image.isNull() else self._exemple()).scaled(
            460, 340, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lay = QHBoxLayout(self)
        gauche = QVBoxLayout()
        form = QFormLayout()
        genre = QHBoxLayout()
        self.r_texte, self.r_image = QRadioButton(tr("Texte")), QRadioButton(tr("Logo (image)"))
        groupe = QButtonGroup(self)
        for r in (self.r_texte, self.r_image):
            groupe.addButton(r)
            genre.addWidget(r)
        genre.addStretch(1)
        (self.r_image if self.f["genre"] == "image" else self.r_texte).setChecked(True)
        form.addRow(tr("Filigrane"), genre)
        self.texte = QLineEdit(self.f["texte"])
        self.texte.setPlaceholderText(tr("© ton nom"))
        form.addRow(tr("Texte"), self.texte)
        ligne = QHBoxLayout()
        self.police = QComboBox()
        self.police.setEditable(True)
        from PySide6.QtGui import QFontDatabase
        self.police.addItems(sorted(QFontDatabase.families()))
        self.police.setCurrentText(self.f["police"])
        ligne.addWidget(self.police, 1)
        self.gras = QCheckBox(tr("Gras"))
        self.gras.setChecked(bool(self.f["gras"]))
        ligne.addWidget(self.gras)
        self.b_couleur = QToolButton()
        self.b_couleur.setFixedWidth(40)
        self.b_couleur.clicked.connect(self._couleur)
        ligne.addWidget(self.b_couleur)
        form.addRow(tr("Police"), ligne)
        ligne = QHBoxLayout()
        self.chemin = QLineEdit(self.f["image"])
        self.chemin.setPlaceholderText(tr("PNG transparent conseillé"))
        b = QPushButton(tr("Parcourir…"))
        b.clicked.connect(self._parcourir)
        ligne.addWidget(self.chemin, 1)
        ligne.addWidget(b)
        form.addRow(tr("Logo"), ligne)
        # place : 9 boutons + mosaïque
        grille = QGridLayout()
        grille.setSpacing(2)
        self.places = QButtonGroup(self)
        for i, nom in enumerate(POSITIONS):
            b = QToolButton()
            b.setCheckable(True)
            b.setFixedSize(26, 22)
            b.setAutoRaise(False)
            b.setStyleSheet("QToolButton { border: 1px solid #9a9a9a; border-radius: 3px; }"
                            "QToolButton:checked { border: 2px solid palette(highlight); }")
            b.setText("●" if nom == self.f["position"] else "")
            b.setChecked(nom == self.f["position"])
            b.setToolTip(nom.replace("_", " "))
            self.places.addButton(b, i)
            grille.addWidget(b, i // 3, i % 3)
        self.places.idClicked.connect(self._place)
        ligne = QHBoxLayout()
        ligne.addLayout(grille)
        ligne.addSpacing(12)
        self.mosaique = QCheckBox(tr("Répété sur toute l'image"))
        self.mosaique.setChecked(bool(self.f["mosaique"]))
        ligne.addWidget(self.mosaique)
        ligne.addStretch(1)
        form.addRow(tr("Place"), ligne)
        self.curseurs = {}
        for cle, nom, mini, maxi, unite in (("taille", tr("Taille (largeur)"), 2, 90, " %"),
                                            ("opacite", tr("Opacité"), 5, 100, " %"),
                                            ("marge", tr("Marge"), 0, 20, " %"), ("angle", tr("Angle"), -90, 90, "°")):
            s = QSlider(Qt.Horizontal)
            s.setRange(mini, maxi)
            s.setValue(int(self.f[cle]))
            v = QLabel(f"{s.value()}{unite}")
            v.setMinimumWidth(44)
            s.valueChanged.connect(lambda x, v=v, u=unite: (v.setText(f"{x}{u}"), self._maj()))
            ligne = QHBoxLayout()
            ligne.addWidget(s, 1)
            ligne.addWidget(v)
            form.addRow(nom, ligne)
            self.curseurs[cle] = s
        self.ombre = QCheckBox(tr("Ombre douce (lisible sur le clair comme sur le foncé)"))
        self.ombre.setChecked(bool(self.f["ombre"]))
        form.addRow("", self.ombre)
        gauche.addLayout(form)
        self.actif = QCheckBox(tr("Ajouter le filigrane à chaque export (Exporter sous, pour le web, par lot)"))
        self.actif.setChecked(bool(self.f["actif"]))
        gauche.addWidget(self.actif)
        note = QLabel(tr("La photo elle-même ne change jamais : le filigrane n'est posé que sur le fichier exporté."))
        note.setObjectName("discret")
        note.setWordWrap(True)
        gauche.addWidget(note)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        ok = QPushButton(tr("OK"))
        ok.setDefault(True)
        ok.clicked.connect(self._ok)
        annuler = QPushButton(tr("Annuler"))
        annuler.clicked.connect(self.reject)
        boutons.addWidget(ok)
        boutons.addWidget(annuler)
        gauche.addLayout(boutons)
        lay.addLayout(gauche, 1)
        self.apercu = QLabel()
        self.apercu.setMinimumSize(470, 350)
        self.apercu.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.apercu)
        for sig in (self.r_texte.toggled, self.texte.textChanged, self.police.currentTextChanged, self.gras.toggled,
                    self.chemin.textChanged, self.mosaique.toggled, self.ombre.toggled):
            sig.connect(self._maj)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.setInterval(60)
        self._minuterie.timeout.connect(self._dessiner)
        self._maj()

    @staticmethod
    def _exemple() -> QImage:
        img = QImage(600, 400, QImage.Format_ARGB32_Premultiplied)
        p = QPainter(img)
        from PySide6.QtGui import QLinearGradient
        g = QLinearGradient(0, 0, 600, 400)
        g.setColorAt(0, QColor(60, 90, 140))
        g.setColorAt(1, QColor(230, 170, 110))
        p.fillRect(img.rect(), g)
        p.end()
        return img

    def _place(self, i: int):
        for b in self.places.buttons():
            b.setText("●" if self.places.id(b) == i else "")
        self.f["position"] = POSITIONS[i]
        self.mosaique.setChecked(False)
        self._maj()

    def _couleur(self):
        c = QColorDialog.getColor(QColor(self.f["couleur"]), self, tr("Couleur du filigrane"))
        if c.isValid():
            self.f["couleur"] = c.name()
            self._maj()

    def _parcourir(self):
        chemin, _f = QFileDialog.getOpenFileName(self, tr("Logo du filigrane"), self.chemin.text(),
                                                 tr("Images") + " (*.png *.webp *.jpg *.jpeg *.svg)")
        if chemin:
            self.chemin.setText(chemin)
            self.r_image.setChecked(True)

    def valeurs(self) -> dict:
        f = dict(self.f)
        f.update(genre="image" if self.r_image.isChecked() else "texte", texte=self.texte.text(),
                 police=self.police.currentText(), gras=self.gras.isChecked(), image=self.chemin.text().strip(),
                 mosaique=self.mosaique.isChecked(), ombre=self.ombre.isChecked(), actif=self.actif.isChecked(),
                 **{k: s.value() for k, s in self.curseurs.items()})
        return f

    def _maj(self, *_):
        self.b_couleur.setStyleSheet(f"background: {self.f['couleur']}; border: 1px solid #888;")
        texte = self.r_texte.isChecked()
        for w in (self.texte, self.police, self.gras, self.b_couleur):
            w.setEnabled(texte)
        self.chemin.setEnabled(not texte)
        self._minuterie.start()

    def _dessiner(self):
        self.apercu.setPixmap(QPixmap.fromImage(appliquer_qimage(self.image, self.valeurs())))

    def _ok(self):
        enregistrer(self.reglages, self.valeurs())
        self.accept()
