"""Outils ajoutés : pipette, sélection elliptique, lasso magnétique, Pièce, loupe, rotation de la vue, règle (et
Redresser), crayon, pinceau mélangeur, peinture en symétrie, Déplacer un objet (sans IA : on vérifie l'appel).
Usage : essai_outils_plus.py [dossier_sortie]"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWidgets import QApplication

from pixane import outils_plus as op
from pixane.canevas import PEINTURE
from pixane.document import FORMAT_IMAGE, Document, masque, qimage_rgb, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
f = Fenetre()
f.resize(1200, 800)
f.show()
img = np.full((300, 400, 3), 230, np.uint8)
img[:, :200] = [200, 60, 60]
img[100:200, 250:350] = [20, 20, 120]            # carré bleu foncé (lasso magnétique)
img[40:50, 290:300] = 0                          # tache noire (Pièce)
rng = np.random.default_rng(1)
img[:70, 200:] = np.clip(img[:70, 200:].astype(int) + rng.integers(-8, 9, (70, 200, 1)), 0, 255)   # grain
doc = Document(qimage_rgb(img))
f._installer_document(doc)
c = f.canevas
app.processEvents()


def souris(genre, pt_image, mod=Qt.NoModifier, bouton=Qt.LeftButton):
    p = c.vers_ecran(QPointF(*pt_image))
    if c.angle_vue:                                     # position réelle à l'écran
        p = c._transfo_vue().map(p)
    t = {"p": QEvent.MouseButtonPress, "m": QEvent.MouseMove, "r": QEvent.MouseButtonRelease,
         "d": QEvent.MouseButtonDblClick}[genre]
    b = Qt.NoButton if genre == "m" else bouton
    bs = Qt.NoButton if genre == "r" else bouton
    QApplication.sendEvent(c, QMouseEvent(t, p, c.mapToGlobal(p), b, bs, mod))


def glisser(points, mod=Qt.NoModifier):
    souris("p", points[0], mod)
    for q in points[1:]:
        souris("m", q, mod)
    souris("r", points[-1], mod)


def pixel(x, y):
    return QColor(doc.image.pixel(x, y))


def nom_couleur():
    return QColor(c.couleur_peinture).name()


pile = f.groupe_historique.activeStack()
# ---------------------------------------------------------------- boîte à outils
for o in (op.PIPETTE, op.ELLIPSE_SEL, op.LASSO_MAG, op.PIECE, op.DEPLACER_IA, op.LOUPE, op.ROTATION_VUE, op.REGLE,
          op.CRAYON, op.MELANGEUR):
    verifier(o in f._actions_outils and not f._actions_outils[o].icon().isNull(), f"outil {o} dans la boîte, avec icône")

# ---------------------------------------------------------------- pipette
f._choisir_outil(op.PIPETTE)
verifier(not f.opt_pipette.isHidden(), "pipette : options visibles")
glisser([(50, 50)])
verifier(nom_couleur() == "#c83c3c", f"pipette : couleur prise {nom_couleur()}")
f.opt_pipette_ech.setCurrentIndex(f.opt_pipette_ech.findData(31))
glisser([(200, 20)])                                    # à cheval sur deux couleurs : moyenne
m = QColor(c.couleur_peinture)
verifier(60 < m.green() < 230 and m.red() > 200, f"pipette 31×31 : moyenne {m.name()}")
f.opt_pipette_ech.setCurrentIndex(0)

# ---------------------------------------------------------------- sélection elliptique
f._choisir_outil(op.ELLIPSE_SEL)
glisser([(100, 100), (150, 130), (200, 200)])
sel = masque(doc.selection)
verifier(sel[150, 150] > 200 and sel[102, 102] < 50 and sel[150, 102] > 100,
         f"ellipse : centre {sel[150, 150]}, coin {sel[102, 102]}, bord gauche {sel[150, 102]}")
glisser([(150, 150)])
verifier(doc.selection_vide(), "ellipse : un simple clic désélectionne")

# ---------------------------------------------------------------- lasso magnétique
f._choisir_outil(op.LASSO_MAG)
for q in ((252, 102), (348, 102), (348, 198), (252, 198)):
    souris("p", q)
    souris("r", q)
c.finir_magnetique()
sel = masque(doc.selection)
verifier(sel[150, 300] > 200 and sel[150, 230] < 50 and sel[50, 300] < 50, "lasso magnétique : le carré sélectionné")
dedans = int((sel > 127).sum())
verifier(8000 < dedans < 11500, f"lasso magnétique : colle au bord ({dedans} px pour 10000)")

# ---------------------------------------------------------------- Pièce
f._modifier_selection("rien")
f._choisir_outil(op.PIECE)
glisser([(283, 33), (307, 33), (307, 57), (283, 57)])          # autour de la tache noire
verifier(not doc.selection_vide(), "Pièce : la zone entourée devient la sélection")
glisser([(295, 45), (240, 45)])                                # glissée sur le gris sain
verifier(pixel(295, 45).red() > 190, f"Pièce : tache remplacée par du gris {pixel(295, 45).name()}")
verifier(pixel(300, 150).name() == "#141478", f"Pièce : le reste intact {pixel(300, 150).name()}")
pile.undo()
f._modifier_selection("rien")

# ---------------------------------------------------------------- loupe
f._choisir_outil(op.LOUPE)
z = c.zoom
glisser([(100, 100)])
verifier(abs(c.zoom - z * 2) < 0.01, f"loupe : clic = zoom ×2 ({z:.2f} -> {c.zoom:.2f})")
glisser([(100, 100)], Qt.AltModifier)
verifier(abs(c.zoom - z) < 0.01, "loupe : Alt+clic = zoom /2")
glisser([(50, 50), (70, 60), (90, 70)])
verifier(c.zoom > z * 3, f"loupe : cadre zoomé ({c.zoom:.2f})")
centre = c.vers_image(QPointF(c.width() / 2, c.height() / 2))
verifier(abs(centre.x() - 70) < 3 and abs(centre.y() - 60) < 3,
         f"loupe : cadre au centre ({centre.x():.0f}, {centre.y():.0f})")
c.definir_zoom(z, QPointF(c.width() / 2, c.height() / 2))

# ---------------------------------------------------------------- rotation de la vue
c.definir_angle_vue(30)
app.processEvents()
f._choisir_outil(op.PIPETTE)
glisser([(50, 250)])
verifier(nom_couleur() == "#c83c3c", f"vue tournée : la pipette prend le bon endroit (rouge) {nom_couleur()}")
glisser([(380, 280)])
verifier(nom_couleur() == "#e6e6e6", f"vue tournée : la pipette prend le bon endroit (gris) {nom_couleur()}")
grab = c.grab()
verifier(not grab.isNull(), "vue tournée : le canevas se dessine")
if sortie:
    sortie.mkdir(parents=True, exist_ok=True)
    grab.save(str(sortie / "vue_tournee.png"))
f._choisir_outil(op.ROTATION_VUE)
souris("d", (200, 150))
verifier(c.angle_vue == 0, "rotation : double-clic = vue droite")
glisser([(300, 150), (300, 250)])
verifier(abs(c.angle_vue) > 5, f"rotation : glisser tourne la vue ({c.angle_vue:.0f}°)")
c.definir_angle_vue(0)
verifier(doc.image.width() == 400, "rotation de la vue : la photo ne change pas")

# ---------------------------------------------------------------- règle
f._choisir_outil(op.REGLE)
glisser([(100, 100), (200, 110)])
verifier(c.regle is not None and f.b_redresser_regle.isEnabled(), f"règle : {f.texte_regle.text()}")
a = op.angle_pour_redresser(*c.regle)
verifier(abs(a + 5.71) < 0.05, f"règle : angle pour redresser {a:.2f}")
a = op.angle_pour_redresser(QPointF(0, 0), QPointF(5, 100))
verifier(abs(abs(a) - 2.86) < 0.05, f"règle presque verticale : {a:.2f}")
n = pile.index()
f.redresser_avec_regle()
verifier(pile.index() == n + 1 and c.regle is None, "règle : Redresser tourne la photo")
pile.undo()

# ---------------------------------------------------------------- crayon (dans un nouveau calque)
pile.push(__import__("pixane.fenetre", fromlist=["CommandeEtat"]).CommandeEtat(
    doc, doc.etat(), doc.etat_nouveau_calque(), "calque"))
f._choisir_outil(op.CRAYON)
c.taille_pinceau = 1
f._couleur_peinture("#000000")
glisser([(10.5, 280.5), (35.5, 280.5), (60.5, 280.5)])
al = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))[:, :, 3]
verifier(al[280, 30] == 255 and al[279, 30] == 0 and al[281, 30] == 0, "crayon : trait d'un pixel net")
verifier(set(np.unique(al[270:290, 0:80]).tolist()) <= {0, 255}, "crayon : aucun pixel à demi transparent")

# ---------------------------------------------------------------- symétrie
f._choisir_outil(PEINTURE)
verifier(not f.opt_symetrie.isHidden(), "symétrie : option visible avec le pinceau")
f.definir_symetrie("v")
c.taille_pinceau = 10
f._couleur_peinture("#00ff00")
glisser([(20, 30), (40, 30), (60, 30)])
cal = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
verifier(cal[30, 40, 3] > 200 and cal[30, 360, 3] > 200 and cal[30, 200, 3] == 0,
         f"symétrie : trait et son reflet ({cal[30, 40, 3]}, {cal[30, 360, 3]}, {cal[30, 200, 3]})")
f.definir_symetrie("")

# ---------------------------------------------------------------- mélangeur (sur la photo)
doc.actif = 0
f._choisir_outil(op.MELANGEUR)
verifier(not f.opt_melangeur.isHidden(), "mélangeur : option Mélange visible")
f._couleur_peinture("#0000ff")
c.taille_pinceau = 20
glisser([(20, 150), (60, 150), (100, 150), (140, 150)])
apres = pixel(30, 150)
verifier(apres.blue() > 100 and apres.red() > 60, f"mélangeur : bleu mêlé au rouge {apres.name()}")

# ---------------------------------------------------------------- déplacer un objet (IA) : l'appel
appels = []
f._lancer = lambda titre, *a, **k: appels.append((titre, k.get("ensuite")))
f._modifier_selection("tout")
f._choisir_outil(op.DEPLACER_IA)
glisser([(100, 100), (150, 120)])
verifier(bool(appels) and appels[0][1] is not None, "Déplacer un objet : Effacer lancé, l'objet posé ensuite")
if appels:
    nb = len(doc.calques)
    appels[0][1]()
    verifier(len(doc.calques) == nb + 1, "Déplacer un objet : nouveau calque avec l'objet")

print()
print("TOUT EST BON" if not erreurs else f"{len(erreurs)} ÉCHEC(S)")
sys.exit(1 if erreurs else 0)
