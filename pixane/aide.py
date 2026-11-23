"""Fenêtres d'aide, sur le modèle de TwinPanel :
- le guide (docs/GUIDE.md ou GUIDE_en.md) : chapitres à gauche avec une recherche, page mise en forme à droite ;
- les éléments tiers : tableau Élément / Rôle / Licence, nom cliquable vers le site du projet ;
- la licence de Pixane : texte complet (LICENSE, ou LICENSE.en.txt en anglais).
Le guide est lu dans le même fichier que celui livré et recopié dans le README : une seule version à tenir à jour."""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QSplitter, QTextBrowser, QVBoxLayout, QWidget)

from .langue import langue as langue_active, tr
from .theme import CLAIR_C, Couleurs

RACINE = Path(__file__).resolve().parents[1]


# ====================================================================== Markdown -> HTML (le strict nécessaire)
def _en_ligne(t: str, c: Couleurs) -> str:
    """Gras, italique, `code` et liens dans une ligne de texte."""
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", lambda m: f"<code style='background:{c.pastille};font-family:Consolas'>&nbsp;"
                                       f"{m.group(1)}&nbsp;</code>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", rf"<a href='\2' style='color:{c.accent}'>\1</a>", t)
    return t


def _cellules(ligne: str) -> list[str]:
    return [x.strip() for x in ligne.strip().strip("|").split("|")]


def markdown_html(md: str, c: Couleurs) -> str:
    """Convertit le Markdown du guide : titres ###, paragraphes, listes (avec sous-listes), listes numérotées,
    tableaux, citations « > », gras / italique / code."""
    sortie: list[str] = []
    para: list[str] = []
    liste: list[tuple[int, str, list[str]]] = []      # (niveau, type ul/ol, lignes de l'élément)
    tableau: list[list[str]] = []

    def vider_para():
        if para:
            sortie.append(f"<p>{_en_ligne(' '.join(para), c)}</p>")
            para.clear()

    def vider_liste():
        if not liste:
            return
        pile: list[str] = []
        for niveau, genre, lignes in liste:
            while len(pile) > niveau + 1:
                sortie.append(f"</{pile.pop()}>")
            while len(pile) < niveau + 1:
                pile.append(genre)
                sortie.append(f"<{genre} style='margin-top:2px;margin-bottom:2px'>")
            sortie.append(f"<li style='margin-bottom:3px'>{_en_ligne(' '.join(lignes), c)}</li>")
        while pile:
            sortie.append(f"</{pile.pop()}>")
        liste.clear()

    def vider_tableau():
        if not tableau:
            return
        sortie.append(f"<table cellspacing='0' cellpadding='6' width='100%' "
                      f"style='border-collapse:collapse;border:1px solid {c.bordure};margin:6px 0'>")
        for i, ligne in enumerate(tableau):
            fond = c.pastille if i == 0 else (c.survol if i % 2 == 0 else c.panneau)
            balise = "th" if i == 0 else "td"
            cases = "".join(f"<{balise} align='left' style='border:1px solid {c.bordure}'>{_en_ligne(x, c)}"
                            f"</{balise}>" for x in ligne)
            sortie.append(f"<tr style='background:{fond}'>{cases}</tr>")
        sortie.append("</table>")
        tableau.clear()

    def vider():
        vider_para()
        vider_liste()
        vider_tableau()

    for brut in md.splitlines():
        ligne = brut.rstrip()
        retrait = len(ligne) - len(ligne.lstrip())
        net = ligne.strip()
        if not net or net == "---" or net.startswith("<!--"):
            vider()
            continue
        if net.startswith("|"):
            vider_para()
            vider_liste()
            if not re.fullmatch(r"\|[\s:|-]+\|?", net):
                tableau.append(_cellules(net))
            continue
        vider_tableau()
        if net.startswith("#"):
            vider()
            n = len(net) - len(net.lstrip("#"))
            taille = {1: 20, 2: 18, 3: 14}.get(n, 13)
            sortie.append(f"<p style='font-size:{taille}pt;font-weight:600;margin-top:14px;margin-bottom:4px'>"
                          f"{_en_ligne(net.lstrip('#').strip(), c)}</p>")
            continue
        m = re.match(r"([-*]|\d+\.)\s+(.*)", net)
        if m:
            vider_para()
            niveau = min(retrait // 2, 3)
            liste.append((niveau, "ol" if m.group(1)[0].isdigit() else "ul", [m.group(2)]))
            continue
        if net.startswith(">"):
            vider()
            sortie.append(f"<table cellpadding='8' width='100%' style='background:{c.accent_doux};margin:6px 0'>"
                          f"<tr><td>{_en_ligne(net.lstrip('> '), c)}</td></tr></table>")
            continue
        if liste and retrait > 0:              # suite de l'élément de liste
            liste[-1][2].append(net)
        else:
            vider_liste()
            para.append(net)
    vider()
    return "\n".join(sortie)


# ====================================================================== guide
@dataclass
class Chapitre:
    titre: str
    texte: str


def _sans_accents(t: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(ch) != "Mn")


def fichier_guide() -> Path:
    return RACINE / "docs" / ("GUIDE_en.md" if langue_active() == "en" else "GUIDE.md")


def chapitres(md: str) -> list[Chapitre]:
    """Découpe le guide en chapitres (titres « ## ») ; ce qui précède le premier sert d'introduction."""
    resultat: list[Chapitre] = []
    titre, lignes = None, []
    intro: list[str] = []
    for ligne in md.splitlines():
        if ligne.startswith("## "):
            if titre is not None:
                resultat.append(Chapitre(titre, "\n".join(lignes)))
            titre, lignes = ligne[3:].strip(), []
        elif titre is None:
            if not ligne.startswith("# "):
                intro.append(ligne)
        else:
            lignes.append(ligne)
    if titre is not None:
        resultat.append(Chapitre(titre, "\n".join(lignes)))
    if resultat and "\n".join(intro).strip():
        resultat[0].texte = "\n".join(intro).strip() + "\n\n---\n\n" + resultat[0].texte
    return resultat


class FenetreGuide(QDialog):
    """Guide de Pixane : liste des chapitres (avec recherche) à gauche, chapitre mis en forme à droite."""

    def __init__(self, couleurs: Couleurs | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Guide de Pixane Photo"))
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
        self.resize(1080, 760)
        self.c = couleurs or CLAIR_C
        try:
            self.tous = chapitres(fichier_guide().read_text(encoding="utf-8"))
        except OSError:
            self.tous = [Chapitre(tr("Guide"), tr("Le guide est introuvable : {chemin}", chemin=str(fichier_guide())))]
        lay = QVBoxLayout(self)
        sep = QSplitter(Qt.Horizontal)
        gauche = QWidget()
        lg = QVBoxLayout(gauche)
        lg.setContentsMargins(0, 0, 0, 0)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(tr("Rechercher dans le guide"))
        self.recherche.setClearButtonEnabled(True)
        self.recherche.textChanged.connect(self._filtrer)
        lg.addWidget(self.recherche)
        self.liste = QListWidget()
        self.liste.setWordWrap(True)
        self.liste.currentItemChanged.connect(self._montrer)
        lg.addWidget(self.liste, 1)
        sep.addWidget(gauche)
        self.page = QTextBrowser()
        self.page.setOpenExternalLinks(True)
        self.page.document().setDocumentMargin(18)
        self.page.setStyleSheet(f"QTextBrowser {{ background: {self.c.panneau}; border: 1px solid {self.c.bordure};"
                                f" border-radius: 8px; }}")
        sep.addWidget(self.page)
        sep.setSizes([330, 750])
        sep.setStretchFactor(1, 1)
        lay.addWidget(sep, 1)
        b = QDialogButtonBox(QDialogButtonBox.Close)
        b.button(QDialogButtonBox.Close).setText(tr("Fermer"))
        b.rejected.connect(self.reject)
        lay.addWidget(b)
        QShortcut(QKeySequence.Find, self, activated=self.recherche.setFocus)
        self._filtrer("")

    def ouvrir(self, chapitre: str | None = None):
        """Montre la fenêtre sur le chapitre dont le titre contient ce mot (le premier sinon)."""
        self.recherche.clear()
        if chapitre:
            for i in range(self.liste.count()):
                if chapitre.lower() in self.liste.item(i).text().lower():
                    self.liste.setCurrentRow(i)
                    break
        self.show()
        self.raise_()
        self.activateWindow()

    def _filtrer(self, texte: str):
        cle = _sans_accents(texte.strip())
        self.liste.clear()
        for ch in self.tous:
            if not cle or cle in _sans_accents(ch.titre + "\n" + ch.texte):
                it = QListWidgetItem(ch.titre)
                it.setData(Qt.UserRole, ch)
                self.liste.addItem(it)
        if self.liste.count():
            self.liste.setCurrentRow(0)
        else:
            self.page.setHtml(f"<p style='color:{self.c.discret}'>{html.escape(tr('Rien trouvé dans le guide.'))}</p>")

    def _montrer(self, item, _avant=None):
        if item is None:
            return
        ch: Chapitre = item.data(Qt.UserRole)
        corps = markdown_html(ch.texte, self.c)
        cle = self.recherche.text().strip()
        if cle:                              # surligner le mot cherché (hors balises)
            motif = re.compile("(" + re.escape(html.escape(cle, quote=False)) + ")", re.IGNORECASE)
            corps = re.sub(r"(>[^<]+)", lambda m: motif.sub(
                rf"<span style='background:{self.c.accent_doux}'>\1</span>", m.group(1)), corps)
        self.page.setHtml(f"<div style='color:{self.c.texte}'>"
                          f"<p style='font-size:20pt;font-weight:600;margin-bottom:6px'>{html.escape(ch.titre)}</p>"
                          f"{corps}</div>")


# ====================================================================== éléments tiers
@dataclass
class Composant:
    nom: str
    url: str
    role: str        # texte français, traduit à l'affichage
    licence: str


LIVRES = [
    Composant("Python 3.11", "https://www.python.org", "Langage du programme", "PSF License"),
    Composant("PySide6 / Qt 6", "https://doc.qt.io/qtforpython-6/", "Fenêtres, boutons, dessin",
              "LGPL-3.0"),
    Composant("numpy", "https://numpy.org", "Calculs sur les pixels", "BSD-3-Clause"),
    Composant("Pillow", "https://python-pillow.github.io", "Lecture et écriture des images", "MIT-CMU"),
    Composant("websocket-client", "https://github.com/websocket-client/websocket-client",
              "Dialogue avec le moteur IA", "Apache-2.0"),
    Composant("rawpy / LibRaw", "https://github.com/letmaik/rawpy", "Ouvrir les fichiers RAW des appareils photo",
              "MIT (LibRaw : LGPL-2.1 ou CDDL-1.0)"),
    Composant("OpenEXR", "https://openexr.com", "Ouvrir et enregistrer les images HDR (.exr, 32 bits)",
              "BSD-3-Clause"),
]
TELECHARGES = [
    Composant("ComfyUI", "https://github.com/Comfy-Org/ComfyUI", "Moteur IA (programme séparé)", "GPL-3.0"),
    Composant("comfyui-inpaint-nodes", "https://github.com/Acly/comfyui-inpaint-nodes",
              "Extension : LaMa, préparation des zones", "GPL-3.0"),
    Composant("ComfyUI-Inpaint-CropAndStitch", "https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch",
              "Extension : découper autour de la zone, recoller", "GPL-3.0"),
    Composant("ComfyUI_UltimateSDUpscale", "https://github.com/ssitu/ComfyUI_UltimateSDUpscale",
              "Extension : upscale par morceaux", "GPL-3.0"),
    Composant("ComfyUI-GGUF", "https://github.com/city96/ComfyUI-GGUF", "Extension : modèles GGUF",
              "Apache-2.0 (gguf : MIT)"),
    Composant("7-Zip (7zr.exe)", "https://www.7-zip.org", "Décompresser ComfyUI", "LGPL-2.1"),
    Composant("FLUX.1 Fill [dev]", "https://huggingface.co/black-forest-labs/FLUX.1-Fill-dev",
              "Effacer, remplir, agrandir", "FLUX.1 [dev] Non-Commercial"),
    Composant("FLUX.1 [schnell]", "https://huggingface.co/black-forest-labs/FLUX.1-schnell",
              "Upscale net, créer une image d'après un texte (facultatif)", "Apache-2.0"),
    Composant("FLUX.1 Kontext [dev]", "https://huggingface.co/black-forest-labs/FLUX.1-Kontext-dev",
              "Restaurer une vieille photo (facultatif)", "FLUX.1 [dev] Non-Commercial"),
    Composant("T5, CLIP, VAE", "https://huggingface.co/comfyanonymous/flux_text_encoders",
              "Encodeurs de texte et décodeur d'image", "Apache-2.0"),
    Composant("LaMa", "https://github.com/advimman/lama", "Effacer (premier passage)", "Apache-2.0"),
    Composant("RealESRGAN x4plus", "https://github.com/xinntao/Real-ESRGAN", "Upscale", "BSD-3-Clause"),
    Composant("SCUNet", "https://github.com/cszn/SCUNet", "Réduire le bruit", "Apache-2.0"),
    Composant("BiRefNet", "https://github.com/ZhengPeng7/BiRefNet", "Sujet, arrière-plan", "MIT"),
    Composant("SAM 3.1", "https://huggingface.co/facebook/sam3.1",
              "Sélection d'objet, sélection rapide, ciel, supprimer les personnes, retouche portrait",
              "SAM License (Meta)"),
    Composant("Qwen3.5 2B", "https://huggingface.co/Qwen/Qwen3.5-2B",
              "Agrandir : description automatique (facultatif)", "Apache-2.0"),
    Composant("Google Fonts (via Fontsource)", "https://fontsource.org",
              "Polices gratuites de la recherche de police semblable (facultatif)", "OFL-1.1, Apache-2.0, UFL-1.0"),
]


class FenetreTiers(QDialog):
    def __init__(self, couleurs: Couleurs | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Éléments tiers"))
        self.resize(900, 640)
        c = couleurs or CLAIR_C

        def tableau(items: list[Composant]) -> str:
            lignes = [f"<tr style='background:{c.pastille}'>"
                      + "".join(f"<th align='left' style='border:1px solid {c.bordure}'>{html.escape(t)}</th>"
                                for t in (tr("Élément"), tr("Rôle"), tr("Licence"))) + "</tr>"]
            for i, x in enumerate(items):
                fond = c.survol if i % 2 else c.panneau
                lignes.append(
                    f"<tr style='background:{fond}'>"
                    f"<td style='border:1px solid {c.bordure}'><a href='{x.url}' style='color:{c.accent}'>"
                    f"{html.escape(x.nom)}</a></td>"
                    f"<td style='border:1px solid {c.bordure}'>{html.escape(tr(x.role))}</td>"
                    f"<td style='border:1px solid {c.bordure}'>{html.escape(x.licence)}</td></tr>")
            return (f"<table cellspacing='0' cellpadding='6' width='100%' style='border-collapse:collapse;"
                    f"margin:6px 0'>{''.join(lignes)}</table>")

        texte = (f"<div style='color:{c.texte}'>"
                 f"<p>{html.escape(tr('Programmes et modèles d’autres auteurs utilisés par Pixane Photo. Ils restent sous leur propre licence : la licence de Pixane Photo ne s’applique pas à eux. Clic sur un nom : site du projet et texte complet de sa licence.'))}</p>"
                 f"<p style='font-size:13pt;font-weight:600;margin-top:12px'>{html.escape(tr('Livrés avec Pixane Photo'))}</p>"
                 f"{tableau(LIVRES)}"
                 f"<p style='font-size:13pt;font-weight:600;margin-top:12px'>"
                 f"{html.escape(tr('Téléchargés seulement si vous installez le moteur IA'))}</p>"
                 f"{tableau(TELECHARGES)}"
                 f"<p style='color:{c.discret}'>{html.escape(tr('Pixane Photo lance ComfyUI comme un programme séparé : aucun code de ComfyUI n’est inclus dans Pixane Photo. FLUX.1 Fill [dev] : usage non commercial seulement.'))}</p>"
                 f"</div>")
        lay = QVBoxLayout(self)
        page = QTextBrowser()
        page.setOpenExternalLinks(True)
        page.document().setDocumentMargin(14)
        page.setStyleSheet(f"QTextBrowser {{ background: {c.panneau}; border: 1px solid {c.bordure};"
                           f" border-radius: 8px; }}")
        page.setHtml(texte)
        lay.addWidget(page, 1)
        b = QDialogButtonBox(QDialogButtonBox.Close)
        b.button(QDialogButtonBox.Close).setText(tr("Fermer"))
        b.rejected.connect(self.reject)
        lay.addWidget(b)


# ====================================================================== licence
def image_licence(largeur: int = 480) -> QLabel | None:
    """Image « Licence Pixane : gratuit, non commercial, modifiable » (la même que dans le README), dans la langue
    de Pixane, à la largeur voulue ; None si le fichier manque."""
    from PySide6.QtGui import QGuiApplication, QPixmap
    nom = "licence-pixane-en.png" if langue_active() == "en" else "licence-pixane.png"
    pm = QPixmap(str(Path(__file__).resolve().parent / "ressources" / nom))
    if pm.isNull():
        return None
    ratio = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
    pm = pm.scaledToWidth(round(largeur * ratio), Qt.SmoothTransformation)
    pm.setDevicePixelRatio(ratio)
    l = QLabel()
    l.setObjectName("image_licence")
    l.setPixmap(pm)
    l.setAlignment(Qt.AlignCenter)
    l.setToolTip(tr("Licence Pixane : gratuit, non commercial, modifiable"))
    return l


class FenetreLicence(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Licence Pixane 1.3"))
        self.resize(760, 640)
        f = RACINE / ("LICENSE.en.txt" if langue_active() == "en" else "LICENSE")
        try:
            texte = f.read_text(encoding="utf-8-sig")
        except OSError:
            texte = tr("Le texte de la licence est introuvable : {chemin}", chemin=str(f))
        lay = QVBoxLayout(self)
        image = image_licence(560)
        if image is not None:
            lay.addWidget(image)
        if langue_active() == "en":
            note = QLabel(tr("Traduction de courtoisie : seul le texte français (fichier LICENSE) fait foi."))
            note.setWordWrap(True)
            lay.addWidget(note)
        boite = QPlainTextEdit(texte)
        boite.setReadOnly(True)
        boite.setFont(QFont("Consolas", 10))
        lay.addWidget(boite, 1)
        b = QDialogButtonBox(QDialogButtonBox.Close)
        b.button(QDialogButtonBox.Close).setText(tr("Fermer"))
        b.rejected.connect(self.reject)
        lay.addWidget(b)
