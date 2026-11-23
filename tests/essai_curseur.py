"""Curseur du canevas : flèche visible tant qu'aucune image n'est ouverte (le rond du pinceau n'est dessiné qu'avec
une image) ; rond du pinceau (flèche cachée) une fois l'image ouverte ; flèche de nouveau après fermeture.
Usage : python tests/essai_curseur.py DOSSIER_SORTIE"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

sortie = Path(sys.argv[1] if len(sys.argv) > 1 else "sortie_curseur")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ERREUR  ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane.canevas import OUTILS_ROND, PINCEAU
from pixane.fenetre import Fenetre

f = Fenetre()
f.show()
app.processEvents()
c = f.canevas
c.definir_outil(PINCEAU) if hasattr(c, "definir_outil") else None
verifier(c.doc is None and c.cursor().shape() == Qt.ArrowCursor,
         f"sans image : flèche visible (outil {c.outil}, curseur {c.cursor().shape()})")
img = QImage(400, 300, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(120, 140, 160))
img.save(str(sortie / "essai.png"))
f.charger(str(sortie / "essai.png"))
app.processEvents()
if c.outil in OUTILS_ROND:
    verifier(c.cursor().shape() == Qt.BlankCursor, "avec une image et le pinceau : rond du pinceau (flèche cachée)")
c.definir_document(None)
app.processEvents()
if c.doc is not None:
    c.definir_document(None)
verifier(c.cursor().shape() == Qt.ArrowCursor, "image fermée : flèche de nouveau")
print("ERREURS :", erreurs if erreurs else "aucune")
f.close()
sys.exit(1 if erreurs else 0)
