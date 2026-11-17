"""Édition > Préférences… : onglets, valeurs reprises des menus, rien avant OK, appliqué avec les fonctions des menus,
une seule question pour la langue / la taille de l'interface ; image de chaque onglet en clair et en sombre.
Usage : python tests/essai_preferences.py DOSSIER_SORTIE"""
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
for v in ("QT_SCALE_FACTOR", "PIXANE_ECHELLE"):
    os.environ.pop(v, None)

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

sortie = Path(sys.argv[1] if len(sys.argv) > 1 else "sortie_preferences")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ERREUR  ") + texte)
    if not cond:
        erreurs.append(texte)


CLES = ("theme", "langue", "echelle_interface", "taille_icones", "barre_rapide", "pas_grille", "ia_nouveau_calque",
        "agrandir_pleine", "recuperation_minutes", "maj_auto", "dossier", "preferences/onglet")
reglages = QSettings("Pixane", os.environ["PIXANE_REGLAGES"])
avant = {c: reglages.value(c) for c in CLES}
for c, v in (("theme", "clair"), ("echelle_interface", 100), ("taille_icones", 22), ("barre_rapide", True),
             ("pas_grille", 100), ("ia_nouveau_calque", False), ("agrandir_pleine", True),
             ("recuperation_minutes", 3), ("maj_auto", False), ("preferences/onglet", 0)):
    reglages.setValue(c, v)
reglages.sync()

app = QApplication(sys.argv)
from pixane import preferences as P
from pixane.fenetre import Fenetre

f = Fenetre()
f.resize(1200, 800)
f.show()
app.processEvents()
questions = []
QMessageBox.question = staticmethod(lambda *a, **k: (questions.append(a), QMessageBox.No)[1])
verifier(f.a_preferences.shortcut().toString() == "Ctrl+,", "Édition > Préférences… (Ctrl+,)")

# ---- images de chaque onglet (clair puis sombre)
for mode in ("clair", "sombre"):
    f.changer_theme(mode)
    d = P.DialoguePreferences(f)
    d.show()
    for i in range(d.onglets.count()):
        d.onglets.setCurrentIndex(i)
        app.processEvents()
        d.grab().save(str(sortie / f"onglet{i + 1}_{mode}.png"))
    d.close()
f.changer_theme("clair")
d = P.DialoguePreferences(f)
noms = [d.onglets.tabText(i) for i in range(d.onglets.count())]
verifier(noms == ["Affichage", "Fonctions installées", "Intelligence artificielle", "Enregistrement", "Mises à jour"],
         f"5 onglets : {noms}")
verifier(d.onglets.currentIndex() == 4, "dernier onglet ouvert retenu")
v = d.valeurs()
verifier(v["theme"] == "clair" and v["echelle"] == 100 and v["icones"] == 22 and v["barre_rapide"]
         and v["grille"] == 100 and not v["nouveau_calque"] and v["pleine"] and v["recuperation"] == 3
         and not v["maj"], "valeurs reprises des réglages et des menus")
d.close()


# ---- Annuler : rien ne change
def ouvrir_avec(regler, accepter):
    def exec_(self):
        regler(self)
        return 1 if accepter else 0
    P.DialoguePreferences.exec = exec_
    f.preferences()


def tout_changer(d):
    d.theme.setCurrentIndex(d.theme.findData("sombre"))
    d.icones.setCurrentIndex(d.icones.findData(28))
    d.echelle.setCurrentIndex(d.echelle.findData(85))
    d.barre_rapide.setChecked(False)
    d.grille.setValue(40)
    d.nouveau_calque.setChecked(True)
    d.pleine.setChecked(False)
    d.recuperation.setCurrentIndex(d.recuperation.findData(0))
    d.maj.setChecked(True)


ouvrir_avec(tout_changer, False)
verifier(f.mode_theme == "clair" and f._taille_icones() == 22 and f.a_barre_rapide.isChecked() and not questions
         and f.canevas.pas_grille == 100, "Annuler : rien n'est appliqué")

# ---- OK : appliqué avec les fonctions des menus
ouvrir_avec(tout_changer, True)
app.processEvents()
r = QSettings("Pixane", os.environ["PIXANE_REGLAGES"])
verifier(f.mode_theme == "sombre" and r.value("theme") == "sombre", "thème sombre tout de suite")
verifier(f._barre_outils.iconSize().width() == 28, "icônes des outils en Grandes tout de suite")
verifier(not f.a_barre_rapide.isChecked() and r.value("barre_rapide", type=bool) is False,
         "barre d'accès rapide cachée (case du menu décochée aussi)")
verifier(f.canevas.pas_grille == 40 and int(r.value("pas_grille")) == 40, "écart de la grille")
verifier(f.a_ia_nouveau_calque.isChecked() and not f.barre_agrandir.pleine.isChecked(), "réglages de l'IA")
verifier(not f._recuperation.minuterie.isActive() and int(float(r.value("recuperation_minutes"))) == 0,
         "copie de récupération : jamais")
verifier(f.a_maj_auto.isChecked(), "mises à jour au démarrage (case du menu Aide cochée)")
verifier(int(r.value("echelle_interface")) == 85 and len(questions) == 1,
         "taille de l'interface : gardée pour le démarrage, une seule question")
coches = {nom: next(a.data() for a in g.actions() if a.isChecked())
          for nom, g in (("theme", f._actions_theme), ("echelle", f._actions_echelle), ("icones", f._actions_icones))}
verifier(coches == {"theme": "sombre", "echelle": 85, "icones": 28}, f"menus Affichage recochés : {coches}")

# ---- récupération remise
ouvrir_avec(lambda d: d.recuperation.setCurrentIndex(d.recuperation.findData(5)), True)
verifier(f._recuperation.minuterie.isActive() and f._recuperation.minuterie.interval() == 5 * 60 * 1000,
         "copie de récupération toutes les 5 min")

f.close()
for c, v in avant.items():
    if v is None:
        reglages.remove(c)
    else:
        reglages.setValue(c, v)
print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
QTimer.singleShot(100, app.quit)
app.exec()
sys.exit(1 if erreurs else 0)
