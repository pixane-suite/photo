"""Vrais calques : les pixels qui dépassent de la feuille sont gardés (coller, déplacer, transformer, peindre,
enregistrer en .piximg / ORA / PSD, zone de travail, Tout faire apparaître, taille, rotation, miroir, recadrer).
Usage : essai_hors_feuille.py dossier_de_sortie"""
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QEvent, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PySide6.QtWidgets import QApplication

from pixane.canevas import DEPLACER
from pixane.document import FORMAT_IMAGE, Calque, Document, image_entiere, image_vide, nouvelle_selection, rect_entier, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
erreurs = []
ROUGE, BLEU, VERT = (0, 0, 255), (255, 0, 0), (0, 255, 0)      # tableau() : B, V, R


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def couleur(img, x, y):
    return tuple(int(v) for v in tableau(img.convertToFormat(QImage.Format_ARGB32_Premultiplied))[y, x, :3])


def rect(c):
    r = rect_entier(c)
    return r.x(), r.y(), r.width(), r.height()


app = QApplication(sys.argv)
sortie = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp())
sortie.mkdir(parents=True, exist_ok=True)
f = Fenetre()
f.show()
c = f.canevas


def nouveau_doc():
    fond = QImage(200, 100, FORMAT_IMAGE)
    fond.fill(QColor(255, 255, 255))
    d = Document(fond)
    f._installer_document(d)
    return d


# 1. coller une image 400 × 200 (rouge à gauche, bleu à droite), la garder en taille réelle
doc = nouveau_doc()
grande = QImage(400, 200, FORMAT_IMAGE)
grande.fill(QColor(255, 0, 0))
p = QPainter(grande)
p.fillRect(200, 0, 200, 200, QColor(0, 0, 255))
p.end()
QApplication.clipboard().setImage(grande)
f.coller()
k = doc.calques[1]
verifier(k.hors is not None and rect(k) == (-100, -50, 400, 200), f"collée en taille réelle : calque 400 × 200 {rect(k)}")
verifier(couleur(k.image, 50, 50) == ROUGE and couleur(k.image, 150, 50) == BLEU, "la feuille montre le milieu")
# Entrée puis une autre action : rien n'est perdu ; Ctrl+T repart du calque entier
f.transformer()
verifier(c.transfo is not None and (c.transfo.bw, c.transfo.bh) == (400, 200), "Ctrl+T : le cadre entoure tout (400 × 200)")
c.transfo.sx = c.transfo.sy = 0.5
f._valider_transfo()
k = doc.calques[1]
verifier(k.hors is None and couleur(k.image, 5, 50) == ROUGE and couleur(k.image, 194, 50) == BLEU,
         "réduite à 50 % : l'image entière revient dans la feuille")
f.historique.undo()
verifier(rect(doc.calques[1]) == (-100, -50, 400, 200), "Ctrl+Z : de nouveau 400 × 200")

# 2. outil Déplacer : sortir puis revenir sans perte
doc = nouveau_doc()
carre = image_vide(200, 100)
p = QPainter(carre)
p.fillRect(10, 10, 20, 20, QColor(255, 0, 0))
p.end()
doc.calques = doc.calques + (Calque("Carré", carre),)
doc.actif = 1
doc._fusion = None
f._choisir_outil(DEPLACER)


def glisser(de, a):
    e0, e1 = c.vers_ecran(QPointF(*de)), c.vers_ecran(QPointF(*a))
    milieu = (e0 + e1) / 2
    c.event(QMouseEvent(QEvent.MouseButtonPress, e0, e0, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    for e in (milieu, e1):
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, Qt.NoModifier))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, e1, e1, Qt.LeftButton, Qt.NoButton, Qt.NoModifier))


glisser((20, 20), (-30, 20))
k = doc.calques[1]
verifier(not tableau(k.image)[:, :, 3].any() and k.hors is not None, "carré sorti de la feuille : invisible mais gardé")
r = c.rect_deplacer()
verifier(r is not None and (r.x(), r.width()) == (-40, 20), f"le cadre de Déplacer le montre hors de la feuille {r}")
glisser((-30, 20), (20, 20))
k = doc.calques[1]
verifier(couleur(k.image, 15, 15) == ROUGE and k.hors is None, "ramené : le carré est intact")

# 3. peindre (seulement dans la feuille) ne touche pas à ce qui dépasse
glisser((20, 20), (-0, 20))                       # carré à moitié dehors : x de -10 à 10
k = doc.calques[1]
verifier(k.hors is not None and couleur(k.image, 5, 15) == ROUGE, "carré à moitié dehors")
peint = QImage(k.image)
p = QPainter(peint)
p.fillRect(0, 0, 200, 100, QColor(0, 255, 0))
p.end()
apres = doc.etat_calque_modifie(1, image=peint)
doc.appliquer_etat(apres)
entiere, x, y = image_entiere(doc.calques[1])
verifier((x, y) == (-10, 0) and couleur(entiere, 5, 15) == ROUGE and couleur(entiere, 15, 15) == VERT,
         "peint en vert dans la feuille : la partie dehors reste rouge")

# 4. enregistrer et rouvrir (.piximg, ORA, PSD)
for ext in (".piximg", ".ora", ".psd"):
    doc.enregistrer(sortie / f"hors{ext}")
    d2 = Document.ouvrir(sortie / f"hors{ext}")
    k2 = d2.calques[1]
    e2, x2, y2 = image_entiere(k2)
    verifier(k2.hors is not None and (x2, y2) == (-10, 0) and couleur(e2, 5, 15) == ROUGE and couleur(e2, 15, 15) == VERT,
             f"{ext} : ce qui dépasse est enregistré et relu")

# 5. Taille de la zone de travail : ce qui dépassait réapparaît
f._installer_document(doc)
avant = doc.taille()
doc.appliquer_etat(doc.etat_zone_travail(220, 100, 20, 0, None))
verifier(couleur(doc.calques[1].image, 15, 15) == ROUGE and doc.calques[1].hors is None,
         "feuille agrandie de 20 px à gauche : la partie cachée réapparaît")
doc.appliquer_etat(doc.etat_zone_travail(200, 100, -20, 0, None))
verifier(doc.calques[1].hors is not None, "feuille rognée : de nouveau gardée hors de la feuille")

# 6. Tout faire apparaître
f.tout_faire_apparaitre()
verifier(doc.taille() == (210, 100) and doc.calques[1].hors is None, f"Tout faire apparaître : {doc.taille()}")
f.historique.undo()
verifier(doc.taille() == (200, 100) and doc.calques[1].hors is not None, "Ctrl+Z")
f.tout_faire_apparaitre()
f.historique.undo()

# 7. taille de l'image, miroir, rotation : ce qui dépasse suit
doc.appliquer_etat(doc.etat_taille(100, 50))
verifier(rect(doc.calques[1]) == (-5, 0, 105, 50),
         f"taille 50 % : la partie dehors suit {rect(doc.calques[1])}")
doc.appliquer_etat(doc.etat_taille(200, 100))
doc.appliquer_etat(doc.etat_miroir(True))
r = rect_entier(doc.calques[1])
verifier(r.right() == 209, f"miroir : dépasse maintenant à droite {rect(doc.calques[1])}")
doc.appliquer_etat(doc.etat_miroir(True))
doc.appliquer_etat(doc.etat_pivote(90))
r = rect_entier(doc.calques[1])
verifier(doc.taille() == (100, 200) and r.y() == -10, f"rotation 90° : dépasse maintenant en haut {rect(doc.calques[1])}")
doc.appliquer_etat(doc.etat_pivote(-90))
verifier(rect_entier(doc.calques[1]).x() == -10, "rotation inverse : revenu")

# 8. Recadrer : ce qui est hors du cadre est supprimé
doc.appliquer_etat(doc.etat_recadre(QRect(0, 0, 150, 80)))
verifier(doc.calques[1].hors is None and doc.taille() == (150, 80), "Recadrer : le dehors est supprimé")

# 9. Ctrl+T sur une sélection d'un calque qui dépasse : le dehors (non sélectionné) reste
doc = nouveau_doc()
large = image_vide(300, 100)
p = QPainter(large)
p.fillRect(0, 0, 300, 100, QColor(0, 0, 255))
p.fillRect(150, 40, 20, 20, QColor(255, 0, 0))
p.end()
doc.calques = doc.calques + (Calque("Large", image_vide(200, 100)),)
doc.actif = 1
doc._fusion = None
doc.appliquer_etat(doc.etat_calque_entier(1, large, -100, 0))
sel = nouvelle_selection(200, 100)
p = QPainter(sel)
p.fillRect(50, 40, 20, 20, QColor(0, 0, 0, 255))
p.end()
doc.selection = sel
f.transformer()
c.transfo.centre = QPointF(150, 50)
f._valider_transfo()
e, x, y = image_entiere(doc.calques[1])
verifier((x, y) == (-100, 0) and couleur(e, 10, 50) == BLEU and couleur(doc.calques[1].image, 150, 50) == ROUGE,
         "sélection transformée : le reste du calque, même dehors, ne bouge pas")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for dd in f.documents:
    dd.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
