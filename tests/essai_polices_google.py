"""Polices gratuites Google Fonts dans « Trouver une police semblable » : mémoire des polices Google (dossier déjà
téléchargé : %LOCALAPPDATA%\\Pixane\\polices-google, ou PIXANE_POLICES_GOOGLE), recherche qui les trouve (marquées
« pas installée »), option désactivée -> pas comparées, fenêtre (libellé, bouton Télécharger et installer ;
l'installation dans Windows est simulée), option du menu et des Préférences, dossier effacé quand on décoche.
Sans le dossier téléchargé : seulement les essais qui n'en ont pas besoin.
Usage : essai_polices_google.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QImage, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_polices_google")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane import polices_google as pg, polices_semblables as ps
from pixane.selection_texte import Analyse

vrai = Path(os.environ.get("PIXANE_POLICES_GOOGLE") or
            Path(os.environ["LOCALAPPDATA"]) / "Pixane" / "polices-google")
pg.dossier = lambda: vrai                        # lecture seule : le dossier déjà téléchargé
pg.active = lambda: True
mem = pg.memoire()
installees = set(ps.familles())
petite = [x for x in ("Times New Roman", "Arial", "Georgia", "Impact", "Verdana", "Tahoma") if x in installees]

if not mem:
    print("(dossier des polices Google absent : essais de recherche sautés)")
else:
    verifier(len(mem) > 1500 and all(len(v) == 7 and v[5] for v in list(mem.values())[:50]),
             f"mémoire des polices Google : {len(mem)} polices, avec identifiant et licence")
    # une police Google bien reconnaissable, pas installée sur ce PC
    choix = [f for f in ("Abril Fatface", "Lobster", "Bebas Neue", "Righteous", "Pacifico", "Alfa Slab One",
                         "Bungee", "Cinzel", "Playfair Display", "Oswald") if f in mem and f not in installees]
    verifier(bool(choix), f"polices Google d'essai pas installées : {choix[:3]}")
    for fam in choix[:3]:
        ident = pg.source(fam)[0]
        idq = QFontDatabase.addApplicationFont(str(vrai / "normal" / f"{ident}.ttf"))
        nom = QFontDatabase.applicationFontFamilies(idq)[0]
        f = QFont(nom)
        f.setPixelSize(64)
        f.setLetterSpacing(QFont.PercentageSpacing, 125)
        texte = "COLDPLAY"
        fm = QFontMetrics(f)
        w, h = fm.horizontalAdvance(texte) + 80, fm.height() + 40
        img = QImage(w, h, QImage.Format_RGB888)
        img.fill(QColor(20, 25, 40))
        p = QPainter(img)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, texte)
        p.end()
        QFontDatabase.removeApplicationFont(idq)
        a = np.frombuffer(img.constBits(), np.uint8).reshape(h, img.bytesPerLine())[:, :w * 3].reshape(h, w, 3)
        m = Analyse(a.copy()).calculer()
        res = ps.chercher(m, texte, 5, liste=petite)
        noms = [(r.famille, r.google) for r in res]
        rang = next((k for k, r in enumerate(res) if r.famille == nom and r.google == ident and r.licence), None)
        lie = fam in ("Lobster", "Pacifico")      # écriture liée : lettres collées, pas de comparaison lettre par lettre
        verifier(rang is not None and rang < (3 if lie else 1),
                 f"{fam} (Google, pas installée) trouvée {'dans les 3 premières' if lie else 'en premier'}, "
                 f"marquée Google ({noms[:3]})")
    pg.liberer()
    verifier(not pg._chargees, "polices Google chargées pour la recherche : retirées ensuite")
    res = ps.chercher(m, "COLDPLAY", 5, liste=petite, google={})
    verifier(all(not r.google for r in res), "option désactivée : aucune police Google comparée")

# --- mise à jour (téléchargements simulés) : nouvelle police, police modifiée, police retirée
import json
import tempfile
tmp = Path(tempfile.mkdtemp(prefix="pixane-google-maj-"))
pg_dossier = pg.dossier
pg.dossier = lambda: tmp
TTF = b"\x00\x01\x00\x00" + b"x" * 100
liste_v = [{"id": "aaa", "family": "Aaa", "subsets": ["latin"], "weights": [400], "styles": ["normal"],
            "type": "google", "category": "serif", "license": "OFL-1.1", "lastModified": "2026-01-01"},
           {"id": "bbb", "family": "Bbb", "subsets": ["latin"], "weights": [400], "styles": ["normal"],
            "type": "google", "category": "serif", "license": "OFL-1.1", "lastModified": "2026-01-01"}]
recus = []
vrai_tel = pg._telecharger_octets


def faux(url, essais=3):
    if url == pg.LISTE_URL:
        return json.dumps(liste_v).encode()
    recus.append(url.split("/fonts/")[1].split("@")[0])
    return TTF


pg._telecharger_octets = faux
pg.telecharger()
verifier(sorted(recus) == ["aaa", "bbb"], f"premier téléchargement : les 2 polices ({recus})")
recus.clear()
pg.telecharger(forcer=True)
verifier(recus == [], "rien de changé : rien retéléchargé")
liste_v[1]["lastModified"] = "2026-06-01"                           # bbb modifiée
liste_v[0] = dict(liste_v[0], id="ccc", family="Ccc")                # aaa retirée, ccc nouvelle
pg.telecharger(forcer=True)
verifier(sorted(recus) == ["bbb", "ccc"] and not (tmp / "normal" / "aaa.ttf").exists(),
         f"mise à jour : bbb (modifiée) et ccc (nouvelle) téléchargées, aaa (retirée) effacée ({recus})")
verifier(sorted(json.loads((tmp / "a_refaire.json").read_text())) == ["aaa", "bbb", "ccc"],
         "leur mémoire est notée à refaire")
pg._telecharger_octets = vrai_tel
pg.dossier = pg_dossier
import shutil
shutil.rmtree(tmp, ignore_errors=True)

# --- fenêtre : libellé et bouton (installation simulée)
from pixane.dialogue_polices import FenetrePolices
r = ps.Resultat("Abril Fatface", False, False, 77.0, google="abril-fatface", licence="OFL-1.1")
verifier("pas installée" in FenetrePolices._libelle(r) and "OFL-1.1" in FenetrePolices._libelle(r),
         "libellé : « gratuite, pas installée (Google Fonts, OFL-1.1) »")
m = np.zeros((60, 200), np.uint8)
m[10:50, 10:40] = 255
m[10:50, 60:90] = 255
d = FenetrePolices(QImage(200, 60, QImage.Format_Grayscale8), m, "AB", False)
from PySide6.QtWidgets import QListWidgetItem
it = QListWidgetItem(FenetrePolices._libelle(r))
it.setData(Qt.UserRole, r)
d.liste.addItem(it)
d.liste.setCurrentRow(0)
d.show()
verifier(d.b_installer.isVisible(), "police Google choisie : bouton « Télécharger et installer »")
appels = []
pg.installer = lambda ident, progres=None: (appels.append(ident), ("Abril Fatface", ["a.ttf", "b.ttf"]))[1]
d._finir("creer")
verifier(appels == ["abril-fatface"] and d.choisi.google == "" and d.action == "creer",
         "Créer un texte avec une police Google : installée d'abord, puis le texte")
d.close()

# --- option : menu, Préférences ; décochée -> dossier effacé (dossier d'essai)
import shutil
import tempfile
essai = Path(tempfile.mkdtemp(prefix="pixane-google-"))
(essai / "normal").mkdir()
(essai / "normal" / "x.ttf").write_bytes(b"x")
pg.dossier = lambda: essai
from pixane import polices_google
lances = []
polices_google.lancer_en_fond = lambda: lances.append(1)
from pixane.moteur import Moteur
Moteur.demarrer = lambda self, signaler=None: None
from pixane.fenetre import Fenetre
Fenetre._moteur_en_echec = lambda self, *a: None
f = Fenetre()
f.reglages.setValue("polices_google", False)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
f.a_option_google.setChecked(True)
verifier(f.reglages.value("polices_google", False, type=bool) and lances, "coché (accepté) : réglage + préparation lancée")
f.a_option_google.setChecked(False)
verifier(not essai.exists() and not f.reglages.value("polices_google", True, type=bool),
         "décoché : dossier des polices Google effacé")
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.No)
f.a_option_google.setChecked(True)
verifier(not f.a_option_google.isChecked() and not f.reglages.value("polices_google", False, type=bool),
         "coché puis téléchargement refusé : reste décoché")
f.a_option_polices.setChecked(False)
verifier(not f.a_option_google.isEnabled(), "recherche de police désactivée : option Google grisée")
f.a_option_polices.setChecked(True)
from pixane.preferences import DialoguePreferences
dp = DialoguePreferences(f)
verifier(dp.google.isEnabled() and "google" in dp.valeurs(), "Préférences : case Polices gratuites Google Fonts")
dp.close()
f.close()
shutil.rmtree(essai, ignore_errors=True)
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
