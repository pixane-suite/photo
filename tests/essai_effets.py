"""Effets créatifs du menu Filtres (rétro, peinture, miniature, lumière, bordures) : chaque effet garde la taille et
le type du calque (8 bits et 16 / 32 bits), change bien l'image, et se trouve dans le menu Filtres.
Usage : essai_effets.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from pixane import effets, filtres
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
rng = np.random.default_rng(1)
y, x = np.mgrid[0:180, 0:240]
t = np.zeros((180, 240, 4), np.uint8)
t[..., 0], t[..., 1], t[..., 2], t[..., 3] = x, y, 255 - x // 2, 255
t[60:120, 80:160, :3] = (250, 240, 220)
for k, f in effets.FONCTIONS.items():
    p = filtres.defauts(k)
    r = f(t, p)
    rf = f(t.astype(np.float32), p)
    change = np.abs(r.astype(int) - t.astype(int)).mean()
    verifier(r.shape == t.shape and r.dtype == np.uint8 and rf.dtype == np.float32 and change > 0.5,
             f"{effets.noms()[k]} : taille et type gardés, image changée ({change:.1f})")
r = effets.bordure(t, dict(filtres.defauts("bordure"), style=2))
verifier(r[0, 0, 3] == 0 and r[90, 120, 3] == 255, "Coins arrondis : coins transparents, centre intact")
r = effets.bordure(t, dict(filtres.defauts("bordure"), style=0))
verifier(tuple(r[175, 120, :3]) == (250, 250, 248) and tuple(r[90, 120, :3]) == tuple(t[90, 120, :3]),
         "Polaroid : bas blanc, photo intacte au milieu")
r = effets.pixel_art(t, dict(taille=10, couleurs=4))
verifier(len(np.unique(r[..., :3].reshape(-1, 3), axis=0)) <= 4 and (r[0:10, 0:10] == r[0, 0]).all(),
         "Pixel art : 4 couleurs, pixels de 10 px")

f = Fenetre()
f.show()
img = QImage(t.data, 240, 180, 240 * 4, QImage.Format_RGBA8888).copy()
img.save(str(sortie / "effets.png"))
f.charger(str(sortie / "effets.png"))
textes = []
for a in f.menuBar().actions():
    if a.menu():
        for b in a.menu().actions():
            if b.menu():
                textes += [(b.text(), c.text()) for c in b.menu().actions()]
groupes = effets.noms_groupes()
verifier((groupes["Rétro"], effets.noms()["vhs"] + "…") in textes and (groupes["Lumière"], effets.noms()["rayons"] + "…")
         in textes, "menu Filtres : sous-menus Rétro, Peinture, Lumière")
verifier(hasattr(f, "a_filtre_bordure") and hasattr(f, "a_filtre_miniature"), "Effet miniature et Bordure dans le menu")
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
for d in list(f.documents):
    d.modifie = False
f.close()
sys.exit(1 if erreurs else 0)
