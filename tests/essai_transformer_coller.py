"""Coller une image plus grande que la photo (taille réelle, rien de perdu, Ctrl+T pour la réduire), Transformer (Ctrl+T)
seulement la sélection, et cadre à poignées de l'outil Déplacer. Usage : essai_transformer_coller.py"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from dataclasses import replace

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication

from pixane.canevas import DEPLACER, RECTANGLE
from pixane.document import FORMAT_IMAGE, Calque, Document, image_vide, nouvelle_selection, tableau
from pixane.texte import Texte
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []
ROUGE, BLEU = (0, 0, 255), (255, 0, 0)          # tableau() : ordre B, V, R, alpha


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.show()

fond = QImage(200, 100, FORMAT_IMAGE)
fond.fill(QColor(255, 255, 255))
doc = Document(fond)
f._installer_document(doc)

# 1. coller une image 800 × 400 (rouge à gauche, bleu à droite) dans une photo 200 × 100
grande = QImage(800, 400, FORMAT_IMAGE)
grande.fill(QColor(255, 0, 0))
p = QPainter(grande)
p.fillRect(400, 0, 400, 400, QColor(0, 0, 255))
p.end()
QApplication.clipboard().setImage(grande)
f.coller()
from pixane.document import rect_entier
k = doc.calques[1]
r = rect_entier(k)
verifier(len(doc.calques) == 2 and f.canevas.transfo is None, "collée sur un nouveau calque, sans cadre ni réduction")
verifier((r.x(), r.y(), r.width(), r.height()) == (-300, -150, 800, 400),
         f"taille réelle 800 × 400, centrée, ce qui dépasse est gardé ({r.x()}, {r.y()}, {r.width()}, {r.height()})")
a = tableau(k.image)
verifier(a[50, 5, 2] > 200 and a[50, 194, 0] > 200, "la feuille montre le milieu (rouge à gauche, bleu à droite)")
f.transformer()
t = f.canevas.transfo
verifier(t is not None and t.source.size() == grande.size(), "Ctrl+T : toute l'image dans le cadre")
t.sx = t.sy = 0.25
f._valider_transfo()
a = tableau(doc.calques[1].image)
verifier(a[50, 5, 2] > 200 and a[50, 194, 0] > 200 and a[50, 99, 3] == 255, "réduite à 25 % : l'image entière tient")
f.historique.undo()
f.historique.undo()
verifier(len(doc.calques) == 1, "Ctrl+Z deux fois : transformation puis collage annulés")

# 2. petite image : collée telle quelle, pas de cadre
petite = QImage(20, 10, FORMAT_IMAGE)
petite.fill(QColor(0, 255, 0))
QApplication.clipboard().setImage(petite)
f.coller()
verifier(f.canevas.transfo is None and len(doc.calques) == 2, "petite image : collée sans cadre")
f.historique.undo()

# 3. Ctrl+T avec une sélection : seul l'élément sélectionné bouge
calque = QImage(200, 100, FORMAT_IMAGE)
calque.fill(QColor(255, 255, 255))
p = QPainter(calque)
p.fillRect(10, 10, 20, 20, QColor(255, 0, 0))     # élément sélectionné
p.fillRect(150, 10, 20, 20, QColor(0, 0, 255))    # reste du calque
p.end()
doc2 = Document(calque)
f._installer_document(doc2)
sel = nouvelle_selection(200, 100)
p = QPainter(sel)
p.fillRect(5, 5, 30, 30, QColor(0, 0, 0, 255))
p.end()
doc2.selection = sel
f.transformer()
t = f.canevas.transfo
verifier(t is not None and (t.bw, t.bh) == (30, 30) and t.fond is not None, "cadre autour de la sélection seule")
t.centre = QPointF(100, 50)
f._valider_transfo()
a = tableau(doc2.calques[0].image)
verifier(tuple(a[50, 100, :3]) == ROUGE, "élément sélectionné déplacé au centre")
verifier(tuple(a[20, 20, :3]) != ROUGE and a[20, 20, 3] == 0, "sa place d'origine est vide")
verifier(tuple(a[20, 160, :3]) == BLEU, "le reste du calque n'a pas bougé")
verifier(doc2.rect_selection() is None, "sélection retirée après la transformation")
f.historique.undo()
verifier(tuple(tableau(doc2.calques[0].image)[20, 20, :3]) == ROUGE and doc2.rect_selection() is not None,
         "Ctrl+Z : élément et sélection revenus")

# 4. Ctrl+T sans sélection : tout le calque (inchangé)
doc2.selection = nouvelle_selection(200, 100)
f.transformer()
verifier(f.canevas.transfo is not None and f.canevas.transfo.fond is None and f.canevas.transfo.bw == 200,
         "sans sélection : tout le calque")
f._annuler_transfo()

# 5. outil Déplacer : cadre à poignées
c = f.canevas


def souris_ecran(points):
    c.event(QMouseEvent(QEvent.MouseButtonPress, points[0], points[0], Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for e in points[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, points[-1], points[-1], Qt.LeftButton, Qt.NoButton,
                        Qt.NoModifier))


def bbox(img):
    ys, xs = (tableau(img)[:, :, 3] > 0).nonzero()
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


fond3 = QImage(200, 100, FORMAT_IMAGE)
fond3.fill(QColor(255, 255, 255))
doc3 = Document(fond3)
carre = image_vide(200, 100)
p = QPainter(carre)
p.fillRect(20, 20, 40, 40, QColor(255, 0, 0))
p.end()
doc3.calques = doc3.calques + (Calque("Carré", carre),)
doc3.actif = 1
doc3._fusion = None
f._installer_document(doc3)
f._choisir_outil(DEPLACER)
verifier(f.opt_deplacer.isVisible() and f.c_cadre_deplacer.isEnabled(), "case « Afficher le cadre de transformation »")
verifier(c.rect_deplacer() == QRectF(20, 20, 40, 40), f"cadre autour du carré ({c.rect_deplacer()})")
points = c._points_cadre_deplacer(c.rect_deplacer())
verifier(c._sous_cadre_deplacer(points["bd"]) == "bd" and c._sous_cadre_deplacer(points["h"]) == "h",
         "poignées reconnues sous la souris")
verifier(c._sous_cadre_deplacer(points["hg"] - QPointF(14, 14)) == "tourner", "juste à l'extérieur d'un coin : tourner")
verifier(c._sous_cadre_deplacer(c.vers_ecran(QPointF(40, 40))) is None, "au milieu : déplacer (pas de poignée)")
# glisser le coin bas droit de (60, 60) à (100, 100) : le carré double
souris_ecran([points["bd"], c.vers_ecran(QPointF(80, 80)), c.vers_ecran(QPointF(100, 100))])
t = c.transfo
verifier(t is not None and abs(t.sx - 2) < 0.1 and abs(t.sy - 2) < 0.1, "poignée tirée : mode Transformer, taille x2")
f._valider_transfo()
x0, y0, x1, y1 = bbox(doc3.calques[1].image)
verifier(c.transfo is None and abs(x0 - 20) <= 1 and abs(y0 - 20) <= 1 and abs(x1 - 99) <= 2 and abs(y1 - 99) <= 2,
         f"validé : carré de 80 px, coin haut gauche fixe ({x0}, {y0}, {x1}, {y1})")
verifier(c.rect_deplacer() is not None and abs(c.rect_deplacer().width() - 80) <= 2, "le cadre suit la nouvelle taille")
f.historique.undo()
verifier(bbox(doc3.calques[1].image) == (20, 20, 59, 59), "Ctrl+Z : taille d'origine")
# glisser au milieu : simple déplacement, pas de transformation
souris_ecran([c.vers_ecran(QPointF(40, 40)), c.vers_ecran(QPointF(50, 45)), c.vers_ecran(QPointF(60, 50))])
verifier(c.transfo is None and bbox(doc3.calques[1].image) == (40, 30, 79, 69), "glisser au milieu : déplacé seulement")
f.historique.undo()
# sélection : le cadre n'entoure qu'elle
sel = nouvelle_selection(200, 100)
p = QPainter(sel)
p.fillRect(20, 20, 10, 40, QColor(0, 0, 0, 255))
p.end()
doc3.selection = sel
c.update()
verifier(c.rect_deplacer() == QRectF(20, 20, 10, 40), "avec une sélection : cadre autour de la partie sélectionnée")
doc3.selection = nouvelle_selection(200, 100)
# pas de cadre : case décochée, calque verrouillé, texte, autre outil
f.c_cadre_deplacer.setChecked(False)
verifier(c.rect_deplacer() is None and c._sous_cadre_deplacer(points["bd"]) is None, "case décochée : pas de cadre")
f.c_cadre_deplacer.setChecked(True)
doc3.calques = doc3.calques[:1] + (replace(doc3.calques[1], verrou=True),)
verifier(c.rect_deplacer() is None, "calque verrouillé : pas de cadre")
doc3.calques = doc3.calques[:1] + (replace(doc3.calques[1], verrou=False, texte=Texte(texte="A", x=40, y=40)),)
verifier(c.rect_deplacer() is None, "calque de texte : pas de cadre (il se déplace comme un texte)")
doc3.calques = doc3.calques[:1] + (replace(doc3.calques[1], texte=None),)
f._choisir_outil(RECTANGLE)
verifier(c.rect_deplacer() is None and not f.opt_deplacer.isVisible(), "autre outil : pas de cadre")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
