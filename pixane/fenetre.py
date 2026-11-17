"""Fenêtre principale de Pixane."""
from __future__ import annotations

import io
import json
import os
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QBuffer, QMimeData, QObject, QPoint, QProcess, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtCore import QEvent, QPointF, QUrl
from PySide6.QtGui import (QAction, QActionGroup, QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPainter, QUndoCommand,
                           QTransform, QUndoStack)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDockWidget, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSizePolicy, QSlider,
                               QSpinBox, QToolBar, QToolButton, QUndoView, QVBoxLayout, QWidget, QInputDialog, QDoubleSpinBox)

from . import affinage, calque_forme, calque_pinceau, durees, langue, recettes, theme, traduction
from .document import vectoriel
from .icones import icone
from .langue import tr
from .actions_calques import ActionsCalques
from .contour import ActionContour
from .onglets import Onglets
from .ia_photo import ActionsPhotoIA
from .options_forme import OptionsForme
from .options_pinceau import OptionsPinceau
from .calques import PanneauCalques
from .canevas import (DENSITE_MOINS, DENSITE_PLUS, DOIGT, EPONGE, GOUTTE, HISTORIQUE, NETTETE_PINCEAU, PLUME,
                      OUTILS_FILTRE, BAGUETTE, CORRECTEUR, DEGRADE, DEPLACER, FORMES, GOMME, GOMME_CALQUE, LASSO, MAIN, OBJET,
                      SEL_TEXTE,
                      OUTILS_AUTO, OUTILS_ROND, PEINTURE, PINCEAU, RAPIDE, RECADRER, RECTANGLE, SEAU, SUPPRIMER,
                      TAILLE_MAX, TAMPON, TAMPON_MOTIF, TEXTE, Canevas)
from .dialogues import Attente, BarreAgrandir, ChoixResultat, ReglagesUpscale
from .document import (EXTENSIONS_CALQUES, EXTENSIONS_LECTURE, FORMAT_IMAGE, Document, image_entiere,
                       Origine, a_plat, attacher_origine, masque, nouvelle_selection, origine_valide, qimage_rgb,
                       tableau, transformation_depuis, trous_a_remplir, vue_ia)
from .moteur import Annule, ErreurMoteur, Moteur, trouver_comfyui
from .panneau_texte import BoutonCouleur, PanneauTexte
from .garde_fou import garder_aplats, part_aplats
from .raccord import finaliser, fond_prolonge, lisere_auto, preparer, reaccorder
from .reglages_image import FenetreReglages, ajuster, auto, neutre
from .dialogues_document import ExportImpression, NouvelleImage, ZoneTravail
from .dialogues_image import APropos, Redresser, TailleImage
from .transformation import Transformation
from . import mises_a_jour
from .texte import Texte

NOM = "Pixane Photo"
MIME_PLACE = "application/x-pixane-place"   # presse-papiers : place d'origine de ce qui a été copié dans Pixane


def png_variante(brut: QImage, png: bytes) -> bytes:
    """« Partir de celle-ci » : la proposition brute (telle que sortie du moteur), avec la même zone à refaire
    (transparence) que l'image envoyée la première fois."""
    import io
    from PIL import Image
    depart = Image.open(io.BytesIO(png))
    rgb = Image.fromarray(np.ascontiguousarray(tableau(brut.convertToFormat(FORMAT_IMAGE))[:, :, :3]), "RGB")
    if rgb.size != depart.size:
        rgb = rgb.resize(depart.size, Image.LANCZOS)
    if depart.mode in ("RGBA", "LA", "PA") or "transparency" in depart.info:
        rgb.putalpha(depart.convert("RGBA").getchannel("A"))
    tampon = io.BytesIO()
    rgb.save(tampon, "PNG", compress_level=1)
    return tampon.getvalue()


def reglages() -> QSettings:
    """Réglages de l'utilisateur ; les essais automatiques ont les leurs (variable PIXANE_REGLAGES)."""
    return QSettings("Pixane", os.environ.get("PIXANE_REGLAGES", "Pixane"))



def taille_position(v: int) -> int:
    """Glissière (0..1000) -> taille du pinceau (2..5000 px), progressive : précise pour les petites tailles."""
    return max(2, min(TAILLE_MAX, round(2 * (TAILLE_MAX / 2) ** (v / 1000))))


def position_taille(taille: int) -> int:
    import math
    return round(1000 * math.log(max(2, taille) / 2) / math.log(TAILLE_MAX / 2))

class Tache(QObject):
    """Exécute une fonction dans un fil secondaire et renvoie le résultat par signal."""
    fini = Signal(object)
    echec = Signal(str)
    progres = Signal(object)

    def __init__(self, fonction):
        super().__init__()
        self.fonction = fonction

    def lancer(self):
        threading.Thread(target=self._executer, daemon=True).start()

    def _executer(self):
        try:
            self.fini.emit(self.fonction(self.progres.emit))
        except Annule:
            self.echec.emit("")
        except ErreurMoteur as e:
            self.echec.emit(str(e))
        except Exception as e:  # erreur imprévue : on l'affiche plutôt que de planter
            self.echec.emit(f"{type(e).__name__} : {e}")


class FenetreNouveautes(QDialog):
    """Nouvelle version trouvée : ce qui change (nouveautés, corrections) dans toutes les versions pas encore
    installées, puis Télécharger ou Plus tard."""

    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QDialogButtonBox, QTextBrowser
        from . import __version__
        self.setWindowTitle(tr("Mise à jour"))
        self.resize(640, 520)
        lay = QVBoxLayout(self)
        n = len(info["versions"])
        titre = QLabel(tr("<b>Pixane Photo {v} est disponible</b> (vous avez la {actuelle}).", v=info["version"],
                          actuelle=__version__) + (" " + tr("{n} versions depuis la vôtre.", n=n) if n > 1 else ""))
        titre.setWordWrap(True)
        lay.addWidget(titre)
        lay.addWidget(QLabel(tr("Ce qui change :")))
        self.notes = QTextBrowser()
        self.notes.setOpenExternalLinks(True)
        self.notes.setMarkdown(mises_a_jour.texte_nouveautes(info["versions"]))
        lay.addWidget(self.notes, 1)
        boutons = QDialogButtonBox()
        telecharger = boutons.addButton(tr("Télécharger"), QDialogButtonBox.AcceptRole)
        telecharger.setDefault(True)
        boutons.addButton(tr("Plus tard"), QDialogButtonBox.RejectRole)
        boutons.accepted.connect(self.accept)
        boutons.rejected.connect(self.reject)
        lay.addWidget(boutons)


def ajuster_case(case, plus_long: str) -> None:
    """Case à chiffres à la largeur de son plus long texte (sinon Qt la fait bien plus large, et la barre du haut
    déborde : Qt cache alors toute une partie des options)."""
    case.setMaximumWidth(case.fontMetrics().horizontalAdvance(plus_long) + 44)


class CommandeProfondeur(QUndoCommand):
    """Image > Mode > 8 / 16 / 32 bits : la profondeur du document change avec ses calques (Annuler la remet)."""

    def __init__(self, doc: Document, avant, apres, bits_avant: int, bits_apres: int, texte: str):
        super().__init__(texte)
        self.doc, self.avant, self.apres = doc, avant, apres
        self.bits_avant, self.bits_apres = bits_avant, bits_apres

    def redo(self):
        self.doc.profondeur = self.bits_apres
        self.doc._ref16 = []
        self.doc.appliquer_etat(self.apres)

    def undo(self):
        self.doc.profondeur = self.bits_avant
        self.doc._ref16 = []
        self.doc.appliquer_etat(self.avant)


class CommandeEtat(QUndoCommand):
    """Passage d'un état du document à un autre. Deux commandes de même `cle` à la suite n'en font qu'une
    (ex. les lettres tapées dans un texte : un seul Ctrl+Z annule toute la saisie)."""

    def __init__(self, doc: Document, avant, apres, texte: str, cle=None):
        super().__init__(texte)
        self.doc, self.avant, self.apres, self.cle = doc, avant, apres, cle

    def id(self):
        return 1 if self.cle is not None else -1

    def mergeWith(self, autre):
        if autre.cle != self.cle or autre.doc is not self.doc:
            return False
        self.apres = autre.apres
        return True

    def redo(self):
        self.doc.appliquer_etat(self.apres)

    def undo(self):
        self.doc.appliquer_etat(self.avant)


class CommandeZoneTravail(CommandeEtat):
    """Taille de la zone de travail : les repères suivent aussi avec Annuler / Rétablir."""

    def __init__(self, doc: Document, avant, apres, texte: str, reperes_avant, reperes_apres):
        super().__init__(doc, avant, apres, texte)
        self.reperes_avant, self.reperes_apres = list(reperes_avant), list(reperes_apres)

    def redo(self):
        self.doc.reperes = list(self.reperes_apres)
        super().redo()

    def undo(self):
        self.doc.reperes = list(self.reperes_avant)
        super().undo()


class BoutonFamille(QToolButton):
    """Bouton d'une famille d'outils : un petit triangle dans le coin montre que d'autres outils sont cachés
    dessous (clic droit ou clic maintenu), comme dans Photoshop."""

    def paintEvent(self, ev):
        super().paintEvent(ev)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.palette().buttonText())
        w, h = self.width(), self.height()
        p.drawPolygon([QPointF(w - 2, h - 8), QPointF(w - 2, h - 2), QPointF(w - 8, h - 2)])
        p.end()


class Carte(QPushButton):
    """Bouton large du panneau IA : icône, titre et une ligne d'explication."""

    def __init__(self, titre: str, explication: str):
        super().__init__()
        self.setObjectName("carte")
        self.setCursor(Qt.PointingHandCursor)
        # place pour le titre et deux lignes d'explication (sinon coupée quand elle passe à la ligne : texte
        # anglais, Affichage > Taille de l'interface)
        from PySide6.QtGui import QFontMetrics
        self.setFixedHeight(max(64, 3 * QFontMetrics(self.font()).lineSpacing() + 20))
        self.image = QLabel()
        self.image.setFixedSize(28, 28)
        t = QLabel(f"<b>{titre}</b>")
        e = QLabel(explication)
        e.setObjectName("discret")
        e.setWordWrap(True)
        textes = QVBoxLayout()
        textes.setSpacing(1)
        textes.addWidget(t)
        textes.addWidget(e)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(12)
        lay.addWidget(self.image, 0, Qt.AlignVCenter)
        lay.addLayout(textes, 1)
        for w in (self.image, t, e):
            w.setAttribute(Qt.WA_TransparentForMouseEvents)

    def definir_icone(self, ic: QIcon):
        self.image.setPixmap(ic.pixmap(28, 28))


class Fenetre(ActionsCalques, ActionContour, Onglets, OptionsPinceau, OptionsForme, ActionsPhotoIA, QMainWindow):
    etat_moteur = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(NOM)
        self.resize(1440, 920)
        self.setAcceptDrops(True)
        # les essais automatiques utilisent leurs propres réglages (variable PIXANE_REGLAGES)
        self.reglages = reglages()
        self.doc: Document | None = None
        self._init_onglets()
        self.moteur = Moteur()
        self._taches = set()
        self._icones = []            # (objet, nom d'icône) à redessiner quand le thème change
        self.mode_theme = self.reglages.value("theme", theme.AUTO)
        self.couleurs = theme.appliquer(QApplication.instance(), self.mode_theme)
        self.texte_moteur = tr("démarrage…")

        self.canevas = Canevas()
        self.canevas.selection_modifiee.connect(self._selection_modifiee)
        self.canevas.refus.connect(lambda m: self.statusBar().showMessage(m, 6000))
        self.canevas.degrade_masque.connect(self._degrade_dans_masque)
        from .regles import entourer
        cadre, self.regle_h, self.regle_v, self.coin_regles = entourer(self.canevas)
        self.setCentralWidget(self._centre_avec_onglets(cadre))
        self.barre_agrandir = BarreAgrandir(self.canevas)
        self.barre_agrandir.pleine.setChecked(self.reglages.value("agrandir_pleine", True, type=bool))
        self.barre_agrandir.pleine.toggled.connect(lambda v: self.reglages.setValue("agrandir_pleine", v))
        self.barre_agrandir.lancer.connect(self._lancer_agrandir)
        self.barre_agrandir.annuler.connect(self._fin_agrandir)
        self.barre_agrandir.valeurs_changees.connect(self.canevas.definir_cadre)
        self.canevas.cadre_change.connect(self.barre_agrandir.definir_px)
        self.canevas.cadre_valide.connect(self._lancer_agrandir)
        self.canevas.cadre_annule.connect(self._fin_agrandir)
        self.canevas.texte_nouveau.connect(self._nouveau_texte)
        self.canevas.texte_choisi.connect(self._texte_choisi)
        self.canevas.trace_dessine.connect(self._trace_dessine)
        self.canevas.message.connect(lambda m: self.statusBar().showMessage(m, 6000))
        self.canevas.recadre_change.connect(self._recadre_change)
        self.canevas.recadre_valide.connect(self._recadrer)
        self.canevas.couleur_prise.connect(self._couleur_prise)
        self.canevas.transfo_change.connect(self._transfo_change)
        self.canevas.transfo_mode_change.connect(self._transfo_change)
        self.canevas.persp_valide.connect(self._valider_persp)
        self.canevas.persp_annule.connect(self._annuler_persp)
        self.canevas.transfo_valide.connect(self._valider_transfo)
        self.canevas.transfo_annule.connect(self._annuler_transfo)
        self.canevas.transfo_demandee.connect(self.transformer)
        self.canevas.selection_fleche.connect(self.decaler_selection)
        self._transfo_avant = None
        self.groupe_historique.indexChanged.connect(self._historique_bouge)
        QApplication.instance().installEventFilter(self)     # boutons retour / suivant de la souris
        self._session_texte = 0      # regroupe les changements d'un même texte dans Annuler

        self._menus()
        self._barre_commandes()
        self._barre_rapide()
        self._outils()
        self._panneau_ia()
        self._panneau_calques()
        self._panneau_historique()
        self._panneau_nuancier()
        self._panneau_actions()
        self._panneau_texte()
        self._barre_etat()
        from .selection_ia import SelectionAuto
        self.selection_auto = SelectionAuto(self)
        from .suppression import Suppression
        self.suppression = Suppression(self)
        self.canevas.fin_session_ia.connect(self.selection_auto.fin_session)
        from .recuperation import Recuperation
        self._recuperation = Recuperation(self)
        if not os.environ.get("PIXANE_REGLAGES") or os.environ.get("PIXANE_RECUPERATION"):
            QTimer.singleShot(400, self._recuperation.proposer)
        self._appliquer_theme()
        self._choisir_outil(PINCEAU)
        self._actualiser()
        self.option_polices(self.a_option_polices.isChecked(), demarrage=True)
        self.a_langues_orthographe.setEnabled(self.a_option_orthographe.isChecked())
        if self.a_option_orthographe.isChecked():
            from . import orthographe
            orthographe.charger_mots_perso()
        self._demarrer_moteur()
        if self.reglages.value("maj_auto", False, type=bool):
            QTimer.singleShot(8000, lambda: self.verifier_maj(silencieux=True))
        QTimer.singleShot(3000, self._convertir_pinceaux)
        if not os.environ.get("PIXANE_REGLAGES") and self.reglages.value("polices_semblables", True, type=bool):
            from . import polices_semblables     # mémoire des polices (police semblable) : processus à part
            QTimer.singleShot(60000, polices_semblables.lancer_en_fond)
        # suivre les changements de couleur ou de thème faits dans Windows
        self._signature_windows = theme.signature_windows()
        self._veille_windows = QTimer(self)
        self._veille_windows.timeout.connect(self._verifier_windows)
        self._veille_windows.start(2000)

    def option_polices(self, actif: bool, demarrage: bool = False) -> None:
        """Affichage > Recherche de police semblable (aussi choisi à l'installation) : menu et bouton montrés ou
        cachés ; activé, la mémoire des polices se prépare en fond ; désactivé, elle est effacée."""
        from . import polices_semblables
        self.a_police_semblable.setVisible(actif)
        self.b_police.setVisible(actif)
        if not demarrage:
            self.reglages.setValue("polices_semblables", actif)
        if actif:
            if not demarrage and not os.environ.get("PIXANE_REGLAGES"):
                polices_semblables.lancer_en_fond()
        else:                       # décoché (ici ou à l'installation) : la mémoire des polices ne garde pas de place
            self._effacer_memoire_polices()

    def option_orthographe(self, actif: bool) -> None:
        """Affichage > Orthographe et césure : soulignement et césure (les textes en cadre sont redessinés)."""
        self.reglages.setValue("orthographe", actif)
        self.a_langues_orthographe.setEnabled(actif)
        if actif:
            from . import orthographe
            orthographe.charger_mots_perso()
        self._redessiner_textes()
        self.panneau_texte.option_orthographe()

    def langues_orthographe(self) -> None:
        from .dialogue_orthographe import DialogueLangues
        if DialogueLangues(self).exec():
            self.panneau_texte.option_orthographe()

    def _redessiner_textes(self) -> None:
        """Textes à césure redessinés (option changée) : aucune étape d'Annuler, le texte lui-même ne change pas."""
        from .texte import mise, rendre
        mise.cache_clear()
        for doc in list(self.documents):
            w, h = doc.taille()
            for i, c in enumerate(doc.calques):
                if c.texte is not None and c.texte.cesure and c.texte.cadre_l > 0:
                    doc.apercu_calque(i, rendre(c.texte, w, h), texte=c.texte)

    def rechercher_textes(self) -> None:
        from .rechercher_texte import FenetreRechercher
        if getattr(self, "_rechercher", None) is None:
            self._rechercher = FenetreRechercher(self)
        self._rechercher.show()
        self._rechercher.raise_()
        self._rechercher.cherche.setFocus()
        self._rechercher.cherche.selectAll()

    def _effacer_memoire_polices(self, essais: int = 5) -> None:
        """Le fichier peut être pris un instant (antivirus qui lit un fichier juste écrit) : nouvel essai plus tard."""
        from . import polices_semblables
        try:
            Path(polices_semblables.fichier_memoire()).unlink(missing_ok=True)
        except OSError:
            if essais > 1:
                QTimer.singleShot(1000, lambda: self._effacer_memoire_polices(essais - 1))

    def police_semblable(self) -> None:
        """Sélection > Trouver une police semblable : d'après les lettres sélectionnées (outil Sélection de texte)."""
        if not self.doc:
            return
        from dataclasses import replace as remplacer
        from .dialogue_polices import FenetrePolices
        from .document import masque as masque_selection
        rect = self.doc.rect_selection()
        m = masque_selection(self.doc.selection)
        if rect is None or rect.width() < 8 or rect.height() < 8:
            QMessageBox.information(self, tr("Police semblable"), tr(
                "Sélectionne d'abord les lettres du texte : outil Sélection de texte (Y), un cadre autour du texte."))
            return
        zone = m[rect.top():rect.bottom() + 1, rect.left():rect.right() + 1]
        if (zone > 127).mean() > 0.85:
            QMessageBox.information(self, tr("Police semblable"), tr(
                "La sélection est un bloc plein : il faut les lettres seules. Utilise l'outil Sélection de texte "
                "(Y) : il ne garde que les lettres."))
            return
        a = tableau(self.doc.image.copy(rect).convertToFormat(FORMAT_IMAGE)).copy()
        a[:, :, 3] = np.minimum(a[:, :, 3], zone)          # seulement les lettres, sur fond blanc
        lettres = QImage(rect.width(), rect.height(), QImage.Format_ARGB32_Premultiplied)
        lettres.fill(Qt.white)
        p = QPainter(lettres)
        from .document import qimage_rgba
        p.drawImage(0, 0, qimage_rgba(a))
        p.end()
        c = self.doc.calque_actif
        depart = c.texte.texte.replace("\n", " / ") if c.texte is not None else \
            self.reglages.value("police_lettres", "", type=str)
        d = FenetrePolices(lettres, zone, depart, c.texte is not None, self)
        if not d.exec() or d.choisi is None:
            self.reglages.setValue("police_lettres", d.texte.text())
            return
        self.reglages.setValue("police_lettres", d.texte.text())
        r = d.choisi
        if d.action == "appliquer" and c.texte is not None:
            t = remplacer(c.texte, police=r.famille, gras=r.gras, italique=r.italique)
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(), self.doc.etat_texte_modifie(self.doc.actif, t),
                                              tr("Police semblable")))
        else:
            couleur = a[:, :, :3][zone > 127].mean(axis=0) if (zone > 127).any() else (255, 255, 255)
            t = Texte(texte=d.lettres() or "Texte", police=r.famille, gras=r.gras, italique=r.italique,
                      taille=float(rect.height()) / max(1, d.lettres().count("\n") + 1),
                      couleur=QColor(*(int(v) for v in couleur)).name(QColor.HexArgb),
                      x=rect.center().x(), y=rect.center().y())
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(), self.doc.etat_nouveau_texte(t),
                                              tr("Police semblable")))
        self.statusBar().showMessage(tr("Police : {nom}", nom=r.famille), 8000)

    def _convertir_pinceaux(self) -> None:
        """Une seule fois : les pinceaux et motifs ajoutés avant le 14/11/2026 (copies telles quelles, parfois plus
        d'un Go) deviennent des paquets lus à la demande. En arrière-plan ; Pixane reste utilisable."""
        from .bibliotheque import bibliotheque
        b = bibliotheque()
        if not b.anciens():
            return
        self.statusBar().showMessage(tr("Rangement des pinceaux ajoutés (une seule fois, en arrière-plan)…"), 15000)

        def fini(n):
            try:
                self.statusBar().showMessage(tr("Pinceaux rangés : ils s'ouvrent maintenant sans attente."), 8000)
            except RuntimeError:                         # fenêtre fermée entre-temps
                pass
        b.convertir_anciens(fini)

    # ================================================================ interface
    def _icone(self, objet, nom: str):
        self._icones.append((objet, nom))
        return objet

    def _action(self, menu, texte, raccourci=None, fonction=None, cle=None, icone=None):
        a = QAction(texte, self)
        if raccourci:
            a.setShortcut(QKeySequence(raccourci))
        if fonction:
            a.triggered.connect(fonction)
        if menu is not None:
            menu.addAction(a)
        if cle:
            setattr(self, cle, a)
        if icone:
            self._icone(a, icone)
        return a

    def _menus(self):
        m = self.menuBar().addMenu(tr("&Fichier"))
        self._action(m, tr("Nouvelle image…"), QKeySequence.New, self.nouvelle_image, "a_nouvelle")
        self._action(m, tr("Nouvelle image depuis le presse-papiers"), "Ctrl+Alt+V", self.nouvelle_depuis_presse_papiers,
                     "a_nouvelle_pp")
        self._action(m, tr("Ouvrir…"), QKeySequence.Open, self.ouvrir, "a_ouvrir", "ouvrir")
        self.m_recents = m.addMenu(tr("Fichiers récents"))
        self.m_recents.aboutToShow.connect(self._remplir_recents)
        self._action(m, tr("Enregistrer"), QKeySequence.Save, self.enregistrer, "a_enregistrer", "enregistrer")
        self._action(m, tr("Enregistrer sous…"), "Ctrl+Shift+S", self.enregistrer_sous, "a_enregistrer_sous")
        self._action(m, tr("Exporter sous…"), "Ctrl+Alt+Shift+W", self.exporter_sous, "a_exporter_sous")
        self._action(m, tr("Exporter pour le web…"), "Ctrl+Alt+Shift+S", self.exporter_web, "a_exporter_web")
        self._action(m, tr("Exporter pour l'impression (CMJN)…"), None, self.exporter_impression, "a_exporter_cmjn")
        self._action(m, tr("Traitement par lot…"), None, self.traitement_lot, "a_lot", "lot")
        m.addSeparator()
        self._action(m, tr("Imprimer…"), QKeySequence.Print, self.imprimer, "a_imprimer")
        m.addSeparator()
        self._action(m, tr("Fermer la photo"), "Ctrl+W", lambda: self.fermer_onglet(), "a_fermer")
        self._action(m, tr("Photo suivante"), "Ctrl+Tab", lambda: self.onglet_suivant(1))
        self._action(m, tr("Photo précédente"), "Ctrl+Shift+Tab", lambda: self.onglet_suivant(-1))
        m.addSeparator()
        self._action(m, tr("Quitter"), "Ctrl+Q", self.close)

        m = self.menuBar().addMenu(tr("&Édition"))
        # Annuler / Rétablir : pendant un travail pas encore validé (Transformer, Agrandir, Recadrer), geste par geste
        self.a_annuler = QAction(tr("Annuler|édition"), self)
        self.a_annuler.setShortcut(QKeySequence.Undo)
        self.a_annuler.triggered.connect(self.retour)
        self.a_retablir = QAction(tr("Rétablir|édition"), self)
        self.a_retablir.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.a_retablir.triggered.connect(self.suivant)
        g = self.groupe_historique
        for s in (g.canUndoChanged, g.canRedoChanged, g.undoTextChanged, g.redoTextChanged, g.activeStackChanged,
                  self.canevas.travail_change):
            s.connect(self._maj_annuler)
        self._maj_annuler()
        self._icone(self.a_annuler, "annuler")
        self._icone(self.a_retablir, "retablir")
        m.addAction(self.a_annuler)
        m.addAction(self.a_retablir)
        m.addSeparator()
        self._action(m, tr("Couper"), QKeySequence.Cut, self.couper, "a_couper")
        self._action(m, tr("Copier"), QKeySequence.Copy, self.copier, "a_copier")
        self._action(m, tr("Coller"), QKeySequence.Paste, self.coller, "a_coller")
        self._action(m, tr("Supprimer la sélection"), QKeySequence.Delete, self.supprimer_selection,
                     "a_supprimer_selection")
        m.addSeparator()
        self._action(m, tr("Remplir avec un motif…"), None, self.remplir_motif, "a_remplir_motif")
        self._action(m, tr("Rechercher et remplacer dans les textes…"), "Ctrl+H", self.rechercher_textes,
                     "a_rechercher_textes")
        m.addSeparator()
        self._action(m, tr("Transformer le calque"), "Ctrl+T", self.transformer, "a_transformer")
        sous = m.addMenu(tr("Transformation"))
        self._m_transformation = sous
        for mode, texte in (("perspective", tr("Perspective")), ("distordre", tr("Distordre")),
                            ("deformation", tr("Déformation"))):
            self._action(sous, texte, None, lambda *_, m_=mode: self.transformer(m_), f"a_transfo_{mode}")
        m.addSeparator()
        self._action(m, tr("Préférences…"), "Ctrl+,", self.preferences, "a_preferences")

        m = self.menuBar().addMenu(tr("&Sélection"))
        self._action(m, tr("Tout sélectionner"), "Ctrl+A", lambda: self._modifier_selection("tout"), "a_tout")
        self._action(m, tr("Désélectionner"), "Ctrl+D", lambda: self._modifier_selection("rien"), "a_rien")
        self._action(m, tr("Inverser la sélection"), "Ctrl+Shift+I", lambda: self._modifier_selection("inverser"),
                     "a_inverser")
        sous = m.addMenu(tr("Modifier la sélection"))
        self._action(sous, tr("Agrandir…"), None, lambda: self._modifier_bord("agrandir"), "a_sel_agrandir")
        self._action(sous, tr("Réduire…"), None, lambda: self._modifier_bord("reduire"), "a_sel_reduire")
        self._action(sous, tr("Adoucir les bords…"), None, lambda: self._modifier_bord("adoucir"), "a_sel_adoucir")
        self._action(m, tr("Améliorer le contour…"), "Ctrl+Alt+R", self.ameliorer_contour, "a_contour")
        self._action(m, tr("Plage de couleurs…"), None, self.plage_couleurs, "a_plage_couleurs")
        self._action(m, tr("Sélectionner le sujet (IA)"), "Ctrl+Alt+S", self.selectionner_sujet, "a_sujet")
        self._action(m, tr("Sélectionner le ciel (IA)"), None, self.ia_selection_ciel, "a_sel_ciel")
        self._action(m, tr("Trouver une police semblable…"), None, self.police_semblable, "a_police_semblable")
        m.addSeparator()
        self._action(m, tr("Recadrer à la sélection"), None, self._recadrer_selection, "a_recadrer_selection",
                     "recadrer")

        m = self.menuBar().addMenu(tr("I&mage"))
        self._m_image = m
        self._action(m, tr("Réglages de l'image…"), "Ctrl+U", self.reglages_image, "a_reglages_image", "reglages")
        m.addSeparator()
        sous = m.addMenu(tr("Mode"))
        groupe = QActionGroup(self)
        for mode, texte in (("rvb", tr("Couleurs RVB")), ("gris", tr("Niveaux de gris"))):
            a = QAction(texte, self, checkable=True)
            a.triggered.connect(lambda *_, md=mode: self.changer_mode(md))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_mode = groupe
        sous.addSeparator()
        groupe = QActionGroup(self)
        for bits, texte in ((8, tr("8 bits par couche")), (16, tr("16 bits par couche")),
                            (32, tr("32 bits par couche (HDR)"))):
            a = QAction(texte, self, checkable=True)
            a.setData(bits)
            a.triggered.connect(lambda *_, b=bits: self.changer_profondeur(b))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_bits = groupe
        sous.addSeparator()
        self.a_tramage = QAction(tr("Tramage vers 8 bits"), self, checkable=True)
        self.a_tramage.setToolTip(tr("Image 16 ou 32 bits montrée, exportée ou passée en 8 bits : un très léger grain "
                                     "invisible évite les marches dans les dégradés (comme Photoshop)."))
        self.a_tramage.setChecked(self.reglages.value("tramage", True, type=bool))
        self.a_tramage.toggled.connect(self.basculer_tramage)
        self.basculer_tramage(self.a_tramage.isChecked())
        sous.addAction(self.a_tramage)
        self._m_mode = sous
        m.addSeparator()
        self._action(m, tr("Taille de l'image…"), "Ctrl+Alt+I", self.taille_image, "a_taille")
        self._action(m, tr("Mise à l'échelle d'après le contenu…"), None, self.echelle_contenu, "a_echelle_contenu")
        self._action(m, tr("Taille de la zone de travail…"), "Ctrl+Alt+C", self.zone_travail, "a_zone_travail")
        self._action(m, tr("Tout faire apparaître"), None, self.tout_faire_apparaitre, "a_tout_apparaitre")
        self._action(m, tr("Pivoter de 90° à droite"), None, lambda: self._geometrie(tr("Pivoter"), 90), "a_pivoter_d")
        self._action(m, tr("Pivoter de 90° à gauche"), None, lambda: self._geometrie(tr("Pivoter"), -90),
                     "a_pivoter_g")
        self._action(m, tr("Pivoter de 180°"), None, lambda: self._geometrie(tr("Pivoter"), 180), "a_pivoter_180")
        self._action(m, tr("Pivoter selon un angle…"), None, self.pivoter_angle, "a_pivoter_angle")
        self._action(m, tr("Retourner horizontalement"), None, lambda: self._geometrie(tr("Retourner"), "h"),
                     "a_miroir_h")
        self._action(m, tr("Retourner verticalement"), None, lambda: self._geometrie(tr("Retourner"), "v"),
                     "a_miroir_v")
        self._action(m, tr("Redresser…"), None, self.redresser, "a_redresser")
        self._action(m, tr("Recadrage en perspective"), None, self.recadrage_perspective, "a_recadrage_persp")

        m = self.menuBar().addMenu(tr("&Calque"))
        self._action(m, tr("Style du calque…"), "Ctrl+Alt+F", self.style_calque, "a_style", "style")
        self._action(m, tr("Copier le style"), None, self.copier_style, "a_copier_style")
        self._action(m, tr("Coller le style"), None, self.coller_style, "a_coller_style")
        self._action(m, tr("Enlever le style"), None, self.enlever_style, "a_enlever_style")
        self._action(m, tr("Mettre le style dans les pixels"), None, self.figer_style, "a_figer_style")
        m.addSeparator()
        self._action(m, tr("Nouveau calque"), "Ctrl+Shift+N", lambda: self.calques.nouveau() if self.doc else None,
                     "a_nouveau_calque")
        self._action(m, tr("Dupliquer le calque"), "Ctrl+J", lambda: self.calques.dupliquer() if self.doc else None,
                     "a_dupliquer_calque")
        self._action(m, tr("Fusionner les calques"), "Ctrl+E", lambda: self.calques.fusionner() if self.doc else None,
                     "a_fusionner_calques")
        self._action(m, tr("Aplatir l'image"), None, lambda: self.calques.aplatir() if self.doc else None,
                     "a_aplatir")
        m.addSeparator()
        self._action(m, tr("Harmoniser avec l'arrière-plan…"), None, self.harmoniser, "a_harmoniser")
        m_filtres = self._menus_calques(self._m_image, m)
        m_filtres.addSeparator()
        self._action(m_filtres, tr("Flou selon la profondeur (IA)…"), None, self.ia_flou_profondeur,
                     "a_ia_profondeur")

        m = self.menuBar().addMenu(tr("&Affichage"))
        self._action(m, tr("Zoom avant"), "Ctrl++", lambda: self.canevas.zoomer(1.25), "a_zoom_plus", "zoom_plus")
        self._action(m, tr("Zoom arrière"), "Ctrl+-", lambda: self.canevas.zoomer(0.8), "a_zoom_moins", "zoom_moins")
        self._action(m, tr("Ajuster à la fenêtre"), "Ctrl+0", self.canevas.ajuster, "a_ajuster", "ajuster")
        self._action(m, tr("Taille réelle (100 %)"), "Ctrl+1", self.canevas.zoom_100)
        m.addSeparator()
        self.a_epreuve = self._action(m, tr("Aperçu de l'impression (CMJN)"), "Ctrl+Alt+Y", self.basculer_epreuve,
                                      "a_epreuve")
        self.a_epreuve.setCheckable(True)
        self.a_exposition = self._action(m, tr("Exposition 32 bits…"), None, self.exposition_ecran, "a_exposition")
        self.a_exposition.setToolTip(tr("Image 32 bits : régler l'aperçu à l'écran pour voir les zones plus "
                                        "claires que le blanc (l'image ne change pas)."))
        m.addSeparator()
        self.a_barre_rapide = self._action(m, tr("Barre d'accès rapide"), None, None, "a_barre_rapide")
        self.a_barre_rapide.setCheckable(True)
        # option choisie à l'installation (case « Recherche de police semblable »), modifiable ici
        a = self._action(m, tr("Recherche de police semblable"), None, None, "a_option_polices")
        a.setCheckable(True)
        a.setChecked(self.reglages.value("polices_semblables", True, type=bool))
        a.setToolTip(tr("Coché : Sélection > Trouver une police semblable, et Pixane Photo prépare une fois la liste de tes "
                        "polices en arrière-plan. La durée dépend du nombre de polices installées (environ 1 min 20 et "
                        "15 Mo pour 1 200 polices). Décoché : rien de tout cela."))
        a.toggled.connect(lambda v: self.option_polices(v))
        # option choisie à l'installation (case « Orthographe et césure » et ses langues), modifiable ici
        a = self._action(m, tr("Orthographe et césure"), None, None, "a_option_orthographe")
        a.setCheckable(True)
        a.setChecked(self.reglages.value("orthographe", True, type=bool))
        a.setToolTip(tr("Coché : mots mal orthographiés soulignés en rouge dans le panneau Texte (clic droit : "
                        "suggestions) et césure possible des textes en cadre. Décoché : rien de tout cela."))
        a.toggled.connect(self.option_orthographe)
        self._action(m, tr("Langues de l'orthographe…"), None, self.langues_orthographe, "a_langues_orthographe")
        m.setToolTipsVisible(True)
        m.addSeparator()
        self._menu_regles(m)
        m.addSeparator()
        sous = m.addMenu(tr("Thème"))
        groupe = QActionGroup(self)
        for mode, texte in ((theme.AUTO, tr("Comme Windows")), (theme.CLAIR, tr("Clair")), (theme.SOMBRE, tr("Sombre"))):
            a = QAction(texte, self, checkable=True)
            a.setData(mode)
            a.setChecked(mode == self.mode_theme)
            a.triggered.connect(lambda _=False, md=mode: self.changer_theme(md))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_theme = groupe
        sous = m.addMenu(tr("Langue"))
        groupe = QActionGroup(self)
        actuel = self.reglages.value("langue", langue.AUTO)
        for code, texte in [(langue.AUTO, tr("Comme Windows"))] + list(langue.LANGUES.items()):
            a = QAction(texte, self, checkable=True)
            a.setData(code)
            a.setChecked(code == actuel)
            a.triggered.connect(lambda _=False, c=code: self.changer_langue(c))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_langue = groupe
        # taille de toute l'interface (au prochain démarrage) et des icônes des outils (tout de suite)
        from .__main__ import ECHELLES
        sous = m.addMenu(tr("Taille de l'interface"))
        sous.setToolTipsVisible(True)
        groupe = QActionGroup(self)
        actuelle = self._echelle_reglee()
        for pc in ECHELLES:
            texte = {75: tr("{n} % (très compacte)", n=pc), 85: tr("{n} % (compacte, petits écrans)", n=pc),
                     100: tr("{n} % (normale)", n=pc)}.get(pc, f"{pc} %")
            a = QAction(texte, self, checkable=True)
            a.setData(pc)
            a.setChecked(pc == actuelle)
            a.triggered.connect(lambda _=False, v=pc: self.changer_echelle(v))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_echelle = groupe
        sous = m.addMenu(tr("Taille des icônes des outils"))
        groupe = QActionGroup(self)
        actuelle = self._taille_icones()
        for n, texte in ((18, tr("Petites")), (22, tr("Normales")), (28, tr("Grandes")), (36, tr("Très grandes"))):
            a = QAction(texte, self, checkable=True)
            a.setData(n)
            a.setChecked(n == actuelle)
            a.triggered.connect(lambda _=False, v=n: self.changer_taille_icones(v))
            groupe.addAction(a)
            sous.addAction(a)
        self._actions_icones = groupe

        m = self.menuBar().addMenu(tr("&IA"))
        self._action(m, tr("Effacer"), "Shift+E", self.ia_effacer, "a_effacer", "effacer")
        self._action(m, tr("Supprimer les personnes…"), None, self.ia_supprimer_personnes, "a_ia_personnes")
        self._action(m, tr("Remplir"), "Shift+R", self.ia_remplir, "a_remplir", "remplir")
        self._action(m, tr("Modifier avec une consigne…"), "Shift+M", self.ia_modifier, "a_modifier", "modifier")
        self._action(m, tr("Créer une image d'après un texte…"), None, self.ia_creer, "a_ia_creer")
        self._action(m, tr("Agrandir l'image…"), "Shift+A", self.ia_agrandir, "a_agrandir", "agrandir")
        self._action(m, tr("Upscale…"), "Shift+U", self.ia_upscale, "a_upscale", "upscale")
        self._action(m, tr("Supprimer l'arrière-plan"), "Shift+B", self.supprimer_arriere_plan, "a_arriere_plan",
                     "arriere_plan")
        m.addSeparator()
        self._action(m, tr("Réduire le bruit (IA)"), None, self.ia_debruiter, "a_ia_bruit")
        self._action(m, tr("Netteté (IA)"), None, self.ia_nettete, "a_ia_nettete")
        self._action(m, tr("Restaurer une vieille photo…"), None, self.ia_restaurer, "a_ia_restaurer")
        self._action(m, tr("Coloriser"), None, self.ia_coloriser, "a_ia_coloriser")
        self._action(m, tr("Changer la lumière…"), None, self.ia_lumiere, "a_ia_lumiere")
        self._action(m, tr("Retouche portrait…"), None, self.ia_portrait, "a_ia_portrait")
        self._action(m, tr("Remplacer le ciel…"), None, self.ia_remplacer_ciel, "a_ia_ciel")
        m.addSeparator()
        a = self._action(m, tr("Mettre les résultats dans un nouveau calque"), None, None, "a_ia_nouveau_calque")
        a.setCheckable(True)
        a.setChecked(self.reglages.value("ia_nouveau_calque", False, type=bool))
        a.setToolTip(tr("Décoché : le résultat de l'IA va dans le calque choisi (il le suit quand on le déplace ou "
                        "le redimensionne). Coché : chaque résultat va dans un nouveau calque."))
        a.toggled.connect(lambda v: self.reglages.setValue("ia_nouveau_calque", v))
        m.setToolTipsVisible(True)
        m.addSeparator()
        self._action(m, tr("Installer le moteur IA…"), None, self.installer_moteur, "a_installer_moteur")

        m = self.menuBar().addMenu(tr("&Aide"))
        self._action(m, tr("Guide de Pixane Photo"), None, lambda: self.guide(), "a_guide")
        self._action(m, tr("Raccourcis"), "F1", lambda: self.guide(tr("Raccourcis")), "a_raccourcis")
        m.addSeparator()
        self._action(m, tr("Rechercher une mise à jour…"), None, lambda: self.verifier_maj(False))
        a = self._action(m, tr("Vérifier les mises à jour au démarrage"), None, None, "a_maj_auto")
        a.setCheckable(True)
        a.setChecked(self.reglages.value("maj_auto", False, type=bool))
        a.toggled.connect(lambda v: self.reglages.setValue("maj_auto", v))
        m.addSeparator()
        self._action(m, tr("À propos de Pixane Photo"), None, self.a_propos)

    def _barre_rapide(self):
        """2e ligne sous le menu : commandes de calque et d'image toujours à portée (Affichage > Barre d'accès
        rapide pour la masquer)."""
        b = QToolBar(tr("Accès rapide"))
        self.barre_rapide = b
        b.setObjectName("barre_rapide")
        b.setMovable(False)
        b.setIconSize(QSize(18, 18))
        self.addToolBarBreak(Qt.TopToolBarArea)
        self.addToolBar(Qt.TopToolBarArea, b)
        icones = {"a_transformer": "transformer", "a_pivoter_g": "pivoter_g", "a_pivoter_d": "pivoter_d",
                  "a_miroir_h": "miroir_h", "a_miroir_v": "miroir_v", "a_grouper": "grouper",
                  "a_degrouper": "degrouper", "a_retourner_calque_h": "sym_h", "a_retourner_calque_v": "sym_v"}
        for cle, nom in icones.items():
            self._icone(getattr(self, cle), nom)
        lots = [("a_transformer", "a_pivoter_g", "a_pivoter_d", "a_miroir_h", "a_miroir_v"),
                ("a_grouper", "a_degrouper", "a_retourner_calque_h", "a_retourner_calque_v"),
                tuple(f"a_aligner_{m}" for m in ("gauche", "centre_h", "droite", "haut", "centre_v", "bas")),
                ("a_repartir_h", "a_repartir_v")]
        bulles = {"a_pivoter_g": tr("Pivoter l'image de 90° à gauche"), "a_pivoter_d": tr("Pivoter l'image de 90° à droite"),
                  "a_miroir_h": tr("Retourner l'image entière horizontalement"),
                  "a_miroir_v": tr("Retourner l'image entière verticalement"),
                  "a_retourner_calque_h": tr("Retourner le calque : symétrie horizontale"),
                  "a_retourner_calque_v": tr("Retourner le calque : symétrie verticale")}
        for k, lot in enumerate(lots):
            if k:
                b.addSeparator()
            for cle in lot:
                a = getattr(self, cle)
                bouton = b.addAction(a)
                texte = bulles.get(cle, a.text().replace("&", ""))
                if cle.startswith("a_aligner_"):
                    texte = tr("Aligner : {quoi}", quoi=a.text().lower())
                raccourci = a.shortcut().toString(QKeySequence.NativeText)
                b.widgetForAction(a).setToolTip(texte + (f" ({raccourci})" if raccourci else ""))
        visible = self.reglages.value("barre_rapide", True, type=bool)
        b.setVisible(visible)
        self.alignement_deplacer.setVisible(not visible)
        self.a_barre_rapide.setChecked(visible)
        self.a_barre_rapide.toggled.connect(lambda v: (b.setVisible(v), self.alignement_deplacer.setVisible(not v),
                                                       self.reglages.setValue("barre_rapide", v)))

    def _barre_commandes(self):
        """Barre du haut : fichiers, annuler, options de l'outil, zoom, thème."""
        b = QToolBar(tr("Commandes"))
        self.barre_haut = b
        b.setMovable(False)
        b.setIconSize(QSize(20, 20))
        self.addToolBar(Qt.TopToolBarArea, b)
        for a in (self.a_ouvrir, self.a_enregistrer):
            b.addAction(a)
        b.addSeparator()
        b.addAction(self.a_annuler)
        b.addAction(self.a_retablir)
        b.addSeparator()

        # options de l'outil (comme Photoshop) : chaque groupe n'apparaît qu'avec les outils qui s'en servent
        self.options = QWidget()
        tout = QHBoxLayout(self.options)
        tout.setContentsMargins(6, 0, 6, 0)
        tout.setSpacing(14)
        self.opt_taille = QWidget()
        lay = QHBoxLayout(self.opt_taille)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Taille")))
        # glissière progressive (fine pour les petites tailles, jusqu'à 5000 px) et case où taper la taille
        self.curseur_taille = QSlider(Qt.Horizontal)
        self.curseur_taille.setRange(0, 1000)
        self.curseur_taille.setFixedWidth(110)
        self.curseur_taille.setValue(position_taille(self.canevas.taille_pinceau))
        self.valeur_taille = QSpinBox()
        self.valeur_taille.setRange(2, TAILLE_MAX)
        self.valeur_taille.setSuffix(" px")
        self.valeur_taille.setKeyboardTracking(False)
        self.valeur_taille.setValue(self.canevas.taille_pinceau)
        ajuster_case(self.valeur_taille, "5000 px")
        self.valeur_taille.setToolTip(tr("Taille du pinceau (2 à {max} px) ; [ et ] pour la changer",
                                         max=TAILLE_MAX))
        self.curseur_taille.valueChanged.connect(lambda v: self.canevas.definir_taille(taille_position(v)))
        self.valeur_taille.valueChanged.connect(self.canevas.definir_taille)
        self.canevas.taille_changee.connect(self._taille_changee)
        self.canevas.taille_changee.connect(lambda _v: self.pinceau_barre_change()
                                            if hasattr(self, "case_calque_pinceau") else None)
        lay.addWidget(self.curseur_taille)
        lay.addWidget(self.valeur_taille)
        tout.addWidget(self.opt_taille)
        self.opt_selection = QWidget()
        lay = QHBoxLayout(self.opt_selection)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.p_nouvelle = QPushButton(tr("Nouvelle"))
        self.p_ajouter = QPushButton(tr("Ajouter"))
        self.p_retirer = QPushButton(tr("Retirer"))
        self.p_nouvelle.setToolTip(tr("Nouvelle : la sélection tracée remplace l'ancienne (un simple clic "
                                      "désélectionne). Pendant le tracé : Maj ajoute, Alt retire."))
        self.p_ajouter.setToolTip(tr("Ajouter à la sélection (Maj pendant le tracé du rectangle ou du lasso)"))
        self.p_retirer.setToolTip(tr("Retirer de la sélection (Alt pendant le tracé)"))
        groupe = QButtonGroup(self)
        for p_, mode in ((self.p_nouvelle, "nouvelle"), (self.p_ajouter, "ajouter"), (self.p_retirer, "retirer")):
            p_.setObjectName("pastille")
            p_.setCheckable(True)
            p_.setCursor(Qt.PointingHandCursor)
            p_.clicked.connect(lambda _=False, m=mode: self._mode_selection(m))
            groupe.addButton(p_)
            lay.addWidget(p_)
        self.p_nouvelle.setChecked(True)
        tout.addWidget(self.opt_selection)
        self.opt_transfo = QWidget()
        lay = QHBoxLayout(self.opt_transfo)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.cases_transfo = {}
        lay.addWidget(QLabel(tr("Mode")))
        self.mode_transfo = QComboBox()
        for mode, texte in (("libre", tr("Libre")), ("perspective", tr("Perspective")),
                            ("distordre", tr("Distordre")), ("deformation", tr("Déformation"))):
            self.mode_transfo.addItem(texte, mode)
        self.mode_transfo.setToolTip(tr("Libre : taille, rotation (Ctrl+coin : le coin bouge seul). Perspective : un "
                                        "coin tiré entraîne son voisin en miroir. Distordre : chaque coin bouge seul. "
                                        "Déformation : grille de points pour courber l'image."))
        self.mode_transfo.activated.connect(self._mode_transfo_choisi)
        lay.addWidget(self.mode_transfo)
        for cle, texte, bas, haut, suffixe, aide in (
                ("l", tr("Largeur"), 1, 5000, " %", tr("Largeur en % de la taille de départ")),
                ("h", tr("Hauteur"), 1, 5000, " %", tr("Hauteur en % de la taille de départ")),
                ("a", tr("Angle"), -180, 180, " °", tr("Angle en degrés (sens des aiguilles d'une montre ; négatif : "
                                                        "sens inverse). Flèches : 1° ; Maj+flèches : 10°"))):
            lay.addWidget(QLabel(texte))
            case = QDoubleSpinBox()
            case.setRange(bas, haut)
            case.setDecimals(1)
            case.setSingleStep(1)
            case.setSuffix(suffixe)
            case.setKeyboardTracking(False)
            case.setToolTip(aide)
            case.valueChanged.connect(self._transfo_tapee)
            ajuster_case(case, "-180,0 °" if cle == "a" else "5000,0 %")
            lay.addWidget(case)
            self.cases_transfo[cle] = case
        b_ok = QPushButton(tr("Valider"))
        b_ok.clicked.connect(self._valider_transfo)
        b_non = QPushButton(tr("Annuler"))
        b_non.clicked.connect(self._annuler_transfo)
        lay.addWidget(b_ok)
        lay.addWidget(b_non)
        self.opt_transfo.hide()
        tout.addWidget(self.opt_transfo)
        self.opt_persp = QWidget()
        lay = QHBoxLayout(self.opt_persp)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Recadrage en perspective : posez les 4 coins sur les bords de l'objet")))
        b_ok = QPushButton(tr("Recadrer"))
        b_ok.clicked.connect(self._valider_persp)
        b_non = QPushButton(tr("Annuler"))
        b_non.clicked.connect(self._annuler_persp)
        lay.addWidget(b_ok)
        lay.addWidget(b_non)
        self.opt_persp.hide()
        tout.addWidget(self.opt_persp)
        self._options_retouche(tout)
        self._options_pinceau(tout)
        self._options_dessin(tout)
        self._options_forme(tout)
        self._options_recadrer(tout)
        b.addWidget(self.options)

        vide = QWidget()
        vide.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        b.addWidget(vide)
        b.addAction(self.a_zoom_moins)
        self.valeur_zoom = QLabel("—")
        self.valeur_zoom.setMinimumWidth(52)
        self.valeur_zoom.setAlignment(Qt.AlignCenter)
        b.addWidget(self.valeur_zoom)
        b.addAction(self.a_zoom_plus)
        b.addAction(self.a_ajuster)
        b.addSeparator()
        self.a_theme = QAction(tr("Thème clair / sombre"), self)
        self.a_theme.triggered.connect(self._basculer_theme)
        b.addAction(self.a_theme)

    def _options_retouche(self, tout: QHBoxLayout):
        """Pinceau de couleur et tampon : couleur, opacité, dureté."""
        self.opt_couleur = BoutonCouleur(tr("Couleur du pinceau"))
        self.opt_couleur.definir(self.reglages.value("peinture_couleur", "#ff000000"))
        self.opt_couleur.change.connect(self._couleur_peinture)
        self._couleur_peinture(self.opt_couleur.couleur, enregistrer=False)
        tout.addWidget(self.opt_couleur)
        self.opt_retouche = QWidget()
        lay = QHBoxLayout(self.opt_retouche)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.opt_opacite = QSpinBox()
        self.opt_durete = QSpinBox()
        for nom, case, cle, defaut, aide in (
                (tr("Opacité"), self.opt_opacite, "outil_opacite", 100, tr("100 % = couvre tout ; moins = laisse "
                                                                            "voir dessous")),
                (tr("Dureté"), self.opt_durete, "outil_durete", 80, tr("100 % = bord net ; 0 % = bord très doux"))):
            etiquette = QLabel(nom)
            if case is self.opt_opacite:
                self.etiquette_opacite = etiquette
            lay.addWidget(etiquette)
            case.setRange(1 if case is self.opt_opacite else 0, 100)
            case.setSuffix(" %")
            case.setToolTip(aide)
            case.setValue(int(self.reglages.value(cle, defaut)))
            ajuster_case(case, "100 %")
            case.valueChanged.connect(self._reglages_retouche)
            lay.addWidget(case)
            lay.addSpacing(6)
        tout.addWidget(self.opt_retouche)
        self._reglages_retouche()
        # Densité − / + : tons touchés ; Éponge : saturer ou désaturer ; Historique : instantané
        self.opt_densite = QWidget()
        lay = QHBoxLayout(self.opt_densite)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Tons")))
        self.opt_gamme = QComboBox()
        for cle, texte in (("ombres", tr("Ombres")), ("moyens", tr("Tons moyens")),
                           ("lumieres", tr("Hautes lumières"))):
            self.opt_gamme.addItem(texte, cle)
        self.opt_gamme.setCurrentIndex(1)
        self.opt_gamme.currentIndexChanged.connect(
            lambda *_: setattr(self.canevas, "gamme_densite", self.opt_gamme.currentData()))
        lay.addWidget(self.opt_gamme)
        tout.addWidget(self.opt_densite)
        self.opt_eponge = QWidget()
        lay = QHBoxLayout(self.opt_eponge)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Mode")))
        self.opt_mode_eponge = QComboBox()
        self.opt_mode_eponge.addItem(tr("Désaturer"), False)
        self.opt_mode_eponge.addItem(tr("Saturer"), True)
        self.opt_mode_eponge.currentIndexChanged.connect(
            lambda *_: setattr(self.canevas, "eponge_saturer", bool(self.opt_mode_eponge.currentData())))
        lay.addWidget(self.opt_mode_eponge)
        tout.addWidget(self.opt_eponge)
        self.opt_historique = QWidget()
        lay = QHBoxLayout(self.opt_historique)
        lay.setContentsMargins(0, 0, 0, 0)
        b = QPushButton(tr("Prendre un instantané"))
        b.setToolTip(tr("Le pinceau d'historique repeindra l'état actuel de l'image (au départ : la photo à "
                        "l'ouverture)"))
        b.clicked.connect(self.prendre_instantane)
        lay.addWidget(b)
        tout.addWidget(self.opt_historique)
        for w in (self.opt_densite, self.opt_eponge, self.opt_historique):
            w.hide()
        self.canevas.source_historique = self._source_historique

    # ---------------------------------------------------------------- pinceau d'historique
    def prendre_instantane(self):
        """L'état actuel de l'image devient celui que repeint le pinceau d'historique."""
        if self.doc is None:
            return
        self.doc.instantane = (tuple(self.doc.calques), QImage(self.doc.image_profonde()))
        self.statusBar().showMessage(tr("Instantané pris : le pinceau d'historique repeindra l'image telle qu'elle "
                                        "est maintenant."), 6000)

    def _source_historique(self, calque):
        """Image que le pinceau d'historique repeint sur ce calque : le même calque dans l'instantané (même nom et
        même taille), sinon l'image visible de l'instantané."""
        doc = self.doc
        inst = getattr(doc, "instantane", None)
        if inst is None:
            return None
        calques, image = inst
        for c in calques:
            if c.nom == calque.nom and c.image.size() == calque.image.size() and not c.special:
                return c.image
        if image.size() == calque.image.size():
            from .document import FORMAT_CALQUE
            return image.convertToFormat(FORMAT_CALQUE)
        return None

    def _options_recadrer(self, tout: QHBoxLayout):
        self.opt_recadrer = QWidget()
        lay = QHBoxLayout(self.opt_recadrer)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Proportions")))
        self.opt_proportion = QComboBox()
        for texte, valeur in ((tr("Libre"), None), (tr("Comme la photo"), "photo"), ("1:1", 1.0), ("4:3", 4 / 3),
                              ("3:2", 1.5), ("16:9", 16 / 9), ("3:4", 3 / 4), ("2:3", 2 / 3), ("9:16", 9 / 16)):
            self.opt_proportion.addItem(texte, valeur)
        self.opt_proportion.currentIndexChanged.connect(self._proportion)
        lay.addWidget(self.opt_proportion)
        self.b_recadrer = QPushButton(tr("Recadrer"))
        self.b_recadrer.setToolTip(tr("Garder seulement l'intérieur du cadre (Entrée, ou double-clic dans le cadre)"))
        self.b_recadrer.clicked.connect(self._recadrer)
        self.b_annuler_recadre = QPushButton(tr("Annuler"))
        self.b_annuler_recadre.setToolTip(tr("Enlever le cadre (Échap)"))
        self.b_annuler_recadre.clicked.connect(self.canevas.annuler_recadre)
        lay.addWidget(self.b_recadrer)
        lay.addWidget(self.b_annuler_recadre)
        tout.addWidget(self.opt_recadrer)
        self._recadre_change(None)
        # outil Déplacer : cadre à poignées (agrandir, réduire, tourner sans passer par Ctrl+T)
        self.opt_deplacer = QWidget()
        lay = QHBoxLayout(self.opt_deplacer)
        lay.setContentsMargins(0, 0, 0, 0)
        self.c_cadre_deplacer = QCheckBox(tr("Afficher le cadre de transformation"))
        self.c_cadre_deplacer.setToolTip(tr("Cadre à poignées autour du calque (ou de la sélection) : coins = taille, "
                                            "juste à l'extérieur d'un coin = tourner"))
        self.c_cadre_deplacer.setChecked(self.reglages.value("cadre_deplacer", True, type=bool))
        self.canevas.cadre_deplacer = self.c_cadre_deplacer.isChecked()
        self.c_cadre_deplacer.toggled.connect(self._cadre_deplacer)
        lay.addWidget(self.c_cadre_deplacer)
        lay.addSpacing(16)
        # aligner / répartir : ici seulement quand la barre d'accès rapide (qui les a aussi) est masquée
        self.alignement_deplacer = QWidget()
        lay_outil = lay
        lay = QHBoxLayout(self.alignement_deplacer)
        lay.setContentsMargins(0, 0, 0, 0)
        from .actions_calques import alignements
        for k, (mode, texte) in enumerate(alignements()):       # aligner : comme dans Photoshop
            if k == 3:
                lay.addSpacing(6)
            b = QToolButton()
            b.setAutoRaise(True)
            b.setDefaultAction(getattr(self, f"a_aligner_{mode}"))
            b.setToolTip(tr("Aligner : {quoi} (plusieurs calques choisis : entre eux ; un seul : sur la sélection "
                            "ou l'image)", quoi=texte.lower()))
            lay.addWidget(b)
        lay.addSpacing(6)
        for sens in "hv":
            b = QToolButton()
            b.setAutoRaise(True)
            b.setDefaultAction(getattr(self, f"a_repartir_{sens}"))
            b.setToolTip(tr("Répartir horizontalement (3 calques choisis ou plus)") if sens == "h"
                         else tr("Répartir verticalement (3 calques choisis ou plus)"))
            lay.addWidget(b)
        lay_outil.addWidget(self.alignement_deplacer)
        lay_outil.addStretch(1)
        tout.addWidget(self.opt_deplacer)
        # baguette magique
        self.opt_baguette = QWidget()
        lay = QHBoxLayout(self.opt_baguette)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(QLabel(tr("Tolérance")))
        self.opt_tolerance = QSpinBox()
        self.opt_tolerance.setRange(0, 255)
        self.opt_tolerance.setValue(self.reglages.value("baguette_tolerance", 32, type=int))
        self.opt_tolerance.setToolTip(tr("Écart de couleur accepté. Astuce : après le clic, glisse la souris à droite "
                                         "ou à gauche pour régler la tolérance en voyant le résultat."))
        self.opt_tolerance.valueChanged.connect(lambda v: self.reglages.setValue("baguette_tolerance", v))
        lay.addWidget(self.opt_tolerance)
        self.opt_contigu = QCheckBox(tr("Contiguë"))
        self.opt_contigu.setToolTip(tr("Coché : seulement la zone touchée. Décoché : toutes les couleurs proches de "
                                       "l'image."))
        self.opt_doux = QCheckBox(tr("Bords doux"))
        self.opt_doux.setToolTip(tr("Bord progressif, selon l'écart de couleur (pas d'escalier)"))
        self.opt_trous = QCheckBox(tr("Boucher les trous"))
        self.opt_trous.setToolTip(tr("Ajoute ce qui est entièrement entouré par la zone (oiseaux dans un ciel, "
                                     "reflets…)"))
        for case, cle, defaut in ((self.opt_contigu, "baguette_contigu", True), (self.opt_doux, "baguette_doux", True),
                                  (self.opt_trous, "baguette_trous", False)):
            case.setChecked(self.reglages.value(cle, defaut, type=bool))
            case.toggled.connect(lambda v, c=cle: self.reglages.setValue(c, v))
            lay.addWidget(case)
        self.opt_echantillon = QComboBox()
        self.opt_echantillon.addItem(tr("Image visible"), "image")
        self.opt_echantillon.addItem(tr("Calque choisi"), "calque")
        self.opt_echantillon.setToolTip(tr("Couleurs comparées sur l'image telle qu'on la voit, ou sur le calque "
                                           "choisi seulement"))
        lay.addWidget(self.opt_echantillon)
        tout.addWidget(self.opt_baguette)
        # sélection de texte
        self.opt_sel_texte = QWidget()
        lay = QHBoxLayout(self.opt_sel_texte)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.opt_pleines = QCheckBox(tr("Lettres pleines"))
        self.opt_pleines.setToolTip(tr("Coché : l'intérieur des lettres est pris aussi (motifs, intérieur des O et "
                                       "des A). Pratique pour effacer ou déplacer un texte."))
        self.opt_pleines.setChecked(self.reglages.value("texte_pleines", False, type=bool))
        self.opt_pleines.toggled.connect(lambda v: self.reglages.setValue("texte_pleines", v))
        self.opt_pleines.toggled.connect(lambda _v: self.selection_auto.texte_relancer())
        lay.addWidget(self.opt_pleines)
        b_police = QPushButton(tr("Police semblable…"))
        b_police.setToolTip(tr("Cherche parmi tes polices celles qui ressemblent le plus aux lettres sélectionnées"))
        b_police.clicked.connect(self.police_semblable)
        lay.addWidget(b_police)
        self.b_police = b_police
        aide = QLabel(tr("Alt+clic : enlever · Maj+clic : ajouter · Ctrl : toute la couleur"))
        aide.setToolTip(tr("Alt+clic : enlever un morceau · Maj+clic : ajouter · Ctrl en plus : toute la couleur"))
        aide.setEnabled(False)
        lay.addWidget(aide)
        tout.addWidget(self.opt_sel_texte)

    def _couleur_peinture(self, couleur: str, enregistrer: bool = True):
        self.canevas.couleur_peinture = QColor(couleur)
        if getattr(self, "opt_degrade_bouton", None) is not None:      # aperçu des points « couleur de peinture »
            self.opt_degrade_bouton.rafraichir()
        if enregistrer:
            self.reglages.setValue("peinture_couleur", couleur)
        if hasattr(self, "case_calque_pinceau"):
            self.pinceau_barre_change()

    def _couleur_prise(self, couleur: str):
        self.opt_couleur.definir(QColor(couleur).name(QColor.HexArgb))
        self._couleur_peinture(self.opt_couleur.couleur)
        self.statusBar().showMessage(tr("Couleur prise : {couleur}", couleur=couleur), 4000)

    def _reglages_retouche(self, *_):
        self.canevas.opacite = self.opt_opacite.value() / 100
        self.canevas.durete = self.opt_durete.value() / 100
        self.reglages.setValue("outil_opacite", self.opt_opacite.value())
        self.reglages.setValue("outil_durete", self.opt_durete.value())
        if hasattr(self, "case_calque_pinceau"):
            self.pinceau_barre_change()

    def _proportion(self, *_):
        v = self.opt_proportion.currentData()
        if v == "photo":
            v = self.doc.image.width() / self.doc.image.height() if self.doc else None
        self.canevas.definir_proportion(v)

    def _recadre_change(self, r):
        self.b_recadrer.setEnabled(r is not None)
        self.b_annuler_recadre.setEnabled(r is not None)

    def _recadrer(self):
        r = self.canevas.rect_recadre()
        if not self.doc or r is None:
            return
        if r == self.doc.image.rect():
            self.canevas.annuler_recadre()
            return
        avant = self.doc.etat()
        apres = self.doc.etat_recadre(r)
        self.canevas.annuler_recadre()
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Recadrer")))
        self.statusBar().showMessage(tr("Recadré : {l} × {h} px (Ctrl+Z pour revenir)", l=r.width(), h=r.height()),
                                     6000)

    def _recadrer_selection(self):
        if not self.doc:
            return
        r = self.doc.rect_selection()
        if r is None:
            QMessageBox.information(self, NOM, tr("Sélectionne d'abord la partie à garder (rectangle, lasso ou "
                                                  "pinceau)."))
            return
        avant = self.doc.etat()
        apres = self.doc.etat_recadre(r)
        w, h = apres[0][0].image.width(), apres[0][0].image.height()
        apres = (apres[0], apres[1], nouvelle_selection(w, h))
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Recadrer à la sélection")))

    def _outils(self):
        barre = QToolBar(tr("Outils"))
        barre.setMovable(False)
        n = self._taille_icones()
        barre.setIconSize(QSize(n, n))
        self._barre_outils = barre
        barre.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.addToolBar(Qt.LeftToolBarArea, barre)
        groupe = QActionGroup(self)
        self._actions_outils = {}
        for outil, texte, touche, nom in ((MAIN, tr("Main : déplacer la vue"), "H", "main"),
                                          (DEPLACER, tr("Déplacer : bouge le calque choisi"), "V", "deplacer"),
                                          (RECTANGLE, tr("Sélection rectangle"), "M", "rectangle"),
                                          (LASSO, tr("Lasso"), "L", "lasso"),
                                          (PINCEAU, tr("Pinceau de sélection"), "B", "pinceau"),
                                          (GOMME, tr("Gomme de sélection"), "E", "gomme"),
                                          (BAGUETTE, tr("Baguette magique : zone de couleur proche (glisser après "
                                                        "le clic : tolérance)"), "W", "baguette"),
                                          (RAPIDE, tr("Sélection rapide (IA) : peins sur l'objet, Alt pour "
                                                      "retirer"), "Q", "rapide"),
                                          (OBJET, tr("Sélection d'objet (IA) : cadre autour de l'objet, ou clic "
                                                     "dessus"), "O", "objet"),
                                          (SEL_TEXTE, tr("Sélection de texte : cadre autour d'un texte, les lettres "
                                                         "seules sont sélectionnées"), "Y", "sel_texte"),
                                          (GOMME_CALQUE, tr("Gomme de calque : efface les pixels du calque choisi"),
                                           "G", "gomme_calque"),
                                          (TEXTE, tr("Texte : écrire, déplacer, tourner"), "T", "texte"),
                                          (RECADRER, tr("Recadrer : garder une partie de la photo"), "C", "recadrer"),
                                          (PEINTURE, tr("Pinceau de couleur : peint sur le calque choisi (Alt+clic : "
                                                        "prendre une couleur)"), "P", "peinture"),
                                          (TAMPON, tr("Tampon : recopie une zone (Alt+clic : endroit à copier)"),
                                           "S", "tampon"),
                                          (TAMPON_MOTIF, tr("Tampon de motif : peint avec un motif de la "
                                                            "bibliothèque (choisi dans la barre du haut)"), "",
                                           "tampon_motif"),
                                          (SUPPRIMER, tr("Supprimer (IA) : peins sur un défaut, il disparaît au "
                                                         "lâcher"), "J", "suppression"),
                                          (CORRECTEUR, tr("Pinceau correcteur : recopie une zone en la raccordant "
                                                          "à la lumière autour (Alt+clic : endroit à copier)"),
                                           "R", "correcteur"),
                                          (DEGRADE, tr("Dégradé : glisse du début à la fin (Maj : droit)"), "D",
                                           "degrade"),
                                          (SEAU, tr("Pot de peinture : remplit une zone de couleur proche"), "K",
                                           "seau"),
                                          (FORMES, tr("Formes : rectangle, ellipse, étoile, flèche… (calque de "
                                                      "forme modifiable)"), "U", "formes"),
                                          (PLUME, tr("Plume : tracés en lignes et en courbes, point par point "
                                                     "(calque de forme ou sélection)"), "A", "plume"),
                                          (DENSITE_MOINS, tr("Densité − : éclaircit là où l'on peint"), "",
                                           "densite_moins"),
                                          (DENSITE_PLUS, tr("Densité + : assombrit là où l'on peint"), "",
                                           "densite_plus"),
                                          (EPONGE, tr("Éponge : ravive ou ternit les couleurs là où l'on peint"), "",
                                           "eponge"),
                                          (GOUTTE, tr("Goutte d'eau : floute là où l'on peint"), "", "goutte"),
                                          (NETTETE_PINCEAU, tr("Netteté : rend plus net là où l'on peint"), "",
                                           "nettete_pinceau"),
                                          (DOIGT, tr("Doigt : étale la couleur comme de la peinture fraîche"), "",
                                           "doigt"),
                                          (HISTORIQUE, tr("Pinceau d'historique : repeint l'état de l'instantané "
                                                          "(la photo à l'ouverture)"), "", "historique")):
            a = QAction(texte, self, checkable=True)
            if touche:
                a.setShortcut(touche)
            a.setToolTip(f"{texte}  ({touche})" if touche else texte)
            a.triggered.connect(lambda _=False, o=outil: self._choisir_outil(o))
            self._icone(a, nom)
            groupe.addAction(a)
            self.addAction(a)                  # raccourci actif même quand l'outil est caché dans son groupe
            self._actions_outils[outil] = a
            if outil == PINCEAU:
                a.setChecked(True)
        # comme Photoshop : un bouton par famille d'outils ; clic droit (ou clic maintenu) pour choisir dans la
        # famille ; le bouton montre le dernier outil choisi. Main et Déplacer restent seuls.
        self._bouton_groupe = {}
        for famille in ((MAIN,), (DEPLACER,), (RECTANGLE, LASSO, PINCEAU, GOMME), (OBJET, RAPIDE, BAGUETTE, SEL_TEXTE),
                        (SUPPRIMER, CORRECTEUR, TAMPON, TAMPON_MOTIF, HISTORIQUE),
                        (PEINTURE, GOMME_CALQUE, DEGRADE, SEAU), (DENSITE_MOINS, DENSITE_PLUS, EPONGE),
                        (GOUTTE, NETTETE_PINCEAU, DOIGT), (FORMES,), (PLUME,),
                        (RECADRER,), (TEXTE,)):
            if len(famille) == 1:
                barre.addAction(self._actions_outils[famille[0]])
                continue
            bouton = BoutonFamille()
            bouton.setPopupMode(QToolButton.DelayedPopup)
            bouton.setToolButtonStyle(Qt.ToolButtonIconOnly)
            bouton.setIconSize(barre.iconSize())
            bouton.setAutoRaise(True)
            menu = QMenu(bouton)
            for o in famille:
                a = self._actions_outils[o]
                a.setToolTip(a.toolTip() + "\n" + tr("Clic droit (ou clic maintenu) : les autres outils de ce groupe"))
                menu.addAction(a)
                self._bouton_groupe[o] = bouton
            bouton.setMenu(menu)
            bouton.setDefaultAction(self._actions_outils[famille[0]])
            bouton.setContextMenuPolicy(Qt.CustomContextMenu)
            bouton.customContextMenuRequested.connect(
                lambda _p, b=bouton: b.menu().exec(b.mapToGlobal(b.rect().topRight())))
            barre.addWidget(bouton)

    def _mode_selection(self, mode: str):
        if self.canevas.outil in (RECTANGLE, LASSO) + OUTILS_AUTO:
            self.canevas.mode_forme = mode
        else:
            self.canevas.definir_mode_retirer(mode == "retirer")

    def _choisir_outil(self, outil: str):
        if getattr(self.canevas, "transfo", None) is not None:
            self._valider_transfo()
        if outil != PLUME and self.canevas.plume_points is not None:
            self.canevas.finir_plume(fermer=False)          # tracé en cours : gardé tel quel
        if self.canevas.outil != outil and hasattr(self, "selection_auto"):
            self.selection_auto.fin_session()
        if outil != TEXTE and hasattr(self, "panneau_texte"):
            self.panneau_texte.bouton_trace.setChecked(False)      # « Dessiner un tracé » n'a lieu qu'avec l'outil T
        self.canevas.definir_outil(outil)
        self._actions_outils[outil].setChecked(True)
        self._maj_cible_degrade()
        if outil in self._bouton_groupe:
            bouton = self._bouton_groupe[outil]
            menu = bouton.menu()
            bouton.setDefaultAction(self._actions_outils[outil])
            bouton.setMenu(menu)
        if outil in (RECTANGLE, LASSO) + OUTILS_AUTO:
            {"nouvelle": self.p_nouvelle, "ajouter": self.p_ajouter,
             "retirer": self.p_retirer}[self.canevas.mode_forme].setChecked(True)
        elif outil == PINCEAU:
            (self.p_retirer if self.canevas.mode_retirer else self.p_ajouter).setChecked(True)
        self.p_nouvelle.setVisible(outil in (RECTANGLE, LASSO) + OUTILS_AUTO)
        self.options.setEnabled(outil not in (MAIN, TEXTE))
        self.opt_taille.setVisible(outil in OUTILS_ROND or outil in (MAIN, TEXTE, RECTANGLE, LASSO))
        if outil in (BAGUETTE, OBJET, SEL_TEXTE):
            self.opt_taille.setVisible(False)
        self.opt_selection.setVisible(outil in (RECTANGLE, LASSO, PINCEAU) + OUTILS_AUTO)
        self.opt_baguette.setVisible(outil == BAGUETTE)
        self.opt_sel_texte.setVisible(outil == SEL_TEXTE)
        self.opt_couleur.setVisible(outil in (PEINTURE, DEGRADE, SEAU))
        self.opt_retouche.setVisible(outil in (PEINTURE, TAMPON, TAMPON_MOTIF, CORRECTEUR, DEGRADE, SEAU, HISTORIQUE)
                                     + OUTILS_FILTRE)
        self.opt_densite.setVisible(outil in (DENSITE_MOINS, DENSITE_PLUS))
        self.opt_eponge.setVisible(outil == EPONGE)
        self.opt_historique.setVisible(outil == HISTORIQUE)
        self.etiquette_opacite.setText(tr("Force") if outil in OUTILS_FILTRE else tr("Opacité"))
        self.opt_degrade.setVisible(outil == DEGRADE)
        self.opt_seau.setVisible(outil == SEAU)
        self.opt_motif.setVisible(outil == TAMPON_MOTIF or (outil == SEAU and self.canevas.seau_motif))
        self.montrer_options_forme(outil)
        self.opt_recadrer.setVisible(outil == RECADRER)
        self.opt_deplacer.setVisible(outil == DEPLACER)
        self.maj_bouton_pinceau()
        # la barre du haut se remet en page (sinon un groupe trop large la ferait déborder)
        self.options.adjustSize()
        self.barre_haut.layout().invalidate()
        aides = {RECTANGLE: tr("Rectangle : la nouvelle sélection remplace l'ancienne. Maj : ajouter, Alt : retirer. "
                               "Un simple clic désélectionne."),
                 LASSO: tr("Lasso : entoure la zone en gardant le bouton appuyé. Maj : ajouter, Alt : retirer."),
                 BAGUETTE: tr("Baguette magique : clic sur une couleur ; garde le bouton appuyé et glisse à droite ou "
                              "à gauche pour régler la tolérance. Maj : ajouter, Alt : retirer."),
                 RAPIDE: tr("Sélection rapide (IA) : peins grossièrement sur l'objet, l'IA trouve ses contours. "
                            "Alt + peindre : retirer une partie. Maj : objet suivant. Échap : recommencer."),
                 OBJET: tr("Sélection d'objet (IA) : tire un cadre autour de l'objet, ou clique dessus. "
                           "Maj : ajouter, Alt : retirer."),
                 SEL_TEXTE: tr("Sélection de texte : tire un cadre autour du texte, avec un peu de fond autour. "
                               "Ensuite, Alt+clic enlève un morceau en trop, Maj+clic ajoute un morceau oublié."),
                 RECADRER: tr("Recadrer : tire un cadre sur la photo, ajuste-le, puis Entrée (ou double-clic). "
                              "Échap pour annuler."),
                 PEINTURE: tr("Pinceau de couleur : peint sur le calque choisi. Alt+clic sur la photo : prendre une "
                              "couleur."),
                 TAMPON: tr("Tampon : Alt+clic sur l'endroit à copier, puis peins là où il doit être recopié."),
                 SUPPRIMER: tr("Supprimer (IA) : peins sur un fil, une tache, un bouton… ; au lâcher, il disparaît "
                               "(dans le calque choisi). Pour un gros objet, préfère Effacer."),
                 CORRECTEUR: tr("Pinceau correcteur : Alt+clic sur une zone saine, puis peins sur le défaut ; au "
                                "lâcher, la copie prend la lumière et la couleur d'autour."),
                 DEGRADE: tr("Dégradé : glisse du début à la fin (Maj : horizontal, vertical ou à 45°). Dans la "
                             "sélection s'il y en a une ; sur un masque : fondu progressif."),
                 SEAU: tr("Pot de peinture : clic sur une zone ; elle se remplit de la couleur choisie (d'après le "
                          "calque choisi, ou l'image visible avec « Tous les calques »). Alt+clic : prendre une "
                          "couleur."),
                 FORMES: tr("Formes : glisse pour dessiner (Maj : carré, cercle, ligne droite). Chaque forme va dans "
                            "un calque de forme, qui reste modifiable : choisis-le et change en haut son remplissage, "
                            "son contour, son épaisseur."),
                 PLUME: tr("Plume : clic = point d'angle, cliquer-glisser = courbe ; clic sur le premier point pour "
                           "fermer, Entrée ou double-clic pour finir ouvert, Échap pour abandonner. Sur un calque de "
                           "forme : tire ses points ou leurs poignées (Alt : une poignée seule)."),
                 DENSITE_MOINS: tr("Densité − : peins pour éclaircir ; choisis en haut les tons touchés (ombres, tons "
                                   "moyens, hautes lumières) et la force."),
                 DENSITE_PLUS: tr("Densité + : peins pour assombrir ; choisis en haut les tons touchés et la force."),
                 EPONGE: tr("Éponge : peins pour raviver (Saturer) ou ternir (Désaturer) les couleurs."),
                 GOUTTE: tr("Goutte d'eau : peins pour flouter (un fond, un grain de peau) ; sur un masque, adoucit "
                            "son bord."),
                 NETTETE_PINCEAU: tr("Netteté : peins sur les détails à rendre plus nets (yeux, texte)."),
                 DOIGT: tr("Doigt : glisse pour étaler la couleur, comme de la peinture fraîche ; la force dit "
                           "jusqu'où elle s'étale."),
                 HISTORIQUE: tr("Pinceau d'historique : peins pour faire revenir l'état de l'instantané (au départ, "
                                "la photo à l'ouverture) ; « Prendre un instantané » en haut garde l'état actuel.")}
        if outil in aides:
            self.statusBar().showMessage(aides[outil], 10000)
        if outil == RECADRER:
            self._proportion()
        self.dock_texte.setVisible(outil == TEXTE)
        if outil == TEXTE:
            self._sync_texte()
        if outil == PEINTURE:
            self._pinceau_montre = None
            self.sync_calque_pinceau()

    def _taille_changee(self, v: int):
        for w, val in ((self.curseur_taille, position_taille(v)), (self.valeur_taille, v)):
            w.blockSignals(True)
            w.setValue(val)
            w.blockSignals(False)

    def _panneau_ia(self):
        dock = QDockWidget(tr("INTELLIGENCE ARTIFICIELLE"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 4, 10, 10)
        lay.setSpacing(8)
        aide = QLabel(tr("Peins sur l'objet avec le pinceau (ou entoure-le au lasso), puis choisis une action."))
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.b_effacer = Carte(tr("Effacer"), tr("Enlève ce qui est peint"))
        self.b_remplir = Carte(tr("Remplir"), tr("Redessine ce qui est peint"))
        self.texte_remplir = QLineEdit()
        self.texte_remplir.setPlaceholderText(tr("Texte facultatif (laisser vide)"))
        self.b_modifier = Carte(tr("Modifier"), tr("Change ce qui est peint, d'après ta consigne"))
        self.b_agrandir = Carte(tr("Agrandir l'image"), tr("Étend la photo au-delà des bords"))
        self.b_upscale = Carte(tr("Upscale"), tr("Augmente la définition"))
        self.b_arriere_plan = Carte(tr("Arrière-plan"), tr("Supprime le fond, garde le sujet"))
        for carte, fonction, nom in ((self.b_effacer, self.ia_effacer, "effacer"),
                                     (self.b_remplir, self.ia_remplir, "remplir"),
                                     (self.b_modifier, self.ia_modifier, "modifier"),
                                     (self.b_agrandir, self.ia_agrandir, "agrandir"),
                                     (self.b_upscale, self.ia_upscale, "upscale"),
                                     (self.b_arriere_plan, self.supprimer_arriere_plan, "arriere_plan")):
            carte.clicked.connect(fonction)
            self._icone(carte, nom)
        lay.addWidget(self.b_effacer)
        lay.addWidget(self.b_remplir)
        lay.addWidget(self.texte_remplir)
        lay.addWidget(self.b_modifier)
        lay.addSpacing(6)
        lay.addWidget(self.b_agrandir)
        lay.addWidget(self.b_upscale)
        lay.addWidget(self.b_arriere_plan)
        dock.setWidget(w)
        dock.setFixedWidth(290)
        w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

    def _panneau_calques(self):
        dock = QDockWidget(tr("CALQUES"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.calques = PanneauCalques(lambda nom: icone(nom, self.couleurs.texte, self.couleurs.accent, 20))
        self.calques.demande.connect(self._commande_calques)
        self.calques.style_demande.connect(self.style_calque)
        self.calques.refus.connect(lambda m: self.statusBar().showMessage(m, 6000))
        self.calques.reglage_demande.connect(
            lambda t: self.nouveau_calque_remplissage(t.split(":", 1)[1]) if t.startswith("remplissage:")
            else self.nouveau_calque_reglage(t) if t else self.modifier_reglage())
        dock.setWidget(self.calques)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.dock_calques = dock

    def _panneau_historique(self):
        """Liste des étapes (comme Photoshop) : un clic revient à cette étape ; les suivantes restent dans
        Rétablir tant qu'on ne fait rien d'autre."""
        dock = QDockWidget(tr("HISTORIQUE"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.vue_historique = QUndoView(self.groupe_historique)
        self.vue_historique.setEmptyLabel(tr("Photo ouverte"))
        contenu = QWidget()
        lay = QVBoxLayout(contenu)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.addWidget(self.vue_historique, 1)
        # le pinceau d'historique est aussi rangé sous le Tampon ; ce bouton le rend facile à trouver
        self.bouton_pinceau_historique = QPushButton(tr("Pinceau d'historique"))
        self.bouton_pinceau_historique.setToolTip(self._actions_outils[HISTORIQUE].toolTip())
        self._icone(self.bouton_pinceau_historique, "historique")
        self.bouton_pinceau_historique.clicked.connect(self._actions_outils[HISTORIQUE].trigger)
        lay.addWidget(self.bouton_pinceau_historique)
        dock.setWidget(contenu)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDockWidget(self.dock_calques, dock)
        self.dock_calques.raise_()
        self.dock_historique = dock

    def _panneau_nuancier(self):
        """Nuancier (comme Photoshop) : couleurs enregistrées ; un clic = couleur de peinture."""
        from .nuancier import PanneauNuancier
        dock = QDockWidget(tr("NUANCIER"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.nuancier = PanneauNuancier(lambda: self.canevas.couleur_peinture)
        self.nuancier.choisi.connect(self._couleur_nuancier)
        dock.setWidget(self.nuancier)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDockWidget(self.dock_historique, dock)
        self.dock_calques.raise_()
        self.dock_nuancier = dock

    def imprimer(self):
        """Fichier > Imprimer : l'image visible, sur le papier et à la taille choisis."""
        if not self.doc:
            return
        from .imprimer import DialogueImprimer
        d = DialogueImprimer(self.doc.image, self.doc.dpi, self)
        if d.exec():
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                d.imprimer()
            finally:
                QApplication.restoreOverrideCursor()
            self.statusBar().showMessage(tr("Envoyé à l'imprimante « {nom} ».", nom=d.imprimante.currentText()), 6000)
        d.deleteLater()

    def _panneau_actions(self):
        """Actions (comme Photoshop) : enregistrer des réglages, filtres, tailles, rotations, puis les rejouer."""
        from .actions_auto import PanneauActions
        dock = QDockWidget(tr("ACTIONS"), self)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.panneau_actions = PanneauActions()
        self.panneau_actions.jouer.connect(self.jouer_action)
        dock.setWidget(self.panneau_actions)
        dock.setFixedWidth(290)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDockWidget(self.dock_historique, dock)
        self.dock_calques.raise_()
        self.dock_actions = dock

    def noter_action(self, etape: dict):
        """Une opération enregistrable vient d'être faite : elle va dans l'action en cours d'enregistrement."""
        if hasattr(self, "panneau_actions"):
            self.panneau_actions.ajouter(etape)

    def jouer_action(self, action: dict):
        """Rejoue une action sur l'image ouverte : une seule étape d'Annuler."""
        from .actions_auto import etat_apres, nom_etape
        titre = tr("Action : {nom}", nom=action["nom"])
        if not self.doc:
            return
        if not self._verifier_verrou(titre, tous=True):
            return
        doc = self.doc
        avant = doc.etat()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        sautees = []
        try:
            for e in action["etapes"]:
                etat = etat_apres(doc, e)
                if etat is None:
                    sautees.append(nom_etape(e))
                    continue
                doc.appliquer_etat(etat)
        finally:
            QApplication.restoreOverrideCursor()
        apres = doc.etat()
        doc.appliquer_etat(avant)
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
        if sautees:
            self.statusBar().showMessage(tr("Étapes sautées (le calque choisi n'a pas de pixels) : {liste}",
                                            liste=", ".join(sautees)), 8000)
        else:
            self.statusBar().showMessage(tr("Action « {nom} » jouée ({n} étape(s)). Ctrl+Z pour revenir.",
                                            nom=action["nom"], n=len(action["etapes"])), 6000)

    def _couleur_nuancier(self, couleur: str):
        self.opt_couleur.definir(QColor(couleur).name(QColor.HexArgb))
        self._couleur_peinture(self.opt_couleur.couleur)
        self.statusBar().showMessage(tr("Couleur de peinture : {couleur}", couleur=couleur), 3000)

    def _panneau_texte(self):
        self.dock_texte = QDockWidget(tr("TEXTE"), self)
        self.dock_texte.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.panneau_texte = PanneauTexte(lambda nom: icone(nom, self.couleurs.texte, self.couleurs.accent, 20))
        try:                                       # style du dernier texte écrit
            self.panneau_texte.defaut = Texte.depuis_dict(json.loads(self.reglages.value("texte_defaut", "{}")))
            self.panneau_texte.afficher(None)
        except (ValueError, TypeError):
            pass
        self.panneau_texte.modifie.connect(self._texte_modifie)
        self.panneau_texte.apercu_police.connect(self._apercu_police)
        self.panneau_texte.tracer.connect(self._mode_trace)
        self.dock_texte.setWidget(self.panneau_texte)
        self.dock_texte.setFixedWidth(290)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_texte)
        self.dock_texte.hide()

    # ---------------------------------------------------------- texte
    def _sync_texte(self):
        """Le panneau Texte montre le calque choisi s'il est un texte (et la barre du pinceau, le calque de pinceau
        choisi)."""
        if hasattr(self, "case_calque_pinceau"):
            self.sync_calque_pinceau()
        if hasattr(self, "opt_genre"):
            self.sync_calque_forme()
        if not hasattr(self, "panneau_texte"):
            return
        c = self.doc.calque_actif if self.doc else None
        if c is not None and c.texte is not None:
            if self.panneau_texte.t is not c.texte:
                self.panneau_texte.afficher(c.texte, c.verrou)
        elif self.panneau_texte.lie or c is None:
            self.panneau_texte.afficher(None)
        self.canevas.update()

    def _nouveau_texte(self, pt):
        if not self.doc:
            return
        w, h = self.doc.taille()
        t = replace(self.panneau_texte.defaut, texte=tr("Texte"), x=pt.x(), y=pt.y(), angle=0.0,
                    taille=float(max(12, round(min(w, h) / 12))))
        self._session_texte += 1
        self.historique.push(CommandeEtat(self.doc, self.doc.etat(), self.doc.etat_nouveau_texte(t),
                                          tr("Nouveau texte")))
        self.panneau_texte.commencer_saisie()

    def _texte_choisi(self, index: int):
        if self.doc and index != self.doc.actif:
            self._session_texte += 1
            self.doc.actif = index
            self.doc.calques_changes.emit()

    def _texte_modifie(self, t: Texte, champ: str):
        doc = self.doc
        if not doc or doc.calque_actif.texte is None:
            return
        if doc.calque_actif.verrou:
            self.statusBar().showMessage(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour "
                                            "pouvoir le modifier.", nom=doc.calque_actif.nom), 6000)
            self.panneau_texte.afficher(doc.calque_actif.texte, True)
            return
        cle = ("texte", self._session_texte, doc.actif, champ)
        self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_texte_modifie(doc.actif, t),
                                          tr("Modifier le texte"), cle))

    def _mode_trace(self, oui: bool):
        """« Dessiner un tracé » : glisser sur la photo dessine la ligne que le texte suivra."""
        self.canevas.trace_texte = oui
        if oui:
            self.statusBar().showMessage(tr("Glisse sur la photo pour dessiner la ligne que le texte va suivre."),
                                         8000)

    def _trace_dessine(self, points: list):
        from .texte import trace_depuis
        self.panneau_texte.bouton_trace.setChecked(False)
        doc = self.doc
        if not doc or doc.calque_actif.texte is None or doc.calque_actif.verrou:
            return
        t = doc.calque_actif.texte
        t = replace(t, trace=trace_depuis(t, points), courbe=0.0, vertical=False)
        self._session_texte += 1
        self.historique.push(CommandeEtat(doc, doc.etat(), doc.etat_texte_modifie(doc.actif, t),
                                          tr("Texte sur un tracé")))

    def _apercu_police(self, famille: str):
        """Police survolée dans la liste du panneau Texte : le texte de la photo la prend tout de suite (aperçu, pas
        dans Annuler) ; liste fermée sans choix : il revient comme avant."""
        from .texte import rendre
        doc = self.doc
        if not doc:
            return
        avant = getattr(self, "_police_avant", None)
        if not famille:                                   # liste fermée : le texte d'avant (s'il n'a pas changé)
            self._police_avant = None
            if avant is not None and avant[0] is doc and avant[1] < len(doc.calques):
                c = doc.calques[avant[1]]
                if c.texte is avant[2]:
                    doc.apercu_calque(avant[1], rendre(c.texte, *doc.taille()), texte=c.texte)
            return
        c = doc.calque_actif
        if c.texte is None or c.verrou or not self.panneau_texte.lie:
            return
        if avant is None or avant[0] is not doc or avant[1] != doc.actif:
            self._police_avant = (doc, doc.actif, c.texte)
        t = replace(self._police_avant[2], police=famille)
        doc.apercu_calque(doc.actif, rendre(t, *doc.taille()), texte=self._police_avant[2])

    def _texte_en_pixels(self):
        if self.doc and self.doc.calque_actif.texte is not None and not self.doc.calque_actif.verrou:
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(), self.doc.etat_en_pixels(self.doc.actif),
                                              tr("Convertir en image")))

    def _commande_calques(self, etat, texte: str):
        if self.doc and etat is not None:
            self.historique.push(CommandeEtat(self.doc, self.doc.etat(), etat, texte))

    def _barre_etat(self):
        self.pastille_moteur = QLabel()
        self.pastille_image = QLabel()
        for p_ in (self.pastille_moteur, self.pastille_image):
            p_.setObjectName("pastille_etat")
        self.statusBar().addWidget(self.pastille_moteur)
        self.statusBar().addPermanentWidget(self.pastille_image)
        self.statusBar().setSizeGripEnabled(False)
        self.canevas.infos.connect(self._infos_image)
        self.etat_moteur.connect(self._moteur_change)
        self.pastille_image.hide()

    def _infos_image(self, largeur: int, hauteur: int, zoom: float):
        self.pastille_image.setText(f"{largeur} × {hauteur} px")
        self.pastille_image.show()
        self.valeur_zoom.setText(f"{zoom * 100:.0f} %")

    def _moteur_change(self, texte: str):
        self.texte_moteur = texte
        self._peindre_pastille_moteur()

    def _peindre_pastille_moteur(self):
        c = self.couleurs
        etat = self.moteur.etat
        couleur = c.vert if etat == "prêt" else c.rouge if etat in ("introuvable", "erreur", "incomplet") \
            else c.orange
        texte = tr("Moteur IA : {etat}", etat=self.texte_moteur)
        self.pastille_moteur.setText(f'<span style="color:{couleur}">●</span>&nbsp; {texte}')

    # ---------------------------------------------------------- thème
    def changer_theme(self, mode: str):
        self.mode_theme = mode
        self.reglages.setValue("theme", mode)
        self.couleurs = theme.appliquer(QApplication.instance(), mode)
        self._appliquer_theme()

    def changer_langue(self, code: str):
        """La langue est choisie au démarrage : on propose de redémarrer Pixane."""
        if code == self.reglages.value("langue", langue.AUTO):
            return
        self.reglages.setValue("langue", code)
        rep = QMessageBox.question(self, NOM, tr("La nouvelle langue sera utilisée au prochain démarrage de "
                                                 "Pixane Photo.\n\nRedémarrer maintenant ?"))
        if rep == QMessageBox.Yes:
            self._redemarrer()

    def preferences(self):
        """Édition > Préférences… : appliqué après OK, avec les mêmes fonctions et les mêmes réglages que les menus."""
        from .preferences import DialoguePreferences
        d = DialoguePreferences(self)
        if not d.exec():
            return
        v = d.valeurs()
        if v["theme"] != self.mode_theme:
            self.changer_theme(v["theme"])
        if v["icones"] != self._taille_icones():
            self.changer_taille_icones(v["icones"])
        # cases des menus : leur fonction suit (toggled), comme un clic dans le menu
        for action, cle in ((self.a_barre_rapide, "barre_rapide"), (self.a_option_polices, "polices"),
                            (self.a_option_orthographe, "orthographe"), (self.a_ia_nouveau_calque, "nouveau_calque"),
                            (self.a_maj_auto, "maj")):
            if action.isChecked() != v[cle]:
                action.setChecked(v[cle])
        if self.barre_agrandir.pleine.isChecked() != v["pleine"]:
            self.barre_agrandir.pleine.setChecked(v["pleine"])
        if v["grille"] != self.canevas.pas_grille:
            self.canevas.pas_grille = v["grille"]
            self.reglages.setValue("pas_grille", v["grille"])
            self.canevas.update()
        self.reglages.setValue("recuperation_minutes", v["recuperation"])
        self._recuperation.definir_minutes(v["recuperation"])
        if v["dossier"] and Path(v["dossier"]).is_dir():
            self.reglages.setValue("dossier", v["dossier"])
        # langue et taille de l'interface : au prochain démarrage, une seule question
        demarrage = False
        if v["langue"] != self.reglages.value("langue", langue.AUTO):
            self.reglages.setValue("langue", v["langue"])
            demarrage = True
        if v["echelle"] != self._echelle_reglee():
            self.reglages.setValue("echelle_interface", int(v["echelle"]))
            demarrage = True
        self._cocher_menus()
        if demarrage and QMessageBox.question(self, NOM, tr(
                "La langue ou la taille de l'interface changera au prochain démarrage de Pixane Photo.\n\n"
                "Redémarrer maintenant ?")) == QMessageBox.Yes:
            self._redemarrer()

    def _cocher_menus(self):
        """Choix des sous-menus d'Affichage remis d'accord avec les réglages (changés dans les Préférences)."""
        for groupe, actuel in ((self._actions_theme, self.mode_theme),
                               (self._actions_langue, self.reglages.value("langue", langue.AUTO)),
                               (self._actions_echelle, self._echelle_reglee()),
                               (self._actions_icones, self._taille_icones())):
            for a in groupe.actions():
                a.setChecked(a.data() == actuel)

    def _redemarrer(self):
        """Ferme Pixane (en demandant pour les images non enregistrées) et le relance, avec l'image ouverte."""
        if not self._peut_fermer_tout():
            return
        chemin = str(self.doc.chemin) if self.doc and self.doc.chemin else None
        racine = str(Path(__file__).resolve().parents[1])
        QProcess.startDetached(sys.executable, ["-m", "pixane"] + ([chemin] if chemin else []), racine)
        self.close()

    def _echelle_reglee(self) -> int:
        try:
            return int(self.reglages.value("echelle_interface", 100))
        except (TypeError, ValueError):
            return 100

    def changer_echelle(self, pc: int):
        """Affichage > Taille de l'interface : toute l'interface plus petite ou plus grande (textes, icônes,
        boutons, panneaux), en plus de la mise à l'échelle de Windows ; au prochain démarrage."""
        if pc == self._echelle_reglee():
            return
        self.reglages.setValue("echelle_interface", int(pc))
        rep = QMessageBox.question(self, NOM, tr("La nouvelle taille de l'interface ({n} %) sera utilisée au "
                                                 "prochain démarrage de Pixane Photo.\n\nRedémarrer maintenant ?",
                                                 n=pc))
        if rep == QMessageBox.Yes:
            self._redemarrer()

    def _taille_icones(self) -> int:
        try:
            n = int(self.reglages.value("taille_icones", 22))
        except (TypeError, ValueError):
            n = 22
        return n if n in (18, 22, 28, 36) else 22

    def changer_taille_icones(self, n: int):
        """Affichage > Taille des icônes des outils : la barre des outils, tout de suite."""
        self.reglages.setValue("taille_icones", int(n))
        self._barre_outils.setIconSize(QSize(n, n))
        for b in self._barre_outils.findChildren(QToolButton):
            b.setIconSize(QSize(n, n))

    def _verifier_windows(self):
        signature = theme.signature_windows()
        if signature != self._signature_windows:
            self._signature_windows = signature
            self.changer_theme(self.mode_theme)

    def _basculer_theme(self):
        mode = theme.CLAIR if self.couleurs.sombre else theme.SOMBRE
        for a in self._actions_theme.actions():
            a.setChecked(a.text() == (tr("Clair") if mode == theme.CLAIR else tr("Sombre")))
        self.changer_theme(mode)

    def _appliquer_theme(self):
        c = self.couleurs
        for objet, nom in self._icones:
            ic = icone(nom, c.texte, c.accent)
            if isinstance(objet, Carte):
                objet.definir_icone(ic)
            else:
                objet.setIcon(ic)
        self.a_theme.setIcon(icone("soleil" if c.sombre else "lune", c.texte, c.accent))
        self.canevas.definir_couleurs(c.canevas, c.discret, c.accent)
        if hasattr(self, "calques"):
            self.calques.appliquer_icones()
        if hasattr(self, "panneau_texte"):
            self.panneau_texte.appliquer_icones()
        self._peindre_pastille_moteur()

    def _maj_cible_degrade(self):
        """Étiquette « → dans le masque » de l'outil Dégradé."""
        lab = getattr(self, "opt_degrade_masque", None)
        if lab is not None:
            lab.setVisible(self.doc is not None and self.canevas.outil == DEGRADE and self.canevas.sur_masque())

    def _degrade_dans_masque(self):
        self.statusBar().showMessage(tr("Le dégradé va dans le masque du calque : il rend le calque plus ou moins "
                                        "transparent, il ne le colore pas. Pour colorer, clique sur la vignette du "
                                        "calque (panneau Calques) ; pour un texte, le dégradé se pose alors sur "
                                        "les lettres."), 12000)

    def _actualiser(self):
        a_doc = self.doc is not None
        self._maj_cible_degrade()
        pret = a_doc and self.moteur.etat == "prêt"
        for a in (self.a_enregistrer, self.a_enregistrer_sous, self.a_fermer, self.a_tout, self.a_rien, self.a_inverser,
                  self.a_zoom_plus, self.a_zoom_moins, self.a_ajuster, self.a_recadrer_selection, self.a_taille, self.a_echelle_contenu,
                  self.a_pivoter_d, self.a_pivoter_g, self.a_pivoter_180, self.a_pivoter_angle, self.a_miroir_h, self.a_miroir_v,
                  self.a_redresser, self.a_recadrage_persp, self.a_transformer, self.a_transfo_perspective, self.a_transfo_distordre,
                  self.a_transfo_deformation, self.a_reglages_image, self.a_sel_agrandir,
                  self.a_sel_reduire, self.a_sel_adoucir, self.a_contour, self.a_plage_couleurs, self.a_couper, self.a_copier, self.a_supprimer_selection, self.a_remplir_motif,
                  self.a_style, self.a_copier_style, self.a_coller_style, self.a_enlever_style, self.a_figer_style,
                  self.a_nouveau_calque, self.a_dupliquer_calque, self.a_fusionner_calques, self.a_aplatir, self.a_zone_travail, self.a_exporter_cmjn, self.a_exporter_sous, self.a_imprimer,
                  self.a_tout_apparaitre,
                  self.a_epreuve, *self._actions_calques_doc()):
            a.setEnabled(a_doc)
        self._m_mode.setEnabled(a_doc)
        for a in self._actions_mode.actions():
            a.setChecked(a_doc and (a.text() == tr("Niveaux de gris")) == (self.doc.mode == "gris"))
        for a in self._actions_bits.actions():
            a.setChecked(a_doc and a.data() == self.doc.profondeur)
        self.a_exposition.setEnabled(a_doc and self.doc.profondeur == 32)
        self.a_epreuve.setChecked(a_doc and bool(self.doc.epreuve))
        for a in (self.a_effacer, self.a_remplir, self.a_modifier, self.a_agrandir, self.a_upscale, self.a_arriere_plan,
                  self.a_ia_bruit, self.a_ia_nettete, self.a_ia_restaurer,
                  self.a_sujet, self.a_sel_ciel, self.a_ia_coloriser, self.a_ia_lumiere, self.a_ia_ciel,
                  self.a_ia_profondeur, self.a_ia_personnes, self.a_ia_portrait):
            a.setEnabled(pret)
        self.a_ia_creer.setEnabled(self.moteur.etat == "prêt")      # aussi sans image ouverte : en crée une
        for b in (self.b_effacer, self.b_remplir, self.b_modifier, self.b_agrandir, self.b_upscale, self.b_arriere_plan):
            b.setEnabled(pret)
        titre = NOM
        if self.doc:
            nom = self.doc.nom_affiche()
            bits = {16: tr(" (16 bits)"), 32: tr(" (32 bits)")}.get(self.doc.profondeur, "")
            titre = f"{nom}{bits}{' •' if self.doc.modifie else ''} — {NOM}"
        self.setWindowTitle(titre)

    def guide(self, chapitre: str | None = None):
        """Guide de Pixane dans sa propre fenêtre (comme TwinPanel) ; F1 l'ouvre sur les raccourcis."""
        from .aide import FenetreGuide
        if getattr(self, "_fenetre_guide", None) is None or self._fenetre_guide.c is not self.couleurs:
            self._fenetre_guide = FenetreGuide(self.couleurs, self)
        self._fenetre_guide.ouvrir(chapitre)

    # ================================================================ moteur
    def installer_moteur(self):
        """Télécharge ComfyUI portable, ses extensions et les modèles (fenêtre qui montre tout avant)."""
        from .installation_moteur import PORTABLE, FenetreInstallation, deja_installe
        install = trouver_comfyui()
        dossier = None
        if install is not None:
            racine = Path(install["dir"]).parent
            if racine.name != PORTABLE or not deja_installe(racine.parent):
                self.completer_moteur(install)          # ComfyUI installé autrement : seulement ce qui manque
                return
            dossier = str(racine.parent)        # installé par Pixane : on complète (ex. Flux Schnell)
        schnell = kontext = False
        profondeur = True                       # petit modèle (137 Mo) : toujours proposé (case cochée)
        if dossier is not None:
            from .installation_moteur import lire_infos
            infos = lire_infos(Path(dossier)) or {}
            schnell = "schnell" in infos.get("elements", []) or "schnell" in (infos.get("versions") or {})
            kontext = "kontext" in infos.get("elements", []) or "kontext" in (infos.get("versions") or {})
        f = FenetreInstallation(self, dossier=dossier, schnell=schnell, kontext=kontext, profondeur=profondeur)
        f.commence.connect(self.moteur.arreter)      # ComfyUI ne doit pas tourner pendant qu'on le remplace
        f.installe.connect(lambda _d: self._redemarrer_moteur())
        f.exec()
        if self.moteur.etat == "arrêté":               # arrêté en route : on relance l'ancien
            self._redemarrer_moteur()

    def completer_moteur(self, install: dict | None = None):
        """ComfyUI déjà installé (pas par Pixane) : fenêtre qui ne télécharge que ce qui lui manque."""
        from .completer_moteur import FenetreCompleter
        install = install or trouver_comfyui()
        if install is None or self.moteur.etat != "prêt":
            QMessageBox.information(self, tr("Compléter le moteur IA"), tr(
                "Le moteur IA doit être démarré pour que Pixane Photo voie ce qui lui manque. Attends qu'il soit prêt "
                "(en bas de la fenêtre), puis recommence."))
            return
        f = FenetreCompleter(self.moteur.infos, self.moteur.dossiers_modeles(), install, self.moteur.externe, self)
        f.fini.connect(lambda _ok: self._redemarrer_moteur())      # relit ce que ComfyUI a maintenant
        f.exec()

    def _verifier_moteur_complet(self, install: dict):
        """ComfyUI installé autrement : s'il lui manque des extensions ou des modèles, le proposer (une fois pour
        une même liste ; ensuite, un message en bas et le menu IA > Installer le moteur IA)."""
        from .completer_moteur import manquants
        from .installation_moteur import go
        from dataclasses import replace
        from . import traduction
        elements, _notes = manquants(self.moteur.infos, self.moteur.dossiers_modeles(), install["dir"])
        if not traduction.installe():               # proposé aussi (une fois), avec l'explication dans la fenêtre
            elements += traduction.elements()[:1]
            elements[-1] = replace(elements[-1], nom=tr("Traducteur des consignes, français → anglais"),
                                   taille=traduction.TAILLE)
        if not elements:
            return
        cle = ",".join(sorted(e.cle for e in elements))
        if self.reglages.value("moteur_complet_vu", "") == cle:
            self.statusBar().showMessage(tr("Il manque des éléments au moteur IA : menu IA > Installer le moteur "
                                            "IA."), 10000)
            return
        if os.environ.get("PIXANE_REGLAGES") and not os.environ.get("PIXANE_PROPOSER"):
            return          # essais automatiques : pas de question qui bloque (le vrai Pixane, lui, demande)
        self.reglages.setValue("moteur_complet_vu", cle)
        if QMessageBox.question(self, tr("Moteur IA"), tr(
                "Pixane Photo utilise le ComfyUI déjà installé sur ce PC, mais il lui manque :\n{liste}\n\n"
                "À télécharger : environ {taille} (seulement ce qui manque, rien n'est remplacé).\n\n"
                "Voir le détail et installer maintenant ? (Plus tard : menu IA > Installer le moteur IA.)",
                liste="\n".join("• " + e.nom for e in elements),
                taille=go(sum(e.taille or 0 for e in elements)))) == QMessageBox.Yes:
            self.completer_moteur(install)

    def _verifier_moteur_a_jour(self):
        """Après le démarrage du moteur : si Pixane l'a installé et qu'une nouvelle version de Pixane demande
        d'autres versions (ComfyUI, extension, modèle), le proposer une fois. Installé autrement : proposer ce
        qui lui manque."""
        from .installation_moteur import PORTABLE, go, mises_a_jour_moteur
        install = trouver_comfyui()
        if install is None:
            return
        r = Path(install["dir"]).parent
        if r.name != PORTABLE:
            self._verifier_moteur_complet(install)
            return
        maj = mises_a_jour_moteur(r.parent)
        if not maj:
            return
        cle = ",".join(f"{e.cle}:{e.sha256 or e.url}" for e in maj)
        if self.reglages.value("moteur_maj_vue", "") == cle:
            self.statusBar().showMessage(tr("Une mise à jour du moteur IA attend : menu IA > Installer le moteur "
                                            "IA."), 10000)
            return
        self.reglages.setValue("moteur_maj_vue", cle)
        taille = sum(e.taille or 0 for e in maj)
        if QMessageBox.question(self, tr("Moteur IA"), tr(
                "Cette version de Pixane Photo utilise de nouvelles versions pour le moteur IA :\n{liste}\n\n"
                "À télécharger : environ {taille}. Le moteur sera arrêté pendant la mise à jour.\n\n"
                "Mettre à jour maintenant ? (Plus tard : menu IA > Installer le moteur IA.)",
                liste="\n".join("• " + e.nom for e in maj), taille=go(taille))) == QMessageBox.Yes:
            self.installer_moteur()

    def _redemarrer_moteur(self):
        self.moteur.arreter()
        self.moteur = Moteur()
        self.etat_moteur.emit(tr("démarrage…"))
        self._demarrer_moteur()

    def _demarrer_moteur(self):
        def travail(_progres):
            self.moteur.demarrer(self.etat_moteur.emit)
        t = self._tache(travail, lambda _: (self._actualiser(), self._verifier_moteur_a_jour()),
                        self._moteur_en_echec)
        t.lancer()

    def _moteur_en_echec(self, message: str):
        self.etat_moteur.emit(tr("indisponible"))
        self._actualiser()
        if self.moteur.etat == "introuvable":
            if QMessageBox.question(self, tr("Moteur IA"),
                                    tr("Le moteur IA (ComfyUI) n'est pas installé sur ce PC.\n\nVeux-tu que Pixane Photo "
                                       "l'installe maintenant ? Tu verras d'abord la liste des téléchargements "
                                       "(taille, source, licence).\n\nSans lui, tu peux quand même ouvrir, "
                                       "retoucher et enregistrer des photos.")) == QMessageBox.Yes:
                self.installer_moteur()
            return
        QMessageBox.warning(self, tr("Moteur IA"), tr("Le moteur IA n'a pas pu démarrer.\n\n{message}\n\n"
                                                      "Tu peux quand même ouvrir et enregistrer des photos.",
                                                      message=message))

    def _tache(self, fonction, ok, erreur) -> Tache:
        t = Tache(fonction)
        self._taches.add(t)

        def fin_ok(r):
            self._taches.discard(t)
            ok(r)

        def fin_erreur(m):
            self._taches.discard(t)
            erreur(m)
        t.fini.connect(fin_ok)
        t.echec.connect(fin_erreur)
        return t

    # ================================================================ fichiers
    def ouvrir(self):
        dossier = self.reglages.value("dossier", str(Path.home() / "Pictures"))
        chemins, _ = QFileDialog.getOpenFileNames(self, tr("Ouvrir une photo"), dossier,
                                                  f"{tr('Images')} ({EXTENSIONS_LECTURE});;"
                                                  f"{tr('Tous les fichiers')} (*)")
        for chemin in chemins:
            self.charger(chemin)

    def charger(self, chemin: str):
        for d in self.documents:                     # déjà ouverte : on revient à son onglet
            if d.chemin is not None and str(d.chemin.resolve()).lower() == str(Path(chemin).resolve()).lower():
                self._installer_document(d)
                return
        try:
            doc = Document.ouvrir(chemin)
        except Exception as e:
            QMessageBox.critical(self, tr("Ouvrir"), tr("Impossible d'ouvrir ce fichier :\n{erreur}", erreur=e))
            return
        self.reglages.setValue("dossier", str(Path(chemin).parent))
        self._ajouter_recent(chemin)
        self._installer_document(doc)

    def _montrer_document(self, doc: Document | None):
        """Affiche la photo d'un onglet (ou rien)."""
        if self.canevas.transfo is not None:
            self._valider_transfo()
        if self.canevas.recadre is not None:
            self.canevas.annuler_recadre()
        ancien = self.doc
        if ancien is not None:
            for signal, fonction in ((ancien.change, self._actualiser), (ancien.calques_changes, self._sync_texte),
                                     (ancien.calques_changes, self._maj_cible_degrade)):
                try:
                    signal.disconnect(fonction)
                except (RuntimeError, TypeError):
                    pass
        self.doc = doc
        if doc is not None:
            doc.change.connect(self._actualiser)
            doc.calques_changes.connect(self._sync_texte)
            doc.calques_changes.connect(self._maj_cible_degrade)
        self.barre_agrandir.hide()
        self.canevas.cadre = None
        if hasattr(self, "selection_auto"):
            self.selection_auto.fin_session()
        self.canevas.definir_document(doc)
        self.calques.definir_document(doc)
        self._sync_texte()
        self._actualiser()
        if doc is not None and doc.remarques:
            self.statusBar().showMessage("  ".join(doc.remarques), 15000)
            doc.remarques = []

    def enregistrer(self) -> bool:
        if not self.doc:
            return False
        from .raw import est_raw
        if self.doc.chemin is None or est_raw(self.doc.chemin):    # un RAW n'est jamais remplacé
            return self.enregistrer_sous()
        rep = QMessageBox.question(self, tr("Enregistrer"),
                                   tr("Remplacer le fichier d'origine ?\n{chemin}\n\n"
                                      "(« Non » pour choisir un autre nom)", chemin=self.doc.chemin),
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
        if rep == QMessageBox.Cancel:
            return False
        if rep == QMessageBox.No:
            return self.enregistrer_sous()
        return self._ecrire(self.doc.chemin)

    def enregistrer_sous(self) -> bool:
        if not self.doc:
            return False
        plusieurs = len(self.doc.calques) > 1 or any(c.texte is not None or c.style is not None
                                                      for c in self.doc.calques)
        if self.doc.chemin:
            from .raw import est_raw
            garde = not plusieurs or self.doc.chemin.suffix.lower() in (".psd", ".ora")
            ext = self.doc.chemin.suffix if garde else ".piximg"
            if est_raw(self.doc.chemin):
                ext = ".piximg" if plusieurs else ".jpg"
            ajout = getattr(self.doc, "suffixe_nom", None) or tr("_retouche")
            propose = str(self.doc.chemin.with_name(self.doc.chemin.stem + ajout + ext))
        else:
            base = self.doc.nom or "image"
            propose = str(Path(self.reglages.value("dossier", str(Path.home()))) / (base + (".piximg" if plusieurs
                                                                                           else ".jpg")))
        formats = [tr("Projet Pixane Photo") + " (*.piximg)", tr("Photoshop, avec les calques") + " (*.psd)",
                   tr("OpenRaster, pour Krita et GIMP") + " (*.ora)",
                   "JPEG (*.jpg)", "PNG (*.png)", "TIFF (*.tif)", "WebP (*.webp)",
                   tr("OpenEXR, 32 bits (HDR)") + " (*.exr)", tr("Radiance, 32 bits (HDR)") + " (*.hdr)"]
        if self.doc.chemin and self.doc.chemin.suffix.lower() == ".psd":
            formats.insert(0, formats.pop(1))           # photo venue de Photoshop : PSD proposé d'abord
        elif not plusieurs:
            formats = formats[3:] + formats[:3]
        chemin, _ = QFileDialog.getSaveFileName(self, tr("Enregistrer sous"), propose, ";;".join(formats),
                                                formats[0])
        if not chemin:
            return False
        if not Path(chemin).suffix:
            chemin += ".jpg"
        return self._ecrire(Path(chemin))

    def _ecrire(self, chemin: Path) -> bool:
        if self.canevas.transfo is not None:
            self._valider_transfo()
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.doc.enregistrer(chemin)
        except Exception as e:
            QMessageBox.critical(self, tr("Enregistrer"), tr("Impossible d'enregistrer :\n{erreur}", erreur=e))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self._ajouter_recent(str(chemin))
        self._recuperation.enregistree(self.doc)
        self.doc.suffixe_nom = None                 # déjà dans le nom du fichier enregistré
        ext = chemin.suffix.lower()
        textes = any(c.texte is not None for c in self.doc.calques)
        styles = any(c.style is not None and not c.style.vide() for c in self.doc.calques)
        if len(self.doc.calques) > 1 and ext not in EXTENSIONS_CALQUES:
            self.statusBar().showMessage(tr("Enregistré à plat (sans les calques) : {chemin}  —  pour garder les "
                                            "calques, enregistre aussi en .piximg", chemin=chemin), 10000)
        elif ext in (".ora", ".psd") and textes:
            self.statusBar().showMessage(tr("Enregistré : {chemin}  —  dans ce format, les textes sont des images ; "
                                            "pour les garder modifiables, enregistre aussi en .piximg",
                                            chemin=chemin), 10000)
        elif ext in (".ora", ".psd") and styles:
            self.statusBar().showMessage(tr("Enregistré : {chemin}  —  dans ce format, les styles de calque sont mis "
                                            "dans les pixels ; pour les garder modifiables, enregistre aussi en .piximg",
                                            chemin=chemin), 10000)
        else:
            self.statusBar().showMessage(tr("Enregistré : {chemin}", chemin=chemin), 5000)
        self._actualiser()
        return True

    def _peut_fermer(self) -> bool:
        if not self.doc or not self.doc.modifie:
            return True
        rep = QMessageBox.question(self, NOM, tr("La photo a été modifiée. Enregistrer avant de continuer ?"),
                                   QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if rep == QMessageBox.Save:
            return self.enregistrer_sous()
        return rep == QMessageBox.Discard

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        for u in urls:
            self.charger(u)

    def closeEvent(self, e):
        if not self._peut_fermer_tout():
            e.ignore()
            return
        self.moteur.arreter()
        traduction.arreter()
        self._recuperation.tout_effacer()
        self.reglages.setValue("texte_defaut", json.dumps(self.panneau_texte.defaut.vers_dict(), ensure_ascii=False))
        QApplication.instance().removeEventFilter(self)     # boutons de la souris : plus après la fermeture
        e.accept()

    # ================================================================ sélection
    def _selection_modifiee(self, avant, texte):
        self.historique.push(CommandeEtat(self.doc, avant, self.doc.etat(), texte))

    # ================================================================ couper, copier, coller, supprimer
    def copier(self) -> bool:
        """Copie les pixels sélectionnés du calque choisi (tout le calque sans sélection) ; ils gardent leur
        transparence et leur place (pour Coller), et vont aussi aux autres logiciels (PNG)."""
        if not self.doc:
            return False
        img, place = self.doc.pixels_choisis()
        donnees = QMimeData()
        donnees.setImageData(img)
        tampon = QBuffer()
        tampon.open(QBuffer.WriteOnly)
        img.save(tampon, "PNG")
        donnees.setData("image/png", tampon.data())
        donnees.setData(MIME_PLACE, f"{place.x()},{place.y()}".encode())
        QApplication.clipboard().setMimeData(donnees)
        self.statusBar().showMessage(tr("Copié : {l} × {h} px (calque « {nom} »).", l=img.width(), h=img.height(),
                                        nom=self.doc.calque_actif.nom), 5000)
        return True

    def remplir_motif(self, choix=None):
        """Édition > Remplir avec un motif… : le calque choisi (dans la sélection s'il y en a une) couvert d'un
        motif de la bibliothèque. choix : (clé, échelle, opacité) sans fenêtre (essais)."""
        action = tr("Remplir avec un motif")
        if not self._verifier_pixels(action):
            return
        doc, c = self.doc, self.doc.calque_actif
        sel = None if doc.selection_vide() else doc.selection
        if not isinstance(choix, tuple):                  # (clic de menu : un booléen arrive ici)
            from .motifs import DialogueRemplirMotif
            ou = tr("Calque « {nom} », {ou}.", nom=c.nom,
                    ou=tr("dans la sélection") if sel is not None else tr("sur tout le calque"))
            d = DialogueRemplirMotif(self, self.canevas.motif_cle, self.canevas.motif_echelle, 1.0, ou)
            if not d.exec():
                return
            choix = (d.cle, d.echelle, d.opacite)
        cle, echelle, opacite = choix
        from .motifs import image_pavee
        from .outils_dessin import remplir_motif
        motif = image_pavee(cle, c.image.width(), c.image.height(), echelle)
        if motif is None:
            QMessageBox.information(self, action, tr("Motif introuvable dans la bibliothèque."))
            return
        avant = doc.etat()
        apres = doc.etat_calque_modifie(doc.actif, image=remplir_motif(c.image, motif, opacite, sel), texte=None)
        self.historique.push(CommandeEtat(doc, avant, apres, action))

    def couper(self):
        if not self.doc or not self._verifier_selection_simple() or not self._verifier_verrou(tr("Couper")):
            return
        avant = self.doc.etat()
        apres = self.doc.etat_effacer_selection()
        if apres is not None and self.copier():
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Couper")))

    def coller(self):
        if not self.doc:
            self.nouvelle_depuis_presse_papiers()
            return
        donnees = QApplication.clipboard().mimeData()
        img = QApplication.clipboard().image()
        if donnees is None or img.isNull():
            self.statusBar().showMessage(tr("Le presse-papiers ne contient pas d'image."), 5000)
            return
        place = None
        if donnees.hasFormat(MIME_PLACE):
            try:
                x, y = (int(v) for v in bytes(donnees.data(MIME_PLACE)).decode().split(","))
                place = QPoint(x, y)
            except ValueError:
                pass
        img = img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
        w, h = self.doc.taille()
        t = None
        if img.width() > w or img.height() > h:
            # plus grande que la photo : réduite pour tenir entière, puis le cadre Transformer s'ouvre ; tous ses
            # pixels sont gardés jusqu'à la validation (on peut la réagrandir sans perte)
            from PySide6.QtCore import QRect
            t = Transformation(img, QRect(0, 0, img.width(), img.height()))
            t.centre = QPointF(w / 2, h / 2)
            t.sx = t.sy = min(w / img.width(), h / img.height())
            img, place = t.rendu(w, h), QPoint(0, 0)
        avant = self.doc.etat()
        apres = self.doc.etat_coller(img, place)
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Coller")))
        if t is not None and self.canevas.transfo is None:
            self._commencer_transfo(t)
            self.statusBar().showMessage(tr("Image collée plus grande que la photo : réduite à {p} %. Ajuste sa taille "
                                            "avec les poignées, puis Entrée.", p=round(t.sx * 100)), 15000)

    def supprimer_selection(self):
        if not self.doc or not self._verifier_selection_simple() or \
                not self._verifier_verrou(tr("Supprimer la sélection")):
            return
        if self.doc.calque_actif.texte is not None:
            self.statusBar().showMessage(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme "
                                            "texte (Ctrl+Z pour revenir).", nom=self.doc.calque_actif.nom), 6000)
        if vectoriel(self.doc.calque_actif):
            self.statusBar().showMessage(self.canevas.texte_devient_image(self.doc.calque_actif), 6000)
        avant = self.doc.etat()
        apres = self.doc.etat_effacer_selection()
        if apres is not None:
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Supprimer la sélection")))

    # ================================================================ réglages de l'image
    def reglages_image(self):
        """Luminosité, contraste, couleurs, netteté du calque choisi (dans la sélection s'il y en a une), avec un
        aperçu en direct calculé en arrière-plan (la fenêtre reste fluide même sur une grande photo)."""
        if not self.doc or not self._verifier_verrou(tr("Réglages de l'image")):
            return
        doc = self.doc
        avant, modifie = doc.etat(), doc.modifie
        index, calque = doc.actif, doc.calque_actif
        selection = None if doc.selection_vide() else doc.selection.copy()
        d = FenetreReglages(calque.nom, selection is not None, self,
                            propose_auto=lambda: auto(calque.image, selection))
        d.adjustSize()                               # à droite, sur le panneau IA : la photo reste visible
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        suivi = {"occupe": False, "attente": None, "ouvert": True}

        def montrer(r, img):
            if not suivi["ouvert"]:
                return
            if neutre(r) or img is None:
                doc.apercu_calque(index, calque.image, calque.texte)
            else:
                doc.apercu_calque(index, img)

        def calculer(r):
            if suivi["occupe"]:
                suivi["attente"] = r                 # on ne garde que la dernière demande
                return
            if neutre(r):
                montrer(r, None)
                return
            suivi["occupe"] = True
            t = Tache(lambda _progres: ajuster(calque.image, r, selection))
            t.fini.connect(lambda img: fini(r, img))
            t.echec.connect(lambda _m: fini(r, None))
            suivi["tache"] = t                       # garde la tâche en vie
            t.lancer()

        def fini(r, img):
            suivi["occupe"] = False
            montrer(r, img)
            if suivi["attente"] is not None:
                r2, suivi["attente"] = suivi["attente"], None
                calculer(r2)

        d.change.connect(calculer)
        ok = d.exec() == QDialog.Accepted
        suivi["ouvert"] = False
        r = d.valeurs()
        doc.appliquer_etat(avant)
        doc.modifie = modifie
        if ok and not neutre(r):
            if calque.texte is not None:
                self.statusBar().showMessage(tr("Le texte « {nom} » devient une image : il n'est plus modifiable "
                                                "comme texte (Ctrl+Z pour revenir).", nom=calque.nom), 6000)
            if vectoriel(calque):
                self.statusBar().showMessage(self.canevas.texte_devient_image(calque), 6000)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                img = ajuster(calque.image, r, selection)
            finally:
                QApplication.restoreOverrideCursor()
            apres = doc.etat_calque_modifie(index, image=img, texte=None)
            self.historique.push(CommandeEtat(doc, avant, apres, tr("Réglages de l'image")))

    # ================================================================ nouvelle image, fichiers récents
    def nouvelle_image(self):
        pp = QApplication.clipboard().image()
        l, h = (pp.width(), pp.height()) if not pp.isNull() else (1920, 1080)
        d = NouvelleImage(l if not pp.isNull() else None, h if not pp.isNull() else None, self.reglages, self)
        if d.exec():
            doc = Document(d.image())
            doc.dpi = d.format_choisi().dpi
            doc.mode = d.mode_couleur()
            doc.nom = d.nom_document()
            doc.reperes = d.reperes()
            self._installer_document(doc)
            self.doc.modifie = True
            if doc.reperes:
                self.canevas.reperes_visibles = True      # fond perdu et zone de sécurité visibles tout de suite
            self._actualiser()

    def nouvelle_depuis_presse_papiers(self):
        img = QApplication.clipboard().image()
        if img.isNull():
            self.statusBar().showMessage(tr("Le presse-papiers ne contient pas d'image."), 5000)
            return
        self._installer_document(Document(img.convertToFormat(QImage.Format_ARGB32_Premultiplied)))
        self.doc.modifie = True
        self._actualiser()

    def _recents(self) -> list[str]:
        v = self.reglages.value("recents", [])
        return [v] if isinstance(v, str) else list(v or [])

    def _ajouter_recent(self, chemin: str):
        chemin = str(Path(chemin))
        liste = [chemin] + [c for c in self._recents() if c.lower() != chemin.lower()]
        self.reglages.setValue("recents", liste[:10])

    def _remplir_recents(self):
        m = self.m_recents
        m.clear()
        liste = self._recents()
        if not liste:
            a = m.addAction(tr("(aucun)"))
            a.setEnabled(False)
            return
        for i, c in enumerate(liste):
            a = m.addAction(f"&{(i + 1) % 10}  {Path(c).name}")
            a.setToolTip(c)
            a.setStatusTip(c)
            a.triggered.connect(lambda _=False, ch=c: self._ouvrir_recent(ch))
        m.addSeparator()
        m.addAction(tr("Effacer la liste"), lambda: self.reglages.setValue("recents", []))

    def _ouvrir_recent(self, chemin: str):
        if not Path(chemin).is_file():
            QMessageBox.information(self, tr("Fichiers récents"),
                                    tr("Ce fichier n'existe plus :\n{chemin}", chemin=chemin))
            self.reglages.setValue("recents", [c for c in self._recents() if c != chemin])
            return
        self.charger(chemin)

    # ================================================================ géométrie de l'image
    def _geometrie(self, titre: str, quoi):
        if not self.doc or not self._verifier_verrou(titre, tous=True):
            return
        avant = self.doc.etat()
        if quoi in ("h", "v"):
            apres = self.doc.etat_miroir(quoi == "h")
            if any(c.texte is not None for c in self.doc.calques):
                self.statusBar().showMessage(tr("Les textes retournés deviennent des images (Ctrl+Z pour "
                                                "revenir)."), 6000)
        else:
            apres = self.doc.etat_pivote(quoi)
        self.historique.push(CommandeEtat(self.doc, avant, apres, titre))
        self.noter_action({"genre": "geometrie", "quoi": quoi})

    def taille_image(self):
        if not self.doc or not self._verifier_verrou(tr("Taille de l'image"), tous=True):
            return
        w, h = self.doc.taille()
        d = TailleImage(w, h, self, image=self.doc.image)
        if d.exec() and d.valeurs() != (w, h):
            W, H = d.valeurs()
            avant = self.doc.etat()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                apres = self.doc.etat_taille(W, H)
            finally:
                QApplication.restoreOverrideCursor()
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Taille de l'image")))
            from .actions_auto import etape_taille
            self.noter_action(etape_taille(w, h, W, H))

    def echelle_contenu(self):
        """Image > Mise à l'échelle d'après le contenu : nouvelles proportions, le sujet garde les siennes."""
        titre = tr("Mise à l'échelle d'après le contenu")
        if not self.doc or not self._verifier_verrou(titre, tous=True):
            return
        from .dialogues_image import EchelleContenu
        from .document import masque
        w, h = self.doc.taille()
        sel = None if self.doc.selection_vide() else masque(self.doc.selection)
        d = EchelleContenu(w, h, self.doc.image, sel, self)
        if not d.exec() or d.valeurs() == (w, h):
            return
        W, H = d.valeurs()
        avant = self.doc.etat()
        modifiables = any(c.texte is not None or c.pinceau is not None or c.forme is not None
                          for c in self.doc.calques)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            apres = self.doc.etat_echelle_contenu(W, H, d.proteger(), d.force_valeur())
        finally:
            QApplication.restoreOverrideCursor()
        self.historique.push(CommandeEtat(self.doc, avant, apres, titre))
        if modifiables:
            self.statusBar().showMessage(tr("Les textes, formes et traits de pinceau sont devenus des images "
                                            "(Ctrl+Z pour revenir)."), 6000)

    def zone_travail(self):
        """Image > Taille de la zone de travail : agrandit (ou rogne) la feuille sans étirer l'image."""
        if not self.doc or not self._verifier_verrou(tr("Taille de la zone de travail"), tous=True):
            return
        w, h = self.doc.taille()
        d = ZoneTravail(w, h, self.doc.dpi, self, image=self.doc.image)
        if not d.exec() or d.pixels() == (w, h):
            return
        (W, H), (dx, dy) = d.pixels(), d.decalage()
        avant = self.doc.etat()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            apres = self.doc.etat_zone_travail(W, H, dx, dy, d.couleur())
        finally:
            QApplication.restoreOverrideCursor()
        decales = [(s, v + (dy if s == "h" else dx)) for s, v in self.doc.reperes]
        self.historique.push(CommandeZoneTravail(self.doc, avant, apres, tr("Taille de la zone de travail"),
                                                 self.doc.reperes, decales))

    def tout_faire_apparaitre(self):
        """Image > Tout faire apparaître : la feuille s'agrandit pour montrer tout ce qui dépasse des calques."""
        if not self.doc or not self._verifier_verrou(tr("Tout faire apparaître"), tous=True):
            return
        r = self.doc.rect_tout()
        avant = self.doc.etat()
        apres = self.doc.etat_tout_faire_apparaitre()
        if apres is None:
            self.statusBar().showMessage(tr("Rien ne dépasse de la feuille."), 6000)
            return
        dx, dy = -r.x(), -r.y()
        decales = [(s, v + (dy if s == "h" else dx)) for s, v in self.doc.reperes]
        self.historique.push(CommandeZoneTravail(self.doc, avant, apres, tr("Tout faire apparaître"),
                                                 self.doc.reperes, decales))
        self.statusBar().showMessage(tr("Feuille agrandie : {l} × {h} px", l=r.width(), h=r.height()), 6000)

    def changer_mode(self, mode: str):
        """Image > Mode : couleurs RVB ou niveaux de gris."""
        if not self.doc or mode == self.doc.mode:
            return
        self.doc.changer_mode(mode)
        self.statusBar().showMessage(tr("Mode : niveaux de gris (l'image est vue et enregistrée en gris ; les "
                                        "calques gardent leurs couleurs)") if mode == "gris"
                                     else tr("Mode : couleurs RVB"), 8000)
        self._actualiser()

    def basculer_tramage(self, actif: bool):
        """Image > Mode > Tramage vers 8 bits (gardé dans les réglages)."""
        from . import profondeur
        profondeur.tramage = bool(actif)
        self.reglages.setValue("tramage", bool(actif))
        if self.doc and self.doc.profondeur > 8:
            self.doc._tramee = None
            self.doc.change.emit()

    def exposition_ecran(self):
        """Affichage > Exposition 32 bits : aperçu plus clair ou plus sombre (l'image ne change pas)."""
        if not self.doc or self.doc.profondeur != 32:
            return
        from .dialogue_hdr import DialogueExposition

        def rafraichir():
            if self.doc:
                self.doc.change.emit()
        d = DialogueExposition(self, rafraichir)
        d.exec()
        d.deleteLater()

    def changer_profondeur(self, bits: int):
        """Image > Mode > 8 / 16 / 32 bits par couche (annulable). De 32 bits vers moins : Virage HDR si l'image a
        des couleurs plus claires que le blanc."""
        if not self.doc or bits == self.doc.profondeur:
            self._actualiser()
            return
        doc = self.doc
        virage = None
        if doc.profondeur == 32:
            from . import profondeur as prof
            from .dialogue_hdr import DialogueVirage
            img = doc.image_profonde()
            if float(prof.tab32(img)[..., :3].max(initial=0)) > 1.0 + 1e-4:
                d = DialogueVirage(self, img, bits)
                ok = d.exec() == QDialog.Accepted
                virage = d.valeurs()
                d.deleteLater()
                if not ok:
                    self._actualiser()
                    return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            avant, apres = doc.etat(), doc.etat_profondeur(bits, virage)
            self.historique.push(CommandeProfondeur(doc, avant, apres, doc.profondeur, bits,
                                                    tr("Mode {n} bits", n=bits)))
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(
            tr("16 bits par couche : 65 536 nuances par couleur au lieu de 256 (dégradés et réglages sans "
               "cassures). Enregistrez en PSD, TIFF, PNG ou .piximg pour les garder.") if bits == 16
            else tr("32 bits par couche (HDR) : les couleurs peuvent être plus claires que le blanc. Enregistrez en "
                    ".piximg, EXR, HDR ou TIFF pour les garder ; Affichage > Exposition 32 bits pour les voir.")
            if bits == 32 else tr("8 bits par couche."), 10000)
        self._actualiser()

    def basculer_epreuve(self):
        """Affichage > Aperçu de l'impression : couleurs montrées comme une fois imprimées (profil CMJN)."""
        if not self.doc:
            return
        if self.doc.epreuve:
            self.doc.epreuve = None
        else:
            from .impression import profil_defaut, profils_cmjn
            profil = self.reglages.value("cmjn_profil", "") or profil_defaut()
            if profil not in [c for _n, c in profils_cmjn()]:
                profil = profil_defaut()
            if not profil:
                QMessageBox.information(self, tr("Aperçu de l'impression"), tr("Aucun profil CMJN trouvé dans Windows."))
                self.a_epreuve.setChecked(False)
                return
            self.doc.epreuve = (profil, self.reglages.value("cmjn_intention", "perceptive") or "perceptive")
            nom = next((n for n, c in profils_cmjn() if c == profil), profil)
            self.statusBar().showMessage(tr("Aperçu de l'impression : {profil}", profil=nom), 8000)
        self.canevas.update()
        self._actualiser()

    def exporter_sous(self):
        """Fichier > Exporter sous : une copie à plat pour un envoi normal (pleine taille, pleine qualité, résolution,
        profil de couleur et EXIF gardés). La photo ouverte reste telle quelle (son fichier ne change pas)."""
        if not self.doc:
            return
        if self.canevas.transfo is not None:
            self._valider_transfo()
        formats = {".jpg": "JPEG (*.jpg)", ".png": tr("PNG (avec la transparence)") + " (*.png)",
                   ".tif": "TIFF (*.tif)", ".webp": "WebP (*.webp)",
                   ".exr": tr("OpenEXR, 32 bits (HDR)") + " (*.exr)", ".hdr": tr("Radiance, 32 bits (HDR)") + " (*.hdr)"}
        ext = self.reglages.value("exporter_format", ".jpg")
        ext = ext if ext in formats else ".jpg"
        base = self.doc.chemin.stem if self.doc.chemin else (self.doc.nom or "image")
        base += getattr(self.doc, "suffixe_nom", None) or ""
        dossier = self.doc.chemin.parent if self.doc.chemin else Path(self.reglages.value("dossier", str(Path.home())))
        propose = dossier / (base + ext)
        if self.doc.chemin and propose == self.doc.chemin:          # ne pas proposer d'écraser la photo d'origine
            propose = dossier / (base + tr("_retouche") + ext)
        ordre = [ext] + [e for e in formats if e != ext]
        chemin, filtre = QFileDialog.getSaveFileName(self, tr("Exporter sous"), str(propose),
                                                     ";;".join(formats[e] for e in ordre), formats[ext])
        if not chemin:
            return
        chemin = Path(chemin)
        if chemin.suffix.lower() not in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".exr", ".hdr"):
            chemin = chemin.with_name(chemin.name + next(e for e in formats if formats[e] == filtre))
        self.reglages.setValue("exporter_format", {".jpeg": ".jpg", ".tiff": ".tif"}.get(chemin.suffix.lower(),
                                                                                         chemin.suffix.lower()))
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.doc.exporter(chemin)
        except Exception as e:
            QMessageBox.critical(self, tr("Exporter sous"), tr("Impossible d'enregistrer :\n{erreur}", erreur=e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(tr("Exporté : {chemin}  —  la photo ouverte n'a pas changé", chemin=chemin), 8000)

    def exporter_impression(self):
        """Fichier > Exporter pour l'impression : TIFF, PDF ou JPEG en CMJN, profil intégré."""
        if not self.doc:
            return
        d = ExportImpression(self.doc.dpi, self.reglages, self)
        if not d.exec():
            return
        v = d.valeurs()
        base = self.doc.chemin.stem if self.doc.chemin else (self.doc.nom or "image")
        dossier = self.doc.chemin.parent if self.doc.chemin else Path(self.reglages.value("dossier", str(Path.home())))
        filtre = {".tif": "TIFF (*.tif)", ".pdf": "PDF (*.pdf)", ".jpg": "JPEG (*.jpg)"}[v["ext"]]
        chemin, _ = QFileDialog.getSaveFileName(self, tr("Exporter pour l'impression (CMJN)"),
                                                str(dossier / (base + tr("_cmjn") + v["ext"])), filtre)
        if not chemin:
            return
        if not Path(chemin).suffix:
            chemin += v["ext"]
        from .impression import enregistrer_cmjn
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            enregistrer_cmjn(self.doc.image, Path(chemin), v["profil"], v["intention"], v["compensation"], v["dpi"],
                             v["qualite"])
        except Exception as e:
            QMessageBox.critical(self, tr("Exporter pour l'impression"), tr("Impossible d'enregistrer :\n{erreur}",
                                                                              erreur=e))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(tr("Exporté en CMJN : {chemin}", chemin=chemin), 8000)

    def pivoter_angle(self):
        """Image > Pivoter selon un angle… : toute l'image tourne de l'angle tapé (au degré près, ou au dixième) ;
        la feuille s'agrandit pour tout garder, les coins sont transparents."""
        if not self.doc or not self._verifier_verrou(tr("Pivoter"), tous=True):
            return
        angle, ok = QInputDialog.getDouble(
            self, tr("Pivoter selon un angle"),
            tr("Angle en degrés (sens des aiguilles d'une montre ; négatif : sens inverse) :"),
            float(self.reglages.value("angle_pivoter", 0.0) or 0.0), -359.9, 359.9, 1)
        if not ok or abs(angle) < 0.05:
            return
        self.reglages.setValue("angle_pivoter", angle)
        avant = self.doc.etat()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            apres = self.doc.etat_redresse(angle, recadrer=False)
        finally:
            QApplication.restoreOverrideCursor()
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Pivoter")))

    def redresser(self):
        if not self.doc or not self._verifier_verrou(tr("Redresser"), tous=True):
            return
        d = Redresser(self.doc.image, self)
        if d.exec():
            angle, recadrer = d.valeurs()
            if abs(angle) < 0.05:
                return
            avant = self.doc.etat()
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                apres = self.doc.etat_redresse(angle, recadrer)
            finally:
                QApplication.restoreOverrideCursor()
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Redresser")))

    # ================================================================ transformer un calque (Ctrl+T)
    # ================================================================ style du calque
    def style_calque(self):
        if not self.doc or getattr(self, "_dialogue_style", None) is not None:
            return
        if self.doc.calque_actif.special:
            QMessageBox.information(self, tr("Style du calque"), tr("Un groupe ou un calque de réglage n'a pas de "
                                                                    "style : choisis un calque d'image ou de texte."))
            return
        if self.canevas.transfo is not None:
            self._valider_transfo()
        from .dialogue_style import DialogueStyle
        d = DialogueStyle(self, self.doc.actif)
        self._dialogue_style = d
        self.canevas.style_ouvert = True
        self.canevas._curseur()

        def fin():
            self.canevas.style_ouvert = False
            self.canevas._curseur()
            self.canevas.update()
            self._dialogue_style = None
            d.deleteLater()
        d.fini.connect(fin)
        d.show()
        d.raise_()
        d.activateWindow()

    def copier_style(self):
        if not self.doc:
            return
        st = self.doc.calque_actif.style
        if st is None or st.vide():
            self.statusBar().showMessage(tr("Ce calque n'a pas de style à copier."), 5000)
            return
        self._style_copie = st
        self.statusBar().showMessage(tr("Style copié : choisis un autre calque, puis Calque > Coller le style."), 6000)

    def coller_style(self):
        st = getattr(self, "_style_copie", None)
        if not self.doc or st is None:
            self.statusBar().showMessage(tr("Aucun style copié (Calque > Copier le style)."), 5000)
            return
        self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, style=st), tr("Coller le style"))

    def enlever_style(self):
        if self.doc and self.doc.calque_actif.style is not None:
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, style=None), tr("Enlever le style"))

    def figer_style(self):
        """Les effets deviennent des pixels du calque (pour le gommer, le peindre… avec ses effets)."""
        if not self.doc:
            return
        c = self.doc.calque_actif
        if c.style is None or c.style.vide():
            self.statusBar().showMessage(tr("Ce calque n'a pas de style."), 5000)
            return
        if not self._verifier_verrou(tr("Mettre le style dans les pixels")):
            return
        from .styles import image_rendue
        self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, image=image_rendue(c), style=None,
                                                            texte=None), tr("Mettre le style dans les pixels"))

    def decaler_selection(self, dx: int, dy: int):
        """Flèches du clavier avec un outil de sélection : la sélection (seulement le contour, pas les pixels) bouge
        de 1 pixel (Maj : 10). Les appuis qui se suivent ne font qu'une étape d'Annuler."""
        if not self.doc or self.doc.selection_vide():
            return
        w, h = self.doc.taille()
        sel = nouvelle_selection(w, h)
        p = QPainter(sel)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawImage(dx, dy, self.doc.selection)
        p.end()
        avant = self.doc.etat()
        self.historique.push(CommandeEtat(self.doc, avant, (self.doc.calques, self.doc.actif, sel),
                                          tr("Déplacer la sélection"), cle=("fleches", id(self.doc))))

    def _cadre_deplacer(self, oui: bool):
        self.canevas.cadre_deplacer = oui
        self.reglages.setValue("cadre_deplacer", oui)
        self.canevas.update()

    def transformer(self, mode: str = "libre"):
        mode = mode if isinstance(mode, str) else "libre"    # (clic de menu : un booléen arrive ici)
        if not self.doc or self.canevas.cadre is not None:
            return
        if self.canevas.transfo is not None:              # déjà en cours : on change seulement de mode
            if mode != "libre":
                self._changer_mode_transfo(mode)
            return
        self._mode_demande = mode
        if not self._verifier_pixels(tr("Transformer le calque")):
            return
        c = self.doc.calque_actif
        o = origine_valide(c)
        if o is not None and self.doc.rect_selection() is None:   # meilleure version : on repart d'elle (sans perte)
            self._commencer_transfo(transformation_depuis(o))
            return
        entiere, ox, oy = image_entiere(c)                 # même ce qui dépasse de la feuille
        source, fond = entiere, None
        if self.doc.rect_selection() is not None:        # sélection : seulement l'élément sélectionné
            choix = QImage(entiere.size(), QImage.Format_ARGB32_Premultiplied)
            choix.fill(0)
            p = QPainter(choix)
            p.drawImage(-ox, -oy, self.doc.selection)
            p.end()
            source, fond = entiere.copy(), entiere.copy()
            for img, mode in ((source, QPainter.CompositionMode_DestinationIn),
                              (fond, QPainter.CompositionMode_DestinationOut)):
                p = QPainter(img)
                p.setCompositionMode(mode)
                p.drawImage(0, 0, choix)
                p.end()
        a = tableau(source)[:, :, 3]
        ys, xs = (a > 0).nonzero()
        if not len(ys):
            self.statusBar().showMessage(tr("Rien à transformer : la sélection est vide sur ce calque.") if fond
                                         is not None else tr("Le calque « {nom} » est vide : rien à transformer.",
                                                             nom=c.nom), 6000)
            return
        from PySide6.QtCore import QRect
        rect = QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
        if c.texte is not None:
            self.statusBar().showMessage(tr("Le texte « {nom} » devient une image (pour garder un texte modifiable, "
                                            "change sa taille et tourne-le avec l'outil Texte).", nom=c.nom), 8000)
        t = Transformation(source, rect, fond, QPoint(ox, oy))
        if vectoriel(c):
            if fond is None:                # calque de pinceau (de forme) entier : ses traits suivront (modifiable)
                t.depart_pinceau = QPointF(ox + rect.x(), oy + rect.y())
            else:
                self.statusBar().showMessage(self.canevas.texte_devient_image(c), 8000)
        self._commencer_transfo(t)

    def _commencer_transfo(self, t: Transformation):
        t.echelle_depart = abs(t.sx * t.sy) or 1.0         # pour mettre le style à l'échelle du geste seul
        mode, self._mode_demande = getattr(self, "_mode_demande", "libre"), "libre"
        if mode != "libre":
            t.passer_mode(mode)
        self._transfo_avant = (self.doc.etat(), self.doc.modifie)
        self.canevas.commencer_transfo(t, self.doc.actif)
        self.opt_pinceau.hide()                   # inutile pendant Ctrl+T ; avant show() (sinon la barre déborde)
        self.opt_transfo.show()
        self.options.adjustSize()
        self.barre_haut.layout().invalidate()
        self._transfo_change()
        self.statusBar().showMessage(tr("Transformer : coins = taille (Maj : libre), dedans = déplacer, dehors = "
                                        "tourner, au degré près (Maj : par 15°) ; ou tapez l'angle et la taille en "
                                        "haut. Entrée pour valider, Échap pour annuler."), 15000)

    def retour(self):
        """Annuler (Ctrl+Z, bouton « retour » de la souris) : pendant un travail pas encore validé, défait son
        dernier geste (au début : l'abandonne) ; sinon, annule la dernière action."""
        if not self.canevas.geste_arriere():
            self.groupe_historique.undo()
        self._maj_annuler()

    def suivant(self):
        """Rétablir (Ctrl+Y, bouton « suivant » de la souris) : refait le geste défait, ou l'action annulée."""
        if not self.canevas.geste_avant():
            self.groupe_historique.redo()
        self._maj_annuler()

    def _maj_annuler(self, *_):
        a, r, g = self.a_annuler, self.a_retablir, self.groupe_historique
        pa, pr = tr("Annuler|édition"), tr("Rétablir|édition")
        if self.canevas.travail() is not None:
            a.setText(pa)
            a.setEnabled(True)
            r.setText(pr)
            r.setEnabled(self.canevas.peut_refaire_geste())
        else:
            a.setText(f"{pa} {g.undoText()}".strip())
            a.setEnabled(g.canUndo())
            r.setText(f"{pr} {g.redoText()}".strip())
            r.setEnabled(g.canRedo())

    def eventFilter(self, objet, e):
        """Boutons « retour » / « suivant » de la souris, partout dans la fenêtre : Annuler / Rétablir."""
        if (e.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick)
                and e.button() in (Qt.BackButton, Qt.ForwardButton)
                and isinstance(objet, QWidget) and objet.window() is self):
            (self.retour if e.button() == Qt.BackButton else self.suivant)()
            return True
        return super().eventFilter(objet, e)

    def recadrage_perspective(self):
        """Image > Recadrage en perspective : 4 coins à poser sur une façade, un tableau, un document photographié de
        biais ; Entrée : il devient un rectangle droit."""
        c = self.canevas
        if not self.doc or c.transfo is not None or c.cadre is not None or c.persp is not None:
            return
        c.commencer_persp()
        self.opt_pinceau.hide()
        self.opt_persp.show()
        self.options.adjustSize()
        self.barre_haut.layout().invalidate()
        self.statusBar().showMessage(tr("Tirez les 4 coins sur les bords de l'objet vu de biais (la grille aide à "
                                        "suivre ses lignes) ; dedans : tout déplacer. Entrée ou double-clic pour "
                                        "recadrer, Échap pour annuler."), 20000)

    def _fin_persp(self):
        self.canevas.finir_persp()
        self.opt_persp.hide()
        if hasattr(self, "opt_pinceau"):
            self.maj_bouton_pinceau()
        self.statusBar().clearMessage()

    def _valider_persp(self):
        c = self.canevas
        if c.persp is None:
            return
        coins = list(c.persp)
        self._fin_persp()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            avant = self.doc.etat()
            apres = self.doc.etat_recadre_perspective(coins)
        finally:
            QApplication.restoreOverrideCursor()
        if apres is None:
            self.statusBar().showMessage(tr("Ces 4 coins ne forment pas un quadrilatère utilisable."), 6000)
            return
        self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Recadrage en perspective")))

    def _annuler_persp(self):
        if self.canevas.persp is not None:
            self._fin_persp()

    def _historique_bouge(self, _index):
        """Ctrl+Z ou clic dans l'Historique pendant une transformation : elle est abandonnée."""
        if self.canevas.persp is not None:
            self._fin_persp()
        if self.canevas.transfo is not None:
            self.canevas.finir_transfo()
            self.opt_transfo.hide()
            if hasattr(self, "opt_pinceau"):
                self.maj_bouton_pinceau()
            self._transfo_avant = None

    def _transfo_change(self):
        t = self.canevas.transfo
        if t is not None:
            self._transfo_affiche = True                  # ne pas renvoyer ces valeurs au cadre
            for cle, v in zip("lha", t.resume()):
                self.cases_transfo[cle].setValue(v)
                self.cases_transfo[cle].setEnabled(not t.libre())
            self.mode_transfo.setCurrentIndex(max(0, self.mode_transfo.findData(t.mode)))
            self._transfo_affiche = False

    def _mode_transfo_choisi(self, _i=None):
        self._changer_mode_transfo(self.mode_transfo.currentData())

    def _changer_mode_transfo(self, mode: str):
        t = self.canevas.transfo
        if t is None:
            return
        if mode == "libre" and t.libre():
            t.mode = "distordre" if t.quad is not None else "deformation"
            self.statusBar().showMessage(tr("La forme libre est gardée : pour revenir à un simple cadre, annulez la "
                                            "transformation (Échap)."), 8000)
        else:
            t.passer_mode(mode)
            messages = {"perspective": tr("Perspective : tirez un coin, le coin voisin bouge en miroir."),
                        "distordre": tr("Distordre : chaque coin bouge seul ; un milieu de bord déplace ce bord."),
                        "deformation": tr("Déformation : tirez les points de la grille pour courber l'image ; un "
                                          "coin emmène ses deux poignées.")}
            if mode in messages:
                self.statusBar().showMessage(messages[mode] + " " + tr("Entrée pour valider, Échap pour annuler."),
                                             15000)
        self.canevas._apercu_transfo(lisse=True)
        self.canevas.noter_geste()
        self._transfo_change()
        self.canevas.update()

    def _transfo_tapee(self, _v=None):
        """Largeur, hauteur ou angle tapés dans la barre d'options de Transformer."""
        t = self.canevas.transfo
        if t is None or getattr(self, "_transfo_affiche", False):
            return
        t.sx = self.cases_transfo["l"].value() / 100 * (1 if t.sx >= 0 else -1)
        t.sy = self.cases_transfo["h"].value() / 100 * (1 if t.sy >= 0 else -1)
        t.angle = self.cases_transfo["a"].value()
        self.canevas._apercu_transfo(lisse=True)
        self.canevas.update()

    def _valider_transfo(self, titre: str | None = None):
        t = self.canevas.transfo
        if t is None or self._transfo_avant is None:
            return
        avant, _modifie = self._transfo_avant
        index = self.canevas._transfo_index
        w, h = self.doc.taille()
        img, x, y = t.rendu_entier(lisse=True)            # ce qui dépasse de la feuille est gardé
        self.canevas.finir_transfo()
        self.opt_transfo.hide()
        if hasattr(self, "opt_pinceau"):
            self.maj_bouton_pinceau()
        self._transfo_avant = None
        self.doc.appliquer_etat(avant)
        self.doc.modifie = _modifie
        c = self.doc.calques[index]
        p = calque_pinceau.valide(c) or calque_forme.valide(c)
        if p is not None and t.fond is None and getattr(t, "depart_pinceau", None) is not None and not t.libre():
            # calque de pinceau (de forme) : ses traits passent par la même transformation et sont redessinés
            d = t.depart_pinceau
            tr_ = QTransform.fromTranslate(-d.x(), -d.y()) * t.transfo()
            apres = (self.doc.etat_forme(index, p.transforme(tr_)) if calque_forme.valide(c) is not None
                     else self.doc.etat_pinceau(index, p.transforme(tr_)))
            self.historique.push(CommandeEtat(self.doc, avant, apres, titre or tr("Transformer le calque")))
            return
        if t.libre():                                     # surface de la forme / surface de départ
            poly = t.contour(8)
            aire = abs(sum(poly[i].x() * poly[(i + 1) % len(poly)].y() - poly[(i + 1) % len(poly)].x() * poly[i].y()
                           for i in range(len(poly)))) / 2
            k = (aire / max(1.0, t.bw * t.bh) / getattr(t, "echelle_depart", 1.0)) ** 0.5
        else:
            k = (abs(t.sx * t.sy) / getattr(t, "echelle_depart", 1.0)) ** 0.5
        style = c.style.mis_a_l_echelle(k) if c.style is not None else None
        apres = self.doc.etat_calque_entier(index, img, x, y, texte=None, style=style)
        if t.fond is None and not t.libre():              # calque entier : il garde sa meilleure version
            o = Origine(getattr(t, "meilleure", None) or t.source, t.sx, t.sy, t.angle, t.centre.x(), t.centre.y())
            calques = list(apres[0])
            calques[index] = attacher_origine(calques[index], o)
            apres = (tuple(calques),) + tuple(apres[1:])
        if t.fond is not None:                            # élément sélectionné déplacé : l'ancienne sélection part
            apres = (apres[0], apres[1], nouvelle_selection(w, h))
        self.historique.push(CommandeEtat(self.doc, avant, apres, titre or tr("Transformer le calque")))

    def _annuler_transfo(self):
        if self.canevas.transfo is None or self._transfo_avant is None:
            return
        avant, modifie = self._transfo_avant
        self.canevas.finir_transfo()
        self.opt_transfo.hide()
        if hasattr(self, "opt_pinceau"):
            self.maj_bouton_pinceau()
        self._transfo_avant = None
        self.doc.appliquer_etat(avant)
        self.doc.modifie = modifie
        self.statusBar().clearMessage()

    # ================================================================ sélection : agrandir, réduire, adoucir
    def _modifier_bord(self, mode: str):
        if not self.doc or not self._verifier_selection_simple():
            return
        titres = {"agrandir": tr("Agrandir la sélection"), "reduire": tr("Réduire la sélection"),
                  "adoucir": tr("Adoucir les bords")}
        cle = f"sel_{mode}"
        px, ok = QInputDialog.getInt(self, titres[mode], tr("De combien de pixels ?"),
                                     self.reglages.value(cle, 10, type=int), 1, 500)
        if not ok:
            return
        self.reglages.setValue(cle, px)
        avant = self.doc.etat()
        sel = self.doc.selection_modifiee(mode, px)
        apres = (self.doc.calques, self.doc.actif, sel)
        self.historique.push(CommandeEtat(self.doc, avant, apres, titres[mode]))

    # ================================================================ sujet / arrière-plan (IA, BiRefNet)
    def _detourage(self, titre: str, suite):
        """Demande au moteur le masque du sujet (calculé sur l'image visible), puis appelle suite(masque 0..255)."""
        if not self.doc:
            return
        if not recettes.detourage_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle BiRefNet (444 Mo), qui n'est pas installé. Menu IA > Installer le "
                "moteur IA permet de l'ajouter."))
            return
        doc = self.doc
        png = doc.png_pour_ia(False)
        annuler = threading.Event()

        def calcul(progres):
            nom = self.moteur.envoyer_image(png)
            prompt, sorties = recettes.detourer(nom)
            res = self.moteur.executer(prompt, sorties, annuler, progres)
            if not res:
                raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
            img = QImage.fromData(res[0][1])
            if img.isNull():
                raise ErreurMoteur(tr("Résultat illisible."))
            w, h = doc.taille()
            if (img.width(), img.height()) != (w, h):
                img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, 0].copy()

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def ok(m):
            attente.hide()
            attente.deleteLater()
            if doc is self.doc:
                suite(m)

        def echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        t = self._tache(calcul, ok, echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def selectionner_sujet(self):
        def suite(m):
            from .document import _masque_vers_selection
            avant = self.doc.etat()
            sel = _masque_vers_selection(m).convertToFormat(QImage.Format_ARGB32_Premultiplied)
            self.historique.push(CommandeEtat(self.doc, avant, (self.doc.calques, self.doc.actif, sel),
                                              tr("Sélectionner le sujet")))
        self._detourage(tr("Sélectionner le sujet"), suite)

    def supprimer_arriere_plan(self):
        if not self.doc or not self._verifier_verrou(tr("Supprimer l'arrière-plan")):
            return

        def suite(m):
            import numpy as np
            from .document import qimage_rgba
            c = self.doc.calque_actif
            t = tableau(c.image.convertToFormat(FORMAT_IMAGE))
            t[:, :, 3] = (t[:, :, 3].astype(np.uint16) * m // 255).astype(np.uint8)
            img = qimage_rgba(t).convertToFormat(QImage.Format_ARGB32_Premultiplied)
            avant = self.doc.etat()
            apres = self.doc.etat_calque_modifie(self.doc.actif, image=img, texte=None)
            self.historique.push(CommandeEtat(self.doc, avant, apres, tr("Supprimer l'arrière-plan")))
            self.statusBar().showMessage(tr("Arrière-plan supprimé sur le calque « {nom} » : enregistrez en PNG, "
                                            "PSD ou .piximg pour garder la transparence.", nom=c.nom), 10000)
        self._detourage(tr("Supprimer l'arrière-plan"), suite)

    # ================================================================ aide : à propos, mises à jour
    def a_propos(self):
        icone_app = QApplication.instance().windowIcon()
        APropos(icone_app.pixmap(96, 96) if not icone_app.isNull() else None, self, self.couleurs).exec()

    def verifier_maj(self, silencieux: bool = False):
        def ok(info):
            if info["versions"]:
                if FenetreNouveautes(info, self).exec() == QDialog.Accepted:
                    QDesktopServices.openUrl(QUrl(info["page"]))
            elif not silencieux:
                QMessageBox.information(self, tr("Mise à jour"), tr("Pixane Photo est à jour."))

        def echec(message):
            if not silencieux:
                QMessageBox.information(self, tr("Mise à jour"), message or tr("La recherche a échoué."))

        def chercher(_progres):
            try:
                return mises_a_jour.nouveautes()
            except OSError as e:
                raise ErreurMoteur(str(e)) from e
        t = self._tache(chercher, ok, echec)
        t.lancer()

    def _verifier_selection_simple(self) -> bool:
        if self.doc.selection_vide():
            self.statusBar().showMessage(tr("Sélectionne d'abord une zone (rectangle, lasso ou pinceau de "
                                            "sélection)."), 6000)
            return False
        return True

    def _modifier_selection(self, quoi):
        if not self.doc:
            return
        avant = self.doc.etat()
        {"tout": self.doc.tout_selectionner, "rien": self.doc.deselectionner,
         "inverser": self.doc.inverser_selection}[quoi]()
        textes = {"tout": tr("Tout sélectionner"), "rien": tr("Désélectionner"), "inverser": tr("Inverser la sélection")}
        self.historique.push(CommandeEtat(self.doc, avant, self.doc.etat(), textes[quoi]))

    # ================================================================ IA
    def _verifier_selection(self) -> bool:
        if self.doc.selection_vide():
            QMessageBox.information(self, NOM, tr("Peins d'abord sur l'objet avec le pinceau (ou entoure-le au "
                                                  "lasso ou au rectangle)."))
            return False
        return True

    def _verifier_verrou(self, action: str, tous: bool = False) -> bool:
        """Faux (avec un message) si le calque choisi, ou un calque quelconque (tous=True), est verrouillé."""
        calques = self.doc.calques if tous else [self.doc.calque_actif]
        bloques = [c.nom for c in calques if c.verrou]
        if not bloques:
            return True
        noms = ", ".join(tr("« {nom} »", nom=n) for n in bloques)
        sujet = (tr("Les calques {noms} sont cadenassés", noms=noms) if len(bloques) > 1
                 else tr("Le calque {noms} est cadenassé", noms=noms))
        raison = (tr("{action} change la taille de tous les calques", action=action) if tous
                  else tr("{action} modifie le calque choisi", action=action))
        QMessageBox.information(self, action, tr("{sujet} : {raison}, c'est donc impossible.\n\nClique sur le "
                                                 "cadenas du calque dans le panneau Calques pour le déverrouiller.",
                                                 sujet=sujet, raison=raison))
        return False

    def ia_effacer(self):
        if self.doc and self._verifier_verrou(tr("Effacer")) and self._verifier_selection():
            self._lancer(tr("Effacer"), True, lambda nom: recettes.effacer(nom), remplir_trous=True,
                         variante=lambda nom, force: recettes.variante(nom, force, nb=recettes.NB_EFFACER))

    def ia_remplir(self):
        if self.doc and self._verifier_verrou(tr("Remplir")) and self._verifier_selection():
            texte = self.texte_remplir.text().strip()
            self._lancer(tr("Remplir"), True, lambda nom: recettes.remplir(nom, texte), remplir_trous=True,
                         variante=lambda nom, force: recettes.variante(nom, force, texte))

    def ia_agrandir(self):
        if not self.doc:
            return
        if self.canevas.cadre is not None or not self._verifier_verrou(tr("Agrandir"), tous=True):
            return
        # vide transparent autour de l'image (photo collée dans une image plus grande) : rempli lui aussi
        self._contenu_agrandir = c = self.doc.contenu()
        if c is not None:   # bord abîmé proposé d'office : le bord flou de la photo collée, ou son liseré
            x0, y0, x1, y1 = c
            photo = a_plat(tableau(self.doc.image.copy(x0, y0, x1 - x0, y1 - y0).convertToFormat(FORMAT_IMAGE)))
            abime = tuple(max(u, v) for u, v in zip(self.doc.bord_flou(c), lisere_auto(photo)))
        else:   # bord abîmé proposé d'office : le liseré clair ou foncé détecté sur chaque bord
            abime = lisere_auto(self.doc.rgb_pour_ia())
        iw, ih = self.doc.image.width(), self.doc.image.height()
        self.barre_agrandir.ouvrir(iw, ih, abime, vide=None if c is None else (c, (iw, ih)))
        self.canevas.commencer_cadre(abime, base=c)

    def _fin_agrandir(self):
        self.barre_agrandir.hide()
        self.canevas.finir_cadre()

    def _lancer_agrandir(self):
        if self.canevas.cadre is None or not self.barre_agrandir.b_lancer.isEnabled():
            return
        ajout, abime = self.barre_agrandir.valeurs_px()
        self._fin_agrandir()
        iw, ih = self.doc.image.width(), self.doc.image.height()
        contenu = getattr(self, "_contenu_agrandir", None)
        if contenu is not None:
            # vide autour : on part de la photo sans son bord abîmé (ou flou) ; l'IA la prolonge jusqu'au cadre
            # le bord à demi transparent est toujours redessiné (sinon : liseré clair à la jonction)
            abime = tuple(max(u, v) for u, v in zip(abime, self.doc.bord_flou(contenu)))
            ah, ab, ag, ad = abime
            x0, y0, x1, y1 = contenu
            sain = (x0 + ag, y0 + ah, x1 - ad, y1 - ab)
            image = self.doc.image.copy(sain[0], sain[1], sain[2] - sain[0], sain[3] - sain[1])
            total = [a + m for a, m in zip(ajout, abime)]
        else:
            # 1. jeter le bord abîmé : la partie saine sert de base
            ah, ab, ag, ad = abime
            image = self.doc.image.copy(ag, ah, iw - ag - ad, ih - ah - ab)
            # 2. l'IA redessine le bord jeté + l'agrandissement (taille finale = photo + ajout)
            total = [a + m for a, m in zip(ajout, abime)]
        w, h = image.width(), image.height()
        v = {cle: t * 100 / n for cle, t, n in zip(("haut", "bas", "gauche", "droite"), total, (h, h, w, w))}
        png, geo, orig = preparer(a_plat(tableau(image.convertToFormat(FORMAT_IMAGE))), **v, enlever_lisere=False)

        def raccord(img: QImage) -> QImage:
            return qimage_rgb(finaliser(orig, tableau(img)[:, :, :3], geo))
        doc = self.doc

        # rectangle du résultat dans l'image (cadre), et nouvelle image = image d'avant ∪ cadre
        bx0, by0, bx1, by1 = contenu or (0, 0, iw, ih)
        rx0, ry0, rx1, ry1 = bx0 - ajout[2], by0 - ajout[0], bx1 + ajout[3], by1 + ajout[1]
        ux0, uy0 = min(0, rx0), min(0, ry0)
        toile = (max(iw, rx1) - ux0, max(ih, ry1) - uy0)

        def placer(img: QImage):   # calques décalés ; l'ajout de l'IA dans le calque choisi (ou un nouveau)
            return doc.etat_agrandi(tr("Agrandir"), img, (-ux0, -uy0),
                                    nouveau_calque=self.a_ia_nouveau_calque.isChecked(),
                                    contenu=sain if contenu is not None else None,
                                    place=(rx0 - ux0, ry0 - uy0), toile=toile)
        def prolonge():   # « Fond prolongé », sans IA : seulement si les bords à prolonger sont unis
            r = fond_prolonge(orig, geo)
            return [] if r is None else [(tr("Fond prolongé"), qimage_rgb(r))]
        affiner = None
        if self.barre_agrandir.pleine.isChecked() and affinage.utile(geo.taille, geo.travail):
            m = affinage.masque_ajout(geo.taille, geo.marges, orig.shape[:2], max(geo.bande) * 1.5)
            affiner = lambda img, fin: self._affiner_agrandir(img, m, fin, lambda a: reaccorder(orig, a, geo))
        self._lancer(tr("Agrandir"), False, lambda nom: recettes.agrandir(nom), apres=raccord, png=png,
                     placer=placer, affiner=affiner, sans_ia=prolonge,
                     variante=lambda nom, force: recettes.variante(nom, force, nb=recettes.NB_AGRANDIR,
                                                                   decoupe=False))

    def _affiner_agrandir(self, image: QImage, m, fin, accorder=None):
        """Pleine définition : la proposition choisie est retravaillée par morceaux à la vraie taille, puis
        fin(image) l'applique. Annuler pendant le calcul : la proposition est gardée telle quelle."""
        img = tableau(image)[:, :, :3].copy()
        s, travail, m_t, rects = affinage.plan(img, m)
        annuler = threading.Event()
        titre = tr("Agrandir en pleine définition")

        def calcul(progres):
            t0 = time.monotonic()
            res = travail.copy()
            for i, r in enumerate(rects):
                if annuler.is_set():
                    raise ErreurMoteur("")
                nom = self.moteur.envoyer_image(affinage.png_morceau(res, m_t, r))
                prompt, sorties = recettes.affiner(nom, affinage.FORCE)

                def suivi(info, i=i):
                    f = (i + (info.get("fraction") or 0)) / len(rects)
                    passe = time.monotonic() - t0
                    progres(dict(info, etape=tr("Morceau {i} sur {n}", i=i + 1, n=len(rects)), fraction=f,
                                 restant=int(passe * (1 - f) / f) if f > 0.02 else None))
                for _libelle, donnees in self.moteur.executer(prompt, sorties, annuler, suivi):
                    morceau = QImage.fromData(donnees)
                    if morceau.isNull():
                        raise ErreurMoteur(tr("Résultat illisible."))
                    res = affinage.coller(res, tableau(morceau.convertToFormat(FORMAT_IMAGE))[:, :, :3], m_t, r)
            fini = affinage.terminer(img, res, m, s)
            if accorder is not None:          # Flux a pu de nouveau éclaircir l'ajout : raccord refait
                fini = accorder(fini)
            fini = affinage.accorder_grain(fini, m)
            return qimage_rgb(fini)

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def ok(resultat):
            attente.hide()
            attente.deleteLater()
            fin(resultat)

        def echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, tr("{erreur}\n\nLa proposition choisie est gardée telle quelle.",
                                                    erreur=message))
            fin(image)
        t = self._tache(calcul, ok, echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def ia_upscale(self):
        if not self.doc:
            return
        doc = self.doc
        c, index = doc.calque_actif, doc.actif
        bornes = doc.bornes([index]) if not c.special and c.texte is None and c.visible else None
        calque = None if bornes is None or c.verrou else (c.nom, (bornes.width(), bornes.height()))
        image_possible = not any(k.verrou for k in doc.calques)   # toute l'image : tous les calques changent
        if calque is None and not image_possible:
            self._verifier_verrou(tr("Upscale"), tous=True)        # rien de possible : message, comme avant
            return
        cible = self.reglages.value("upscale_cible", "agrandi") if len(doc.calques) > 1 else "image"
        if not image_possible and cible == "image":
            cible = "agrandi"
        try:
            graphique = part_aplats(doc.rgb_pour_ia()) > 0.5      # pochette, logo : force douce proposée
        except Exception:
            graphique = False
        d = ReglagesUpscale(doc.image.width(), doc.image.height(), self, calque=calque, cible=cible,
                            image_possible=image_possible, graphique=graphique)
        if d.exec():
            v = d.valeurs()
            if calque is not None:
                self.reglages.setValue("upscale_cible", v["cible"])
            if v["net"] and not recettes.schnell_disponible():
                QMessageBox.information(self, tr("Upscale"), tr(
                    "« Upscale net » a besoin du modèle Flux Schnell, qui n'est pas installé. Menu IA > Installer "
                    "le moteur IA permet de l'ajouter ; l'upscale simple marche sans."))
                return
            if v["cible"] != "image":
                self._upscale_calque(index, bornes, v)
                return
            if not self._verifier_verrou(tr("Upscale"), tous=True):
                return
            if v["net"]:
                taille = (self.doc.image.width(), self.doc.image.height())
                origine = self.doc.rgb_pour_ia()           # garde-fou : Flux n'invente rien dans les aplats
                self._lancer(tr("Upscale"), False,
                             lambda nom: recettes.upscale_net(nom, v["facteur"], v["force"], taille),
                             apres=lambda r: garder_aplats(origine, r))
            else:
                self._lancer(tr("Upscale"), False, lambda nom: recettes.upscale_rapide(nom, v["facteur"]))

    def _upscale_calque(self, index: int, bornes, v: dict):
        """Upscale du seul calque choisi : son contenu est envoyé à l'IA (sur un fond qui contraste), puis remis
        dans le calque, plus net à sa taille (« net ») ou agrandi (« agrandi ») ; la feuille ne change pas."""
        doc = self.doc
        c = doc.calques[index]
        if c.verrou:
            QMessageBox.information(self, tr("Upscale"), tr(
                "Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le modifier.", nom=c.nom))
            return
        img, ox, oy = image_entiere(c)
        source = img.copy(bornes.translated(-ox, -oy)).convertToFormat(FORMAT_IMAGE)
        rgb = a_plat(tableau(source))
        tampon = io.BytesIO()
        Image.fromarray(np.ascontiguousarray(rgb), "RGB").save(tampon, "PNG")
        taille = (source.width(), source.height())
        if v["net"]:
            fabriquer = lambda nom: recettes.upscale_net(nom, v["facteur"], v["force"], taille)
        else:
            fabriquer = lambda nom: recettes.upscale_rapide(nom, v["facteur"])
        nouveau = self.a_ia_nouveau_calque.isChecked()

        def apres(r):
            if v["net"]:                                   # garde-fou : Flux n'invente rien dans les aplats
                r = garder_aplats(rgb, r)
            return vue_ia(r, source)
        self._lancer(tr("Upscale"), False, fabriquer, apres=apres, png=tampon.getvalue(),
                     placer=lambda r: doc.etat_upscale_calque(index, r, v["cible"], nouveau, tr("Upscale")))

    # ---------------------------------------------------------------- améliorer, restaurer
    def _dans_selection(self, titre: str):
        """Résultat remis à la taille de la photo ; s'il y a une sélection, seulement dedans."""
        doc = self.doc
        w, h = doc.taille()
        m = None if doc.selection_vide() else tableau(doc.selection.convertToFormat(FORMAT_IMAGE))[:, :, 3].copy()
        original = tableau(doc.image.convertToFormat(FORMAT_IMAGE)).copy()

        def apres(img: QImage) -> QImage:
            if (img.width(), img.height()) != (w, h):
                img = img.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(FORMAT_IMAGE)
            if m is None:
                return img
            a = tableau(img).astype(np.float32)
            k = m.astype(np.float32)[..., None] / 255
            res = (a * k + original * (1 - k) + 0.5).astype(np.uint8)
            return QImage(np.ascontiguousarray(res).data, w, h, w * 4, FORMAT_IMAGE).copy()
        return apres

    def ia_debruiter(self):
        titre = tr("Réduire le bruit (IA)")
        if not self.doc or not self._verifier_verrou(titre):
            return
        if not recettes.debruitage_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle SCUNet (72 Mo), qui n'est pas installé. Menu IA > Installer le "
                "moteur IA permet de l'ajouter."))
            return
        self._lancer(titre, False, lambda nom: recettes.debruiter(nom), apres=self._dans_selection(titre))

    def ia_nettete(self):
        titre = tr("Netteté (IA)")
        if self.doc and self._verifier_verrou(titre):
            self._lancer(titre, False, lambda nom: recettes.nettete_ia(nom), apres=self._dans_selection(titre))

    def ia_modifier(self):
        """Modifier avec une consigne (Flux Kontext) : sur la sélection, le style gardé (voir modifier_ia)."""
        titre = tr("Modifier avec une consigne")
        if not self.doc or not self._verifier_verrou(titre):
            return
        if not recettes.restauration_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Flux Kontext (11,9 Go), qui n'est pas installé. Menu IA > Installer "
                "le moteur IA permet de l'ajouter (case « Flux Kontext »)."))
            return
        from . import modifier_ia
        from .consigne import DialogueConsigne
        doc = self.doc
        zone = None if doc.selection_vide() else masque(doc.selection).copy()
        prep = modifier_ia.preparer(doc, zone, self.a_ia_nouveau_calque.isChecked())
        d = DialogueConsigne(self, transparent=prep.transparent, avec_selection=zone is not None,
                             nb=recettes.NB_RESTAURER)
        if not d.exec():
            return
        consigne, nb = d.consigne(), d.nombre()
        visible = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
        self._lancer(titre, False, lambda nom: recettes.restaurer(nom, prep.taille, nb=nb, texte=consigne),
                     png=prep.png, apres=lambda img: modifier_ia.image_complete(prep, img),
                     placer=lambda image: modifier_ia.etat(doc, prep, image, tr("Modifié")),
                     vue=lambda img: modifier_ia.vue(prep, img, visible), nom_calque=tr("Modifié"),
                     suffixe=tr("_modifie"), duree="kontext")

    def ia_restaurer(self):
        titre = tr("Restaurer une vieille photo")
        if not self.doc or not self._verifier_verrou(titre):
            return
        if not recettes.restauration_disponible():
            QMessageBox.information(self, titre, tr(
                "Cette action a besoin du modèle Flux Kontext (11,9 Go), qui n'est pas installé. Menu IA > Installer "
                "le moteur IA permet de l'ajouter (case « Flux Kontext »)."))
            return
        boite = QMessageBox(QMessageBox.Question, titre, tr(
            "L'IA redessine toute la photo : rayures, taches, poussières et grain enlevés, contraste et visages "
            "rendus plus nets. Elle peut changer de petits détails : compare bien les propositions.") + "\n\n" +
            durees.phrase("kontext"), parent=self)
        b_ok = boite.addButton(tr("Restaurer"), QMessageBox.AcceptRole)
        b_couleur = boite.addButton(tr("Restaurer et coloriser"), QMessageBox.AcceptRole)
        boite.addButton(tr("Annuler"), QMessageBox.RejectRole)
        boite.exec()
        if boite.clickedButton() not in (b_ok, b_couleur):
            return
        coloriser = boite.clickedButton() is b_couleur
        taille = self.doc.taille()
        apres = self._dans_selection(titre)
        if not coloriser:
            # « Restaurer » seul : les couleurs de l'original sont remises après coup, l'IA ne donne que la lumière
            # et les détails (Flux Kontext colorise parfois une photo noir et blanc ou sépia malgré la consigne)
            from .filtres import garder_teinte
            original = tableau(self.doc.image.convertToFormat(FORMAT_IMAGE))
            w, h = taille
            dans_sel = apres

            def apres(img: QImage) -> QImage:
                res = garder_teinte(original, tableau(dans_sel(img).convertToFormat(FORMAT_IMAGE)))
                return QImage(np.ascontiguousarray(res).data, w, h, w * 4, FORMAT_IMAGE).copy()
        if coloriser:
            nom_calque, suffixe = tr("Restaurée et colorisée"), tr("_restauree_colorisee")
        else:
            nom_calque, suffixe = tr("Restaurée"), tr("_restauree")
        self._lancer(titre, False, lambda nom: recettes.restaurer(nom, taille, coloriser), apres=apres,
                     nom_calque=nom_calque, suffixe=suffixe, duree="kontext")

    def _lancer(self, titre: str, avec_selection: bool, fabriquer, apres=None, png: bytes | None = None,
                placer=None, nom_calque: str | None = None, suffixe: str | None = None, affiner=None,
                remplir_trous: bool = False, vue=None, variante=None, sans_ia=None, duree: str | None = None):
        """Envoie l'image au moteur, attend, puis propose les résultats. remplir_trous (Effacer, Remplir) : les trous
        transparents de la sélection (lettres d'un texte coupé…) sont remplis, opaques. nom_calque : nom du calque du résultat
        (le titre sinon) ; suffixe : ajouté au nom proposé à l'enregistrement (ex. « _restauree »).
        affiner(image, fin) : travail de plus sur la proposition choisie (pleine définition), fin(image) l'applique.
        variante(nom, force) : recette des variantes d'une proposition (bouton « Partir de celle-ci ») ; l'image
        envoyée est alors la proposition brute choisie, avec la même zone à refaire que la première fois.
        sans_ia() : propositions de plus, faites par Pixane sans IA ([(libellé, image finale)], calculées avec les
        premières) : ni variantes, ni pleine définition (déjà à la vraie taille). duree : clé de durees (la durée
        par proposition est mesurée et retenue : elle s'affiche ensuite dans la fenêtre de consigne)."""
        doc = self.doc
        if png is None:
            png = doc.png_pour_ia(avec_selection)
        original = doc.image
        zone = None if doc.selection_vide() else masque(doc.selection).copy()   # sélection au lancement
        trous = (trous_a_remplir(tableau(original.convertToFormat(FORMAT_IMAGE)), zone)
                 if remplir_trous and placer is None else None)
        choix = ChoixResultat(titre, original, self)
        if vue is not None:                      # montré tel qu'il sera posé (action qui pose elle-même)
            choix.vue = vue
        elif placer is None:                     # fond transparent : montré tel qu'il sera posé (pas en noir)
            choix.vue = lambda img, base=original: vue_ia(img, base, trous)
        annuler = threading.Event()
        nom_image = {}
        bruts: list[QImage] = []          # résultats tels que sortis du moteur (avant apres), dans l'ordre des vignettes

        def calcul_avec(fab, cle, donnees):
            def calcul(progres):
                if cle not in nom_image:
                    nom_image[cle] = self.moteur.envoyer_image(donnees)
                recette = fab(nom_image[cle])
                prompt, sorties = recette[0], recette[1]
                morceaux = recette[2] if len(recette) > 2 else 1
                res = []
                debut = time.monotonic()
                for libelle, donnees_res in self.moteur.executer(prompt, sorties, annuler, progres, morceaux):
                    img = QImage.fromData(donnees_res)
                    if img.isNull():
                        raise ErreurMoteur(tr("Résultat illisible."))
                    img = img.convertToFormat(FORMAT_IMAGE)
                    res.append((libelle, apres(img) if apres else img, img))
                if duree and res and not annuler.is_set():
                    durees.noter(duree, (time.monotonic() - debut) / len(res))
                return res
            return calcul
        calcul_ia = calcul_avec(fabriquer, "original", png)

        def calcul(progres):
            res = calcul_ia(progres)
            if sans_ia is not None and not premiere_faite:
                res += [(libelle, img, None) for libelle, img in sans_ia()]
            return res
        premiere_faite = False

        def recevoir(res):
            bruts.extend(r[2] for r in res)
            choix.ajouter([(libelle, img) for libelle, img, _brut in res])

        attente = Attente(titre, self)
        attente.annuler.connect(annuler.set)

        def premier_ok(res):
            nonlocal premiere_faite
            premiere_faite = True
            attente.hide()
            attente.deleteLater()
            recevoir(res)
            if variante is not None:
                choix.permettre_variantes(int(self.reglages.value("variante_curseur", 50)))
            if choix.exec() and choix.choix() is not None:
                def fin(image):
                    self._appliquer_resultat(doc, image, titre, placer, nom_calque, zone, trous)
                    if suffixe:
                        doc.suffixe_nom = suffixe
                annuler.set()
                ligne = choix.vignettes.currentRow()
                if affiner is not None and 0 <= ligne < len(bruts) and bruts[ligne] is not None:
                    affiner(choix.choix(), fin)
                else:
                    fin(choix.choix())
            annuler.set()

        def premier_echec(message):
            attente.hide()
            attente.deleteLater()
            if message:
                QMessageBox.warning(self, titre, message)

        def autres():
            annuler.clear()
            t2 = self._tache(calcul, recevoir,
                             lambda m: choix.occupe(False, m or tr("Annulé.")))
            t2.progres.connect(choix.progression)
            t2.lancer()

        def variantes(ligne, curseur):
            if variante is None or not 0 <= ligne < len(bruts):
                choix.occupe(False)
                return
            if bruts[ligne] is None:
                choix.occupe(False, tr("Cette proposition est faite sans IA : pas de variantes."))
                return
            self.reglages.setValue("variante_curseur", curseur)
            force = recettes.force_variante(curseur)
            annuler.clear()
            donnees = png_variante(bruts[ligne], png)
            nom_v = tr("Variante de {n}", n=ligne + 1)
            t2 = self._tache(calcul_avec(lambda nom: variante(nom, force), ("variante", ligne, curseur), donnees),
                             lambda res: recevoir([(nom_v, img, brut) for _l, img, brut in res]),
                             lambda m: choix.occupe(False, m or tr("Annulé.")))
            t2.progres.connect(choix.progression)
            t2.lancer()

        choix.autres_demandees.connect(autres)
        choix.variante_demandee.connect(variantes)
        t = self._tache(calcul, premier_ok, premier_echec)
        t.progres.connect(attente.maj)
        t.lancer()
        attente.show()

    def _appliquer_resultat(self, doc: Document, image: QImage, titre: str, placer=None,
                            nom_calque: str | None = None, zone=None, trous=None):
        """Le résultat choisi va dans le calque choisi, ou dans un nouveau calque (option du menu IA, ou si le
        calque choisi ne peut pas le recevoir). zone : sélection au lancement (le résultat n'en sort pas)."""
        if doc is not self.doc:
            return
        avant = doc.etat()
        nom = nom_calque or titre
        nouveau = self.a_ia_nouveau_calque.isChecked()
        if placer is not None:
            apres = placer(image)
        elif image.size() == doc.image.size():
            apres = doc.etat_resultat_ia(nom, image, zone, nouveau, trous)   # seulement les pixels retouchés
        else:
            apres = doc.etat_redimensionne(nom, image, nouveau)        # Upscale
        if len(apres[0]) > len(doc.calques) and not nouveau:
            self.statusBar().showMessage(tr(
                "Résultat mis dans un nouveau calque : le calque choisi ne peut pas le recevoir (texte, groupe, "
                "réglage, caché ou verrouillé), ou il y a d'autres calques et rien n'était sélectionné."), 10000)
        # travail fini : la sélection disparaît (Ctrl+Z la fait revenir avec l'image d'avant)
        calques, actif, _sel = apres
        apres = (calques, actif, nouvelle_selection(calques[0].image.width(), calques[0].image.height()))
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
