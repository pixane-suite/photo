"""Nuancier (comme le panneau Nuancier de Photoshop) : des couleurs enregistrées (celles d'un artiste, d'un label…),
réutilisables partout. Un clic : couleur de peinture. Importer un nuancier Photoshop (.aco) ou GIMP (.gpl), exporter
en .aco. Les 16 premières couleurs sont aussi dans « Couleurs personnalisées » de chaque fenêtre de choix de couleur.

En haut, un cercle de couleurs (anneau = teinte, carré = saturation et clarté) ; en dessous, des groupes repliables :
harmonies et nuances de la couleur de peinture, couleurs principales de l'image ouverte, et « Mes couleurs ».
Clic droit sur une couleur d'un groupe : l'ajouter à « Mes couleurs ».
"""
from __future__ import annotations

import colorsys
import json
import os
import struct
from pathlib import Path

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QIcon, QImage, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QColorDialog, QFileDialog, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QScrollArea,
                               QSizePolicy, QToolButton, QVBoxLayout, QWidget)

from .langue import tr

DEPART = ["#000000", "#ffffff", "#808080", "#c0c0c0", "#e53935", "#fb8c00", "#fdd835", "#43a047", "#00897b",
          "#1e88e5", "#3949ab", "#8e24aa", "#d81b60", "#6d4c41", "#f5f5dc", "#1a237e", "#b71c1c", "#ffd700"]


def _reglages() -> QSettings:
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))


def charger() -> list[tuple[str, str]]:
    """[(nom, "#rrggbb"), …]"""
    try:
        d = json.loads(_reglages().value("nuancier", "") or "null")
        if isinstance(d, list):
            return [(str(n), QColor(c).name()) for n, c in d if QColor(c).isValid()]
    except (ValueError, TypeError):
        pass
    return [("", c) for c in DEPART]


def enregistrer(couleurs: list[tuple[str, str]]):
    _reglages().setValue("nuancier", json.dumps([[n, c] for n, c in couleurs], ensure_ascii=False))
    partager(couleurs)


def partager(couleurs: list[tuple[str, str]]):
    """Les 16 premières couleurs dans « Couleurs personnalisées » des fenêtres de choix de couleur (QColorDialog)."""
    for i in range(QColorDialog.customCount()):
        QColorDialog.setCustomColor(i, QColor(couleurs[i][1]) if i < len(couleurs) else QColor(255, 255, 255))


# ------------------------------------------------------------------ fichiers
def lire_aco(octets: bytes) -> list[tuple[str, str]]:
    """Nuancier Photoshop .aco (version 1, et version 2 avec les noms) : RVB, TSL (HSB), CMJN, gris."""
    def couleurs_v(pos: int, avec_noms: bool):
        version, n = struct.unpack_from(">HH", octets, pos)
        pos += 4
        res = []
        for _ in range(n):
            espace, w, x, y, z = struct.unpack_from(">HHHHH", octets, pos)
            pos += 10
            nom = ""
            if avec_noms:
                _zero, longueur = struct.unpack_from(">HI", octets, pos)
                pos += 6
                nom = octets[pos:pos + 2 * longueur].decode("utf-16-be", "replace").rstrip("\x00")
                pos += 2 * longueur
            if espace == 0:
                c = QColor.fromRgbF(w / 65535, x / 65535, y / 65535)
            elif espace == 1:
                r, v, b = colorsys.hsv_to_rgb(w / 65535, x / 65535, y / 65535)
                c = QColor.fromRgbF(r, v, b)
            elif espace == 2:                              # CMJN, valeurs inversées (65535 = 0 %)
                c = QColor.fromCmykF(1 - w / 65535, 1 - x / 65535, 1 - y / 65535, 1 - z / 65535).toRgb()
            elif espace == 8:
                g = w / 10000
                c = QColor.fromRgbF(g, g, g)
            else:                                          # Lab et autres : pas pris
                continue
            res.append(("" if nom.lower() == c.name() else nom, c.name()))   # nom = code couleur : pas de nom
        return res, pos, version

    v1, fin, version = couleurs_v(0, False)
    if version == 1 and fin + 4 <= len(octets):
        try:
            v2, _f, version2 = couleurs_v(fin, True)
            if version2 == 2:
                return v2
        except (struct.error, UnicodeDecodeError):
            pass
    if version == 2:
        return couleurs_v(0, True)[0]
    return v1


def ecrire_aco(couleurs: list[tuple[str, str]]) -> bytes:
    """Version 1 puis version 2 (avec les noms), comme Photoshop."""
    def rvb(c):
        q = QColor(c)
        return struct.pack(">HHHHH", 0, q.red() * 257, q.green() * 257, q.blue() * 257, 0)
    o = struct.pack(">HH", 1, len(couleurs)) + b"".join(rvb(c) for _n, c in couleurs)
    o += struct.pack(">HH", 2, len(couleurs))
    for n, c in couleurs:
        nom = (n or QColor(c).name()) + "\x00"
        o += rvb(c) + struct.pack(">HI", 0, len(nom)) + nom.encode("utf-16-be")
    return o


def lire_gpl(texte: str) -> list[tuple[str, str]]:
    """Palette GIMP .gpl : « R G B nom » par ligne."""
    res = []
    for ligne in texte.splitlines():
        p = ligne.split(None, 3)
        if len(p) >= 3 and all(x.isdigit() for x in p[:3]):
            r, v, b = (min(255, int(x)) for x in p[:3])
            res.append((p[3].strip() if len(p) > 3 else "", QColor(r, v, b).name()))
    return res


def lire_fichier(chemin: str) -> list[tuple[str, str]]:
    p = Path(chemin)
    if p.suffix.lower() == ".gpl":
        return lire_gpl(p.read_text(encoding="utf-8", errors="replace"))
    return lire_aco(p.read_bytes())


# ------------------------------------------------------------------ calculs
def harmonies(c: QColor) -> list[tuple[str, list[str]]]:
    """Nuances (du foncé au clair) et harmonies classiques de la couleur c : [(titre, ["#rrggbb", …]), …]."""
    h, s, l, _a = c.getHslF()
    h = 0.0 if h < 0 else h                      # gris : pas de teinte
    s_vive = max(s, 0.55) if s > 0.02 else 0.0

    def hsl(hh, ss, ll):
        return QColor.fromHslF(hh % 1.0, min(1.0, max(0.0, ss)), min(1.0, max(0.0, ll))).name()
    nuances = [hsl(h, s, v) for v in (0.08, 0.18, 0.28, 0.38, 0.5, 0.62, 0.72, 0.82, 0.92)]
    def autour(decalages):
        return [c.name()] + [hsl(h + d / 360, s_vive, l if 0.15 < l < 0.85 else 0.5) for d in decalages]
    return [(tr("Nuances"), nuances),
            (tr("Complémentaire"), autour((180,))),
            (tr("Analogues"), autour((-30, 30, -60, 60))),
            (tr("Triade"), autour((120, 240))),
            (tr("Compl. proches"), autour((150, 210))),
            (tr("Carré"), autour((90, 180, 270)))]


def couleurs_image(rgb: np.ndarray, n: int = 14) -> list[str]:
    """Couleurs principales d'une image (tableau h × w × 3), de la plus présente à la moins présente : k-moyennes
    sur une version réduite ; les couleurs trop proches sont fusionnées."""
    h, w = rgb.shape[:2]
    pas = max(1, int(math.ceil(max(h, w) / 160)))
    x = rgb[::pas, ::pas, :3].reshape(-1, 3).astype(np.float32)
    if len(x) == 0:
        return []
    rng = np.random.default_rng(0)
    centres = [x[rng.integers(len(x))]]
    for _ in range(min(n, len(x)) - 1):          # départ « k-means++ » : centres éloignés les uns des autres
        d = np.min([((x - c) ** 2).sum(1) for c in centres], axis=0)
        if d.sum() <= 0:
            break
        centres.append(x[rng.choice(len(x), p=d / d.sum())])
    centres = np.array(centres)
    for _ in range(12):
        etiq = np.argmin(((x[:, None, :] - centres[None]) ** 2).sum(2), 1)
        for k in range(len(centres)):
            m = etiq == k
            if m.any():
                centres[k] = x[m].mean(0)
    compte = np.bincount(etiq, minlength=len(centres))
    ordre = np.argsort(-compte)
    gardes: list[np.ndarray] = []
    for k in ordre:
        if compte[k] == 0:
            continue
        if all(np.abs(centres[k] - g).sum() > 36 for g in gardes):
            gardes.append(centres[k])
    return [QColor(*(int(round(v)) for v in g)).name() for g in gardes]


# ------------------------------------------------------------------ petits éléments
class Cercle(QWidget):
    """Cercle de couleurs : l'anneau choisit la teinte, le carré au centre la saturation (gauche -> droite) et la
    clarté (haut -> bas)."""
    change = Signal(QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(190, 190)
        self.h, self.s, self.v = 0.0, 1.0, 1.0
        self._prise = None                       # "anneau" ou "carre" pendant un glisser
        self.setCursor(Qt.CrossCursor)

    def couleur(self) -> QColor:
        return QColor.fromHsvF(self.h, self.s, self.v)

    def definir(self, c: QColor):
        h, s, v, _a = QColor(c).getHsvF()
        if h >= 0 and s > 0.001:                 # gris : on garde la teinte d'avant
            self.h = h
        self.s, self.v = s, v
        self.update()

    def _geo(self):
        r = min(self.width(), self.height()) / 2 - 2
        centre = QPointF(self.width() / 2, self.height() / 2)
        epaisseur = 16
        cote = (r - epaisseur - 4) * math.sqrt(2)
        carre = QRectF(centre.x() - cote / 2, centre.y() - cote / 2, cote, cote)
        return centre, r, epaisseur, carre

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        centre, r, ep, carre = self._geo()
        g = QConicalGradient(centre, 0)
        for i in range(13):
            g.setColorAt(i / 12, QColor.fromHsvF((i / 12) % 1.0, 1, 1))
        chemin = QPainterPath()
        chemin.addEllipse(centre, r, r)
        chemin.addEllipse(centre, r - ep, r - ep)
        p.fillPath(chemin, QBrush(g))
        p.fillRect(carre, QColor.fromHsvF(self.h, 1, 1))
        blanc = QLinearGradient(carre.topLeft(), carre.topRight())
        blanc.setColorAt(0, QColor(255, 255, 255))
        blanc.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(carre, blanc)
        noir = QLinearGradient(carre.topLeft(), carre.bottomLeft())
        noir.setColorAt(0, QColor(0, 0, 0, 0))
        noir.setColorAt(1, QColor(0, 0, 0))
        p.fillRect(carre, noir)
        # repères
        a = self.h * 2 * math.pi                  # QConicalGradient : sens inverse des aiguilles, 0 à droite
        m = r - ep / 2
        pa = QPointF(centre.x() + m * math.cos(a), centre.y() - m * math.sin(a))
        for couleur, largeur in ((QColor(0, 0, 0), 3), (QColor(255, 255, 255), 1.5)):
            p.setPen(QPen(couleur, largeur))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(pa, ep / 2 - 1, ep / 2 - 1)
            ps = QPointF(carre.left() + self.s * carre.width(), carre.top() + (1 - self.v) * carre.height())
            p.drawEllipse(ps, 5, 5)
        p.end()

    def _lire(self, pos: QPointF):
        centre, r, ep, carre = self._geo()
        if self._prise == "anneau":
            a = math.atan2(-(pos.y() - centre.y()), pos.x() - centre.x())
            self.h = (a / (2 * math.pi)) % 1.0
        elif self._prise == "carre":
            self.s = min(1.0, max(0.0, (pos.x() - carre.left()) / carre.width()))
            self.v = min(1.0, max(0.0, 1 - (pos.y() - carre.top()) / carre.height()))
        self.update()
        self.change.emit(self.couleur())

    def mousePressEvent(self, e):
        pos = e.position()
        centre, r, ep, carre = self._geo()
        d = math.hypot(pos.x() - centre.x(), pos.y() - centre.y())
        if r - ep - 2 <= d <= r + 2:
            self._prise = "anneau"
        elif carre.adjusted(-4, -4, 4, 4).contains(pos):
            self._prise = "carre"
        else:
            self._prise = None
            return
        self._lire(pos)

    def mouseMoveEvent(self, e):
        if self._prise is not None:
            self._lire(e.position())

    def mouseReleaseEvent(self, _e):
        self._prise = None


class Grille(QWidget):
    """Rangée(s) de petites cases de couleur. Clic : choisie ; clic droit : menu (ajouter à « Mes couleurs »)."""
    clic = Signal(str)
    ajout = Signal(str)
    COTE, ECART = 22, 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.couleurs: list[str] = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)

    def definir(self, couleurs: list[str]):
        self.couleurs = list(couleurs)
        self.updateGeometry()
        self.update()

    def _par_ligne(self) -> int:
        return max(1, (max(self.width(), 200) + self.ECART) // (self.COTE + self.ECART))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        n = max(1, (w + self.ECART) // (self.COTE + self.ECART))
        lignes = max(1, math.ceil(len(self.couleurs) / n))
        return lignes * (self.COTE + self.ECART)

    def sizeHint(self):
        return QSize(200, self.heightForWidth(max(self.width(), 200)))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.setMinimumHeight(self.heightForWidth(self.width()))

    def _case(self, i) -> QRectF:
        n = self._par_ligne()
        return QRectF((i % n) * (self.COTE + self.ECART), (i // n) * (self.COTE + self.ECART), self.COTE, self.COTE)

    def _index(self, pos) -> int:
        for i in range(len(self.couleurs)):
            if self._case(i).contains(pos):
                return i
        return -1

    def paintEvent(self, _e):
        p = QPainter(self)
        for i, c in enumerate(self.couleurs):
            r = self._case(i)
            p.fillRect(r, QColor(c))
            p.setPen(QColor(128, 128, 128, 160))
            p.drawRect(r.adjusted(0, 0, -1, -1))
        p.end()

    def mouseMoveEvent(self, e):
        i = self._index(e.position())
        self.setToolTip(self.couleurs[i] if i >= 0 else "")

    def mousePressEvent(self, e):
        i = self._index(e.position())
        if i < 0:
            return
        if e.button() == Qt.RightButton:
            m = QMenu(self)
            m.addAction(tr("Ajouter à « Mes couleurs »"), lambda c=self.couleurs[i]: self.ajout.emit(c))
            m.exec(e.globalPosition().toPoint())
        else:
            self.clic.emit(self.couleurs[i])


class Groupe(QWidget):
    """Titre cliquable (flèche) qui replie ou déplie son contenu ; état retenu."""

    def __init__(self, titre: str, cle: str, contenu: QWidget, parent=None):
        super().__init__(parent)
        self.cle = cle
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(3)
        self.bouton = QToolButton()
        self.bouton.setText(titre)
        self.bouton.setCheckable(True)
        self.bouton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.bouton.setAutoRaise(True)
        self.bouton.setStyleSheet("QToolButton { font-weight: 600; border: none; }")
        self.contenu = contenu
        lay.addWidget(self.bouton)
        lay.addWidget(contenu)
        ouvert = _reglages().value(f"nuancier_ouvert_{cle}", True, type=bool)
        self.bouton.setChecked(ouvert)
        self._montrer(ouvert)
        self.bouton.toggled.connect(self._montrer)

    def _montrer(self, ouvert: bool):
        self.bouton.setArrowType(Qt.DownArrow if ouvert else Qt.RightArrow)
        self.contenu.setVisible(ouvert)
        _reglages().setValue(f"nuancier_ouvert_{self.cle}", ouvert)


# ------------------------------------------------------------------ panneau
class PanneauNuancier(QWidget):
    choisi = Signal(str)                 # "#rrggbb"

    def __init__(self, couleur_actuelle, parent=None, image_actuelle=None):
        super().__init__(parent)
        self.couleur_actuelle = couleur_actuelle          # fonction : la couleur de peinture (QColor)
        self.image_actuelle = image_actuelle or (lambda: None)   # fonction : l'image ouverte (QImage) ou None
        self.couleurs = charger()
        partager(self.couleurs)
        dehors = QVBoxLayout(self)
        dehors.setContentsMargins(0, 0, 0, 0)
        defile = QScrollArea()
        defile.setWidgetResizable(True)
        defile.setFrameShape(QScrollArea.NoFrame)
        defile.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        dedans = QWidget()
        defile.setWidget(dedans)
        dehors.addWidget(defile)
        lay = QVBoxLayout(dedans)
        lay.setContentsMargins(4, 4, 4, 4)
        # cercle de couleurs
        self.cercle = Cercle()
        self.cercle.definir(QColor(self.couleur_actuelle()))
        self.cercle.change.connect(lambda c: self.choisi.emit(c.name()))
        ligne = QHBoxLayout()
        ligne.addStretch(1)
        ligne.addWidget(self.cercle)
        ligne.addStretch(1)
        lay.addLayout(ligne)
        ligne = QHBoxLayout()
        self.code = QLabel()
        self.code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        ligne.addWidget(self.code, 1)
        self.b_ajouter_cercle = QPushButton(tr("+ Ajouter au nuancier"))
        self.b_ajouter_cercle.setToolTip(tr("Ajoute la couleur du cercle à « Mes couleurs »"))
        self.b_ajouter_cercle.clicked.connect(self.ajouter)
        ligne.addWidget(self.b_ajouter_cercle)
        lay.addLayout(ligne)
        # harmonies et nuances
        boite = QWidget()
        self._grille_harmonies = QGridLayout(boite)
        self._grille_harmonies.setContentsMargins(0, 0, 0, 0)
        self._grille_harmonies.setHorizontalSpacing(6)
        self._grille_harmonies.setVerticalSpacing(4)
        self._grille_harmonies.setColumnStretch(1, 1)
        self.harmonies: dict[str, Grille] = {}
        for k, (titre, _c) in enumerate(harmonies(QColor(0, 0, 0))):
            etiquette = QLabel(titre)
            etiquette.setObjectName("discret")
            g = Grille()
            g.clic.connect(self.choisi.emit)
            g.ajout.connect(self.ajouter_couleur)
            if k == 0:                                     # les 9 nuances : sur toute la largeur
                self._grille_harmonies.addWidget(etiquette, 0, 0, 1, 2)
                self._grille_harmonies.addWidget(g, 1, 0, 1, 2)
            else:                                          # les autres : nom et couleurs sur une ligne
                self._grille_harmonies.addWidget(etiquette, k + 1, 0)
                self._grille_harmonies.addWidget(g, k + 1, 1)
            self.harmonies[titre] = g
        lay.addWidget(Groupe(tr("Harmonies et nuances"), "harmonies", boite))
        # couleurs de l'image
        boite = QWidget()
        b = QVBoxLayout(boite)
        b.setContentsMargins(0, 0, 0, 0)
        self.grille_image = Grille()
        self.grille_image.clic.connect(self.choisi.emit)
        self.grille_image.ajout.connect(self.ajouter_couleur)
        b.addWidget(self.grille_image)
        ligne = QHBoxLayout()
        self.etat_image = QLabel(tr("Ouvre une image : ses couleurs principales apparaissent ici."))
        self.etat_image.setObjectName("discret")
        self.etat_image.setWordWrap(True)
        ligne.addWidget(self.etat_image, 1)
        ligne.addStretch(0)
        self.b_tout_image = QToolButton()
        self.b_tout_image.setText(tr("Tout ajouter"))
        self.b_tout_image.setToolTip(tr("Ajoute toutes les couleurs de l'image à « Mes couleurs »"))
        self.b_tout_image.clicked.connect(self.ajouter_couleurs_image)
        ligne.addWidget(self.b_tout_image)
        b.addLayout(ligne)
        lay.addWidget(Groupe(tr("Couleurs de l'image"), "image", boite))
        self._minuterie_image = QTimer(self)
        self._minuterie_image.setSingleShot(True)
        self._minuterie_image.setInterval(700)
        self._minuterie_image.timeout.connect(self.calculer_image)
        self._image_a_refaire = True
        # mes couleurs
        boite = QWidget()
        mes = QVBoxLayout(boite)
        mes.setContentsMargins(0, 0, 0, 0)
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.IconMode)
        self.liste.setIconSize(QSize(24, 24))
        self.liste.setGridSize(QSize(30, 30))
        self.liste.setMovement(QListWidget.Static)
        self.liste.setResizeMode(QListWidget.Adjust)
        self.liste.setSpacing(0)
        self.liste.setSelectionMode(QListWidget.SingleSelection)
        self.liste.itemClicked.connect(lambda it: self.choisi.emit(it.data(Qt.UserRole)))
        self.liste.setContextMenuPolicy(Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu_couleur)
        self.liste.setMinimumHeight(120)
        mes.addWidget(self.liste, 1)
        bas = QHBoxLayout()
        self.b_ajouter = QToolButton()
        self.b_ajouter.setText("+")
        self.b_ajouter.setToolTip(tr("Ajouter la couleur de peinture au nuancier"))
        self.b_ajouter.clicked.connect(self.ajouter)
        self.b_retirer = QToolButton()
        self.b_retirer.setText("−")
        self.b_retirer.setToolTip(tr("Retirer la couleur choisie du nuancier"))
        self.b_retirer.clicked.connect(self.retirer)
        self.b_plus = QToolButton()
        self.b_plus.setText("…")
        self.b_plus.setToolTip(tr("Importer, exporter, remettre les couleurs de départ"))
        self.b_plus.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(self.b_plus)
        m.addAction(tr("Importer un nuancier (Photoshop .aco, GIMP .gpl)…"), self.importer)
        m.addAction(tr("Exporter le nuancier (.aco, pour Photoshop)…"), self.exporter)
        m.addSeparator()
        m.addAction(tr("Remettre les couleurs de départ"), self.remettre)
        self.b_plus.setMenu(m)
        for b in (self.b_ajouter, self.b_retirer, self.b_plus):
            bas.addWidget(b)
        bas.addStretch(1)
        mes.addLayout(bas)
        lay.addWidget(Groupe(tr("Mes couleurs"), "mes", boite), 1)
        self._remplir()
        self.couleur_changee(QColor(self.couleur_actuelle()))

    # ---------------------------------------------------------------- couleur de peinture, image
    def couleur_changee(self, c: QColor):
        """La couleur de peinture a changé (ici ou ailleurs) : cercle, code et harmonies suivent."""
        c = QColor(c)
        if self.cercle.couleur().name() != c.name():
            self.cercle.blockSignals(True)
            self.cercle.definir(c)
            self.cercle.blockSignals(False)
        self.code.setText(c.name().upper())
        for titre, couleurs in harmonies(c):
            if titre in self.harmonies:
                self.harmonies[titre].definir(couleurs)

    def image_changee(self):
        """L'image ouverte a changé : ses couleurs sont recalculées un peu plus tard (pas à chaque coup de pinceau),
        et seulement si le panneau se voit."""
        self._image_a_refaire = True
        if self.isVisible():
            self._minuterie_image.start()

    def showEvent(self, e):
        super().showEvent(e)
        if self._image_a_refaire:
            self._minuterie_image.start(50)

    def calculer_image(self):
        img = self.image_actuelle()
        self._image_a_refaire = False
        if img is None or img.isNull():
            self.grille_image.definir([])
            self.etat_image.setText(tr("Ouvre une image : ses couleurs principales apparaissent ici."))
            self.etat_image.setVisible(True)
            return
        petite = img.scaled(200, 200, Qt.KeepAspectRatio, Qt.FastTransformation).convertToFormat(
            QImage.Format_RGBA8888)
        a = np.frombuffer(petite.constBits(), np.uint8).reshape(petite.height(), petite.bytesPerLine() // 4, 4)
        a = a[:, :petite.width()]
        opaque = a[..., 3] > 128
        rgb = a[..., :3][opaque] if opaque.any() else a[..., :3].reshape(-1, 3)
        self.grille_image.definir(couleurs_image(rgb.reshape(-1, 1, 3)))
        self.etat_image.setVisible(False)

    def ajouter_couleur(self, c: str):
        if all(QColor(x).name() != QColor(c).name() for _n, x in self.couleurs):
            self._changer(self.couleurs + [("", QColor(c).name())])
        self.liste.setCurrentRow(len(self.couleurs) - 1)

    def ajouter_couleurs_image(self):
        nouvelles = [("", c) for c in self.grille_image.couleurs
                     if all(QColor(x).name() != c for _n, x in self.couleurs)]
        if nouvelles:
            self._changer(self.couleurs + nouvelles)

    def _remplir(self):
        self.liste.clear()
        for nom, c in self.couleurs:
            pm = QPixmap(24, 24)
            pm.fill(QColor(c))
            p = QPainter(pm)                     # contour gris : le blanc se voit sur un fond blanc
            p.setPen(QColor(128, 128, 128, 160))
            p.drawRect(0, 0, 23, 23)
            p.end()
            it = QListWidgetItem(QIcon(pm), "")
            it.setData(Qt.UserRole, c)
            it.setToolTip(f"{nom} ({c})" if nom else c)
            self.liste.addItem(it)

    def _changer(self, couleurs):
        self.couleurs = couleurs
        enregistrer(couleurs)
        self._remplir()

    def ajouter(self):
        c = QColor(self.couleur_actuelle()).name()
        self._changer(self.couleurs + [("", c)])
        self.liste.setCurrentRow(len(self.couleurs) - 1)

    def retirer(self):
        i = self.liste.currentRow()
        if 0 <= i < len(self.couleurs):
            self._changer(self.couleurs[:i] + self.couleurs[i + 1:])

    def renommer(self, i: int):
        nom, ok = QInputDialog.getText(self, tr("Nuancier"), tr("Nom de la couleur :"), text=self.couleurs[i][0])
        if ok:
            liste = list(self.couleurs)
            liste[i] = (nom.strip(), liste[i][1])
            self._changer(liste)

    def _menu_couleur(self, pos):
        it = self.liste.itemAt(pos)
        if it is None:
            return
        i = self.liste.row(it)
        self.liste.setCurrentRow(i)
        m = QMenu(self)
        m.addAction(tr("Renommer…"), lambda: self.renommer(i))
        m.addAction(tr("Retirer du nuancier"), self.retirer)
        m.exec(self.liste.mapToGlobal(pos))

    def importer(self, chemin: str | None = None):
        if not chemin:
            chemin, _f = QFileDialog.getOpenFileName(self, tr("Importer un nuancier"), "",
                                                     tr("Nuanciers") + " (*.aco *.gpl)")
        if not chemin:
            return
        try:
            nouvelles = lire_fichier(chemin)
        except (OSError, struct.error, ValueError) as e:
            QMessageBox.warning(self, tr("Nuancier"), tr("Fichier illisible : {erreur}", erreur=e))
            return
        if not nouvelles:
            QMessageBox.information(self, tr("Nuancier"), tr("Aucune couleur trouvée dans ce fichier."))
            return
        self._changer(self.couleurs + nouvelles)

    def exporter(self, chemin: str | None = None):
        if not chemin:
            chemin, _f = QFileDialog.getSaveFileName(self, tr("Exporter le nuancier"), "nuancier.aco",
                                                     tr("Nuancier Photoshop") + " (*.aco)")
        if chemin:
            Path(chemin).write_bytes(ecrire_aco(self.couleurs))

    def remettre(self):
        self._changer([("", c) for c in DEPART])
