"""Police semblable, lettre par lettre : lettres espacées (« C O L D P L A Y ») et texte blanc sur fond sombre
retrouvent leur police ; découpage des lettres (lettres collées, taches du fond) ; texte en majuscules essayé ;
nombre de lettres vérifié ; mémoire des polices (chaque lettre à sa place) ; lecture des lettres par Windows.
Petite liste de polices, pour aller vite. Usage : essai_polices_lettres.py dossier_sortie"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["PIXANE_REGLAGES"] = "Pixane-essais"
import numpy as np
from PySide6.QtCore import QEventLoop, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter
from PySide6.QtWidgets import QApplication

sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("sortie_polices_lettres")
sortie.mkdir(parents=True, exist_ok=True)
erreurs = []


def verifier(cond, texte):
    print(("ok  " if cond else "ÉCHEC ") + texte)
    if not cond:
        erreurs.append(texte)


app = QApplication(sys.argv)
from pixane import lecture_texte, polices_semblables as ps
from pixane.selection_texte import Analyse

toutes = ps.familles()
petite = [x for x in ("Times New Roman", "Arial", "Georgia", "Impact", "Verdana", "Tahoma", "Segoe UI",
                      "Courier New", "Comic Sans MS", "Consolas", "Palatino Linotype", "Bookman Old Style",
                      "Century Gothic", "Garamond", "Cambria", "Constantia") if x in toutes]
verifier(len(petite) >= 8, f"polices de l'essai présentes ({len(petite)})")


def ecrire(texte, fam, espacement=0.0, gras=False, couleur=(255, 255, 255), fond=(25, 30, 45), taches=False):
    f = QFont(fam)
    f.setPixelSize(64)
    f.setBold(gras)
    f.setLetterSpacing(QFont.PercentageSpacing, 100 + espacement * 100)
    fm = QFontMetrics(f)
    w, h = fm.horizontalAdvance(texte) + 80, fm.height() + 40
    img = QImage(w, h, QImage.Format_RGB888)
    img.fill(QColor(*fond))
    p = QPainter(img)
    p.setRenderHint(QPainter.TextAntialiasing)
    if taches:                                   # restes du fond : petites taches claires au-dessus et en dessous
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(*couleur))
        for x in range(30, w - 30, 97):
            p.drawEllipse(x, 4, 5, 4)
            p.drawEllipse(x + 40, h - 8, 4, 4)
    p.setFont(f)
    p.setPen(QColor(*couleur))
    p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, texte)
    p.end()
    a = np.frombuffer(img.constBits(), np.uint8).reshape(h, img.bytesPerLine())[:, :w * 3].reshape(h, w, 3)
    return Analyse(a.copy()).calculer()


# --- mémoire des polices : chaque lettre à sa place (avant : décalée dans certaines polices, ex. Constantia)
for fam in petite:
    ps.mettre_en_memoire(fam)
mal = []
for fam in petite:
    f = QFont(fam)
    f.setPixelSize(ps.TAILLE_TRI)
    attendu = ps.glyphes_police("AMOSZ", f)
    vu = ps.glyphes_memoire("AMOSZ", fam)
    if attendu is None or vu is None or [g.shape[1] for g in attendu[0]] != [g.shape[1] for g in vu[0]]:
        mal.append(fam)
verifier(not mal, f"mémoire des polices : les bonnes lettres à leur place {mal}")

# --- découpage des lettres
m = ecrire("COLDPLAY", "Times New Roman", espacement=0.6, taches=True)
verifier(ps.compter_lettres(m) == [8], f"lettres espacées + taches du fond : 8 lettres ({ps.compter_lettres(m)})")
m = ecrire("Yellow", "Times New Roman")
verifier(len(ps.lettres_image(ps._recadrer(m / 255.0), [6])[0]) == 6, "« ll » collés : 6 lettres avec le texte tapé")
l1, l2 = ecrire("SKY", "Arial"), ecrire("STARS", "Arial")
deux = np.vstack([np.pad(l1, ((0, 0), (0, l2.shape[1] - l1.shape[1]))), l2])
verifier(ps.compter_lettres(deux) == [3, 5], f"deux lignes : 3 et 5 lettres ({ps.compter_lettres(deux)})")

# --- recherche : la vraie police en tête
cas = [("COLDPLAY", "Times New Roman", dict(espacement=0.4)),                  # blanc, espacé (pochette)
       ("COLDPLAY", "Georgia", dict(espacement=0.4)),
       ("Man In The Moon", "Palatino Linotype", dict(espacement=0.6, gras=True, couleur=(240, 220, 120))),
       ("A SKY FULL OF STARS", "Arial", dict(gras=True, couleur=(235, 200, 60))),
       ("Yellow", "Constantia", dict(couleur=(20, 20, 20), fond=(230, 150, 50)))]
for texte, fam, opt in cas:
    if fam not in petite:
        continue
    infos = {}
    res = ps.chercher(ecrire(texte, fam, **opt), texte, 5, liste=petite, infos=infos)
    noms = [r.famille for r in res]
    verifier(noms[:1] == [fam] and infos.get("lettre_par_lettre"),
             f"{texte} en {fam} {opt} : trouvée en premier, lettre par lettre ({noms[:3]})")

# --- majuscules : « Coldplay » tapé pour des lettres en majuscules -> cherché en « COLDPLAY »
infos = {}
res = ps.chercher(ecrire("COLDPLAY", "Times New Roman", espacement=0.4), "Coldplay", 3, liste=petite, infos=infos)
verifier(infos.get("texte") == "COLDPLAY" and res and res[0].famille == "Times New Roman",
         f"tapé « Coldplay » : recherche faite en « {infos.get('texte')} », Times New Roman en tête")
infos = {}
ps.chercher(ecrire("Yellow", "Georgia"), "Yellow", 3, liste=petite, infos=infos)
verifier(infos.get("texte") == "Yellow", f"vraies minuscules : le texte tapé est gardé ({infos.get('texte')})")

# --- fenêtre : lettres en noir sur blanc, case vide, avertissement si le nombre de lettres ne va pas
from pixane.dialogue_polices import FenetrePolices
m = ecrire("COLDPLAY", "Times New Roman", espacement=0.4)
gris = np.ascontiguousarray(255 - m)
d = FenetrePolices(QImage(gris.data, gris.shape[1], gris.shape[0], gris.shape[1], QImage.Format_Grayscale8).copy(),
                   m, "", False)
d.show()
verifier(gris.min() == 0 and gris[0, 0] == 255, "lettres montrées en noir sur blanc (même un texte blanc)")
ps_familles = ps.familles
ps.familles = lambda: petite
boucle = QEventLoop()
QTimer.singleShot(15000, boucle.quit)
if d._lecteur is not None:
    d._lecteur.fini.connect(lambda *_: QTimer.singleShot(0, boucle.quit))
    boucle.exec()
    verifier(d.texte.text().replace(" ", "") == "COLDPLAY", f"case remplie par la lecture de Windows ({d.texte.text()})")
d.texte.setText("COLDPLY")
d.chercher()
verifier("8 lettres" in d.etat.text() and "7" in d.etat.text(), f"7 lettres tapées pour 8 : prévenu ({d.etat.text()})")
d.grab().save(str(sortie / "fenetre.png"))
d.close()
ps.familles = ps_familles

# --- lecture de Windows : texte très espacé, resserré avant la lecture
if lecture_texte.disponible():
    lus = {}
    for nom, (texte, fam, opt) in {"espace": ("COLDPLAY", "Georgia", dict(espacement=0.8)),
                                   "jaune": ("A SKY FULL OF STARS", "Times New Roman", dict(gras=True))}.items():
        L = lecture_texte.Lecteur()
        boucle = QEventLoop()
        L.fini.connect(lambda t, nom=nom: (lus.__setitem__(nom, t), boucle.quit()))
        QTimer.singleShot(15000, boucle.quit)
        L.lire(ecrire(texte, fam, **opt))
        boucle.exec()
        L.arreter()
        verifier(lus.get(nom, "") == texte, f"Windows lit « {texte} » ({lus.get(nom)})")
print("ERREURS :", erreurs if erreurs else "aucune")
sys.exit(1 if erreurs else 0)
