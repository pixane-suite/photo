"""Compléter un ComfyUI déjà installé (ComfyUI Desktop, portable installé à la main…) : Pixane demande à ComfyUI
ce qu'il a déjà (/object_info : extensions et modèles visibles, même dans des dossiers partagés ; /experiment/models :
ses dossiers de modèles), et ne télécharge que ce qui manque, au même endroit que ComfyUI range ses fichiers.
Rien n'est remplacé ni effacé : on ajoute seulement des fichiers et des dossiers qui n'existaient pas.
"""
from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from . import recettes
from .installation_moteur import (DOSSIER_APP, GO, LICENCE_FLUX, Element, Installation, catalogue, go)
from .langue import tr
from .recettes import _options

DOSSIER_TRAVAIL = DOSSIER_APP / "complement"        # téléchargements en cours (reprise possible)


def _modele_vu(infos: dict, cle: str) -> bool:
    """Le modèle de cet élément est-il déjà visible par ComfyUI ?"""
    o = lambda noeud, entree: _options(infos, noeud, entree)
    if cle == "fill":
        return recettes.FILL_COMPLET in o("UNETLoader", "unet_name") or \
            any("fill" in f.lower() for f in o("UnetLoaderGGUF", "unet_name"))
    if cle == "schnell":
        return any("schnell" in f.lower() for f in o("UNETLoader", "unet_name") + o("UnetLoaderGGUF", "unet_name"))
    if cle == "kontext":
        return any("kontext" in f.lower() for f in o("UNETLoader", "unet_name") + o("UnetLoaderGGUF", "unet_name"))
    if cle == "profondeur":
        return any("depth_anything_3" in f.lower() for f in o("LoadDA3Model", "model_name"))
    if cle == "description":
        return any("qwen3.5" in f.lower() for f in o("CLIPLoader", "clip_name"))
    if cle == "visages":
        return "GFPGANv1.4.pth" in o("UpscaleModelLoader", "model_name")
    if cle == "t5":
        return "t5xxl_fp8_e4m3fn_scaled.safetensors" in o("DualCLIPLoader", "clip_name2") + \
            o("DualCLIPLoader", "clip_name1")
    if cle == "clip":
        return "clip_l.safetensors" in o("DualCLIPLoader", "clip_name1") + o("DualCLIPLoader", "clip_name2")
    if cle == "vae":
        return "ae.safetensors" in o("VAELoader", "vae_name")
    if cle == "lama":
        return "big-lama.pt" in o("INPAINT_LoadInpaintModel", "model_name")
    if cle == "birefnet":
        return recettes.BIREFNET in o("LoadBackgroundRemovalModel", "bg_removal_name")
    if cle == "sam":
        return any("sam3" in f.lower() for f in o("CheckpointLoaderSimple", "ckpt_name"))
    if cle == "esrgan":
        return "RealESRGAN_x4plus.pth" in o("UpscaleModelLoader", "model_name")
    if cle == "scunet":
        return recettes.SCUNET in o("UpscaleModelLoader", "model_name")
    return False


# extension -> nœud qui prouve qu'elle est chargée
NOEUD_EXTENSION = {"inpaint": "INPAINT_InpaintWithModel", "crop": "InpaintCropImproved",
                   "usdu": "UltimateSDUpscale", "usdu_script": "UltimateSDUpscale", "gguf": "UnetLoaderGGUF"}
# modèle -> nœud de ComfyUI lui-même dont il a besoin (sans lui, ComfyUI est trop ancien : inutile de télécharger)
NOEUD_COEUR = {"birefnet": "RemoveBackground", "sam": "SAM3_Detect", "kontext": "ReferenceLatent",
               "profondeur": "DA3Inference", "description": "TextGenerate"}


def manquants(infos: dict, dossiers: dict[str, list[str]], dossier_comfyui: Path, schnell: bool = False,
              kontext: bool = False, profondeur: bool = False,
              description: bool = False, visages: bool = False) -> tuple[list[Element], list[str]]:
    """-> (éléments à télécharger, avec leur chemin complet ; remarques à montrer : ComfyUI trop ancien pour une
    fonction, extension présente mais pas encore chargée).
    infos : /object_info ; dossiers : /experiment/models ({type: [dossiers]}) ; dossier_comfyui : celui de main.py."""
    noeuds = Path(dossier_comfyui) / "custom_nodes"
    base_modeles = Path(dossiers["checkpoints"][0]).parent if dossiers.get("checkpoints") else \
        Path(dossier_comfyui) / "models"
    liste, trop_ancien, pas_chargees = [], [], []
    for e in catalogue(True, schnell, kontext, profondeur, description, visages):
        if e.genre in ("outil", "7z"):
            continue
        if e.genre == "zip":
            if NOEUD_EXTENSION.get(e.cle) in infos:
                continue
            dest = noeuds / e.dest.split("custom_nodes/", 1)[1]
            if dest.exists():                              # déjà là (pas encore chargée) : on n'y touche pas
                if e.nom not in pas_chargees and e.cle != "usdu_script":
                    pas_chargees.append(e.nom)
                continue
            liste.append(replace(e, dest=str(dest)))
            continue
        if _modele_vu(infos, e.cle):
            continue
        if e.cle in NOEUD_COEUR and NOEUD_COEUR[e.cle] not in infos:
            trop_ancien.append(e.nom)
            continue
        genre = e.dest.split("/")[2]                        # ComfyUI/models/<genre>/<fichier>
        dossier = Path(dossiers[genre][0]) if dossiers.get(genre) else base_modeles / genre
        cible = dossier / e.fichier
        if cible.is_file() and cible.stat().st_size == e.taille:     # là, mais pas vu (extension pas chargée)
            continue
        liste.append(replace(e, dest=str(cible)))
    # l'extension GGUF ne sert qu'à lire les modèles .gguf qu'on télécharge
    if not any(e.dest.endswith(".gguf") for e in liste):
        liste = [e for e in liste if e.cle != "gguf"]
    notes = []
    if trop_ancien:
        notes.append(tr("Ce ComfyUI est trop ancien pour : {liste}. Mets-le à jour pour en profiter (Pixane Photo ne le "
                        "remplace pas).", liste=", ".join(trop_ancien)))
    if pas_chargees:
        notes.append(tr("Déjà là mais pas encore chargé par ComfyUI : {liste}. Ferme ComfyUI puis rouvre-le.",
                        liste=", ".join(pas_chargees)))
    return liste, notes


def ajoute_extensions(elements: list[Element]) -> bool:
    return any(e.genre == "zip" for e in elements)


class FenetreCompleter(QDialog):
    """Liste ce qui manque au ComfyUI existant (taille, source, licence, dossier), puis le télécharge."""
    fini = Signal(bool)                       # réussi

    def __init__(self, moteur_infos: dict, dossiers: dict, install: dict, externe: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Compléter le moteur IA"))
        self.setMinimumSize(820, 560)
        self.infos, self.dossiers, self.install, self.externe = moteur_infos, dossiers, install, externe
        self.travail: Installation | None = None
        self.reussi = False
        lay = QVBoxLayout(self)
        intro = QLabel(tr("Un ComfyUI est déjà installé sur ce PC ({dossier}) : Pixane Photo l'utilise. Il lui manque "
                          "seulement les éléments ci-dessous. Ils seront ajoutés dans les dossiers de ce ComfyUI, "
                          "sans rien remplacer ni effacer. Tout vient des sites officiels (GitHub, Hugging Face).",
                          dossier=install["dir"]))
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.liste = QTreeWidget()
        self.liste.setHeaderLabels([tr("Élément"), tr("Taille"), tr("Licence"), tr("Source"), tr("Dossier"),
                                    tr("État")])
        self.liste.setRootIsDecorated(False)
        lay.addWidget(self.liste, 1)
        self.ancien = QLabel()
        self.ancien.setWordWrap(True)
        lay.addWidget(self.ancien)
        from . import traduction
        from .installation_traducteur import explication
        self.c_schnell = QCheckBox(tr("Ajouter Flux Schnell pour « Upscale net » (facultatif)"))
        self.c_kontext = QCheckBox(tr("Ajouter Flux Kontext pour « Modifier avec une consigne » et « Restaurer une "
                                      "vieille photo » (facultatif)"))
        self.c_profondeur = QCheckBox(tr("Ajouter Depth Anything 3 (137 Mo) pour « Flou selon la profondeur » "
                                         "(facultatif)"))
        self.c_visages = QCheckBox(tr("Ajouter GFPGAN (349 Mo) pour « Restaurer les visages flous » (facultatif)"))
        from .installation_moteur import TAILLE_DESCRIPTION, go
        self.c_description = QCheckBox(tr("Ajouter Qwen3.5 2B ({taille}) pour la description automatique d'Agrandir "
                                          "l'image (facultatif)", taille=go(TAILLE_DESCRIPTION)))
        self.c_traducteur = QCheckBox(tr("Ajouter le traducteur des consignes, français → anglais ({taille})",
                                         taille=tr("{n} Mo", n=round(traduction.TAILLE / 1024 ** 2))))
        self.c_traducteur.setToolTip(explication())
        # déjà là : case visible, cochée et grisée (rien à télécharger) ; sinon proposée
        self._deja = {self.c_schnell: _modele_vu(moteur_infos, "schnell"),
                      self.c_kontext: _modele_vu(moteur_infos, "kontext"),
                      self.c_profondeur: _modele_vu(moteur_infos, "profondeur"),
                      self.c_visages: _modele_vu(moteur_infos, "visages"),
                      self.c_description: _modele_vu(moteur_infos, "description"),
                      self.c_traducteur: traduction.installe()}
        self.c_profondeur.setChecked(True)               # petit modèle : proposé (coché)
        self.c_visages.setChecked(True)
        self.c_traducteur.setChecked(True)               # pas installé : proposé ; installé : coché et grisé
        for c, (texte, deja) in zip(self._deja, [
                (tr("Flux Schnell (« Upscale net ») : déjà installé"), self._deja[self.c_schnell]),
                (tr("Flux Kontext (« Modifier avec une consigne », « Restaurer une vieille photo ») : déjà installé"),
                 self._deja[self.c_kontext]),
                (tr("Depth Anything 3 (« Flou selon la profondeur ») : déjà installé"),
                 self._deja[self.c_profondeur]),
                (tr("GFPGAN (« Restaurer les visages flous ») : déjà installé"), self._deja[self.c_visages]),
                (tr("Qwen3.5 2B (description automatique d'Agrandir) : déjà installé"),
                 self._deja[self.c_description]),
                (tr("Traducteur des consignes : déjà installé"), self._deja[self.c_traducteur])]):
            if deja:
                c.setText(texte)
                c.setChecked(True)
                c.setEnabled(False)
            c.toggled.connect(self._actualiser)
            lay.addWidget(c)
        from .installation_traducteur import ChoixDossier
        self.dossier_trad = ChoixDossier()
        self.dossier_trad.change.connect(self._actualiser)
        self.c_traducteur.toggled.connect(lambda v: self.dossier_trad.setEnabled(v))
        lay.addWidget(self.dossier_trad)
        aide_trad = QLabel(explication())
        aide_trad.setWordWrap(True)
        aide_trad.setObjectName("discret")
        lay.addWidget(aide_trad)
        self.licence = QLabel(tr("Flux Fill et Flux Kontext sont sous licence <b>FLUX.1 [dev] non commerciale</b> : "
                                 "usage personnel permis, pas d'usage commercial. <a href=\"{url}\">Lire la "
                                 "licence</a>.", url=LICENCE_FLUX))
        self.licence.setWordWrap(True)
        self.licence.setTextFormat(Qt.RichText)
        self.licence.setOpenExternalLinks(True)
        lay.addWidget(self.licence)
        self.c_licence = QCheckBox(tr("J'accepte la licence FLUX.1 [dev] (usage non commercial)"))
        self.c_licence.toggled.connect(self._actualiser)
        lay.addWidget(self.c_licence)
        self.place = QLabel()
        lay.addWidget(self.place)
        self.barre = QProgressBar()
        self.barre.setRange(0, 1000)
        lay.addWidget(self.barre)
        self.statut = QLabel(tr("Tu peux arrêter à tout moment : le téléchargement reprendra plus tard où il "
                                "s'est arrêté."))
        self.statut.setWordWrap(True)
        lay.addWidget(self.statut)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        self.b_lancer = QPushButton(tr("Télécharger et installer"))
        self.b_lancer.setDefault(True)
        self.b_lancer.setMinimumWidth(self.b_lancer.fontMetrics().horizontalAdvance(self.b_lancer.text()) + 48)
        self.b_lancer.clicked.connect(self.commencer)
        self.b_arreter = QPushButton(tr("Arrêter"))
        self.b_arreter.setEnabled(False)
        self.b_arreter.clicked.connect(lambda: self.travail and self.travail.arret.set())
        b_fermer = QPushButton(tr("Fermer"))
        b_fermer.clicked.connect(self.close)
        for b in (self.b_lancer, self.b_arreter, b_fermer):
            boutons.addWidget(b)
        lay.addLayout(boutons)
        self._actualiser()

    def elements(self) -> list[Element]:
        return self._liste()[0]

    def _liste(self) -> tuple[list[Element], list[str]]:
        from . import traduction
        elements, notes = manquants(self.infos, self.dossiers, self.install["dir"], self.c_schnell.isChecked(),
                                    self.c_kontext.isChecked(), self.c_profondeur.isChecked(),
                                    self.c_description.isChecked(), self.c_visages.isChecked())
        if self.c_traducteur.isChecked() and not traduction.installe():
            elements += traduction.elements()
        return elements, notes

    def _actualiser(self):
        if self.travail is not None:
            return
        elements, notes = self._liste()
        self.liste.clear()
        self._lignes = {}
        for e in elements:
            ligne = QTreeWidgetItem([e.nom, go(e.taille) if e.taille else tr("< 5 Mo"), e.licence,
                                     e.url.split("/")[2].replace("www.", ""), str(Path(e.dest).parent), ""])
            ligne.setToolTip(0, e.url)
            ligne.setToolTip(4, e.dest)
            ligne.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            self.liste.addTopLevelItem(ligne)
            self._lignes[e.cle] = ligne
        for i in range(6):
            self.liste.resizeColumnToContents(i)
        self.ancien.setText("\n".join(notes))
        self.ancien.setVisible(bool(notes))
        flux = any("FLUX.1 [dev]" in e.licence for e in elements)
        self.licence.setVisible(flux)
        self.c_licence.setVisible(flux)
        besoin = sum(e.taille or 2 * 1024 ** 2 for e in elements)
        try:
            libre = min(shutil.disk_usage(Path(e.dest).anchor).free for e in elements) if elements else None
        except OSError:
            libre = None
        assez = libre is None or libre > besoin + GO
        if not elements:
            self.place.setText(tr("Rien ne manque : ce ComfyUI a tout ce qu'il faut à Pixane Photo."))
        else:
            self.place.setText(tr("À télécharger : {besoin} ; libre sur le disque : {libre}", besoin=go(besoin),
                                  libre=go(libre) if libre is not None else "?")
                               + ("" if assez else "  —  " + tr("pas assez de place")))
        self.b_lancer.setEnabled(bool(elements) and assez and (self.c_licence.isChecked() or not flux))

    def commencer(self):
        if not self.b_lancer.isEnabled():
            return
        self.travail = Installation(DOSSIER_TRAVAIL, self.elements(), complement=True, python=self.install["python"])
        self.travail.etat.connect(lambda cle, t: cle in self._lignes and self._lignes[cle].setText(5, t))
        self.travail.progres.connect(lambda fait, total, _v: (self.barre.setValue(int(1000 * fait / max(total, 1))),
                                                               self.statut.setText(tr("{fait} sur {total}",
                                                                                      fait=go(fait),
                                                                                      total=go(total)))))
        self.travail.fini.connect(self._fini)
        for w in (self.b_lancer, self.c_schnell, self.c_kontext, self.c_profondeur, self.c_visages, self.c_description,
                  self.c_traducteur,
                  self.c_licence, self.dossier_trad):
            w.setEnabled(False)
        self.b_arreter.setEnabled(True)
        self.statut.setText(tr("Démarrage…"))
        self._extensions = ajoute_extensions(self.travail.elements)
        self.travail.lancer()

    def _fini(self, reussi: bool, message: str):
        self.b_arreter.setEnabled(False)
        self.travail = None
        self.reussi = reussi
        if reussi:
            self.barre.setValue(1000)
            if self._extensions and self.externe:
                message += "\n\n" + tr("De nouvelles extensions ont été ajoutées : ferme ComfyUI (ComfyUI Desktop) "
                                       "puis rouvre-le pour qu'il les charge.")
            self.statut.setText(message)
            QMessageBox.information(self, tr("Compléter le moteur IA"), message)
            self.fini.emit(True)
            self.accept()
        else:
            self.statut.setText(message)
            for w in (self.c_schnell, self.c_kontext, self.c_profondeur, self.c_visages, self.c_description,
                      self.c_traducteur, self.c_licence):
                w.setEnabled(not self._deja.get(w, False))
            self.dossier_trad.setEnabled(self.c_traducteur.isChecked())
            self.b_lancer.setText(tr("Reprendre"))
            self._actualiser()

    def closeEvent(self, ev):
        if self.travail is not None:
            if QMessageBox.question(self, tr("Compléter le moteur IA"),
                                    tr("Arrêter ? Le téléchargement reprendra plus tard où il s'est arrêté.")) \
                    != QMessageBox.Yes:
                ev.ignore()
                return
            self.travail.arret.set()
        super().closeEvent(ev)
