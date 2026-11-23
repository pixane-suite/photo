"""Essai de la création : texte 3D, vectoriser, panorama, GIF animé, photo d'identité, collage, double exposition,
coller en perspective, retouche du visage / maquillage (consigne et lancement, sans le moteur IA), instantanés.
Usage : essai_creation.py [dossier de sortie]"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

from pixane import creation
from pixane.document import Document, tableau

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
sortie.mkdir(parents=True, exist_ok=True)
echecs = []


def verifier(ok, texte):
    print(("ok  " if ok else "ÉCHEC ") + texte)
    if not ok:
        echecs.append(texte)


app = QApplication.instance() or QApplication(sys.argv)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)


def scene(w=900, h=600, graine=1):
    """Image riche en détails (pour le raccord du panorama)."""
    rng = np.random.default_rng(graine)
    import cv2
    a = np.full((h, w, 3), 200, np.uint8)
    for _ in range(260):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        c = tuple(int(v) for v in rng.integers(0, 255, 3))
        if rng.random() < .5:
            cv2.circle(a, (x, y), int(rng.integers(5, 40)), c, -1)
        else:
            cv2.rectangle(a, (x, y), (x + int(rng.integers(10, 60)), y + int(rng.integers(10, 60))), c, -1)
    a = cv2.GaussianBlur(a, (3, 3), 0)
    img = QImage(a.data, w, h, 3 * w, QImage.Format_RGB888).copy()
    return img


# ---------------------------------------------------------------- texte 3D
from pixane.styles import styles_prets
noms = [n for n, _s in styles_prets()]
verifier("Texte 3D" in noms and "Texte 3D doré" in noms, "styles prêts « Texte 3D » et « Texte 3D doré »")

# ---------------------------------------------------------------- vectoriser
logo = QImage(300, 200, QImage.Format_ARGB32_Premultiplied)
logo.fill(QColor(255, 255, 255))
p = QPainter(logo)
p.setRenderHint(QPainter.Antialiasing)
p.setBrush(QColor(220, 30, 30))
p.setPen(Qt.NoPen)
p.drawEllipse(30, 30, 140, 140)
p.setBrush(QColor(30, 60, 200))
p.drawRect(170, 60, 100, 100)
p.end()
svg = creation.vectoriser_svg(logo)
verifier(svg.count("<path") >= 2, f"vectoriser : {svg.count('<path')} tracés")
rendu = creation.svg_vers_image(svg, 300, 200)
a = tableau(rendu.convertToFormat(QImage.Format_RGBA8888))
verifier(a[100, 100, 0] > 180 and a[100, 100, 2] < 90 and a[110, 220, 2] > 150, "vectoriser : rendu fidèle (rouge, bleu)")
(sortie / "vectorise.svg").write_text(svg, encoding="utf-8")

# ---------------------------------------------------------------- panorama
grande = scene(1500, 600)
morceaux = [grande.copy(0, 0, 700, 600), grande.copy(400, 0, 700, 600), grande.copy(800, 0, 700, 600)]
pano = creation.panorama(morceaux)
verifier(pano is not None and pano.width() > 1100, f"panorama : {pano.width() if pano else None} px de large")
if pano is not None:
    pano.save(str(sortie / "panorama.png"))
    al = tableau(pano.convertToFormat(QImage.Format_RGBA8888))[..., 3]
    verifier(al.min() == 255, "panorama recadré : aucun bord vide")
verifier(creation.panorama([scene(500, 400, 3), scene(500, 400, 9)]) is None, "panorama : photos sans raccord refusées")

# ---------------------------------------------------------------- GIF
imgs = []
for k in range(4):
    i = QImage(120, 80, QImage.Format_ARGB32_Premultiplied)
    i.fill(QColor(255, 255, 255))
    p = QPainter(i)
    p.fillRect(k * 25, 20, 30, 30, QColor(200, 0, 0))
    p.end()
    imgs.append(i)
gif = sortie / "anime.gif"
n = creation.gif_anime(imgs, gif, 150, aller_retour=True)
from PIL import Image
g = Image.open(gif)
verifier(n == 6 and g.n_frames == 6 and g.info.get("duration") == 150, f"GIF : {g.n_frames} images (aller-retour), 150 ms")

# ---------------------------------------------------------------- photo d'identité
photo_essai = scene(800, 1000, 5)
cadre, v = creation.cadre_identite(photo_essai, "35x45")
vx, vy, vw, vh = 300, 300, 160, 200                     # un visage connu : la tête doit faire 34 mm sur 45
cx_, cy_, cw_, ch_ = creation.cadre_depuis_visage((vx, vy, vw, vh), "35x45")
verifier(abs(vh * 1.55 / ch_ * 45 - 34) < 0.5 and abs(cx_ + cw_ / 2 - (vx + vw / 2)) < 1,
         "identité : tête de 34 mm sur 45, centrée")
x, y, w, h = cadre
verifier(abs(w / h - 35 / 45) < 0.02, f"identité : cadre aux proportions 35 × 45 ({w} × {h}, visage {v})")
ph = creation.photo_identite(photo_essai, "35x45", cadre)
verifier((ph.width(), ph.height()) == (creation.mm(35), creation.mm(45)), f"identité : {ph.width()} × {ph.height()} px à 300 dpi")
pl, nb = creation.planche(ph)
verifier((pl.width(), pl.height()) == (creation.mm(150), creation.mm(100)) and nb == 8,
         f"planche 10 × 15 cm : {nb} photos")

# ---------------------------------------------------------------- consignes visage
c = creation.consigne_visage(["sourire", "peau"], creation.VISAGE)
verifier(c.startswith("Make the person smile") and "Keep the same person" in c, "consigne visage : " + c[:60])
c = creation.consigne_visage(["levres"], creation.MAQUILLAGE, "plum")
verifier("plum lipstick" in c, "consigne maquillage avec couleur : " + c[:40])
verifier(creation.consigne_visage([], creation.VISAGE) == "", "rien coché : pas de consigne")

# ---------------------------------------------------------------- dans la fenêtre
from pixane.fenetre import Fenetre
f = Fenetre()
f.show()
f.resize(1300, 850)
app.processEvents()
for cle in ("a_collage", "a_panorama", "a_gif", "a_identite", "a_vectoriser", "a_coller_persp", "a_double_expo",
            "a_ia_visage", "a_ia_maquillage"):
    a_ = getattr(f, cle, None)
    verifier(a_ is not None and a_.parent() is f and any(a_ in m.actions() for m in
             [x.menu() for x in f.menuBar().actions() if x.menu()]), f"menu : {cle}")

# collage
ch_imgs = []
for k in range(3):
    chemin = sortie / f"photo{k}.png"
    scene(400 + k * 100, 300, k + 20).save(str(chemin))
    ch_imgs.append(str(chemin))
from pixane.creation import DialogueCollage
d = DialogueCollage(f, ch_imgs)
d.largeur.setValue(1200)
d.hauteur.setValue(800)
d.colonnes.setValue(3)
doc = f.nouveau_collage(d)
verifier(doc is not None and len(doc.calques) == 4 and doc.taille() == (1200, 800),
         f"collage : {len(doc.calques) if doc else 0} calques (fond + 3 photos)")
f.doc.image.save(str(sortie / "collage.png"))
d.deleteLater()

# panorama dans la fenêtre
for k, m in enumerate(morceaux):
    m.save(str(sortie / f"pano{k}.png"))
doc = f.assembler_panorama([str(sortie / f"pano{k}.png") for k in range(3)])
verifier(doc is not None and f.doc is doc, "panorama : nouvelle image ouverte")

# GIF dans la fenêtre : 3 calques
f._installer_document(Document(imgs[0]))
from pixane.fenetre import CommandeEtat
for i in imgs[1:3]:
    f.historique.push(CommandeEtat(f.doc, f.doc.etat(), f.doc.etat_nouveau_calque(i, "vue"), "vue"))
from pixane.creation import DialogueGif
dg = DialogueGif([(c.nom, c.image) for c in f.doc.calques if not c.special and not c.groupe], f)
n = f.exporter_gif(str(sortie / "calques.gif"), dg)
verifier(n == 3, f"GIF depuis les calques : {n} images")

# vectoriser dans la fenêtre (dialogue accepté sans attendre)
f._installer_document(Document(logo))
from pixane.creation import DialogueVectoriser
DialogueVectoriser.exec = lambda self: True
avant = len(f.doc.calques)
f.vectoriser()
verifier(len(f.doc.calques) == avant + 1 and f.doc.calque_actif.nom.startswith("Vectoris"), "vectoriser : nouveau calque")
f.historique.undo()
verifier(len(f.doc.calques) == avant, "vectoriser : Ctrl+Z l'enlève")

# photo d'identité dans la fenêtre
from pixane.creation import DialogueIdentite
di = DialogueIdentite(photo_essai, f)
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import QEvent
avant_cadre = di.cadre()
k_ = di._echelle()
pm_ = di.vue.pixmap()
pos = QPointF((di.vue.width() - pm_.width()) / 2 + 200 * k_, (di.vue.height() - pm_.height()) / 2 + 250 * k_)
di._clic(QMouseEvent(QEvent.MouseButtonPress, pos, pos, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
x_, y_, w_, h_ = di.cadre()
verifier(abs(x_ + w_ / 2 - 200) < 3 and di.cadre() != avant_cadre, "identité : un clic centre le cadre sur le visage")
doc = f.photo_identite(di)
verifier(doc is not None and doc.taille() == (creation.mm(150), creation.mm(100)) and doc.dpi == 300,
         "photo d'identité : planche ouverte à 300 dpi")

# double exposition
base = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
base.fill(QColor(255, 255, 255))
p = QPainter(base)
p.setBrush(QColor(20, 20, 20))
p.drawEllipse(120, 50, 160, 200)
p.end()
f._installer_document(Document(base))
cal = f.double_exposition(str(sortie / "photo1.png"))
m = np.frombuffer(cal.masque.constBits(), np.uint8).reshape(cal.masque.height(), cal.masque.bytesPerLine())[:, :cal.masque.width()] if cal else None
verifier(cal is not None and cal.mode == "ecran" and m[150, 200] > 200 and m[10, 10] < 30,
         "double exposition : calque Superposition, visible dans la silhouette sombre seulement")
f.historique.undo()

# coller en perspective
f._installer_document(Document(scene(600, 400, 7)))
carre = QImage(100, 100, QImage.Format_ARGB32_Premultiplied)
carre.fill(QColor(0, 200, 0))
f.coller_perspective(carre)
c = f.canevas
verifier(c.persp is not None, "coller en perspective : 4 coins à placer")
c.persp = [QPointF(100, 100), QPointF(300, 140), QPointF(300, 260), QPointF(100, 300)]
f._valider_persp()
a = tableau(f.doc.calque_actif.image.convertToFormat(QImage.Format_RGBA8888))
verifier(f.doc.calque_actif.nom.startswith("Coll") and a[200, 200, 1] > 180 and a[200, 200, 3] > 250
         and a[110, 290, 3] == 0 and a[50, 50, 3] == 0, "coller en perspective : image posée dans le quadrilatère")
f.historique.undo()
f.recadrage_perspective()
verifier(f._persp_coller is None, "le recadrage en perspective reste un recadrage")
f._annuler_persp()

# retouche du visage : le lancement passe par le même chemin que « Modifier avec une consigne »
lance = []
f._lancer = lambda titre, *a, **k: lance.append((titre, k.get("duree")))
from pixane import recettes
recettes.restauration_disponible = lambda: True
r = f.ia_visage(False, consigne=creation.consigne_visage(["sourire"], creation.VISAGE), nb=2)
verifier(lance and lance[-1][1] == "kontext" and "smile" in r, f"retouche du visage : lancée ({lance[-1] if lance else None})")
f.ia_visage(True, consigne=creation.consigne_visage(["levres"], creation.MAQUILLAGE, "red"))
verifier(len(lance) == 2 and "Maquillage" in lance[-1][0], "maquillage : lancé")

# instantanés
f.nouvel_instantane("Avant")
app.processEvents()
etat_avant = f.doc.etat()
img_avant = f.doc.image.copy()
f.historique.push(CommandeEtat(f.doc, f.doc.etat(), f.doc.etat_nouveau_calque(carre.scaled(600, 400), "vert"), "vert"))
f.nouvel_instantane("Après")
f._maj_instantanes()
verifier(f.liste_instantanes.count() == 2 and f.liste_instantanes.item(0).text() == "Avant", "instantanés : liste")
f.revenir_instantane(0)
verifier(f.doc.image == img_avant, "instantané : retour à « Avant »")
f.historique.undo()
verifier(f.doc.image != img_avant, "Ctrl+Z annule le retour")
f.liste_instantanes.setCurrentRow(1)
f.supprimer_instantane()
verifier(len(f.doc.instantanes) == 1, "instantané supprimé")
f.grab().save(str(sortie / "fenetre.png"))

for d in list(f.documents):
    d.modifie = False
f.close()
print()
print(f"{len(echecs)} ÉCHEC(S)" if echecs else "TOUT EST BON")
