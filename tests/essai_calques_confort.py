"""Calques, sélection, texte, Effacer : groupe déplacé d'un bloc, cadre d'un calque qui dépasse de la feuille,
Pixelliser, polices ajoutées à chaud (dossier d'essai, rien n'est installé dans Windows), lasso par points, lettres
choisies à la souris sur la photo, analyse avant Effacer (ombre, bord oublié), onglet ouvert visible.
Usage : essai_calques_confort.py dossier_sortie"""
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from dataclasses import replace

import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_calques_confort")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane import styles_polices
dossier_polices = Path(tempfile.mkdtemp(prefix="pixane-polices-"))
styles_polices._dossiers = lambda: [dossier_polices]          # polices à chaud : un dossier d'essai
from pixane.moteur import Moteur
Moteur.demarrer = lambda self, signaler=None: None
from pixane import fenetre as fe
from pixane.canevas import DEPLACER, LASSO, RECTANGLE, TEXTE
from pixane.document import _masque_vers_selection, tableau
from pixane.texte import boites_lettres, transformation

f = fe.Fenetre()
f.resize(1300, 850)
f.show()
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(0, 0, 0))
p = str(sortie / "noir.png")
img.save(p)
f.charger(p)
app.processEvents()
doc, c = f.doc, f.canevas


def ecran(x, y):
    return c.vers_ecran(QPointF(x, y)).toPoint()


def glisser(a, b, modif=Qt.NoModifier):
    QTest.mousePress(c, Qt.LeftButton, modif, a)
    QTest.mouseMove(c, b)
    QTest.mouseRelease(c, Qt.LeftButton, modif, b)
    app.processEvents()


# --- onglets de droite : l'onglet ouvert a son propre style
verifier("QMainWindow > QTabBar::tab:selected" in app.styleSheet(), "onglet ouvert (Calques, Historique…) mis en évidence")

# --- groupe : carré + texte déplacés ensemble, une seule étape dans Annuler
carre = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
carre.fill(Qt.transparent)
q = QPainter(carre)
q.fillRect(50, 50, 40, 40, QColor(255, 0, 0))
q.end()
f.historique.push(fe.CommandeEtat(doc, doc.etat(), doc.etat_nouveau_calque(carre, "carré"), "x"))
i_carre = doc.actif
f._choisir_outil(TEXTE)
c.texte_nouveau.emit(QPointF(200, 150))
app.processEvents()
i_t = doc.actif
x0 = doc.calques[i_t].texte.x
f.calques.choisis = {i_carre, i_t}
f.calques.grouper()
g = next(i for i, k in enumerate(doc.calques) if k.groupe)
doc.actif = g
f.calques.choisis = {g}
doc.calques_changes.emit()
f._choisir_outil(DEPLACER)
glisser(ecran(300, 250), ecran(330, 270))
ic = next(i for i, k in enumerate(doc.calques) if k.nom.startswith("carré"))
it = next(i for i, k in enumerate(doc.calques) if k.texte)
verifier(QColor(doc.calques[ic].image.pixel(110, 100)).name() == "#ff0000"
         and QColor.fromRgba(doc.calques[ic].image.pixel(55, 55)).alpha() == 0
         and abs(doc.calques[it].texte.x - x0 - 30) < 1 and f.historique.undoText() == "Déplacer les calques",
         "outil Déplacer sur un groupe : tout le groupe bouge (une étape)")
f.historique.undo()
verifier(abs(doc.calques[it].texte.x - x0) < 1, "Annuler : le groupe revient")

# --- Pixelliser
doc.actif = it
doc.calques_changes.emit()
f._etat_pixelliser()
verifier(f.a_pixelliser_texte.isEnabled() and not f.a_pixelliser_dynamique.isEnabled(),
         "Calque > Pixelliser : Texte possible, Objet dynamique grisé")
f.pixelliser("texte")
verifier(doc.calques[it].texte is None and f.historique.undoText() == "Pixelliser", "Pixelliser > Texte")
f.historique.undo()

# --- cadre d'un calque qui dépasse de la feuille (autre outil que Texte)
t = doc.calques[it].texte
f.historique.push(fe.CommandeEtat(doc, doc.etat(), doc.etat_texte_modifie(it, replace(t, x=-40, y=290)), "x"))
f._choisir_outil(RECTANGLE)
doc.actif = it
doc.calques_changes.emit()
verifier(c._etendue_calque(doc.calque_actif) is not None, "texte qui dépasse : cadre montré avec l'outil Rectangle")
doc.actif = 0
verifier(c._etendue_calque(doc.calque_actif) is None, "calque dans la feuille : pas de cadre")
f.historique.undo()

# --- lettres choisies à la souris sur la photo
f._choisir_outil(TEXTE)
doc.actif = it
doc.calques_changes.emit()
app.processEvents()
f.panneau_texte.saisie.selectAll()
QTest.keyClicks(f.panneau_texte.saisie, "Viva La Vida")
app.processEvents()
t = doc.calques[it].texte
b = boites_lettres(t)
tr_ = transformation(t)


def ecran_l(q):
    return c.vers_ecran(tr_.map(q)).toPoint()


glisser(ecran_l(QPointF(b[5].left() + 1, b[5].center().y())), ecran_l(QPointF(b[6].right() - 1, b[6].center().y())))
cur = f.panneau_texte.saisie.textCursor()
verifier(cur.selectedText() == "La" and doc.calques[it].texte.x == t.x,
         f"glisser sur « La » dans l'image : lettres choisies ({cur.selectedText()!r}), texte pas déplacé")
verifier(c.selection_lettres == (5, 7), "et surlignées sur la photo")
QTest.mouseDClick(c, Qt.LeftButton, Qt.NoModifier, ecran_l(b[9].center()))
app.processEvents()
verifier(f.panneau_texte.saisie.textCursor().selectedText() == "Vida", "double-clic sur un mot : le mot est choisi")
p1 = ecran_l(b[1].center())
glisser(p1, p1 + QPoint(40, 0), Qt.ControlModifier)
verifier(doc.calques[it].texte.x > t.x + 10, "Ctrl + glisser : le texte est déplacé")

# --- lasso par points
f._choisir_outil(LASSO)
f.opt_lasso.setCurrentIndex(1)
for x, y in ((100, 100), (300, 100), (300, 200)):
    QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, ecran(x, y))
QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, ecran(101, 101))
app.processEvents()
sel = tableau(doc.selection)[..., 3]
verifier(c._poly is None and sel[130, 250] > 0 and sel[180, 120] == 0 and f.historique.undoText() == "Lasso par points",
         "lasso par points : fermé par un clic sur le premier point")
for x, y in ((10, 10), (50, 10), (50, 50), (10, 60)):
    QTest.mouseClick(c, Qt.LeftButton, Qt.NoModifier, ecran(x, y))
QTest.keyClick(c, Qt.Key_Backspace)
verifier(len(c._poly) == 3, "Retour arrière : dernier point enlevé")
QTest.keyClick(c, Qt.Key_Return)
verifier(c._poly is None and tableau(doc.selection)[..., 3][30, 30] > 0, "Entrée : fermé")
f.opt_lasso.setCurrentIndex(0)

# --- polices ajoutées à chaud
src = Path(os.environ["LOCALAPPDATA"]) / "Pixane" / "polices-google" / "normal" / "lobster.ttf"
if src.is_file():
    combo = f.panneau_texte.police
    avant = combo.count()
    vues = []
    f.surveillance_polices.nouvelles.connect(vues.extend)
    shutil.copy(src, dossier_polices / "lobster.ttf")
    t0 = time.time()
    while time.time() - t0 < 8 and not vues:
        app.processEvents()
        time.sleep(0.05)
    verifier(vues == ["Lobster"] and combo.findText("Lobster") >= 0 and combo.count() == avant + 1,
             f"police copiée pendant que Pixane tourne : dans la liste ({vues})")
else:
    print("(pas de police Google téléchargée : essai des polices à chaud sauté)")

# --- analyse avant Effacer
from pixane.analyse_effacer import analyser
rng = np.random.default_rng(1)
H, W = 600, 800
yy, xx = np.mgrid[0:H, 0:W]
photo = np.stack([150 + 40 * xx / W, 170 + 20 * yy / H, 120 + 0 * xx], -1) + rng.normal(0, 4, (H, W, 3))
objet = (xx - 400) ** 2 + (yy - 280) ** 2 < 80 ** 2
ombre = ((xx - 440) ** 2 + (yy - 380) ** 2 * 4 < 110 ** 2) & ~objet
photo[ombre] *= 0.55
photo[objet] = [200, 30, 30]
photo = np.clip(photo, 0, 255).astype(np.uint8)
r = analyser(photo, (xx - 400) ** 2 + (yy - 280) ** 2 < 82 ** 2)
verifier(r.ombre is not None and (r.ombre & ombre).sum() > 0.9 * ombre.sum() and r.elargir == 0,
         "analyse : ombre trouvée, pas de bord oublié")
r = analyser(photo, (xx - 400) ** 2 + (yy - 280) ** 2 < 72 ** 2)
verifier(8 <= r.elargir <= 12, f"analyse : bord oublié de 8 px -> élargir de {r.elargir} px")
plat = np.clip(np.stack([150 + 40 * xx / W, 170 + 20 * yy / H, 120 + 0 * xx], -1) + rng.normal(0, 4, (H, W, 3)),
               0, 255).astype(np.uint8)
verifier(analyser(plat, (xx - 400) ** 2 + (yy - 280) ** 2 < 60 ** 2).vide(), "analyse : rien sur un fond uni")
from PIL import Image
pp = str(sortie / "ombre.png")
Image.fromarray(photo).save(pp)
f.charger(pp)
app.processEvents()
f.reglages.setValue("analyse_effacer", True)
m = (xx - 400) ** 2 + (yy - 280) ** 2 < 75 ** 2
f.doc.selection = _masque_vers_selection(np.where(m, 255, 0).astype(np.uint8)).convertToFormat(
    f.doc.selection.format())
lances = []
f._lancer = lambda *a, **k: lances.append(1)
vrai_exec = QDialog.exec
QDialog.exec = lambda self: QDialog.Accepted
f.ia_effacer()
s2 = tableau(f.doc.selection)[..., 3] > 127
verifier(lances and (s2 & ombre).sum() > 0.95 * ombre.sum() and s2[objet].all(),
         "Effacer : ombre et bord ajoutés à la zone, puis Effacer lancé")
QDialog.exec = lambda self: QDialog.Rejected
f.doc.selection = _masque_vers_selection(np.where(m, 255, 0).astype(np.uint8)).convertToFormat(
    f.doc.selection.format())
lances.clear()
f.ia_effacer()
verifier(not lances, "Annuler dans l'analyse : Effacer pas lancé")
QDialog.exec = vrai_exec
for d in list(f.documents):
    d.modifie = False
f.close()
shutil.rmtree(dossier_polices, ignore_errors=True)
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
