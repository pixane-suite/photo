"""Confort de l'interface : panneaux déplaçables et espaces de travail, Navigateur, Info, Deuxième image, écran
d'accueil, rechercher une commande, raccourcis personnalisables, photo suivante du dossier, fichier rechargé,
plans de travail (.piximg), chercher un calque, barre contextuelle, menu rapide, masque rapide, Alt + clic droit
(taille du pinceau), régler en glissant sur un nom.
Usage : essai_interface_plus.py dossier_sortie"""
import os
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QMouseEvent
from PySide6.QtWidgets import QApplication, QDockWidget, QLabel, QMessageBox, QSlider

from pixane.canevas import PEINTURE
from pixane.document import Document, masque, qimage_rgb
from pixane.fenetre import Fenetre
from pixane.moteur import Moteur

Moteur.demarrer = lambda self, signaler=None: None
Fenetre._moteur_en_echec = lambda self, *a: None
sortie = Path(sys.argv[1])
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


def attendre(s=0.3):
    fin = time.time() + s
    while time.time() < fin:
        QApplication.processEvents()
        time.sleep(0.01)


app = QApplication(sys.argv)
f = Fenetre()
f.reglages.remove("etat_fenetre")
f.reglages.remove("espaces")
f.reglages.remove("raccourcis")
f.resize(1440, 920)
f.show()
attendre()
c = f.canevas

# ---------------------------------------------------------------- écran d'accueil
verifier(f.accueil.isVisible(), "accueil : montré sans photo")
f.grab().save(str(sortie / "accueil.png"))

dossier = sortie / "photos"
dossier.mkdir(exist_ok=True)
for i, coul in enumerate(((200, 40, 40), (40, 200, 40), (40, 40, 200))):
    a = np.zeros((300, 400, 3), np.uint8)
    a[:] = coul
    a[100:200, 150:250] = 255 - np.array(coul)
    qimage_rgb(a).save(str(dossier / f"photo{i + 1}.png"))
f.charger(str(dossier / "photo1.png"))
attendre()
verifier(not f.accueil.isVisible(), "accueil : caché avec une photo")
doc = f.doc

# ---------------------------------------------------------------- panneaux et menu Fenêtre
docks = f.findChildren(QDockWidget)
verifier(all(d.features() & QDockWidget.DockWidgetMovable for d in docks), "panneaux déplaçables")
titres = [a.text() for a in f.m_fenetre.actions()]
verifier(any("Navigateur" in t for t in titres) and any("Info" in t for t in titres), f"menu Fenêtre : {titres}")
f.a_verrou_panneaux.setChecked(True)
verifier(all(d.features() == QDockWidget.NoDockWidgetFeatures for d in docks), "verrouiller les panneaux")
f.a_verrou_panneaux.setChecked(False)
f.espace_pret("peinture")
attendre()
verifier(f.dock_nuancier.isVisible() or f.findChild(QDockWidget, "dock_nuancier") is not None, "espace Peinture")
verifier(not f.findChild(QDockWidget, "dock_intelligence_artificielle").isVisible(), "espace Peinture : sans IA")
f.enregistrer_espace("Mon espace")
f.espace_origine()
attendre()
verifier(f.findChild(QDockWidget, "dock_intelligence_artificielle").isVisible(), "disposition d'origine")
f.espace_perso("Mon espace")
attendre()
verifier(not f.findChild(QDockWidget, "dock_intelligence_artificielle").isVisible(), "espace enregistré rappelé")
f.espace_origine()

# ---------------------------------------------------------------- navigateur
f.dock_navigateur.show()
f.dock_navigateur.raise_()
attendre()
nav = f.dock_navigateur.widget()
c.definir_zoom(4, QPointF(c.width() / 2, c.height() / 2))
attendre(0.3)
verifier(abs(nav.zoom.value() - nav._pos(4)) <= 2, "navigateur : la glissière suit le zoom")
k, x0, y0 = nav._echelle()
nav._aller(QPointF(x0 + 50 * k, y0 + 50 * k))
centre = c.vers_image(QPointF(c.width() / 2, c.height() / 2))
verifier(abs(centre.x() - 50) < 2 and abs(centre.y() - 50) < 2, f"navigateur : clic = vue centrée ({centre.x():.0f})")
nav.zoom.setValue(nav._pos(1))
verifier(abs(c.zoom - 1) < 0.05, f"navigateur : glissière de zoom ({c.zoom:.2f})")
f.dock_navigateur.grab().save(str(sortie / "navigateur.png"))
c.ajuster()

# ---------------------------------------------------------------- info
f.dock_info.show()
f.dock_info.raise_()
attendre()
from PySide6.QtGui import QCursor  # noqa: E402
QCursor.setPos(c.mapToGlobal(c.vers_ecran(QPointF(200, 150)).toPoint()))
attendre(0.4)
info = f.dock_info.widget()
verifier("x 200" in info.champs["pos"].text() and info.champs["hex"].text() == "#37D7D7",
         f"info : {info.champs['pos'].text()} {info.champs['hex'].text()}")
verifier("400 × 300" in info.champs["img"].text(), f"info : image {info.champs['img'].text()}")
f.dock_info.grab().save(str(sortie / "info.png"))

# ---------------------------------------------------------------- deuxième image
f.charger(str(dossier / "photo2.png"))
attendre()
f.dock_deuxieme.show()
f.dock_deuxieme.raise_()
attendre(1.2)
p2 = f.dock_deuxieme.widget()
verifier(p2.liste.count() >= 1 and p2.vue.image is not None, f"deuxième image : {p2.liste.count()} autre(s)")
f.dock_deuxieme.hide()

# ---------------------------------------------------------------- photo suivante du dossier
nb = len(f.documents)
f.photo_du_dossier(1)
attendre()
verifier(f.doc.chemin.name == "photo3.png", f"photo suivante : {f.doc.chemin.name}")
verifier(len(f.documents) == nb, "photo suivante : l'ancienne (non modifiée) est fermée")
f.photo_du_dossier(1)
verifier(f.doc.chemin.name == "photo1.png", f"photo suivante : on repart au début ({f.doc.chemin.name})")
f.photo_du_dossier(-1)
verifier(f.doc.chemin.name == "photo3.png", "photo précédente")

# ---------------------------------------------------------------- fichier changé sur le disque
doc = f.doc
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
f._fichiers_changes()                                     # le moment de départ est noté
time.sleep(1.1)
a = np.zeros((300, 400, 3), np.uint8)
a[:] = (250, 250, 0)
qimage_rgb(a).save(str(doc.chemin))
f._fichiers_changes()
attendre()
verifier(QColor(f.doc.image.pixel(10, 10)).name() == "#fafa00", "fichier changé ailleurs : rechargé")

# ---------------------------------------------------------------- rechercher une commande
f.rechercher_commande()
attendre()
d = f._recherche_commande
d.champ.setText("pivoter 90 droite")
attendre()
verifier(d.liste.count() >= 1 and "Pivoter" in d.liste.currentItem().text(),
         f"rechercher une commande : {d.liste.currentItem().text() if d.liste.currentItem() else '-'}")
d.grab().save(str(sortie / "recherche.png"))
avant = f.doc.image.size()
d._lancer()
attendre()
verifier(f.doc.image.width() == avant.height(), "rechercher une commande : Entrée la lance (image pivotée)")
f.historique.undo()
d2 = None
f.rechercher_commande()
attendre()
f._recherche_commande.champ.setText("lasso magn")
attendre()
verifier(f._recherche_commande.liste.count() >= 1, "rechercher : les outils aussi")
f._recherche_commande.close()

# ---------------------------------------------------------------- raccourcis personnalisables
from pixane.interface_plus import DialogueRaccourcis  # noqa: E402
cmds = f._commandes()
d = DialogueRaccourcis(cmds, f._defauts_raccourcis, f)
rang = next(i for i, (ch, a) in enumerate(cmds) if a is f.a_plans)
d.table.setCurrentCell(rang, 0)
d._poser("Ctrl+Alt+J")
d.accept()
f.raccourcis_clavier.__func__  # (existe)
perso = {n: s for n, s in d.nouveaux.items() if s != f._defauts_raccourcis.get(n, "")}
f.reglages.setValue("raccourcis", __import__("json").dumps(perso))
f._appliquer_raccourcis()
verifier(f.a_plans.shortcut().toString() == "Ctrl+Alt+J", "raccourci personnalisé appliqué")
rang = next(i for i, (ch, a) in enumerate(cmds) if a is f.a_effacer)
d.table.setCurrentCell(rang, 0)
d._poser("Ctrl+Alt+J")
verifier(d.nouveaux[f.a_plans.objectName()] == "", "raccourci déjà pris : retiré à l'autre commande")
f.reglages.remove("raccourcis")
f.a_plans.setShortcut(QKeySequence())

# ---------------------------------------------------------------- plans de travail
from pixane.document import _masque_vers_selection  # noqa: E402
m = np.zeros((300, 400), np.uint8)
m[50:150, 100:300] = 255
f.doc.selection = _masque_vers_selection(m).convertToFormat(f.doc.selection.format())
from pixane.interface_plus import DialoguePlans  # noqa: E402
dp = DialoguePlans(f)
dp.ajouter()
f._modifier_selection("rien")
dp.ajouter()
verifier(f.doc.plans[0][1:] == [100, 50, 200, 100] and f.doc.plans[1][1:] == [0, 0, 400, 300],
         f"plans : {f.doc.plans}")
faits = dp.exporter(str(sortie / "plans"))  if (sortie / "plans").mkdir(exist_ok=True) is None else None
verifier(faits and (sortie / "plans" / "Plan 1.png").exists(), f"plans exportés : {faits}")
from PySide6.QtGui import QImage  # noqa: E402
verifier(QImage(str(sortie / "plans" / "Plan 1.png")).size().width() == 200, "plan exporté à sa taille")
c.update()
attendre()
c.grab().save(str(sortie / "plans.png"))
f.doc.enregistrer(sortie / "plans.piximg")
relu = Document.ouvrir(sortie / "plans.piximg")
verifier(relu.plans == f.doc.plans, "plans gardés dans le .piximg")
dp.deleteLater()

# ---------------------------------------------------------------- chercher un calque
from pixane.fenetre import CommandeEtat  # noqa: E402
for nom in ("Ciel", "Personnage", "Ombre du ciel"):
    f.historique.push(CommandeEtat(f.doc, f.doc.etat(), f.doc.etat_nouveau_calque(nom=nom), "calque"))
attendre()
f.calques.recherche.setText("ciel")
attendre()
montres = [f.calques.liste.item(i) for i in range(f.calques.liste.count()) if not f.calques.liste.isRowHidden(i)]
verifier(len(montres) == 2, f"chercher un calque : {len(montres)} montrés pour « ciel »")
f.calques.recherche.clear()

# ---------------------------------------------------------------- barre contextuelle
f.doc.selection = _masque_vers_selection(m).convertToFormat(f.doc.selection.format())
f.doc.change.emit()
attendre(0.6)
verifier(f.barre_ctx.isVisible() and f.barre_ctx._genre == "sel", "barre contextuelle : sous la sélection")
f.grab().save(str(sortie / "barre_contextuelle.png"))
f._modifier_selection("rien")
attendre(0.6)
verifier(f.barre_ctx.isVisible() and f.barre_ctx._genre == "rien", "barre contextuelle : sans sélection")
f.a_barre_ctx.setChecked(False)
attendre(0.4)
verifier(not f.barre_ctx.isVisible(), "barre contextuelle : se cache (menu Affichage)")
f.a_barre_ctx.setChecked(True)


def souris(genre, pos, bouton=Qt.LeftButton, mod=Qt.NoModifier):
    t = {"p": QEvent.MouseButtonPress, "m": QEvent.MouseMove, "r": QEvent.MouseButtonRelease}[genre]
    b = Qt.NoButton if genre == "m" else bouton
    bs = Qt.NoButton if genre == "r" else bouton
    QApplication.sendEvent(c, QMouseEvent(t, QPointF(pos), c.mapToGlobal(QPointF(pos)), b, bs, mod))


# ---------------------------------------------------------------- menu rapide
f._choisir_outil(PEINTURE)
f._couleur_peinture("#123456")
f._couleur_peinture("#abcdef")
p0 = c.vers_ecran(QPointF(200, 150))
souris("p", p0, Qt.RightButton)
souris("r", p0, Qt.RightButton)
attendre()
mr = getattr(f, "_menu_rapide", None)
verifier(mr is not None and mr.isVisible(), "menu rapide : ouvert au clic droit")
if mr is not None:
    mr.grab().save(str(sortie / "menu_rapide.png"))
    verifier(mr.couleurs[:2] == ["#abcdef", "#123456"], f"menu rapide : couleurs récentes {mr.couleurs[:3]}")
    i = next(k for k, (o, _n) in enumerate(mr.outils) if o == "pipette")
    mr.outil_choisi.emit(mr.outils[i][0])
    mr.close()
    verifier(c.outil == "pipette", "menu rapide : outil choisi")

# ---------------------------------------------------------------- Alt + clic droit : taille et dureté
f._choisir_outil(PEINTURE)
c.definir_taille(40)
souris("p", p0, Qt.RightButton, Qt.AltModifier)
souris("m", p0 + QPointF(150, 0), Qt.RightButton, Qt.AltModifier)
c.repaint()
c.grab().save(str(sortie / "taille_pinceau.png"))
souris("r", p0 + QPointF(150, 0), Qt.RightButton, Qt.AltModifier)
verifier(abs(c.taille_pinceau - 80) < 2, f"Alt + clic droit : taille doublée ({c.taille_pinceau})")
d0 = c.durete
souris("p", p0, Qt.RightButton, Qt.AltModifier)
souris("m", p0 + QPointF(0, 60), Qt.RightButton, Qt.AltModifier)
souris("r", p0 + QPointF(0, 60), Qt.RightButton, Qt.AltModifier)
verifier(c.durete < d0 and f.opt_durete.value() == round(c.durete * 100), f"Alt + clic droit : dureté {c.durete:.2f}")

# ---------------------------------------------------------------- masque rapide
f._modifier_selection("rien")
f.a_masque_rapide.setChecked(True)
verifier(c.masque_rapide and c.outil == PEINTURE, "masque rapide : actif (Maj+Q), pinceau de couleur")
f._couleur_peinture("#ffffff")
c.definir_taille(30)
c.opacite = 1.0
calque_avant = f.doc.calque_actif.image.copy()
for genre, x in (("p", 100), ("m", 150), ("m", 200), ("r", 200)):
    souris(genre, c.vers_ecran(QPointF(x, 150)))
sel = masque(f.doc.selection)
verifier(sel[150, 150] > 200 and sel[50, 150] == 0, "masque rapide : le blanc sélectionne")
verifier(f.doc.calque_actif.image == calque_avant, "masque rapide : le calque n'est pas peint")
f._couleur_peinture("#000000")
for genre, x in (("p", 150), ("r", 150)):
    souris(genre, c.vers_ecran(QPointF(x, 150)))
verifier(masque(f.doc.selection)[150, 150] < 30, "masque rapide : le noir retire")
c.repaint()
c.grab().save(str(sortie / "masque_rapide.png"))
f.a_masque_rapide.setChecked(False)
verifier(not c.masque_rapide, "masque rapide : fini")

# ---------------------------------------------------------------- régler en glissant sur un nom
f._choisir_outil(PEINTURE)
attendre()
nom = next(lab for lab in f.opt_retouche.findChildren(QLabel) if lab.text() == "Opacité")
from pixane.glisser_noms import cible  # noqa: E402
cb = cible(nom)
verifier(cb is not None, f"glisser sur un nom : « Opacité » règle {type(cb).__name__}")
if cb is not None:
    v0 = cb.value()
    cb.setValue(50)
    v0 = cb.value()
    for t, x in ((QEvent.MouseButtonPress, 0), (QEvent.MouseMove, -40), (QEvent.MouseButtonRelease, -40)):
        pos = QPointF(5 + x, 5)
        QApplication.sendEvent(nom, QMouseEvent(t, pos, nom.mapToGlobal(pos), Qt.LeftButton,
                                                Qt.NoButton if t == QEvent.MouseButtonRelease else Qt.LeftButton,
                                                Qt.NoModifier))
    verifier(cb.value() < v0, f"glisser sur un nom : valeur {v0} -> {cb.value()}")
    cb.setValue(100)                                      # réglage d'essai remis comme avant

# ---------------------------------------------------------------- plein écran
f.plein_ecran()
attendre(0.5)
verifier(f.isFullScreen(), "plein écran (F11)")
f.plein_ecran()
attendre(0.5)
verifier(not f.isFullScreen(), "plein écran : retour")

for d in list(f.documents):
    d.modifie = False
f.close()
print()
print("ERREURS :", "aucune" if not erreurs else "\n  " + "\n  ".join(erreurs))
sys.exit(1 if erreurs else 0)
