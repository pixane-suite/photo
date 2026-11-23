"""Texte : création au clic, saisie (un seul Annuler), style, effets, déplacer / tourner à la souris, .piximg / .ora,
Agrandir / Upscale, gomme (texte -> image), verrou.
Usage : essai_texte.py dossier_sortie   (une image d'essai est fabriquée ; le moteur n'est pas démarré)"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"   # ne touche pas aux réglages de l'utilisateur
import numpy as np
from PIL import Image
from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication
from pixane.canevas import GOMME_CALQUE, TEXTE
from pixane.document import Document, qimage_rgb, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: (_ for _ in ()).throw(Exception("moteur désactivé pour l'essai"))
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
# image d'essai : dégradé
yy, xx = np.mgrid[0:800, 0:1200]
Image.fromarray(np.dstack([xx * 255 // 1200, yy * 255 // 800, np.full_like(xx, 140)]).astype(np.uint8)).save(
    sortie / "fond.png")

app = QApplication(sys.argv)
from pixane.fenetre import reglages
reglages().remove("texte_defaut")              # partir du style par défaut
f = Fenetre()
f.resize(1440, 920)
f.show()
f.charger(str(sortie / "fond.png"))
app.processEvents()
doc, c, pt_ = f.doc, f.canevas, f.panneau_texte
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def souris(points, modif=Qt.NoModifier):
    """Appuyer sur le premier point (image), glisser par les suivants, lâcher sur le dernier."""
    ecran = [c.vers_ecran(QPointF(*p)) for p in points]
    c.event(QMouseEvent(QEvent.MouseButtonPress, ecran[0], ecran[0], Qt.LeftButton, Qt.LeftButton, modif))
    for e in ecran[1:]:
        c.event(QMouseEvent(QEvent.MouseMove, e, e, Qt.NoButton, Qt.LeftButton, modif))
    c.event(QMouseEvent(QEvent.MouseButtonRelease, ecran[-1], ecran[-1], Qt.LeftButton, Qt.NoButton, modif))


def rgb(img):
    return tableau(img)[:, :, :3].astype(int)


original = rgb(doc.image)

# 1. outil T : clic -> nouveau calque de texte
f._choisir_outil(TEXTE)
verifier(f.dock_texte.isVisible(), "outil T -> panneau Texte visible")
souris([(600, 400)])
t = doc.calque_actif.texte
verifier(len(doc.calques) == 2 and t is not None and doc.calque_actif.nom == "Texte", "clic -> calque « Texte »")
verifier(abs(t.x - 600) < 1 and abs(t.y - 400) < 1 and t.taille == round(800 / 12), "placé au clic, taille d'après la photo")
verifier(not np.array_equal(rgb(doc.image), original), "le texte se voit")

# 2. saisie lettre par lettre : un seul Annuler
n = f.historique.count()
pt_.saisie.selectAll()
for lettre in "Bonjour":
    pt_.saisie.insertPlainText(lettre)
verifier(doc.calque_actif.texte.texte == "Bonjour" and doc.calque_actif.nom == "Bonjour", "saisie -> texte et nom suivent")
verifier(f.historique.count() == n + 1, f"saisie regroupée dans Annuler ({f.historique.count() - n} entrée)")
pt_.saisie.insertPlainText("\nPixane")
verifier(doc.calque_actif.texte.texte == "Bonjour\nPixane", "deux lignes")

# 3. style et effets
avant = rgb(doc.image)
pt_.styles["gras"].setChecked(True)
pt_.effets["contour"][0].setChecked(True)
pt_.effets["ombre"][0].setChecked(True)
pt_.effets["fond"][0].setChecked(True)
pt_.couleur.definir("#ffffcc00"); pt_.couleur.change.emit("#ffffcc00")
t = doc.calque_actif.texte
verifier(t.gras and t.contour and t.ombre and t.fond and t.couleur == "#ffffcc00", "gras, contour, ombre, fond, couleur")
verifier(not np.array_equal(rgb(doc.image), avant), "effets visibles")
verifier(pt_.defaut.gras and pt_.defaut.contour, "le prochain texte reprend le style")
pt_.courbe.setValue(120)
verifier(doc.calque_actif.texte.courbe == 120, "courbe 120°")
pt_.lettres.setValue(10)
pt_.interligne.setValue(1.5)
pt_.alignements["centre"][0].click()
t = doc.calque_actif.texte
verifier(t.lettres == 10 and t.interligne == 1.5 and t.alignement == "centre", "espacement, interligne, centré")
f.historique.undo()
verifier(doc.calque_actif.texte.alignement == "gauche" and pt_.alignements["gauche"][0].isChecked(),
         "Annuler -> alignement revenu, panneau à jour")
f.historique.redo()

# 4. déplacer et tourner à la souris
c.repaint()
t0 = doc.calque_actif.texte
souris([(t0.x, t0.y), (t0.x + 20, t0.y)])            # sans Ctrl, sur les lettres : elles sont choisies
verifier(doc.calque_actif.texte.x == t0.x and pt_.saisie.textCursor().hasSelection(),
         "glisser sur les lettres -> lettres choisies, texte pas déplacé")
souris([(t0.x, t0.y), (t0.x + 50, t0.y + 20), (t0.x + 100, t0.y + 40)], Qt.ControlModifier)
t1 = doc.calque_actif.texte
verifier(abs(t1.x - t0.x - 100) < 1 and abs(t1.y - t0.y - 40) < 1, "Ctrl + glisser -> texte déplacé")
verifier(f.historique.undoText() == "Déplacer le texte", "déplacement annulable")
_, _, poignee = c._cadre_texte_ecran(t1)
p_img = c.vers_image(poignee)
cible = (t1.x + 200, t1.y)                     # à droite du centre -> 90°
souris([(p_img.x(), p_img.y()), cible])
verifier(abs(doc.calque_actif.texte.angle - 90) < 1, f"poignée -> rotation 90° ({doc.calque_actif.texte.angle})")
c.repaint()
f.grab().save(str(sortie / "texte_fenetre.png"))

# 5. clic sur un texte existant -> choisi ; ailleurs -> nouveau texte
souris([(150, 120)])
verifier(len(doc.calques) == 3 and doc.calque_actif.texte.gras, "2e texte, avec le style du précédent")
t2 = doc.calque_actif.texte
souris([(t1.x + 100, t1.y)])                   # sur le premier texte (tourné)
verifier(doc.actif == 1 and len(doc.calques) == 3, "clic sur le 1er texte -> il est choisi")

# 6. .piximg et .ora
chr_ = sortie / "essai.piximg"
doc.enregistrer(chr_)
relu = Document.ouvrir(chr_)
verifier([x.texte for x in relu.calques] == [x.texte for x in doc.calques], ".piximg : textes gardés (modifiables)")
verifier(np.abs(rgb(relu.image) - rgb(doc.image)).max() <= 2, ".piximg : même image")
ora = sortie / "essai.ora"
doc.enregistrer(ora)
relu = Document.ouvrir(ora)
verifier(all(x.texte is None for x in relu.calques) and len(relu.calques) == 3, ".ora : textes en images")

# 7. Agrandir et Upscale simulés : les textes suivent
w, h = doc.taille()
tx = doc.calques[1].texte
grand = np.zeros((h + 50, w + 100, 3), np.uint8)
grand[50:, 100:] = rgb(doc.image)
f._appliquer_resultat(doc, qimage_rgb(grand), "Agrandir", lambda img: doc.etat_agrandi("Agrandir", img, (100, 50)))
verifier(abs(doc.calques[1].texte.x - tx.x - 100) < 0.01 and abs(doc.calques[1].texte.y - tx.y - 50) < 0.01,
         "Agrandir -> texte décalé, toujours modifiable")
W, H = doc.taille()
big = np.ascontiguousarray(np.repeat(np.repeat(rgb(doc.image), 2, 0), 2, 1).astype(np.uint8))
f._appliquer_resultat(doc, qimage_rgb(big), "Upscale")
verifier(abs(doc.calques[1].texte.taille - 2 * tx.taille) < 0.01, "Upscale -> texte redessiné 2× plus grand")
f.historique.undo()
f.historique.undo()

# 8. gomme sur un texte -> image ; Annuler -> texte
messages = []
c.refus.connect(messages.append)
doc.actif = 1
c.definir_outil(GOMME_CALQUE)
t_av = doc.calque_actif.texte
souris([(t_av.x, t_av.y)])
verifier(doc.calque_actif.texte is None and messages, "gomme -> le texte devient une image (avec message)")
f.historique.undo()
verifier(doc.calque_actif.texte == t_av, "Annuler -> de nouveau un texte")
f._texte_en_pixels()
verifier(doc.calque_actif.texte is None, "Convertir en image")
f.historique.undo()

# 9. verrou
c.definir_outil(TEXTE)
f.calques._cadenas(f.calques.liste.itemWidget(f.calques.liste.item(len(doc.calques) - 1 - doc.actif)))
verifier(doc.calque_actif.verrou, "texte verrouillé")
t_v = doc.calque_actif.texte
messages.clear()
souris([(t_v.x, t_v.y), (t_v.x + 80, t_v.y)])
verifier(doc.calque_actif.texte == t_v and messages, "verrouillé : pas de déplacement, message")
pt_.styles["italique"].setChecked(True)
verifier(not doc.calque_actif.texte.italique, "verrouillé : le panneau ne modifie rien")

# 10. outil Déplacer (V) : texte (reste modifiable) puis calque d'image (seul le calque bouge)
from pixane.canevas import DEPLACER
f.historique.undo()                            # déverrouille
c.definir_outil(DEPLACER)
doc.actif = 1
t_d = doc.calque_actif.texte
souris([(10, 10), (60, 30)])
verifier(doc.calque_actif.texte is not None and abs(doc.calque_actif.texte.x - t_d.x - 50) < 1,
         "Déplacer sur un texte -> déplacé, toujours modifiable")
doc.actif = 0
fond_avant = rgb(doc.calques[0].image.convertToFormat(doc.image.format()))
autres = [x.image for x in doc.calques[1:]]
souris([(300, 300), (340, 320)])
fond_apres = rgb(doc.calques[0].image.convertToFormat(doc.image.format()))
verifier(np.array_equal(fond_apres[100:200, 140:240], fond_avant[80:180, 100:200]), "Déplacer -> le calque d'image bouge de (40, 20)")
verifier(all(a is b for a, b in zip(autres, [x.image for x in doc.calques[1:]])), "Déplacer -> les autres calques ne bougent pas")
verifier(f.historique.undoText() == "Déplacer le calque", "déplacement du calque annulable")
f.historique.undo()
f.historique.undo()

# 11. fusion -> image
doc.actif = 1
f.calques.rafraichir()
f.calques.fusionner()
verifier(doc.calques[0].texte is None, "fusionner -> image")

print("ERREURS :", erreurs if erreurs else "aucune")
doc.modifie = False
QTimer.singleShot(200, f.close)
app.exec()
os._exit(0)
