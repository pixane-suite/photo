"""Édition > Préférences… (Ctrl+,) : tous les réglages durables de Pixane Photo au même endroit, en onglets.
Rien n'est appliqué avant OK : la fenêtre rend les valeurs choisies (valeurs()) et la fenêtre principale les applique
avec les mêmes fonctions que les menus, qui restent (Affichage, IA, Aide). Mêmes clés de réglage que les menus.
Même fenêtre que Pixane Video (onglets, libellé à gauche, petite note grise sous chaque onglet)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from . import langue, theme
from .langue import tr

MINUTES_RECUPERATION = (1, 3, 5, 10, 0)          # 0 : jamais
TAILLES_ICONES = (18, 22, 28, 36)


def texte_echelle(pc: int) -> str:
    """Même libellé que le menu Affichage > Taille de l'interface."""
    return {75: tr("{n} % (très compacte)", n=pc), 85: tr("{n} % (compacte, petits écrans)", n=pc),
            100: tr("{n} % (normale)", n=pc)}.get(pc, f"{pc} %")


def textes_icones() -> dict[int, str]:
    return {18: tr("Petites"), 22: tr("Normales"), 28: tr("Grandes"), 36: tr("Très grandes")}


def _liste(choix, actuel) -> QComboBox:
    """Liste déroulante de (valeur, texte), avec la valeur actuelle choisie."""
    b = QComboBox()
    for v, t in choix:
        b.addItem(t, v)
    i = b.findData(actuel)
    b.setCurrentIndex(max(0, i))
    return b


def _note(texte: str) -> QLabel:
    n = QLabel(texte)
    n.setObjectName("discret")
    n.setWordWrap(True)
    return n


def _onglet(note: str) -> tuple[QWidget, QFormLayout]:
    w = QWidget()
    lay = QVBoxLayout(w)
    form = QFormLayout()
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    lay.addLayout(form)
    lay.addWidget(_note(note))
    lay.addStretch(1)
    return w, form


def dossier_moteur() -> str | None:
    """Dossier de ComfyUI utilisé par Pixane Photo (None : pas trouvé)."""
    try:
        from .moteur import trouver_comfyui
        d = trouver_comfyui()
    except Exception:
        return None
    return str(d["dir"]) if d else None


class DialoguePreferences(QDialog):
    def __init__(self, fenetre):
        super().__init__(fenetre)
        self.f = fenetre
        r = fenetre.reglages
        self.setWindowTitle(tr("Préférences"))
        self.onglets = QTabWidget()

        # ---- Affichage
        from .__main__ import ECHELLES
        w, form = _onglet(tr("La langue et la taille de l'interface changent au prochain démarrage ; le reste tout de "
                             "suite. Ces réglages sont aussi dans le menu Affichage."))
        self.theme = _liste(((theme.AUTO, tr("Comme Windows")), (theme.CLAIR, tr("Clair")),
                             (theme.SOMBRE, tr("Sombre"))), fenetre.mode_theme)
        form.addRow(tr("Thème"), self.theme)
        self.langue = _liste([(langue.AUTO, tr("Comme Windows"))] + list(langue.LANGUES.items()),
                             r.value("langue", langue.AUTO))
        form.addRow(tr("Langue"), self.langue)
        self.echelle = _liste([(pc, texte_echelle(pc)) for pc in ECHELLES], fenetre._echelle_reglee())
        form.addRow(tr("Taille de l'interface"), self.echelle)
        self.icones = _liste(list(textes_icones().items()), fenetre._taille_icones())
        form.addRow(tr("Taille des icônes des outils"), self.icones)
        self.barre_rapide = QCheckBox(tr("Barre d'accès rapide"))
        self.barre_rapide.setChecked(fenetre.a_barre_rapide.isChecked())
        form.addRow("", self.barre_rapide)
        self.grille = QSpinBox()
        self.grille.setRange(2, 5000)
        self.grille.setSuffix(" px")
        self.grille.setValue(fenetre.canevas.pas_grille)
        form.addRow(tr("Écart de la grille"), self.grille)
        self.onglets.addTab(w, tr("Affichage"))

        # ---- Fonctions installées (options de l'installateur, modifiables ici)
        w, form = _onglet(tr("Fonctions choisies à l'installation. Décochée, une fonction ne prend plus de place ni "
                             "de temps. Aussi dans le menu Affichage."))
        self.polices = QCheckBox(tr("Recherche de police semblable"))
        self.polices.setChecked(fenetre.a_option_polices.isChecked())
        self.polices.setToolTip(fenetre.a_option_polices.toolTip())
        form.addRow("", self.polices)
        self.orthographe = QCheckBox(tr("Orthographe et césure"))
        self.orthographe.setChecked(fenetre.a_option_orthographe.isChecked())
        self.orthographe.setToolTip(fenetre.a_option_orthographe.toolTip())
        form.addRow("", self.orthographe)
        b = QPushButton(tr("Langues de l'orthographe…"))
        b.clicked.connect(fenetre.langues_orthographe)
        self.orthographe.toggled.connect(b.setEnabled)
        b.setEnabled(self.orthographe.isChecked())
        self.b_langues = b
        form.addRow("", b)
        self.onglets.addTab(w, tr("Fonctions installées"))

        # ---- Intelligence artificielle
        w, form = _onglet(tr("Le moteur IA (ComfyUI) fait tous les calculs de l'IA sur ce PC. Ces réglages sont "
                             "aussi dans le menu IA."))
        self.nouveau_calque = QCheckBox(tr("Mettre les résultats dans un nouveau calque"))
        self.nouveau_calque.setChecked(fenetre.a_ia_nouveau_calque.isChecked())
        self.nouveau_calque.setToolTip(fenetre.a_ia_nouveau_calque.toolTip())
        form.addRow("", self.nouveau_calque)
        self.pleine = QCheckBox(tr("Agrandir l'image : en pleine définition"))
        self.pleine.setChecked(fenetre.barre_agrandir.pleine.isChecked())
        form.addRow("", self.pleine)
        d = dossier_moteur()
        moteur = QLabel(d or tr("pas trouvé"))
        moteur.setWordWrap(True)
        moteur.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(tr("Moteur IA"), moteur)
        b = QPushButton(tr("Installer ou compléter le moteur IA…"))
        b.clicked.connect(fenetre.installer_moteur)
        form.addRow("", b)
        self.onglets.addTab(w, tr("Intelligence artificielle"))

        # ---- Enregistrement
        w, form = _onglet(tr("Copie de récupération : si Pixane Photo se ferme mal (panne, plantage), les photos "
                             "modifiées sont proposées au démarrage suivant."))
        try:
            minutes = int(float(r.value("recuperation_minutes", 3)))
        except (TypeError, ValueError):
            minutes = 3
        self.recuperation = _liste([(m, tr("Toutes les {n} min", n=m)) for m in MINUTES_RECUPERATION if m]
                                   + [(0, tr("Jamais"))], minutes)
        form.addRow(tr("Copie de récupération"), self.recuperation)
        ligne = QHBoxLayout()
        self.dossier = QLineEdit(str(r.value("dossier", str(Path.home() / "Pictures"))))
        b = QPushButton(tr("Parcourir…"))
        b.clicked.connect(self._choisir_dossier)
        ligne.addWidget(self.dossier, 1)
        ligne.addWidget(b)
        form.addRow(tr("Dossier des images"), ligne)
        form.addRow("", _note(tr("Proposé pour ouvrir et enregistrer une nouvelle image ; il suit le dernier dossier "
                                 "utilisé.")))
        self.onglets.addTab(w, tr("Enregistrement"))

        # ---- Mises à jour
        w, form = _onglet(tr("Pixane Photo regarde sur GitHub s'il existe une version plus récente ; il ne "
                             "télécharge rien sans te demander. Aussi dans le menu Aide."))
        self.maj = QCheckBox(tr("Vérifier les mises à jour au démarrage"))
        self.maj.setChecked(fenetre.a_maj_auto.isChecked())
        form.addRow("", self.maj)
        b = QPushButton(tr("Rechercher une mise à jour…"))
        b.clicked.connect(lambda: fenetre.verifier_maj(False))
        form.addRow("", b)
        self.onglets.addTab(w, tr("Mises à jour"))

        try:
            self.onglets.setCurrentIndex(int(r.value("preferences/onglet", 0)))
        except (TypeError, ValueError):
            pass
        self.onglets.currentChanged.connect(lambda i: r.setValue("preferences/onglet", i))
        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(self.onglets)
        lay.addWidget(boutons)
        # assez large pour voir tous les onglets sans flèches (et le dossier en entier)
        self.onglets.tabBar().setUsesScrollButtons(False)
        self.setMinimumWidth(max(560, self.onglets.tabBar().sizeHint().width() + 40))

    def _choisir_dossier(self):
        d = QFileDialog.getExistingDirectory(self, tr("Dossier des images"), self.dossier.text())
        if d:
            self.dossier.setText(str(Path(d)))

    def valeurs(self) -> dict:
        return {"theme": self.theme.currentData(), "langue": self.langue.currentData(),
                "echelle": self.echelle.currentData(), "icones": self.icones.currentData(),
                "barre_rapide": self.barre_rapide.isChecked(), "grille": self.grille.value(),
                "polices": self.polices.isChecked(), "orthographe": self.orthographe.isChecked(),
                "nouveau_calque": self.nouveau_calque.isChecked(), "pleine": self.pleine.isChecked(),
                "recuperation": self.recuperation.currentData(), "dossier": self.dossier.text().strip(),
                "maj": self.maj.isChecked()}
