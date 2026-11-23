"""Confort de l'outil Texte et de Nouvelle image : Ctrl+Z retire un texte posé par erreur ; double-clic (calque ou
texte de l'image) pour l'éditer ; filtre des polices par style et taille de la liste ; lettres sélectionnées
surlignées sur la photo ; couleur montrée pendant le choix (Annuler la remet) ; nouvelle image en 16 et 32 bits.
Usage : essai_texte_confort.py dossier_sortie"""
import collections
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QTextCursor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QColorDialog, QDialog

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_texte_confort")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def attendre(n=5):
    for _ in range(n):
        app.processEvents()


app = QApplication(sys.argv)
from pixane.moteur import Moteur
Moteur.demarrer = lambda self, signaler=None: None
from pixane import fenetre as fe
from pixane.canevas import RECTANGLE, TEXTE
from pixane.profondeur import bits

f = fe.Fenetre()
f.resize(1200, 800)
f.show()
img = QImage(600, 400, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(0, 0, 0))
p = str(sortie / "fond.png")
img.save(p)
f.charger(p)
attendre()
saisie = f.panneau_texte.saisie

# --- Ctrl+Z après un texte posé par erreur
f._choisir_outil(TEXTE)
n = len(f.doc.calques)
f.canevas.texte_nouveau.emit(QPointF(300, 200))
attendre()
verifier(len(f.doc.calques) == n + 1 and QApplication.focusWidget() is saisie, "clic : texte posé, saisie prête")
QTest.keyClick(saisie, Qt.Key_Z, Qt.ControlModifier)
attendre()
verifier(len(f.doc.calques) == n, "Ctrl+Z (rien tapé) : le texte posé par erreur est retiré")
f.canevas.texte_nouveau.emit(QPointF(300, 200))
attendre()
QTest.keyClicks(saisie, "Viva La Vida")
attendre()
QTest.keyClick(saisie, Qt.Key_Z, Qt.ControlModifier)
attendre()
verifier(len(f.doc.calques) == n + 1, "Ctrl+Z après avoir tapé : annule la frappe, le texte reste")
saisie.selectAll()
QTest.keyClicks(saisie, "Viva La Vida")
attendre()
it = f.doc.actif
t = f.doc.calques[it].texte

# --- double-clic
f.doc.actif = 0
f.doc.calques_changes.emit()
f._choisir_outil(RECTANGLE)
attendre()
QTest.mouseDClick(f.canevas, Qt.LeftButton, Qt.NoModifier, f.canevas.vers_ecran(QPointF(t.x, t.y)).toPoint())
attendre()
verifier(f.canevas.outil == TEXTE and f.doc.actif == it and QApplication.focusWidget() is saisie,
         "double-clic sur le texte de l'image : outil Texte, ce texte prêt à modifier")
f.doc.actif = 0
f.doc.calques_changes.emit()
f._choisir_outil(RECTANGLE)
attendre()
f.doc.actif = it
f.calques._double_clic(f.calques.liste.currentItem())
attendre()
verifier(f.canevas.outil == TEXTE and f.doc.actif == it and QApplication.focusWidget() is saisie,
         "double-clic sur le calque de texte : idem")

# --- sélection surlignée sur la photo
c = saisie.textCursor()
c.setPosition(5)
c.setPosition(7, QTextCursor.KeepAnchor)
saisie.setTextCursor(c)
attendre()
from pixane.texte import zones_lettres
z = zones_lettres(f.doc.calques[it].texte, 5, 7)
tout = zones_lettres(f.doc.calques[it].texte, 0, 12)
verifier(f.canevas.selection_lettres == (5, 7) and len(z) == 1 and len(tout) == 1
         and z[0].boundingRect().width() < tout[0].boundingRect().width() * 0.4,
         "lettres « La » sélectionnées : une bande sur la photo, plus courte que le texte entier")
f.canevas.grab().save(str(sortie / "selection.png"))

# --- couleur montrée pendant le choix
doc = f.doc
vus = []
orig = doc.apercu_calque


def dominante(im):
    c = collections.Counter(im.pixelColor(x, y).name() for x in range(0, im.width(), 3)
                            for y in range(0, im.height(), 3) if im.pixelColor(x, y).alpha() > 250)
    return c.most_common(1)[0][0] if c else ""


doc.apercu_calque = lambda i, im, texte=None: (vus.append(dominante(im)), orig(i, im, texte=texte))
saisie.selectAll()
attendre()
avant = doc.calques[it].texte
n_hist = f.historique.count()
vrai_exec = QColorDialog.exec
for ok in (False, True):
    QColorDialog.exec = lambda self, ok=ok: (self.setCurrentColor(QColor("#ff0000")),
                                             self.setCurrentColor(QColor("#00ff00")),
                                             QDialog.Accepted if ok else QDialog.Rejected)[2]
    vus.clear()
    f.panneau_texte.couleur._choisir()
    attendre()
    if not ok:
        verifier(vus[:2] == ["#ff0000", "#00ff00"] and doc.calques[it].texte == avant
                 and f.historique.count() == n_hist,
                 f"couleur essayée montrée sur la photo, Annuler remet tout ({vus})")
    else:
        verifier(f.historique.count() == n_hist + 1 and doc.calques[it].texte.style_de(0)["couleur"] == "#ff00ff00",
                 "OK : la couleur choisie est appliquée (dans Annuler)")
QColorDialog.exec = vrai_exec
doc.apercu_calque = orig

# --- liste des polices : filtre et taille
pt = f.panneau_texte
from pixane.styles_polices import style_de
pt._choisir_liste(pt.style_police, "manuscrite")
pt._choisir_liste(pt.taille_liste, "grande")
pt.police.showPopup()
attendre()
vue = pt.police.view()
vis = [pt.police.itemText(i) for i in range(pt.police.count()) if not vue.isRowHidden(i)]
verifier(0 < len(vis) < pt.police.count() / 3 and all(style_de(x) == "manuscrite" for x in vis),
         f"filtre Manuscrites : {len(vis)} polices, toutes manuscrites ({vis[:4]})")
verifier(pt.police.itemDelegate().echelle > 2 and vue.minimumWidth() >= 800, "liste Grande : aperçu agrandi")
pt.police.hidePopup()
for nom, attendu in (("Times New Roman", "serif"), ("Arial", "sans"), ("Courier New", "fixe"),
                     ("Segoe Script", "manuscrite")):
    if nom in [pt.police.itemText(i) for i in range(pt.police.count())]:
        verifier(style_de(nom) == attendu, f"style de {nom} : {style_de(nom)}")
pt._choisir_liste(pt.style_police, "")
pt._choisir_liste(pt.taille_liste, "petite")
pt.police.showPopup()
attendre()
verifier(not any(vue.isRowHidden(i) for i in range(pt.police.count())), "filtre Toutes : toutes les polices")
pt.police.hidePopup()

# --- nouvelle image 16 et 32 bits
vrai = fe.NouvelleImage.exec
for b in (16, 32, 8):
    fe.NouvelleImage.exec = lambda self, b=b: (self.bits.setCurrentIndex(self.bits.findData(b)), self.accept(), 1)[2]
    f.nouvelle_image()
    verifier(f.doc.profondeur == b and bits(f.doc.calques[0].image) == b and not f.historique.canUndo(),
             f"nouvelle image en {b} bits")
fe.NouvelleImage.exec = vrai
f.doc.modifie = False
f.close()
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
