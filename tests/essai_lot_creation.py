"""Lot « création » : styles de texte ajoutés, Couleurs d'une autre image, filigrane à l'export.
Usage : essai_lot_creation.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QDialog

from pixane import couleurs_reference, styles
from pixane.document import FORMAT_IMAGE, tableau
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


sortie = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
sortie.mkdir(parents=True, exist_ok=True)
app = QApplication(sys.argv)

# 1. styles de texte
noms = [n for n, _s in styles.styles_prets()]
nouveaux = ["Ombre longue", "Contour double", "Arc-en-ciel", "Glitch", "Rétro 80", "Argent", "Glace", "Bande dessinée"]
verifier(all(n in noms for n in nouveaux) and len(noms) >= 22, f"{len(noms)} styles prêts, dont les 8 nouveaux")


def image(couleur, bruit=0):
    rng = np.random.default_rng(2)
    t = np.zeros((120, 160, 4), np.uint8)
    t[..., :3] = np.clip(np.array(couleur) + rng.normal(0, 25, (120, 160, 3)) * bruit, 0, 255)
    t[..., 3] = 255
    return t


# 2. Couleurs d'une autre image : calcul
bleue, orange = image((60, 90, 170), 1), image((230, 140, 50), 0.6)
ref = couleurs_reference.statistiques(orange)
r = couleurs_reference.transferer(bleue, {"ref": ref, "force": 100, "lumiere": 100})
moy = r[..., :3].reshape(-1, 3).mean(0)
verifier(abs(moy[0] - 230) < 25 and abs(moy[2] - 50) < 25 and r.dtype == np.uint8,
         f"photo bleue + référence orange : elle devient orange ({moy.round()})")
r0 = couleurs_reference.transferer(bleue, {"ref": ref, "force": 0, "lumiere": 50})
verifier(np.abs(r0.astype(int) - bleue.astype(int)).max() <= 2, "force 0 : rien ne change")
rf = couleurs_reference.transferer(bleue.astype(np.float32), {"ref": ref, "force": 100, "lumiere": 50})
verifier(rf.dtype == np.float32, "calque 16 / 32 bits : calcul en nombres flottants")

# 3. dans la fenêtre : deux photos ouvertes, la 2e sert de référence
f = Fenetre()
f.show()
for nom, t in (("ref.png", orange), ("photo.png", bleue)):
    QImage(t.data, 160, 120, 160 * 4, FORMAT_IMAGE).copy().save(str(sortie / nom))
    f.charger(str(sortie / nom))
app.processEvents()


def valider():
    for w in app.topLevelWidgets():
        if isinstance(w, QDialog) and w.isVisible():
            w.accept()
            return
    QTimer.singleShot(200, valider)


QTimer.singleShot(1500, valider)
f.couleurs_autre_image()
moy = tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[..., :3].reshape(-1, 3).mean(0)
verifier(moy[0] > 150 and moy[2] < 110, f"Image > Réglages > Couleurs d'une autre image : appliqué ({moy.round()})")
f.historique.undo()
moy = tableau(f.doc.calques[0].image.convertToFormat(FORMAT_IMAGE))[..., :3].reshape(-1, 3).mean(0)
verifier(moy[2] > 140, "Ctrl+Z : couleurs d'origine")

# 4. filigrane
from PIL import Image
from pixane import export, filigrane
f.reglages.remove("filigrane")
reglage = dict(filigrane.charger(f.reglages), texte="© chrypox", taille=40, opacite=100, couleur="#ff00ff",
               position="bas_droite", actif=True)
filigrane.enregistrer(f.reglages, reglage)
grise = Image.new("RGB", (400, 300), (128, 128, 128))
avec = np.asarray(filigrane.appliquer(grise, reglage)).astype(int)
diff = np.abs(avec - 128).sum(2) > 30
ys, xs = np.where(diff)
verifier(diff.any() and xs.min() > 200 and ys.min() > 200 and avec.shape == (300, 400, 3),
         f"filigrane texte en bas à droite ({xs.min() if diff.any() else '-'}, {ys.min() if diff.any() else '-'})")
rose = (avec[..., 0] > 200) & (avec[..., 1] < 80) & (avec[..., 2] > 200)
verifier(rose.sum() > 200, "couleur du texte : magenta")
mos = np.asarray(filigrane.appliquer(grise, dict(reglage, mosaique=True, taille=20))).astype(int)
verifier((np.abs(mos - 128).sum(2) > 30)[:150, :200].any(), "Répété sur toute l'image : aussi en haut à gauche")
logo = QImage(50, 50, QImage.Format_ARGB32)
logo.fill(0xFF00FF00)
logo.save(str(sortie / "logo.png"))
vert = np.asarray(filigrane.appliquer(grise, dict(reglage, genre="image", image=str(sortie / "logo.png"),
                                                  position="haut_gauche", marge=0, taille=25))).astype(int)
verifier(tuple(vert[5, 5]) == (0, 255, 0) and tuple(vert[150, 300]) == (128, 128, 128),
         "logo (image) en haut à gauche, 25 % de la largeur")
f.doc.exporter(sortie / "export.jpg", filigrane=reglage)
lu = np.asarray(Image.open(sortie / "export.jpg").convert("RGB")).astype(int)
verifier(((lu[..., 0] > 180) & (lu[..., 1] < 100) & (lu[..., 2] > 180)).sum() > 20, "Exporter sous : filigrane ajouté")
f.doc.exporter(sortie / "sans.jpg")
lu = np.asarray(Image.open(sortie / "sans.jpg").convert("RGB")).astype(int)
verifier(((lu[..., 0] > 180) & (lu[..., 1] < 100) & (lu[..., 2] > 180)).sum() == 0, "sans réglage : pas de filigrane")
moy = tableau(f.doc.image.convertToFormat(FORMAT_IMAGE))[..., :3].reshape(-1, 3).mean(0)
verifier(moy[2] > 140, "la photo ouverte n'a pas changé")
d = export.DialogueExport(f, Image.fromarray(bleue).convert("RGBA"), "x")
verifier(d.filigrane.isChecked(), "Exporter pour le web : case « Ajouter le filigrane » cochée")
donnees, _t = d.octets()
import io
lu = np.asarray(Image.open(io.BytesIO(donnees)).convert("RGB")).astype(int)
verifier(((lu[..., 0] > 160) & (lu[..., 1] < 110) & (lu[..., 2] > 160)).sum() > 10, "Exporter pour le web : filigrane dans le fichier")
d.close()
(sortie / "lot").mkdir(exist_ok=True)
QImage(bleue.data, 160, 120, 160 * 4, FORMAT_IMAGE).copy().save(str(sortie / "lot" / "a.png"))
cible = export.traiter_une(sortie / "lot" / "a.png", sortie / "lot_sortie", {"format": "png", "filigrane": reglage})
lu = np.asarray(Image.open(cible).convert("RGB")).astype(int)
verifier(((lu[..., 0] > 160) & (lu[..., 1] < 110) & (lu[..., 2] > 160)).sum() > 10, "Traitement par lot : filigrane ajouté")
dlg = filigrane.DialogueFiligrane(f, f.doc.image)
dlg.show()
app.processEvents()
dlg._dessiner()
dlg.grab().save(str(sortie / "filigrane.png"))
dlg.close()
f.reglages.remove("filigrane")

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in list(f.documents):
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
