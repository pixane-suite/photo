"""Retouche en plus : restaurer les visages flous (GFPGAN), fluidité des visages, nouveau fond (IA), changer les
vêtements (IA), recadrage conseillé, nettoyer un document photographié, déformation de la marionnette.
Fenetre hérite de RetouchePlusMixin ; _retouche_plus() est appelé par _creation()."""
from __future__ import annotations

import threading

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
                               QRadioButton, QSpinBox, QVBoxLayout, QWidget)

from .langue import tr

# ====================================================================== visages : repères
GABARIT = np.float32([[192.98, 239.95], [318.90, 240.19], [257.17, 371.28]])   # yeux, bouche (FFHQ 512)
COTE = 512


def _composantes(m: np.ndarray, seuil: int = 127):
    """[(aire, cx, cy, x, y, w, h)] des taches blanches d'un masque."""
    import cv2
    n, _lab, stats, cent = cv2.connectedComponentsWithStats((m > seuil).astype(np.uint8), 8)
    return [(int(stats[i, 4]), float(cent[i, 0]), float(cent[i, 1]), *map(int, stats[i, :4])) for i in range(1, n)]


def reperes_visages(visages: list[np.ndarray], yeux: np.ndarray | None, levres: np.ndarray | None,
                    nez: np.ndarray | None) -> list[dict]:
    """Pour chaque masque de visage : cadre, yeux (gauche puis droit, (cx, cy, r)), bouche (cx, cy, l, h), nez."""
    res = []
    for m in visages:
        tache = _composantes(m)
        if not tache:
            continue
        ys, xs = np.nonzero(m > 127)
        if len(xs) < 50:
            continue
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        w, h = x1 - x0 + 1, y1 - y0 + 1
        v = {"cadre": (x0, y0, w, h), "masque": m, "yeux": [], "bouche": None, "nez": None}

        def dedans(cx, cy, marge=0.1):
            return x0 - w * marge <= cx <= x1 + w * marge and y0 - h * marge <= cy <= y1 + h * marge
        if yeux is not None:
            ok = sorted([c for c in _composantes(yeux) if dedans(c[1], c[2]) and c[2] < y0 + h * 0.65],
                        key=lambda c: -c[0])[:2]
            v["yeux"] = [(c[1], c[2], max(c[5], c[6]) / 2) for c in sorted(ok, key=lambda c: c[1])]
        if levres is not None:
            ok = sorted([c for c in _composantes(levres) if dedans(c[1], c[2]) and c[2] > y0 + h * 0.5],
                        key=lambda c: -c[0])
            if ok:
                c = ok[0]
                v["bouche"] = (c[1], c[2], c[5], c[6])
        if nez is not None:
            ok = sorted([c for c in _composantes(nez) if dedans(c[1], c[2], 0)], key=lambda c: -c[0])
            if ok:
                c = ok[0]
                v["nez"] = (c[1], c[2], max(c[5], c[6]) / 2)
        res.append(v)
    return res


def matrice_alignement(v: dict) -> np.ndarray:
    """Matrice 2 × 3 (image -> carré 512 du visage redressé, comme les photos d'apprentissage de GFPGAN)."""
    import cv2
    if len(v["yeux"]) == 2:
        src = [v["yeux"][0][:2], v["yeux"][1][:2]]
        dst = [GABARIT[0], GABARIT[1]]
        if v["bouche"] is not None:
            src.append(v["bouche"][:2])
            dst.append(GABARIT[2])
        M, _i = cv2.estimateAffinePartial2D(np.float32(src), np.float32(dst), method=cv2.LMEDS)
        if M is not None:
            return M.astype(np.float32)
    x, y, w, h = v["cadre"]                       # sans les yeux : d'après le cadre du visage (front-menton)
    k = 300 / max(h, 1)
    cx, cy = x + w / 2, y + h / 2
    return np.float32([[k, 0, 256 - cx * k], [0, k, 285 - cy * k]])


def visage_redresse(rgb: np.ndarray, M: np.ndarray) -> np.ndarray:
    import cv2
    return cv2.warpAffine(rgb, M, (COTE, COTE), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)


def recoller_visages(rgb: np.ndarray, visages: list[dict], matrices, restaures) -> tuple[np.ndarray, np.ndarray]:
    """Image (h, w, 3) float avec les visages restaurés remis en place, et leur poids 0..1 (bords fondus)."""
    import cv2
    h, w = rgb.shape[:2]
    out = rgb.astype(np.float32).copy()
    poids_total = np.zeros((h, w), np.float32)
    carre = np.zeros((COTE, COTE), np.float32)
    b = COTE // 10
    carre[b:-b, b:-b] = 1
    carre = cv2.GaussianBlur(carre, (0, 0), b / 2)
    for v, M, r in zip(visages, matrices, restaures):
        dos = cv2.warpAffine(r.astype(np.float32), M, (w, h), flags=cv2.INTER_CUBIC | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REPLICATE)
        pc = cv2.warpAffine(carre, M, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
        fw = v["cadre"][2]
        noyau = max(3, int(fw * 0.12) | 1)
        zone = cv2.dilate((v["masque"] > 127).astype(np.uint8), np.ones((noyau, noyau), np.uint8)).astype(np.float32)
        zone = cv2.GaussianBlur(zone, (0, 0), max(1.0, fw * 0.05))
        p = np.minimum(pc, zone)
        out = out * (1 - p[..., None]) + dos * p[..., None]
        poids_total = np.maximum(poids_total, p)
    return out, poids_total


# ====================================================================== fluidité des visages
FLUIDITE = (("yeux", "Yeux plus grands"), ("visage", "Visage plus fin"), ("nez", "Nez plus fin"),
            ("sourire", "Sourire"), ("bouche", "Bouche plus large"))
FLUIDITE_NEUTRES = {k: 0 for k, _l in FLUIDITE}


def deformer_visages(a: np.ndarray, visages: list[dict], p: dict) -> np.ndarray:
    """Déforme (h, w, 4) d'après les curseurs (-100..100) : chaque réglage est un champ de déplacement doux autour
    du repère, appliqué en une seule fois (cv2.remap)."""
    import cv2
    h, w = a.shape[:2]
    if not any(p.get(k, 0) for k in FLUIDITE_NEUTRES) or not visages:
        return a
    x0 = max(0, min(int(v["cadre"][0] - v["cadre"][2] * 0.5) for v in visages))
    y0 = max(0, min(int(v["cadre"][1] - v["cadre"][3] * 0.5) for v in visages))
    x1 = min(w, max(int(v["cadre"][0] + v["cadre"][2] * 1.5) for v in visages))
    y1 = min(h, max(int(v["cadre"][1] + v["cadre"][3] * 1.5) for v in visages))
    gx, gy = np.meshgrid(np.arange(x0, x1, dtype=np.float32), np.arange(y0, y1, dtype=np.float32))
    sx, sy = gx.copy(), gy.copy()

    def gonfler(cx, cy, r, s):
        """s > 0 : agrandit ce qui est dans le rond (la source se rapproche du centre)."""
        dx, dy = gx - cx, gy - cy
        d2 = (dx * dx + dy * dy) / (r * r)
        f = np.where(d2 < 1, s * (1 - d2) ** 2, 0).astype(np.float32)
        return -dx * f, -dy * f

    def serrer(cx, cy, rx, ry, s):
        """s > 0 : resserre horizontalement autour de cx (la source s'écarte)."""
        g = np.exp(-(((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2)).astype(np.float32)
        return (gx - cx) * s * g, np.zeros_like(gx)

    for v in visages:
        fx, fy, fw, fh = v["cadre"]
        cx, cy = fx + fw / 2, fy + fh / 2
        dx = np.zeros_like(gx)
        dy = np.zeros_like(gy)
        if p.get("yeux") and v["yeux"]:
            for ex, ey, er in v["yeux"]:
                ddx, ddy = gonfler(ex, ey, max(er * 2.6, fw * 0.12), 0.35 * p["yeux"] / 100)
                dx += ddx
                dy += ddy
        if p.get("visage"):
            s = 0.18 * p["visage"] / 100
            g = np.exp(-(((gy - (cy + fh * 0.15)) / (fh * 0.55)) ** 2)).astype(np.float32)
            bord = np.exp(-(((np.abs(gx - cx) - fw * 0.5) / (fw * 0.3)) ** 2)).astype(np.float32)
            dx += (gx - cx) * s * g * bord
        if p.get("nez") and v["nez"]:
            nx, ny, nr = v["nez"]
            ddx, _z = serrer(nx, ny, max(nr * 1.6, fw * 0.08), max(nr * 1.8, fh * 0.1), 0.35 * p["nez"] / 100)
            dx += ddx
        if v["bouche"] is not None and (p.get("sourire") or p.get("bouche")):
            mx, my, mw, mh = v["bouche"]
            r = max(mw * 0.45, 4)
            for coin in (-1, 1):
                cxc = mx + coin * mw / 2
                g = np.exp(-(((gx - cxc) ** 2 + (gy - my) ** 2) / (r * r))).astype(np.float32)
                if p.get("sourire"):
                    dy += g * (mh * 0.9 + 2) * p["sourire"] / 100
                if p.get("bouche"):
                    dx -= g * coin * mw * 0.12 * p["bouche"] / 100
        sx += dx
        sy += dy
    out = a.copy()
    out[y0:y1, x0:x1] = cv2.remap(a, sx, sy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return out


def panneau_fluidite():
    from PySide6.QtWidgets import QVBoxLayout
    from .dialogues_reglage import Curseur, _Panneau

    class PanneauFluidite(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            info = QLabel(tr("L'IA a trouvé les visages, les yeux, le nez et la bouche. Chaque réglage s'applique à "
                             "tous les visages ; à gauche du milieu : l'inverse."))
            info.setWordWrap(True)
            lay.addWidget(info)
            self.c = {}
            for cle, libelle in FLUIDITE:
                c = Curseur(tr(libelle), -100, 100, self.p.get(cle, 0), "")
                c.change.connect(self._lire)
                lay.addWidget(c)
                self.c[cle] = c

        def _lire(self):
            self.p = {k: int(c.valeur()) for k, c in self.c.items()}
            self.change.emit()

    return PanneauFluidite


def panneau_force(texte: str, depart: int = 80):
    from PySide6.QtWidgets import QVBoxLayout
    from .dialogues_reglage import Curseur, _Panneau

    class PanneauForce(_Panneau):
        def __init__(self, params, histo):
            super().__init__(params, histo)
            lay = QVBoxLayout(self)
            info = QLabel(texte)
            info.setWordWrap(True)
            lay.addWidget(info)
            self.c = Curseur(tr("Force"), 0, 100, self.p.get("force", depart), " %")
            self.c.change.connect(self._lire)
            lay.addWidget(self.c)

        def _lire(self):
            self.p = {"force": int(self.c.valeur())}
            self.change.emit()

    return PanneauForce


# ====================================================================== recadrage conseillé
def cadrages(sujet: np.ndarray | None, W: int, H: int) -> list[tuple[str, QRect]]:
    """Propositions de cadrage autour du sujet (masque 0..255) : règle des tiers, centré, carré, 4:5, 16:9."""
    if sujet is not None and (sujet > 127).mean() > 0.002:
        ys, xs = np.nonzero(sujet > 127)
        bx0, bx1, by0, by1 = xs.min(), xs.max(), ys.min(), ys.max()
        poids = sujet.astype(np.float32)
        cx = float((poids.sum(0) * np.arange(W)).sum() / poids.sum())
        cy = float((poids.sum(1) * np.arange(H)).sum() / poids.sum())
        cy = by0 + (cy - by0) * 0.6                   # le regard est plutôt en haut du sujet
    else:
        bx0, bx1, by0, by1 = W * 0.3, W * 0.7, H * 0.3, H * 0.7
        cx, cy = W / 2, H / 2

    def cadre(rapport: float, echelle: float, px: float, py: float) -> QRect:
        """Le plus grand cadre de ce rapport (× echelle) qui place (cx, cy) en (px, py) du cadre, dans l'image,
        et qui garde le sujet entier si possible."""
        w = min(W, H * rapport) * echelle
        h = w / rapport
        bw, bh = bx1 - bx0, by1 - by0
        if bw > w or bh > h:                          # trop serré : on élargit jusqu'à contenir le sujet
            k = min(max(bw / w, bh / h) * 1.06, min(W / w, H / h))
            w, h = w * k, h * k
        x = min(max(cx - w * px, 0), W - w)
        y = min(max(cy - h * py, 0), H - h)
        x = min(x, bx0) if bx0 >= 0 and bx0 < x else x
        x = max(x, bx1 - w) if bx1 > x + w else x
        y = min(y, by0) if by0 < y else y
        y = max(y, by1 - h) if by1 > y + h else y
        x, y = min(max(x, 0), W - w), min(max(y, 0), H - h)
        return QRect(int(round(x)), int(round(y)), int(round(w)), int(round(h)))

    r = W / H
    tiers_x = 1 / 3 if cx < W / 2 else 2 / 3
    props = [(tr("Règle des tiers"), cadre(r, 0.8, tiers_x, 1 / 3)),
             (tr("Sujet centré"), cadre(r, 0.75, 0.5, 0.45)),
             (tr("Carré"), cadre(1.0, 0.95, 0.5, 0.42)),
             (tr("Portrait 4:5"), cadre(0.8, 0.95, 0.5, 0.4)),
             (tr("Paysage 16:9"), cadre(16 / 9, 0.95, tiers_x, 0.4))]
    vus, res = set(), []
    for n, q in props:
        cle = (q.x() // 8, q.y() // 8, q.width() // 8, q.height() // 8)
        if cle not in vus and q.width() > 8 and q.height() > 8:
            vus.add(cle)
            res.append((n, q))
    return res


class DialogueCadrages(QDialog):
    def __init__(self, image: QImage, props: list[tuple[str, QRect]], parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Recadrage conseillé"))
        self.props = props
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Choisis un cadrage (double-clic ou OK). Ctrl+Z revient à la photo entière."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.liste = QListWidget()
        self.liste.setViewMode(QListWidget.IconMode)
        self.liste.setIconSize(QSize(220, 170))
        self.liste.setResizeMode(QListWidget.Adjust)
        self.liste.setMovement(QListWidget.Static)
        self.liste.setMinimumSize(760, 420)
        k = min(1.0, 600 / max(image.width(), image.height()))
        petite = image.scaled(max(1, int(image.width() * k)), max(1, int(image.height() * k)), Qt.KeepAspectRatio,
                              Qt.SmoothTransformation)
        for nom, q in props:
            pm = QPixmap.fromImage(petite)
            p = QPainter(pm)
            p.fillRect(pm.rect(), QColor(0, 0, 0, 120))
            src = QRectF(q.x() * k, q.y() * k, q.width() * k, q.height() * k)
            p.drawImage(src, petite, src)
            p.setPen(QPen(QColor(255, 255, 255, 170), 1))
            for i in (1, 2):                         # tiers
                p.drawLine(QPointF(src.x() + src.width() * i / 3, src.y()),
                           QPointF(src.x() + src.width() * i / 3, src.bottom()))
                p.drawLine(QPointF(src.x(), src.y() + src.height() * i / 3),
                           QPointF(src.right(), src.y() + src.height() * i / 3))
            p.end()
            it = QListWidgetItem(pm, f"{nom}\n{q.width()} × {q.height()} px")
            self.liste.addItem(it)
        self.liste.setCurrentRow(0)
        self.liste.itemDoubleClicked.connect(lambda _i: self.accept())
        lay.addWidget(self.liste, 1)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)

    def choix(self) -> QRect | None:
        i = self.liste.currentRow()
        return self.props[i][1] if 0 <= i < len(self.props) else None


# ====================================================================== document photographié
def trouver_document(rgb: np.ndarray):
    """4 coins (haut-gauche, haut-droit, bas-droit, bas-gauche) de la feuille, ou None."""
    import cv2
    h, w = rgb.shape[:2]
    k = min(1.0, 1000 / max(h, w))
    petit = cv2.resize(rgb, (int(w * k), int(h * k)), interpolation=cv2.INTER_AREA) if k < 1 else rgb
    gris = cv2.GaussianBlur(cv2.cvtColor(petit, cv2.COLOR_RGB2GRAY), (5, 5), 0)
    aire_img = petit.shape[0] * petit.shape[1]
    meilleur = None
    for bas, haut in ((30, 100), (10, 60), (60, 180)):
        bords = cv2.dilate(cv2.Canny(gris, bas, haut), np.ones((5, 5), np.uint8))
        contours, _h = cv2.findContours(bords, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
            peri = cv2.arcLength(c, True)
            q = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(q) == 4 and cv2.isContourConvex(q) and cv2.contourArea(q) > 0.2 * aire_img:
                if meilleur is None or cv2.contourArea(q) > cv2.contourArea(meilleur):
                    meilleur = q
        if meilleur is not None:
            break
    if meilleur is None:
        return None
    pts = meilleur.reshape(4, 2).astype(np.float32) / k
    s, d = pts.sum(1), np.diff(pts, axis=1).ravel()
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def redresser_document(rgb: np.ndarray, coins: np.ndarray | None) -> np.ndarray:
    import cv2
    if coins is None:
        return rgb
    tl, tr_, br, bl = coins
    w = int(max(np.linalg.norm(tr_ - tl), np.linalg.norm(br - bl)))
    h = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr_)))
    M = cv2.getPerspectiveTransform(coins, np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]]))
    out = cv2.warpPerspective(rgb, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    m = max(2, int(min(w, h) * 0.008))                 # le bord de la feuille (souvent une ombre) est rogné
    return out[m:h - m, m:w - m]


def blanchir_document(rgb: np.ndarray, mode: str = "couleur", force: int = 100) -> np.ndarray:
    """Fond blanc et uni (ombres et lumière inégale enlevées), texte noir. mode : couleur, gris, noir_blanc."""
    import cv2
    h, w = rgb.shape[:2]
    taille = max(15, (max(h, w) // 25) | 1)
    fond = cv2.morphologyEx(rgb, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (taille, taille)))
    fond = cv2.medianBlur(fond, 21 if taille > 21 else (taille | 1))
    norm = np.clip(rgb.astype(np.float32) / np.maximum(fond.astype(np.float32), 1) * 255, 0, 255)
    f = force / 100
    norm = rgb.astype(np.float32) * (1 - f) + norm * f
    gris = cv2.cvtColor(norm.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    if mode == "noir_blanc":
        nb = cv2.adaptiveThreshold(gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 12)
        return np.dstack([nb] * 3)
    if mode == "gris":
        norm = np.dstack([gris] * 3).astype(np.float32)
    noir = np.percentile(gris, 2)                    # étirer : l'encre plus noire, le fond reste blanc
    norm = np.clip((norm - noir) * 255 / max(1, 245 - noir), 0, 255)
    return norm.astype(np.uint8)


class DialogueDocument(QDialog):
    def __init__(self, rgb: np.ndarray, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Nettoyer un document photographié"))
        self.rgb = rgb
        self.coins = trouver_document(rgb)
        lay = QVBoxLayout(self)
        self.vue = QLabel()
        self.vue.setAlignment(Qt.AlignCenter)
        self.vue.setMinimumSize(520, 520)
        lay.addWidget(self.vue, 1)
        f = QFormLayout()
        self.mode = QComboBox()
        for cle, nom in (("couleur", tr("En couleurs")), ("gris", tr("En gris")),
                         ("noir_blanc", tr("Noir et blanc (texte seulement)"))):
            self.mode.addItem(nom, cle)
        self.mode.currentIndexChanged.connect(self._apercu)
        f.addRow(tr("Résultat"), self.mode)
        lay.addLayout(f)
        info = QLabel(tr("Feuille trouvée : elle est redressée (vue de face) puis son fond devient blanc.")
                      if self.coins is not None else
                      tr("Bords de la feuille non trouvés : seul le fond est nettoyé. Pour redresser, utilise d'abord "
                         "Image > Recadrage en perspective."))
        info.setWordWrap(True)
        info.setObjectName("discret")
        lay.addWidget(info)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)
        import cv2
        k = min(1.0, 900 / max(rgb.shape[:2]))
        self._petit = cv2.resize(rgb, (int(rgb.shape[1] * k), int(rgb.shape[0] * k))) if k < 1 else rgb
        self._k = k
        self._apercu()

    def _calcul(self, rgb, k=1.0):
        coins = None if self.coins is None else self.coins * k
        return blanchir_document(redresser_document(rgb, coins), self.mode.currentData())

    def _apercu(self):
        a = np.ascontiguousarray(self._calcul(self._petit, self._k))
        img = QImage(a.data, a.shape[1], a.shape[0], a.shape[1] * 3, QImage.Format_RGB888).copy()
        self.vue.setPixmap(QPixmap.fromImage(img).scaled(520, 520, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resultat(self) -> QImage:
        a = np.ascontiguousarray(self._calcul(self.rgb))
        return QImage(a.data, a.shape[1], a.shape[0], a.shape[1] * 3, QImage.Format_RGB888).copy()


# ====================================================================== marionnette
def mls_rigide(vx: np.ndarray, vy: np.ndarray, p: np.ndarray, q: np.ndarray, alpha: float = 1.0):
    """Moindres carrés mobiles, version rigide (Schaefer 2006) : (vx, vy) -> point déplacé, épingles p -> q."""
    n = len(p)
    if n == 0:
        return vx, vy
    if n == 1:
        return vx + (q[0, 0] - p[0, 0]), vy + (q[0, 1] - p[0, 1])
    v = np.stack([vx, vy], -1).astype(np.float64)
    d2 = ((v[..., None, :] - p) ** 2).sum(-1)
    w = 1 / np.maximum(d2, 1e-6) ** alpha
    ws = w.sum(-1, keepdims=True)
    ps = (w[..., None] * p).sum(-2) / ws
    qs = (w[..., None] * q).sum(-2) / ws
    ph = p - ps[..., None, :]
    qh = q - qs[..., None, :]
    d = v - ps
    dpx, dpy = -d[..., 1], d[..., 0]
    ax, ay = ph[..., 0], ph[..., 1]
    apx, apy = -ay, ax
    a00 = w * (ax * d[..., 0, None] + ay * d[..., 1, None])
    a01 = w * (ax * dpx[..., None] + ay * dpy[..., None]) * -1
    a10 = w * (apx * d[..., 0, None] + apy * d[..., 1, None]) * -1
    a11 = w * (apx * dpx[..., None] + apy * dpy[..., None])
    fx = (qh[..., 0] * a00 + qh[..., 1] * a10).sum(-1)
    fy = (qh[..., 0] * a01 + qh[..., 1] * a11).sum(-1)
    nf = np.sqrt(fx * fx + fy * fy)
    nd = np.sqrt((d ** 2).sum(-1))
    k = np.where(nf > 1e-9, nd / np.maximum(nf, 1e-9), 0)
    return fx * k + qs[..., 0], fy * k + qs[..., 1]


def marionnette(a: np.ndarray, depart: list, arrivee: list, pas: int | None = None) -> np.ndarray:
    """Déforme (h, w, c) : chaque épingle va de depart[i] à arrivee[i] ; le reste suit de façon rigide."""
    import cv2
    h, w = a.shape[:2]
    if not depart or all(abs(x0 - x1) < 0.01 and abs(y0 - y1) < 0.01 for (x0, y0), (x1, y1) in zip(depart, arrivee)):
        return a
    pas = pas or max(4, max(h, w) // 120)
    gx, gy = np.meshgrid(np.arange(0, w + pas, pas, dtype=np.float64), np.arange(0, h + pas, pas, dtype=np.float64))
    # chemin inverse : pour chaque point d'arrivée, d'où vient-il ? (épingles inversées), sur une grille grossière
    sx, sy = mls_rigide(gx, gy, np.float64(arrivee), np.float64(depart))
    # puis lu à chaque pixel (interpolation entre les points de la grille, espacés de « pas »)
    px, py = np.meshgrid(np.arange(w, dtype=np.float32) / pas, np.arange(h, dtype=np.float32) / pas)
    mx = cv2.remap(sx.astype(np.float32), px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    my = cv2.remap(sy.astype(np.float32), px, py, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return cv2.remap(a, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


class VueMarionnette(QWidget):
    change = Signal()

    def __init__(self, image: QImage, parent=None):
        super().__init__(parent)
        self.image = image
        self.setMinimumSize(640, 480)
        self.setMouseTracking(True)
        self.depart: list[tuple[float, float]] = []
        self.arrivee: list[tuple[float, float]] = []
        self.rendu = image
        self.tenu = None

    def _echelle(self):
        k = min(self.width() / self.image.width(), self.height() / self.image.height())
        ox = (self.width() - self.image.width() * k) / 2
        oy = (self.height() - self.image.height() * k) / 2
        return k, ox, oy

    def vers_image(self, pos):
        k, ox, oy = self._echelle()
        return (pos.x() - ox) / k, (pos.y() - oy) / k

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(60, 60, 60))
        k, ox, oy = self._echelle()
        cible = QRectF(ox, oy, self.image.width() * k, self.image.height() * k)
        p.drawImage(cible, self.rendu)
        p.setRenderHint(QPainter.Antialiasing)
        for i, (x, y) in enumerate(self.arrivee):
            c = QPointF(ox + x * k, oy + y * k)
            p.setPen(QPen(QColor(0, 0, 0), 2))
            p.setBrush(QColor(255, 210, 0) if i == self.tenu else QColor(255, 255, 255))
            p.drawEllipse(c, 6, 6)
        p.end()

    def _proche(self, pos):
        k, ox, oy = self._echelle()
        for i, (x, y) in enumerate(self.arrivee):
            if (ox + x * k - pos.x()) ** 2 + (oy + y * k - pos.y()) ** 2 < 100:
                return i
        return None

    def mousePressEvent(self, e):
        i = self._proche(e.position())
        if e.button() == Qt.RightButton:
            if i is not None:
                self.depart.pop(i)
                self.arrivee.pop(i)
                self.change.emit()
                self.update()
            return
        if i is None:
            x, y = self.vers_image(e.position())
            if not (0 <= x < self.image.width() and 0 <= y < self.image.height()):
                return
            self.depart.append((x, y))
            self.arrivee.append((x, y))
            i = len(self.arrivee) - 1
        self.tenu = i
        self.update()

    def mouseMoveEvent(self, e):
        if self.tenu is not None and e.buttons() & Qt.LeftButton:
            self.arrivee[self.tenu] = self.vers_image(e.position())
            self.change.emit()
            self.update()

    def mouseReleaseEvent(self, _e):
        self.tenu = None
        self.update()


class DialogueMarionnette(QDialog):
    """Déformation de la marionnette : épingles posées d'un clic, déplacées en glissant, retirées au clic droit."""

    def __init__(self, image: QImage, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Déformation de la marionnette"))
        self.resize(900, 700)
        self.image = image
        k = min(1.0, 900 / max(image.width(), image.height()))
        self.k = k
        self.petite = image.scaled(max(1, int(image.width() * k)), max(1, int(image.height() * k)),
                                   Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        from .document import tableau
        self._a = tableau(self.petite.convertToFormat(QImage.Format_RGBA8888_Premultiplied)).copy()
        lay = QVBoxLayout(self)
        aide = QLabel(tr("Clic : poser une épingle (pose-en sur ce qui doit rester en place, et sur ce qui doit "
                         "bouger). Glisse une épingle pour plier le sujet ; clic droit : la retirer. Marche mieux "
                         "sur un sujet détouré, dans son propre calque."))
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.vue = VueMarionnette(self.petite)
        self.vue.change.connect(self._apercu)
        lay.addWidget(self.vue, 1)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)

    def _apercu(self):
        a = marionnette(self._a, self.vue.depart, self.vue.arrivee)
        a = np.ascontiguousarray(a)
        self.vue.rendu = QImage(a.data, a.shape[1], a.shape[0], a.shape[1] * 4,
                                QImage.Format_RGBA8888_Premultiplied).copy()
        self.vue.update()

    def epingles(self):
        k = self.k
        return ([(x / k, y / k) for x, y in self.vue.depart], [(x / k, y / k) for x, y in self.vue.arrivee])


# ====================================================================== nouveau fond, vêtements
FONDS = [
    ("studio_blanc", "Studio, fond blanc", "a clean white photo studio background, soft even light"),
    ("studio_gris", "Studio, fond gris dégradé", "a professional grey gradient studio backdrop, soft light"),
    ("studio_noir", "Studio, fond noir", "a deep black studio background with subtle rim light"),
    ("plage", "Plage au soleil", "a sunny tropical beach with turquoise sea and blue sky"),
    ("ville_nuit", "Ville la nuit", "a city street at night with blurred colourful lights, bokeh"),
    ("foret", "Forêt", "a green forest with soft sunlight through the trees"),
    ("bureau", "Bureau flou", "a modern office interior, out of focus"),
    ("coucher", "Coucher de soleil", "a warm golden sunset sky over the horizon"),
    ("montagne", "Montagnes", "majestic mountains under a clear sky"),
    ("scene", "Scène de concert", "a concert stage with dramatic coloured spotlights and haze"),
    ("neon", "Mur de néons", "a dark wall with glowing neon lights, pink and blue"),
    ("briques", "Mur de briques", "an old red brick wall"),
]
VETEMENTS = [
    ("tshirt", "T-shirt", "change the clothes to a simple {couleur} t-shirt"),
    ("chemise", "Chemise", "change the clothes to an elegant {couleur} shirt"),
    ("costume", "Costume et cravate", "dress the person in a tailored {couleur} suit with a tie"),
    ("veste", "Veste en cuir", "dress the person in a {couleur} leather jacket"),
    ("pull", "Pull", "dress the person in a cosy {couleur} sweater"),
    ("robe", "Robe de soirée", "dress the person in an elegant {couleur} evening dress"),
    ("sport", "Tenue de sport", "dress the person in {couleur} sportswear"),
    ("couleur", "Seulement la couleur des vêtements", "change the colour of the clothes to {couleur}"),
]
COULEURS_VETEMENTS = [("noir", "black"), ("blanc", "white"), ("gris", "grey"), ("bleu marine", "navy blue"),
                      ("bleu", "blue"), ("rouge", "red"), ("bordeaux", "burgundy"), ("vert", "green"),
                      ("beige", "beige"), ("marron", "brown"), ("jaune", "yellow"), ("rose", "pink")]
GARDER_VETEMENTS = ("Keep the same person, face, hair, pose, body shape, lighting and background; only the clothes "
                    "change.")


def consigne_vetements(cle: str, couleur: str) -> str:
    for c, _fr, en in VETEMENTS:
        if c == cle:
            return en.format(couleur=couleur).capitalize() + ". " + GARDER_VETEMENTS
    return ""


class DialogueChoix(QDialog):
    """Une liste de choix (boutons ronds), une couleur facultative, un texte libre facultatif, le nombre de
    propositions."""

    def __init__(self, parent, titre: str, aide: str, choix, couleurs=None, libre: str | None = None, nb: int = 2,
                 avec_photo: bool = False):
        super().__init__(parent)
        self.setWindowTitle(titre)
        lay = QVBoxLayout(self)
        t = QLabel(aide)
        t.setWordWrap(True)
        t.setObjectName("discret")
        lay.addWidget(t)
        self.groupe = QButtonGroup(self)
        self.cles = []
        grille = QHBoxLayout()
        col1, col2 = QVBoxLayout(), QVBoxLayout()
        for i, (cle, fr, _en) in enumerate(choix):
            r = QRadioButton(tr(fr))
            self.groupe.addButton(r, i)
            self.cles.append(cle)
            (col1 if i < (len(choix) + 1) // 2 else col2).addWidget(r)
        if avec_photo:
            r = QRadioButton(tr("Une autre photo (fichier)…"))
            self.groupe.addButton(r, len(choix))
            self.cles.append("photo")
            col2.addWidget(r)
        grille.addLayout(col1)
        grille.addLayout(col2)
        lay.addLayout(grille)
        self.groupe.button(0).setChecked(True)
        f = QFormLayout()
        self.couleur = QComboBox()
        if couleurs:
            for fr, en in couleurs:
                self.couleur.addItem(tr(fr), en)
            f.addRow(tr("Couleur"), self.couleur)
        self.libre = QLineEdit()
        if libre is not None:
            self.libre.setPlaceholderText(libre)
            f.addRow(tr("Ou décris-le (facultatif)"), self.libre)
        self.nb = QSpinBox()
        self.nb.setRange(1, 4)
        self.nb.setValue(nb)
        f.addRow(tr("Propositions"), self.nb)
        lay.addLayout(f)
        b = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        lay.addWidget(b)

    def cle(self) -> str:
        return self.cles[self.groupe.checkedId()]


# ====================================================================== la fenêtre
class RetouchePlusMixin:

    def _retouche_plus(self, ajouter):
        """ajouter(menu, texte, fonction, clé, avant) : fourni par _creation."""
        ajouter("IA", tr("Restaurer les visages flous (IA)…"), self.ia_visages_flous, "a_ia_visages_flous",
                tr("Retouche portrait…"))
        ajouter("IA", tr("Fluidité des visages (IA)…"), self.ia_fluidite_visages, "a_ia_fluidite_visages",
                tr("Retouche portrait…"))
        ajouter("IA", tr("Changer les vêtements (IA)…"), self.ia_vetements, "a_ia_vetements",
                tr("Retouche portrait…"))
        ajouter("IA", tr("Nouveau fond (IA)…"), self.ia_nouveau_fond, "a_ia_nouveau_fond")
        ajouter("Image", tr("Recadrage conseillé (IA)…"), self.recadrage_conseille, "a_recadrage_conseille")
        ajouter("Image", tr("Nettoyer un document photographié…"), self.nettoyer_document, "a_nettoyer_document")
        ajouter("Édition", tr("Déformation de la marionnette…"), self.deformation_marionnette, "a_marionnette")

    # ---------------------------------------------------------- calcul du moteur (plusieurs images)
    def _moteur_en_fond(self, titre: str, calcul, suite):
        from .dialogues import Attente
        annuler = threading.Event()
        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)
        doc = self.doc

        def ok(r):
            attente.hide()
            attente.deleteLater()
            if doc is self.doc:
                suite(r)

        def echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        t = self._tache(lambda progres: calcul(annuler, progres), ok, echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def _reperes(self, titre: str, suite):
        """SAM : visages un par un, yeux, lèvres, nez -> suite(rgb, [repères])."""
        from . import recettes
        from .document import FORMAT_IMAGE, tableau
        if not self.doc or not self._sam_present(titre):
            return
        rgb = tableau(self.doc.image.convertToFormat(FORMAT_IMAGE))[..., :3].copy()

        def apres(cartes):
            if not cartes or len(cartes) < 4:
                QMessageBox.information(self, titre, tr("Aucun visage trouvé dans cette image."))
                return
            visages, yeux, levres, nez = cartes[:-3], cartes[-3], cartes[-2], cartes[-1]
            reps = reperes_visages(visages, yeux, levres, nez)
            if not reps:
                QMessageBox.information(self, titre, tr("Aucun visage trouvé dans cette image."))
                return
            suite(rgb, reps)
        self._carte_ia(tr("Recherche des visages"), recettes.visages_un_par_un, apres, toutes=True, vide_ok=True)

    # ---------------------------------------------------------- restaurer les visages flous
    def ia_visages_flous(self):
        from . import recettes
        titre = tr("Restaurer les visages flous")
        if not self.doc or not self._verifier_pixels(titre):
            return
        if not recettes.visages_flous_disponible():
            if QMessageBox.question(self, titre, tr(
                    "Cette action a besoin du modèle GFPGAN (349 Mo, licence Apache-2.0), qui n'est pas installé.\n\n"
                    "Ouvrir l'installation du moteur IA maintenant ? (case « Restaurer les visages flous »)")) \
                    == QMessageBox.Yes:
                self.installer_moteur()
            return

        def avec_reperes(rgb, reps):
            import cv2
            matrices = [matrice_alignement(v) for v in reps]
            pngs = []
            for M in matrices:
                c = visage_redresse(rgb, M)
                ok, octets = cv2.imencode(".png", cv2.cvtColor(c, cv2.COLOR_RGB2BGR))
                pngs.append(octets.tobytes())

            def calcul(annuler, progres):
                noms = [self.moteur.envoyer_image(p) for p in pngs]
                prompt, sorties = recettes.restaurer_visages(noms)
                res = self.moteur.executer(prompt, sorties, annuler, progres)
                out = []
                for _n, octets in res:
                    a = cv2.imdecode(np.frombuffer(octets, np.uint8), cv2.IMREAD_COLOR)
                    a = cv2.cvtColor(a, cv2.COLOR_BGR2RGB)
                    if a.shape[:2] != (COTE, COTE):
                        a = cv2.resize(a, (COTE, COTE), interpolation=cv2.INTER_AREA)
                    out.append(a)
                return out

            def fini(restaures):
                if len(restaures) != len(reps):
                    QMessageBox.warning(self, titre, tr("Le calcul s'est arrêté sans résultat."))
                    return
                net, poids = recoller_visages(rgb, reps, matrices, restaures)
                self._dernier_visages = (net, poids)

                def appliquer(a, p):
                    f = poids[..., None] * (p["force"] / 100)
                    out = a.copy()
                    out[..., :3] = np.clip(a[..., :3] * (1 - f) + net * f, 0, 255).astype(np.uint8)
                    return out
                self._dialogue_pixels(titre, panneau_force(tr(
                    "{n} visage(s) restauré(s) par GFPGAN. « Force » : 100 % = le visage refait, moins = mélangé "
                    "avec la photo (plus naturel).", n=len(reps)), 80), {"force": 0}, appliquer, toujours=True)
            self._moteur_en_fond(titre, calcul, fini)
        self._reperes(titre, avec_reperes)

    # ---------------------------------------------------------- fluidité des visages
    def ia_fluidite_visages(self):
        titre = tr("Fluidité des visages")
        if not self.doc or not self._verifier_pixels(titre):
            return

        def avec_reperes(_rgb, reps):
            self._dernier_reperes = reps
            self._dialogue_pixels(titre, panneau_fluidite(), dict(FLUIDITE_NEUTRES),
                                  lambda a, p: deformer_visages(a, reps, p))
        self._reperes(titre, avec_reperes)

    # ---------------------------------------------------------- nouveau fond
    def ia_nouveau_fond(self, cle: str | None = None, texte: str | None = None, nb: int = 2,
                        chemin: str | None = None):
        from . import recettes
        from .fenetre import CommandeEtat
        titre = tr("Nouveau fond")
        if not self.doc or not self._verifier_verrou(titre):
            return None
        if cle is None:
            d = DialogueChoix(self, titre, tr(
                "Le sujet reste ; le fond est refait par l'IA (Flux Fill, environ 1 min par proposition), ou "
                "remplacé par une autre photo."), FONDS, libre=tr("ex. « une bibliothèque ancienne »"),
                avec_photo=True)
            if not d.exec():
                return None
            cle, texte, nb = d.cle(), d.libre.text().strip(), d.nb.value()
        if cle == "photo" and not chemin:
            from .document import EXTENSIONS_LECTURE
            chemin, _f = QFileDialog.getOpenFileName(self, tr("Photo du nouveau fond"),
                                                     self.reglages.value("dossier", ""),
                                                     tr("Images") + f" ({EXTENSIONS_LECTURE})")
            if not chemin:
                return None
        if not texte and cle != "photo":
            texte = next(en for c, _f, en in FONDS if c == cle)
        elif texte and cle != "photo":
            from . import traduction
            try:
                if traduction.installe() and not traduction.semble_anglais(texte):
                    texte = traduction.traduire(texte) or texte
            except Exception:                     # noqa: BLE001 — traducteur absent : le texte tel quel
                pass
        doc = self.doc

        def suite(m):
            import cv2
            from .document import _masque_vers_selection
            if (m > 127).mean() < 0.005:
                QMessageBox.information(self, titre, tr("Aucun sujet trouvé dans cette image."))
                return
            if cle == "photo":
                from .creation import couvrir
                from .document import Calque, Document
                autre = couvrir(QImage(Document.ouvrir(chemin).image), *doc.taille())
                avant = doc.etat()
                etat1 = doc.etat_nouveau_calque(autre, tr("Nouveau fond"))
                masque = QImage(np.ascontiguousarray(m).data, m.shape[1], m.shape[0], m.shape[1],
                                QImage.Format_Grayscale8).copy()
                c = Calque(doc.nom_libre(tr("Sujet")), visible_avant.convertToFormat(
                    QImage.Format_ARGB32_Premultiplied), masque=masque)
                calques = list(etat1[0])
                pos = etat1[1] + 1
                calques.insert(pos, c)
                self.historique.push(CommandeEtat(doc, avant, (tuple(calques), pos, etat1[2]), titre))
                self.statusBar().showMessage(tr("Nouveau fond posé : le sujet est dans son calque, avec un masque. "
                                                "Calque > Harmoniser avec l'arrière-plan accorde ses couleurs."),
                                             10000)
                return
            fond = 255 - m
            fond = cv2.dilate(fond, np.ones((5, 5), np.uint8))           # un liseré du sujet est refait aussi
            sel = _masque_vers_selection(fond).convertToFormat(QImage.Format_ARGB32_Premultiplied)
            self.historique.push(CommandeEtat(doc, doc.etat(), (doc.calques, doc.actif, sel), tr("Sélection du fond")))
            self._lancer(titre, True, lambda nom: recettes.remplir(nom, texte, nb=nb), remplir_trous=True,
                         variante=lambda nom, force: recettes.variante(nom, force, texte))
        visible_avant = doc.image.copy()
        self._detourage(tr("Recherche du sujet"), suite)
        return texte

    # ---------------------------------------------------------- vêtements
    def ia_vetements(self, cle: str | None = None, couleur: str = "black", nb: int = 2):
        titre = tr("Changer les vêtements (IA)")
        if not self.doc or not self._verifier_verrou(titre):
            return None
        from . import recettes
        if not recettes.restauration_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Flux Kontext (11,9 Go), qui n'est pas installé. Menu IA > Installer "
                "le moteur IA permet de l'ajouter (case « Flux Kontext »)."))
            return None
        if cle is None:
            d = DialogueChoix(self, titre, tr(
                "La personne, son visage, sa pose et le fond restent les mêmes ; seuls les vêtements changent. Avec "
                "une sélection, seule cette zone change. Flux Kontext, environ 1 min par proposition."),
                VETEMENTS, couleurs=COULEURS_VETEMENTS)
            if not d.exec():
                return None
            cle, couleur, nb = d.cle(), d.couleur.currentData(), d.nb.value()
        consigne = consigne_vetements(cle, couleur)
        self._modifier_avec(titre, consigne, nb)
        return consigne

    # ---------------------------------------------------------- recadrage conseillé
    def recadrage_conseille(self, sujet: np.ndarray | None = None, d=None):
        from . import recettes
        from .fenetre import CommandeEtat
        if not self.doc:
            return None
        doc = self.doc

        def suite(m):
            W, H = doc.taille()
            props = cadrages(m, W, H)
            dlg = d or DialogueCadrages(doc.image, props, self)
            if d is None and not dlg.exec():
                return
            r = dlg.choix() if d is None else props[0][1]
            if r is None:
                return
            self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_recadre(r), tr("Recadrage conseillé")))
            self._derniers_cadrages = props
        if sujet is not None or d is not None or not recettes.detourage_disponible():
            suite(sujet)
        else:
            self._detourage(tr("Recherche du sujet"), suite)
        return True

    # ---------------------------------------------------------- document
    def nettoyer_document(self, d=None):
        from .document import FORMAT_IMAGE, Document, tableau
        if not self.doc:
            return None
        rgb = tableau(self.doc.image.convertToFormat(FORMAT_IMAGE))[..., :3].copy()
        if d is None:
            d = DialogueDocument(rgb, self)
            if not d.exec():
                return None
        img = d.resultat()
        doc = Document(img.convertToFormat(QImage.Format_ARGB32_Premultiplied))
        doc.dpi = self.doc.dpi
        self._installer_document(doc)
        self.statusBar().showMessage(tr("Document nettoyé : nouvelle image (l'original n'est pas touché)."), 8000)
        return doc

    # ---------------------------------------------------------- marionnette
    def deformation_marionnette(self, epingles=None):
        from .document import tableau
        from .fenetre import CommandeEtat
        titre = tr("Déformation de la marionnette")
        if not self.doc or not self._verifier_pixels(titre):
            return None
        doc = self.doc
        calque = doc.calque_actif
        if epingles is None:
            d = DialogueMarionnette(calque.image, self)
            if not d.exec():
                return None
            epingles = d.epingles()
        depart, arrivee = epingles
        if not depart:
            return None
        a = tableau(calque.image.convertToFormat(QImage.Format_RGBA8888_Premultiplied)).copy()
        out = np.ascontiguousarray(marionnette(a, depart, arrivee))
        img = QImage(out.data, out.shape[1], out.shape[0], out.shape[1] * 4,
                     QImage.Format_RGBA8888_Premultiplied).copy().convertToFormat(calque.image.format())
        self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_calque_modifie(doc.actif, image=img), titre))
        return True
