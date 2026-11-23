"""Image > Réglages > Couleurs d'une autre image : donner à la photo l'ambiance de couleurs d'une image de référence
(une autre photo ouverte, ou un fichier). Méthode de Reinhard : dans l'espace Lab, la moyenne et l'écart de chaque
canal de la photo prennent ceux de la référence. Réglages : force, part de la lumière transférée, neutraliser
(garder un peu des couleurs d'origine).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .langue import tr


def _lab(rgb: np.ndarray) -> np.ndarray:
    import cv2
    return cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.float32) / 255, cv2.COLOR_RGB2Lab)


def statistiques(rgba: np.ndarray) -> list[list[float]]:
    """Moyenne et écart de L, a, b (pixels assez opaques seulement), sur une version réduite."""
    pas = max(1, int(max(rgba.shape[:2]) / 400))
    petit = rgba[::pas, ::pas]
    opaque = petit[..., 3] > 128 if petit.shape[-1] == 4 else np.ones(petit.shape[:2], bool)
    rgb = petit[..., :3][opaque] if opaque.any() else petit[..., :3].reshape(-1, 3)
    lab = _lab(rgb.reshape(-1, 1, 3)).reshape(-1, 3)
    return [lab.mean(0).tolist(), np.maximum(lab.std(0), 1e-3).tolist()]


def transferer(t: np.ndarray, p: dict) -> np.ndarray:
    """p : ref = statistiques de la référence, force (0..100), lumiere (0..100 : part de la lumière transférée)."""
    import cv2
    ref = p.get("ref")
    if not ref:
        return t
    rgb = t[..., :3].astype(np.float32)
    lab = _lab(rgb)
    moy, ecart = statistiques(t)
    rm, re = np.array(ref[0], np.float32), np.array(ref[1], np.float32)
    m, e = np.array(moy, np.float32), np.array(ecart, np.float32)
    nouveau = (lab - m) * (re / e) + rm
    poids = np.array([p.get("lumiere", 50) / 100, 1, 1], np.float32) * (p.get("force", 100) / 100)
    lab2 = lab + (nouveau - lab) * poids
    lab2[..., 0] = np.clip(lab2[..., 0], 0, 100)
    res = cv2.cvtColor(lab2, cv2.COLOR_Lab2RGB) * 255
    out = np.empty(t.shape, np.float32)
    out[..., :3] = res
    out[..., 3] = t[..., 3]
    if t.dtype.kind == "f":
        return np.clip(out, 0, 255).astype(np.float32)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def panneau(documents, actuel, parent_fenetre):
    """Panneau du réglage : choix de la référence (photo ouverte ou fichier), aperçu, force, lumière."""
    from .dialogues_reglage import Curseur, _Panneau
    from .document import Document, tableau

    class PanneauReference(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            self.images = {}                              # clé -> QImage de référence
            lay = QVBoxLayout(self)
            ligne = QHBoxLayout()
            ligne.addWidget(QLabel(tr("Référence :")))
            self.liste = QComboBox()
            for d in documents:
                if d is actuel:
                    continue
                cle = f"doc:{id(d)}"
                self.images[cle] = d.image
                nom = Path(d.chemin).name if getattr(d, "chemin", None) else tr("Image sans nom")
                self.liste.addItem(nom, cle)
            self.liste.activated.connect(lambda _i: self._choisie())
            ligne.addWidget(self.liste, 1)
            b = QPushButton(tr("Fichier…"))
            b.setToolTip(tr("Choisir une image sur le disque"))
            b.clicked.connect(self._fichier)
            ligne.addWidget(b)
            lay.addLayout(ligne)
            self.vignette = QLabel()
            self.vignette.setAlignment(Qt.AlignCenter)
            self.vignette.setMinimumHeight(110)
            lay.addWidget(self.vignette)
            self.force = Curseur(tr("Force"), 0, 100, self.p.get("force", 100), " %")
            self.lumiere = Curseur(tr("Lumière de la référence"), 0, 100, self.p.get("lumiere", 50), " %")
            for c in (self.force, self.lumiere):
                c.change.connect(self._lire)
                lay.addWidget(c)
            aide = QLabel(tr("Choisis une photo dont tu aimes les couleurs : la tienne prend son ambiance."))
            aide.setWordWrap(True)
            aide.setObjectName("discret")
            lay.addWidget(aide)
            if self.liste.count():
                self._choisie(emettre=False)
            else:
                self.vignette.setText(tr("Aucune autre image ouverte : clique sur « Fichier… »."))

        def _lire(self):
            self.p["force"] = int(self.force.valeur())
            self.p["lumiere"] = int(self.lumiere.valeur())
            self.change.emit()

        def _choisie(self, emettre=True):
            img = self.images.get(self.liste.currentData())
            if img is None:
                return
            self.vignette.setPixmap(QPixmap.fromImage(img.scaled(260, 110, Qt.KeepAspectRatio,
                                                                 Qt.SmoothTransformation)))
            self.p["ref"] = statistiques(tableau(img.convertToFormat(QImage.Format_RGBA8888)))
            if emettre:
                self.change.emit()

        def _fichier(self, chemin: str | None = None):
            if not chemin:
                from .document import EXTENSIONS_LECTURE
                chemin, _f = QFileDialog.getOpenFileName(parent_fenetre, tr("Image de référence"), "",
                                                         tr("Images") + f" ({EXTENSIONS_LECTURE})")
            if not chemin:
                return
            try:
                img = QImage(Document.ouvrir(chemin).image)
            except Exception:                              # noqa: BLE001 — fichier illisible : on ne change rien
                return
            cle = f"fichier:{chemin}"
            self.images[cle] = img
            self.liste.addItem(Path(chemin).name, cle)
            self.liste.setCurrentIndex(self.liste.count() - 1)
            self._choisie()

    return PanneauReference
