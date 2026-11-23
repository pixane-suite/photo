"""Agrandir : description facultative (écrite ou « Décrire (IA) ») — barre, recettes, sans moteur.
Usage : python tests/essai_agrandir_texte.py DOSSIER_SORTIE"""
import os
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
os.environ.setdefault("PIXANE_REGLAGES", "Pixane-essais")

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QMessageBox

sortie = Path(sys.argv[1] if len(sys.argv) > 1 else "sortie_agrandir_texte")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ERREUR  ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane import recettes
from pixane.completer_moteur import _modele_vu, manquants
from pixane.installation_moteur import catalogue
from pixane.fenetre import Fenetre

# ---- recettes
p, s = recettes.agrandir("x.png", nb=1, texte="crowd, smoke")
verifier(p["24"]["inputs"]["text"] == "crowd, smoke", "Agrandir : la description va à Flux")
p, s = recettes.agrandir("x.png", nb=1)
verifier(p["24"]["inputs"]["text"] == "", "Agrandir sans description : texte vide (comme avant)")
p, s = recettes.variante("x.png", 0.5, texte="crowd", nb=1, decoupe=False)
verifier(p["24"]["inputs"]["text"] == "crowd" and "34" in p, "Partir de celle-ci : même description")
p, s = recettes.decrire("x.png")
verifier(p["11"]["class_type"] == "CLIPLoader" and p["12"]["class_type"] == "TextGenerate"
         and p["12"]["inputs"]["image"] == ["10", 0] and list(s) == ["13"], "recette Décrire : Qwen3.5 + TextGenerate")

# ---- détection du modèle et installation
infos = {"TextGenerate": {}, "PreviewAny": {},
         "CLIPLoader": {"input": {"required": {"clip_name": [["clip_l.safetensors"]]}}}}
recettes.configurer(infos)
verifier(not recettes.description_disponible() and not _modele_vu(infos, "description"), "modèle absent : vu absent")
infos["CLIPLoader"]["input"]["required"]["clip_name"][0].append("qwen3.5_2b_bf16.safetensors")
recettes.configurer(infos)
verifier(recettes.description_disponible() and _modele_vu(infos, "description"), "modèle présent : vu présent")
cles = [e.cle for e in catalogue(True, description=True)]
verifier("description" in cles and "description" not in [e.cle for e in catalogue(True)],
         "catalogue : Qwen3.5 2B seulement si la case est cochée")
e = next(e for e in catalogue(True, description=True) if e.cle == "description")
verifier(e.taille == 4548221488 and e.licence == "Apache-2.0" and e.url.startswith("https://huggingface.co/Comfy-Org/"),
         f"élément : {e.nom}, 4,2 Go, Apache-2.0, Hugging Face Comfy-Org")
recettes.configurer({})

# ---- barre d'Agrandir
f = Fenetre()
f.resize(1300, 850)
f.show()
img = QImage(800, 500, QImage.Format_ARGB32_Premultiplied)
img.fill(QColor(90, 120, 160))
chemin = sortie / "essai.png"
img.save(str(chemin))
f.charger(str(chemin))
app.processEvents()
f.ia_agrandir()
app.processEvents()
b = f.barre_agrandir
verifier(b.isVisible() and b.texte.text() == "" and b.b_decrire.isVisible(), "barre : case Description vide + Décrire")
b.texte.setText("foule")
b.hide()
f.canevas.finir_cadre()
f.ia_agrandir()
verifier(b.texte.text() == "", "case vidée à chaque Agrandir")
b.grab().save(str(sortie / "barre.png"))
questions = []
QMessageBox.question = staticmethod(lambda *a, **k: (questions.append(a), QMessageBox.No)[1])
b.b_decrire.click()
verifier(len(questions) == 1 and "4,2 Go" in questions[0][2], "Décrire sans le modèle : propose l'installation (4,2 Go)")
f._description_auto = "an oil painting"
verifier(f._texte_agrandir("an oil painting") == "an oil painting", "description de Décrire : envoyée telle quelle")
verifier(f._texte_agrandir("") == "", "pas de description : rien")
b.hide()
f.canevas.finir_cadre()
f.close()

print("ERREURS :", erreurs if erreurs else "aucune")
sys.stdout.flush()
QTimer.singleShot(100, app.quit)
app.exec()
sys.exit(1 if erreurs else 0)
