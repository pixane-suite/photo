"""Essai de retouche_plus : repères et redressement des visages, recollage, fluidité des visages, recadrage
conseillé, document photographié, marionnette, et les commandes de la fenêtre (moteur IA simulé).
Usage : essai_retouche_plus.py [dossier de sortie]"""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

from pixane import retouche_plus as rp
from pixane.document import Document, tableau

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
sortie.mkdir(parents=True, exist_ok=True)
echecs = []


def verifier(ok, texte):
    print(("ok  " if ok else "ÉCHEC ") + texte)
    if not ok:
        echecs.append(texte)


app = QApplication.instance() or QApplication(sys.argv)
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.Ok)
QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.Ok)

# ---------------------------------------------------------------- un visage dessiné
W, H = 800, 600
rgb = np.full((H, W, 3), 170, np.uint8)
cv2.ellipse(rgb, (400, 300), (110, 150), 0, 0, 360, (225, 180, 150), -1)       # visage
for x in (355, 445):
    cv2.circle(rgb, (x, 260), 14, (40, 30, 30), -1)                             # yeux
cv2.ellipse(rgb, (400, 380), (40, 12), 0, 0, 360, (180, 50, 60), -1)            # bouche
cv2.ellipse(rgb, (400, 320), (14, 22), 0, 0, 360, (205, 160, 130), -1)         # nez
visage = np.zeros((H, W), np.uint8)
cv2.ellipse(visage, (400, 300), (110, 150), 0, 0, 360, 255, -1)
yeux = np.zeros((H, W), np.uint8)
for x in (355, 445):
    cv2.circle(yeux, (x, 260), 14, 255, -1)
cv2.circle(yeux, (700, 100), 14, 255, -1)                                       # un « œil » hors du visage
levres = np.zeros((H, W), np.uint8)
cv2.ellipse(levres, (400, 380), (40, 12), 0, 0, 360, 255, -1)
nez = np.zeros((H, W), np.uint8)
cv2.ellipse(nez, (400, 320), (14, 22), 0, 0, 360, 255, -1)

reps = rp.reperes_visages([visage], yeux, levres, nez)
v = reps[0] if reps else None
verifier(v is not None and len(v["yeux"]) == 2 and abs(v["yeux"][0][0] - 355) < 2 and v["bouche"] is not None
         and v["nez"] is not None, "repères : 2 yeux (l'autre tache ignorée), bouche, nez")
M = rp.matrice_alignement(v)
g = (M @ np.array([[355, 260, 1], [445, 260, 1]]).T).T
verifier(np.abs(g - rp.GABARIT[:2]).max() < 25, f"redressement : yeux à leur place du gabarit {g.round().tolist()}")
crop = rp.visage_redresse(rgb, M)
verifier(crop.shape == (512, 512, 3), "visage redressé en 512 × 512")
net, poids = rp.recoller_visages(rgb, [v], [M], [crop])
verifier(np.abs(net - rgb).max() < 40 and np.abs(net - rgb)[poids > 0.5].mean() < 3,
         "recollage : visage inchangé remis à sa place")
verifier(poids[300, 400] > 0.9 and poids[50, 50] == 0, "recollage : le fond n'est pas touché")
rouge = crop.copy()
rouge[..., 0] = 255
net, poids = rp.recoller_visages(rgb, [v], [M], [rouge])
verifier(net[300, 400, 0] > 250 and net[50, 50, 0] == 170, "recollage : le visage restauré remplace l'ancien")

# ---------------------------------------------------------------- fluidité
rgba = np.dstack([rgb, np.full((H, W), 255, np.uint8)])
grand = rp.deformer_visages(rgba, reps, {"yeux": 100})
sombre = lambda a: int((a[230:290, 330:380, :3].sum(-1) < 200).sum())
verifier(sombre(grand) > sombre(rgba) * 1.2, f"yeux plus grands : {sombre(rgba)} -> {sombre(grand)} px")
fin = rp.deformer_visages(rgba, reps, {"visage": 100})
large = lambda a: int((np.abs(a[330, :, :3].astype(int) - [225, 180, 150]).sum(-1) < 30).sum())
verifier(large(fin) < large(rgba) - 6, f"visage plus fin : {large(rgba)} -> {large(fin)} px de large")
sourire = rp.deformer_visages(rgba, reps, {"sourire": 100})
coin = lambda a: int(np.nonzero((a[340:420, 362, 0] > 160) & (a[340:420, 362, 1] < 90))[0].mean())
verifier(coin(sourire) < coin(rgba), f"sourire : coin de la bouche relevé ({coin(rgba)} -> {coin(sourire)})")
verifier(rp.deformer_visages(rgba, reps, dict(rp.FLUIDITE_NEUTRES)) is rgba, "tout à zéro : rien ne change")
cv2.imwrite(str(sortie / "fluidite.png"), cv2.cvtColor(np.hstack([rgba, grand, fin, sourire])[..., :3],
                                                        cv2.COLOR_RGB2BGR))

# ---------------------------------------------------------------- recadrage conseillé
sujet = np.zeros((600, 900), np.uint8)
sujet[200:450, 120:260] = 255
props = rp.cadrages(sujet, 900, 600)
dedans = all(q.x() <= 120 and q.right() >= 259 and q.y() <= 200 and q.bottom() >= 449 and q.x() >= 0
             and q.y() >= 0 and q.right() < 900 and q.bottom() < 600 for _n, q in props)
verifier(len(props) >= 4 and dedans, f"recadrages : {len(props)} propositions, sujet entier, dans l'image")
_n, q = props[0]
cx = 190
verifier(abs((cx - q.x()) / q.width() - 1 / 3) < 0.12, "règle des tiers : le sujet sur le tiers gauche")
verifier(len(rp.cadrages(None, 900, 600)) >= 3, "sans sujet trouvé : des propositions quand même")

# ---------------------------------------------------------------- document
doc_img = np.full((900, 1200, 3), 60, np.uint8)
coins_vrais = np.float32([[250, 120], [950, 180], [900, 820], [200, 760]])
feuille = np.full((700, 500, 3), 235, np.uint8)
for y in range(80, 650, 40):
    cv2.putText(feuille, "Pixane test 123", (30, y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
Mp = cv2.getPerspectiveTransform(np.float32([[0, 0], [499, 0], [499, 699], [0, 699]]), coins_vrais)
plaque = cv2.warpPerspective(feuille, Mp, (1200, 900))
masque_f = cv2.warpPerspective(np.full((700, 500), 255, np.uint8), Mp, (1200, 900))
doc_img = np.where(masque_f[..., None] > 0, plaque, doc_img)
ombre = np.tile(np.linspace(0.65, 1.0, 1200, dtype=np.float32), (900, 1))
doc_img = (doc_img * ombre[..., None]).astype(np.uint8)
coins = rp.trouver_document(doc_img)
verifier(coins is not None and np.abs(coins - coins_vrais).max() < 15, f"document : coins trouvés")
red = rp.redresser_document(doc_img, coins)
propre = rp.blanchir_document(red, "couleur")
fond = np.percentile(propre[..., 1], 60)
verifier(fond > 240 and abs(int(propre[8:28, 20:60].mean()) - int(propre[8:28, -60:-20].mean())) < 12,
         f"document : fond blanc et uni (ombre enlevée), {fond}")
nb = rp.blanchir_document(red, "noir_blanc")
verifier(set(np.unique(nb)) <= {0, 255}, "document noir et blanc : deux couleurs")
cv2.imwrite(str(sortie / "document.png"), cv2.cvtColor(propre, cv2.COLOR_RGB2BGR))

# ---------------------------------------------------------------- marionnette
m = np.zeros((300, 400, 4), np.uint8)
m[100:200, 50:350] = (255, 0, 0, 255)                     # une barre rouge
un = rp.marionnette(m, [(100, 150)], [(100, 120)])
verifier(un[80:100, 100, 3].min() == 255 and un[185:200, 100, 3].max() == 0, "une épingle : tout se déplace")
deux = rp.marionnette(m, [(60, 150), (340, 150)], [(60, 150), (340, 90)])
verifier(deux[150, 60, 3] == 255 and deux[110, 335, 3] == 255 and deux[190, 335, 3] == 0,
         "deux épingles : un bout reste en place, l'autre plie")
verifier(rp.marionnette(m, [(60, 150)], [(60, 150)]) is m, "épingle non déplacée : rien ne change")

# ---------------------------------------------------------------- la fenêtre
from pixane.fenetre import Fenetre
f = Fenetre()
f.show()
f.resize(1300, 850)
app.processEvents()
for cle in ("a_ia_visages_flous", "a_ia_fluidite_visages", "a_ia_vetements", "a_ia_nouveau_fond",
            "a_recadrage_conseille", "a_nettoyer_document", "a_marionnette"):
    a_ = getattr(f, cle, None)
    verifier(a_ is not None and any(a_ in x.menu().actions() for x in f.menuBar().actions() if x.menu()),
             f"menu : {cle}")

photo = QImage(rgb.data, W, H, W * 3, QImage.Format_RGB888).copy().convertToFormat(QImage.Format_ARGB32_Premultiplied)
f._installer_document(Document(photo))
app.processEvents()
from pixane import recettes
recettes.sam_disponible = lambda: True
recettes.visages_flous_disponible = lambda: True
recettes.restauration_disponible = lambda: True
recettes.detourage_disponible = lambda: True
f._carte_ia = lambda titre, fab, suite, **k: suite([visage, yeux, levres, nez])
reglage = {}


def dialogue_pixels(titre, panneau, neutres, calcul, **k):
    reglage["titre"], reglage["calcul"] = titre, calcul


f._dialogue_pixels = dialogue_pixels

# restaurer : le « moteur » rend chaque visage en rouge
envoyes = []


class MoteurFaux:
    etat = "prêt"

    def arreter(self):
        pass

    def envoyer_image(self, png):
        envoyes.append(png)
        return f"v{len(envoyes)}.png"

    def executer(self, prompt, sorties, annuler, progres):
        out = []
        for png in envoyes:
            a = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
            a[..., 2] = 255
            out.append(("v", cv2.imencode(".png", a)[1].tobytes()))
        return out


vrai_moteur = f.moteur
f.moteur = MoteurFaux()
f._moteur_en_fond = lambda titre, calcul, suite: suite(calcul(None, None))
f.ia_visages_flous()
ok = "calcul" in reglage
if ok:
    a = tableau(f.doc.calque_actif.image.convertToFormat(QImage.Format_RGBA8888)).copy()
    r = reglage["calcul"](a, {"force": 100})
    ok = r[300, 400, 0] > 250 and r[50, 50, 0] == 170
verifier(len(envoyes) == 1 and ok, "restaurer les visages : un visage envoyé, recollé (force 100 %)")
reglage.clear()
f.ia_fluidite_visages()
verifier("calcul" in reglage and reglage["calcul"](rgba, {"yeux": 80}) is not rgba,
         "fluidité des visages : aperçu en direct branché")

# vêtements et nouveau fond (texte) : passent par le lancement habituel de l'IA
lances = []
f._lancer = lambda titre, *a, **k: lances.append((titre, a))
c = f.ia_vetements("costume", "navy blue", 2)
verifier(c and "navy blue suit" in c and lances and lances[-1][0].startswith("Changer"), "vêtements : " + c[:50])
sujet_m = np.zeros((H, W), np.uint8)
cv2.ellipse(sujet_m, (400, 300), (110, 150), 0, 0, 360, 255, -1)
f._detourage = lambda titre, suite: suite(sujet_m)
t = f.ia_nouveau_fond("plage", None, 2)
from pixane.document import masque as m_sel
sel = m_sel(f.doc.selection)
verifier("beach" in t and lances[-1][0] == "Nouveau fond" and sel[10, 10] == 255 and sel[300, 400] == 0,
         "nouveau fond (texte) : le fond est sélectionné, Remplir lancé")
f.historique.undo()

# nouveau fond (photo)
autre = sortie / "fond.png"
QImage(300, 200, QImage.Format_RGB32).save(str(autre))
img_fond = QImage(str(autre))
img_fond.fill(QColor(0, 0, 255))
img_fond.save(str(autre))
n0 = len(f.doc.calques)
f.ia_nouveau_fond("photo", None, 1, str(autre))
vis = tableau(f.doc.image.convertToFormat(QImage.Format_RGBA8888))
verifier(len(f.doc.calques) == n0 + 2 and vis[10, 10, 2] > 240 and vis[10, 10, 0] < 20
         and np.abs(vis[300, 400, :3].astype(int) - rgb[300, 400]).max() < 6, "nouveau fond (photo) : fond bleu, sujet gardé par son masque")
f.historique.undo()
verifier(len(f.doc.calques) == n0, "Ctrl+Z enlève le nouveau fond")

# recadrage conseillé (sujet donné, premier choix)
class Choix:
    pass


f.recadrage_conseille(sujet=sujet_m, d=Choix())
verifier(f.doc.taille() != (W, H) and f.doc.taille()[0] <= W, f"recadrage conseillé appliqué : {f.doc.taille()}")
f.historique.undo()
verifier(f.doc.taille() == (W, H), "Ctrl+Z : photo entière")

# document
f._installer_document(Document(QImage(np.ascontiguousarray(doc_img).data, 1200, 900, 3600,
                                      QImage.Format_RGB888).copy()))
d = rp.DialogueDocument(doc_img, f)
nd = f.nettoyer_document(d)
verifier(nd is not None and f.doc is nd and abs(nd.taille()[0] - 702) < 20 and abs(nd.taille()[1] - 645) < 20,
         f"document nettoyé : nouvelle image {nd.taille() if nd else None}")

# marionnette sur un calque
f._installer_document(Document(QImage(np.ascontiguousarray(m).data, 400, 300, 1600,
                                      QImage.Format_RGBA8888).copy()))
f.deformation_marionnette(([(60, 150), (340, 150)], [(60, 150), (340, 90)]))
a = tableau(f.doc.calque_actif.image.convertToFormat(QImage.Format_RGBA8888))
verifier(a[110, 335, 3] == 255 and a[190, 335, 3] == 0, "marionnette : calque déformé")
f.historique.undo()
a = tableau(f.doc.calque_actif.image.convertToFormat(QImage.Format_RGBA8888))
verifier(a[190, 335, 3] == 255, "Ctrl+Z annule la marionnette")
dm = rp.DialogueMarionnette(f.doc.calque_actif.image, f)
dm.show()
app.processEvents()
dm.vue.depart, dm.vue.arrivee = [(60, 150), (340, 150)], [(60, 150), (340, 90)]
dm._apercu()
dm.vue.grab().save(str(sortie / "marionnette.png"))
verifier(dm.epingles()[1][1] == (340, 90), "fenêtre de la marionnette : épingles lues")
dm.close()

f.moteur = vrai_moteur
for d_ in list(f.documents):
    d_.modifie = False
f.close()
print()
print(f"{len(echecs)} ÉCHEC(S)" if echecs else "TOUT EST BON")
