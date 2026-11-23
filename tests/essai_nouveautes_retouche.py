"""Remplacer un texte (lecture Windows + police semblable ; effacement IA simulé), Effacer d'un clic (SAM simulé :
il renvoie le masque d'un disque), Yeux rouges, Filtres > Correction de l'objectif, Affichage > Comparer avant / après.
Usage : essai_nouveautes_retouche.py dossier_sortie"""
import io
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_nouveautes_retouche")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane import dialogue_polices as dp, fenetre as fe, recettes
from pixane.canevas import EFFACER_CLIC, YEUX
from pixane.document import FORMAT_IMAGE, _masque_vers_selection, tableau
from pixane.moteur import Moteur
from pixane.texte import forme, transformation
Moteur.demarrer = lambda self, signaler=None: None
fe.Fenetre._moteur_en_echec = lambda self, *a: None
QMessageBox.information = lambda *a, **k: QMessageBox.Ok

f = fe.Fenetre()
f.resize(1300, 850)
f.show()


def charger(img: QImage, nom: str):
    p = str(sortie / nom)
    img.save(p)
    f.charger(p)
    app.processEvents()
    return f.doc


# ------------------------------------------------------------------ Remplacer un texte
img = QImage(900, 500, QImage.Format_RGB32)
img.fill(QColor(30, 60, 120))
p = QPainter(img)
p.setRenderHint(QPainter.Antialiasing)
police = QFont("Arial")
police.setBold(True)
police.setPixelSize(140)
p.setFont(police)
p.setPen(QColor(250, 210, 40))
p.drawText(QRectF(0, 0, 900, 500), Qt.AlignCenter, "DISCO")
p.end()
doc = charger(img, "disco.png")
a = tableau(doc.image.convertToFormat(FORMAT_IMAGE))[..., :3].astype(int)
lettres = np.abs(a - [30, 60, 120]).sum(-1) > 90
ys, xs = np.nonzero(lettres)
doc.selection = _masque_vers_selection(np.where(lettres, 255, 0).astype(np.uint8)).convertToFormat(
    doc.selection.format())
from pixane import lecture_texte


def faux_polices(self):
    self.show()
    t0 = time.time()
    if not self.texte.text():
        while time.time() - t0 < 30 and not self.texte.text():
            app.processEvents()
            time.sleep(0.05)
        if not self.texte.text():                 # Windows sans lecture des lettres : on les tape
            self.texte.setText("DISCO")
            self.chercher()
    while time.time() - t0 < 120 and (not self.resultats or self.progres.isVisible()):
        app.processEvents()
        time.sleep(0.05)
    verifier(self.remplacer and not self.b_creer.isVisible() and self.b_remplacer.isVisible(),
             "Remplacer un texte : fenêtre en mode remplacer")
    self.liste.setCurrentRow(0)
    verifier(not self.b_remplacer.isEnabled(), "sans nouveau texte : bouton grisé")
    self.nouveau.setText("FUNK")
    self.grab().save(str(sortie / "remplacer_fenetre.png"))
    self._finir("remplacer")
    return self.result()


dp.FenetrePolices.exec = faux_polices
lances = []


def faux_lancer(*a, ensuite=None, **k):
    lances.append(int((tableau(f.doc.selection)[..., 3] > 127).sum()))
    ensuite()


f._lancer = faux_lancer
f.ia_remplacer_texte()
app.processEvents()
t = doc.calque_actif.texte
verifier(t is not None and t.texte == "FUNK" and t.couleur.lower() == "#fffad228",
         f"texte posé, même couleur ({t.couleur if t else None})")
e = transformation(t).map(forme(t)[0]).boundingRect()
verifier(abs(e.top() - ys.min()) <= 3 and abs(e.bottom() - ys.max()) <= 3,
         f"même hauteur que les anciennes lettres ({e.top():.0f}-{e.bottom():.0f} / {ys.min()}-{ys.max()})")
verifier(abs(e.center().x() - (xs.min() + xs.max()) / 2) <= 3, "centré sur l'ancien texte")
verifier(lances and lances[0] > lettres.sum() * 1.1, "zone effacée plus large que les lettres (bord compris)")
verifier(f.historique.undoText() == "Remplacer un texte", "nouveau texte : une étape d'Annuler")
doc.modifie = False

# ------------------------------------------------------------------ Effacer d'un clic (SAM simulé)
H, W = 400, 600
yy, xx = np.mgrid[0:H, 0:W]
fond = np.zeros((H, W, 3), np.uint8) + np.array([90, 140, 200], np.uint8)
disque = (xx - 300) ** 2 + (yy - 200) ** 2 < 60 ** 2
fond[disque] = [220, 40, 40]
doc = charger(QImage(np.ascontiguousarray(fond).data, W, H, W * 3, QImage.Format_RGB888).copy(), "disque.png")
recettes._sam["fichier"] = recettes.SAM


def faux_envoi(png):
    faux_envoi.taille = Image.open(io.BytesIO(png)).size
    return "essai.png"


def faux_sam(prompt, sorties, annuler, progres, *a):
    w, h = faux_envoi.taille
    im = Image.new("L", (w, h), 0)
    e = w / W
    ImageDraw.Draw(im).ellipse([(300 - 60) * e, (200 - 60) * e, (300 + 60) * e, (200 + 60) * e], fill=255)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return [("Objet", buf.getvalue())]


f.moteur.envoyer_image = faux_envoi
f.moteur.executer = faux_sam
effaces = []
f.ia_effacer = lambda: effaces.append(int((tableau(f.doc.selection)[..., 3] > 127).sum()))
f.selection_auto.f.ia_effacer = f.ia_effacer
f._choisir_outil(EFFACER_CLIC)
c = f.canevas
QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, c.vers_ecran(QPointF(300, 200)).toPoint())
t0 = time.time()
while not effaces and time.time() - t0 < 20:
    app.processEvents()
    time.sleep(0.02)
verifier(bool(effaces) and effaces[0] > disque.sum(), f"Effacer d'un clic : objet détouré avec une marge, puis Effacer "
                                                      f"({effaces[0] if effaces else 0} > {disque.sum()} pixels)")
verifier(f.historique.undoText() == "Effacer d'un clic", "la zone trouvée est une étape d'Annuler")
doc.modifie = False

# ------------------------------------------------------------------ Yeux rouges
img = np.zeros((H, W, 3)) + [225, 180, 150]
for cx in (200, 400):
    img[(xx - cx) ** 2 / 50 ** 2 + (yy - 200) ** 2 / 25 ** 2 < 1] = [240, 240, 235]
    img[(xx - cx) ** 2 + (yy - 200) ** 2 < 22 ** 2] = [80, 120, 70]
    img[(xx - cx) ** 2 + (yy - 200) ** 2 < 11 ** 2] = [210, 30, 35]
    img[(xx - cx - 3) ** 2 + (yy - 197) ** 2 < 3 ** 2] = [255, 255, 255]
img = np.ascontiguousarray(np.clip(img, 0, 255).astype(np.uint8))
doc = charger(QImage(img.data, W, H, W * 3, QImage.Format_RGB888).copy(), "yeux.png")
f._choisir_outil(YEUX)
QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, c.vers_ecran(QPointF(200, 200)).toPoint())
r0, r1 = c.vers_ecran(QPointF(350, 170)).toPoint(), c.vers_ecran(QPointF(450, 230)).toPoint()
QTest.mousePress(c, Qt.LeftButton, Qt.NoModifier, r0)
QTest.mouseMove(c, r1)
QTest.mouseRelease(c, Qt.LeftButton, Qt.NoModifier, r1)
app.processEvents()
a = tableau(doc.image.convertToFormat(FORMAT_IMAGE))[..., :3].astype(int)
for cx, comment in ((200, "clic"), (400, "cadre")):
    pup = a[195:205, cx - 8:cx - 3].reshape(-1, 3).mean(0)
    verifier(pup.max() < 60 and a[197, cx + 3].min() > 240 and abs(a[200, cx - 17] - [80, 120, 70]).max() < 3,
             f"yeux rouges ({comment}) : pupille sombre {pup.round()}, reflet et iris gardés")
n = f.historique.count()
QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, c.vers_ecran(QPointF(300, 330)).toPoint())
verifier(f.historique.count() == n, "clic sur la peau : rien ne change")
doc.modifie = False

# ------------------------------------------------------------------ Correction de l'objectif
from pixane import filtres
verifier("correction" in filtres.FILTRES and hasattr(f, "a_filtre_correction"), "Filtres > Correction de l'objectif")
grille = np.full((300, 400, 4), 255, np.uint8)
gy, gx = np.mgrid[0:300, 0:400]
grille[(gx % 40 < 2) | (gy % 40 < 2), :3] = 0
for d in (-60, 60):
    r = filtres.correction_objectif(grille, {"deformation": d, "vignetage": 0, "franges": 0})
    verifier(r[..., 3].min() == 255 and not np.array_equal(r, grille), f"déformation {d} : aucun coin vide")
gris = np.zeros((300, 400, 4), np.uint8) + np.array([128, 128, 128, 255], np.uint8)
v = filtres.correction_objectif(gris, {"deformation": 0, "vignetage": 50, "franges": 0})
verifier(v[150, 200, 0] == 128 and v[0, 0, 0] > 180, "vignetage : coins éclaircis, centre inchangé")

# ------------------------------------------------------------------ Comparer avant / après
doc = f.doc
avant = QImage(doc.image)
b = tableau(doc.calques[0].image.convertToFormat(FORMAT_IMAGE)).copy()
b[..., :3] = 255 - b[..., :3]
from pixane.document import FORMAT_CALQUE, qimage_rgba
f.historique.push(fe.CommandeEtat(doc, doc.etat(), doc.etat_calque_modifie(
    0, image=qimage_rgba(b).convertToFormat(FORMAT_CALQUE)), "inverse"))
f.a_comparer.trigger()
app.processEvents()
verifier(c.comparer and tableau(doc.image_ouverture)[200, 200, 0] != tableau(doc.image)[200, 200, 0],
         "avant / après : rideau ouvert, photo d'ouverture gardée")
pt = c.vers_ecran(QPointF(W * 0.25, 200)).toPoint()
n = f.historique.count()
QTest.mousePress(c, Qt.LeftButton, Qt.NoModifier, pt)
QTest.mouseRelease(c, Qt.LeftButton, Qt.NoModifier, pt)
verifier(abs(c.rideau - 0.25) < 0.02 and f.historique.count() == n, "glisser : le rideau bouge, l'image ne change pas")
ecran = c.grab().toImage()
g = c.vers_ecran(QPointF(W * 0.1, 100)).toPoint()
dr = c.vers_ecran(QPointF(W * 0.9, 100)).toPoint()
verifier(QColor(ecran.pixel(g)).red() > 150 and QColor(ecran.pixel(dr)).red() < 100,
         "à gauche la photo d'avant, à droite la photo actuelle")
c.grab().save(str(sortie / "avant_apres.png"))
QTest.keyClick(c, Qt.Key_Escape)
verifier(not c.comparer and not f.a_comparer.isChecked(), "Échap : rideau fermé")

# ------------------------------------------------------------------ aperçu des propositions = ce qui sera posé
from pixane.document import dans_zone, poids_zone
base = QImage(200, 100, QImage.Format_RGB32)
base.fill(QColor(0, 0, 255))
res = QImage(200, 100, QImage.Format_RGB32)
res.fill(QColor(255, 0, 0))
zone = np.zeros((100, 200), np.uint8)
zone[30:70, 20:80] = 255
v = tableau(dans_zone(res, base, poids_zone(zone, 200, 100)).convertToFormat(FORMAT_IMAGE))
verifier(tuple(v[50, 50, :3]) == (255, 0, 0) and tuple(v[50, 150, :3]) == (0, 0, 255),
         "aperçu des propositions : l'IA dans la zone, l'original ailleurs (comme à l'application)")

for d in list(f.documents):
    d.modifie = False
f.close()
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
