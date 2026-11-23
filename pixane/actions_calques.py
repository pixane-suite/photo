"""Actions de la fenêtre pour les masques, groupes, calques de réglage, réglages de couleur et filtres
(menus Image > Réglages, Calque, Filtres). Partie de la classe Fenetre (classe « mixin »)."""
from __future__ import annotations

import copy
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from . import ajustements, filtres
from .dialogues_reglage import PANNEAUX, DialogueReglage, PanneauFiltre, histogramme
from .document import FORMAT_IMAGE, masque, tableau
from .langue import tr

def alignements() -> tuple:
    """Calque > Aligner (et boutons de l'outil Déplacer) : (mode, texte traduit)."""
    return (("gauche", tr("Bords gauches")), ("centre_h", tr("Centres horizontaux")), ("droite", tr("Bords droits")),
            ("haut", tr("Bords hauts")), ("centre_v", tr("Centres verticaux")), ("bas", tr("Bords bas")))


# Image > Réglages (dans les pixels) ; tous existent aussi en calque de réglage
REGLAGES_PIXELS = ("niveaux", "courbes", "balance", "noir_blanc", "vibrance", "filtre_photo", "melangeur", "mappe",
                   "negatif", "seuil", "posterisation")


class ActionsCalques:
    # ---------------------------------------------------------------- menus
    def _menus_calques(self, m_image, m_calque):
        sous = m_image.addMenu(tr("Réglages"))
        for t in REGLAGES_PIXELS:
            if t in ("filtre_photo", "negatif"):
                sous.addSeparator()
            raccourci = {"niveaux": "Ctrl+L", "courbes": "Ctrl+M", "balance": "Ctrl+B",
                         "noir_blanc": "Ctrl+Alt+Shift+B", "negatif": "Ctrl+I"}.get(t)
            self._action(sous, ajustements.nom(t) + "…", raccourci, lambda *_, t=t: self.reglage(t), f"a_regl_{t}")
            if t == "vibrance":
                self._action(sous, tr("Remplacer la couleur…"), None, self.remplacer_couleur, "a_remplacer_couleur")

        m_calque.addSeparator()
        sous = m_calque.addMenu(tr("Nouveau calque de réglage"))
        for t in ajustements.TYPES:
            self._action(sous, ajustements.nom(t) + "…", None, lambda *_, t=t: self.nouveau_calque_reglage(t),
                         f"a_cr_{t}")
        sous = m_calque.addMenu(tr("Nouveau calque de remplissage"))
        for g, texte in (("couleur", tr("Couleur unie…")), ("degrade", tr("Dégradé…")), ("motif", tr("Motif…"))):
            self._action(sous, texte, None, lambda *_, g=g: self.nouveau_calque_remplissage(g), f"a_remplissage_{g}")
        self._action(m_calque, tr("Modifier le réglage…"), None, self.modifier_reglage, "a_modifier_reglage")
        m_calque.addSeparator()
        self._action(m_calque, tr("Nouveau groupe"), None, lambda: self.calques.nouveau_groupe(), "a_nouveau_groupe")
        self._action(m_calque, tr("Grouper les calques"), "Ctrl+G", lambda: self.calques.grouper(), "a_grouper")
        self._action(m_calque, tr("Dégrouper"), "Ctrl+Shift+G", lambda: self.calques.degrouper(), "a_degrouper")
        self._action(m_calque, tr("Masque d'écrêtage (calque du dessous)"), "Ctrl+Alt+G",
                     lambda: self.calques.ecreter(), "a_ecretage")
        m_calque.addSeparator()
        sous = m_calque.addMenu(tr("Aligner"))
        for mode, texte in alignements():
            self._action(sous, texte, None, lambda *_, m=mode: self.aligner(m), f"a_aligner_{mode}",
                         f"al_{mode}")
        sous = m_calque.addMenu(tr("Répartir"))
        self._action(sous, tr("Répartir horizontalement"), None, lambda: self.repartir("h"), "a_repartir_h",
                     "rep_h")
        self._action(sous, tr("Répartir verticalement"), None, lambda: self.repartir("v"), "a_repartir_v",
                     "rep_v")
        sous = m_calque.addMenu(tr("Retourner le calque"))
        self._action(sous, tr("Symétrie horizontale (gauche ↔ droite)"), None, lambda: self.retourner_calques(True),
                     "a_retourner_calque_h")
        self._action(sous, tr("Symétrie verticale (haut ↔ bas)"), None, lambda: self.retourner_calques(False),
                     "a_retourner_calque_v")
        m_calque.addSeparator()
        sous = m_calque.addMenu(tr("Pixelliser"))
        for quoi, texte in (("texte", tr("Texte")), ("forme", tr("Forme, pinceau, remplissage")),
                            ("style", tr("Style du calque")), ("dynamique", tr("Objet dynamique")),
                            ("tout", tr("Calque entier"))):
            self._action(sous, texte, None, lambda *_, q=quoi: self.pixelliser(q), f"a_pixelliser_{quoi}")
        sous.aboutToShow.connect(self._etat_pixelliser)
        sous = m_calque.addMenu(tr("Masque de calque"))
        self._action(sous, tr("Ajouter : tout visible"), None, lambda: self.calques.ajouter_masque("blanc"),
                     "a_masque_blanc")
        self._action(sous, tr("Ajouter : montrer la sélection"), None,
                     lambda: self.calques.ajouter_masque("selection"), "a_masque_sel")
        self._action(sous, tr("Ajouter : cacher la sélection"), None,
                     lambda: self.calques.ajouter_masque("cacher_selection"), "a_masque_cacher")
        sous.addSeparator()
        self._action(sous, tr("Peindre le masque / les pixels"), "Ctrl+\\", self.basculer_cible_masque,
                     "a_masque_cible")
        self._action(sous, tr("Désactiver / réactiver le masque"), None, self.basculer_masque, "a_masque_actif")
        self._action(sous, tr("Inverser le masque"), None, self.inverser_masque, "a_masque_inverser")
        self._action(sous, tr("Masque vers sélection"), None, self.masque_vers_selection, "a_masque_selection")
        self._action(sous, tr("Appliquer le masque (dans les pixels)"), None, self.appliquer_masque,
                     "a_masque_appliquer")
        self._action(sous, tr("Supprimer le masque"), None, self.supprimer_masque, "a_masque_supprimer")

        m = self.menuBar().addMenu(tr("Fi&ltres"))
        noms = filtres.noms()
        self._action(m, tr("Fluidité…"), "Ctrl+Shift+X", self.fluidite, "a_fluidite")
        m.addSeparator()
        for t in filtres.FILTRES:
            self._action(m, noms[t] + "…", None, lambda *_, t=t: self.filtre(t), f"a_filtre_{t}")
        return m

    def _actions_calques_doc(self) -> list:
        noms = [f"a_regl_{t}" for t in REGLAGES_PIXELS] + ["a_remplacer_couleur"]
        noms += [f"a_cr_{t}" for t in ajustements.TYPES] + [f"a_filtre_{t}" for t in filtres.FILTRES]
        noms += ["a_fluidite", "a_harmoniser"]
        noms += ["a_taille_grille", "a_nouveau_repere", "a_effacer_reperes", "a_exporter_web"]
        noms += ["a_modifier_reglage", "a_nouveau_groupe", "a_grouper", "a_degrouper", "a_ecretage", "a_masque_blanc",
                 "a_masque_sel", "a_masque_cacher", "a_masque_cible", "a_masque_actif", "a_masque_inverser",
                 "a_masque_selection", "a_masque_appliquer", "a_masque_supprimer"]
        return [getattr(self, n) for n in noms]

    # ---------------------------------------------------------------- aligner, répartir, retourner les calques
    def _calques_choisis(self) -> set:
        return set(self.calques.choisis) | {self.doc.actif}

    def aligner(self, mode: str):
        """Plusieurs calques choisis : alignés entre eux ; un seul : sur la sélection, ou sinon sur l'image."""
        if not self.doc:
            return
        etat = self.doc.etat_aligner(self._calques_choisis(), mode)
        if etat is None:
            self.statusBar().showMessage(tr("Rien à aligner : les calques sont déjà alignés, vides ou verrouillés."),
                                         6000)
            return
        self._commande_calques(etat, tr("Aligner les calques"))

    def repartir(self, sens: str):
        if not self.doc:
            return
        if len(self.doc.blocs(self._calques_choisis())) < 3:
            self.statusBar().showMessage(tr("Répartir : choisis au moins 3 calques (Ctrl+clic dans le panneau "
                                            "Calques)."), 8000)
            return
        etat = self.doc.etat_repartir(self._calques_choisis(), sens)
        if etat is None:
            self.statusBar().showMessage(tr("Rien à répartir : les calques sont déjà bien espacés, vides ou "
                                            "verrouillés."), 6000)
            return
        self._commande_calques(etat, tr("Répartir les calques"))

    def retourner_calques(self, horizontal: bool):
        """Symétrie du calque choisi (ou de la sélection dans ce calque) ; plusieurs calques ou un groupe : ensemble."""
        if not self.doc or self.canevas.transfo is not None or self.canevas.cadre is not None:
            return
        titre = tr("Retourner le calque")
        blocs = self.doc.blocs(self._calques_choisis())
        if len(blocs) == 1 and len(blocs[0]) == 1:
            # un seul calque : comme Transformer avec une taille de -100 % (la sélection seule s'il y en a une)
            self.transformer()
            t = self.canevas.transfo
            if t is None:
                return
            if horizontal:
                t.sx = -t.sx
            else:
                t.sy = -t.sy
            self._valider_transfo(titre)
            return
        etat = self.doc.etat_retourner(self._calques_choisis(), horizontal)
        if etat is None:
            self.statusBar().showMessage(tr("Rien à retourner : les calques sont vides ou verrouillés."), 6000)
            return
        self._commande_calques(etat, titre)

    # ---------------------------------------------------------------- export web, lot
    def exporter_web(self):
        from .document import qimage_vers_pil
        from .export import DialogueExport
        if self.doc is None:
            return
        nom = self.doc.chemin.stem if self.doc.chemin else (self.doc.nom or tr("sans titre"))
        nom += getattr(self.doc, "suffixe_nom", None) or ""      # ex. « photo_restauree » → photo_restauree_web
        d = DialogueExport(self, qimage_vers_pil(self.doc.image_tramee()), nom, self.doc.exif, self.doc.icc)
        if d.exec() == QDialog.Accepted:
            self.statusBar().showMessage(tr("Exporté : {chemin}", chemin=d.chemin), 8000)
        d.deleteLater()

    def traitement_lot(self):
        from .export import DialogueLot
        d = DialogueLot(self)
        d.exec()
        d.deleteLater()

    # ---------------------------------------------------------------- règles, repères, grille
    def _menu_regles(self, m):
        def case(texte, raccourci, cle, defaut, fonction):
            a = self._action(m, texte, raccourci, None, cle)
            a.setCheckable(True)
            a.setChecked(self.reglages.value(cle, defaut) == "true")
            a.toggled.connect(lambda v: (self.reglages.setValue(cle, "true" if v else "false"), fonction(v)))
            fonction(a.isChecked())
            return a
        c = self.canevas
        case(tr("Règles"), "Ctrl+R", "a_regles", "false",
             lambda v: [w.setVisible(v) for w in (self.regle_h, self.regle_v, self.coin_regles)])
        case(tr("Grille"), "Ctrl+'", "a_grille", "false", lambda v: (setattr(c, "grille_visible", v), c.update()))
        case(tr("Repères"), "Ctrl+;", "a_reperes", "true", lambda v: (setattr(c, "reperes_visibles", v), c.update()))
        case(tr("Magnétisme (repères, grille, bords)"), "Ctrl+Shift+;", "a_magnetisme", "true",
             lambda v: setattr(c, "magnetisme", v))
        c.pas_grille = int(self.reglages.value("pas_grille", 100))
        self._action(m, tr("Taille de la grille…"), None, self.taille_grille, "a_taille_grille")
        self._action(m, tr("Nouveau repère…"), None, self.nouveau_repere, "a_nouveau_repere")
        self._action(m, tr("Effacer les repères"), None, self.effacer_reperes, "a_effacer_reperes")

    def taille_grille(self):
        from PySide6.QtWidgets import QInputDialog
        v, ok = QInputDialog.getInt(self, tr("Grille"), tr("Écart entre les lignes (pixels de l'image) :"),
                                    self.canevas.pas_grille, 2, 5000)
        if ok:
            self.canevas.pas_grille = v
            self.reglages.setValue("pas_grille", v)
            self.a_grille.setChecked(True)
            self.canevas.update()

    def nouveau_repere(self):
        if not self.doc:
            return
        from PySide6.QtWidgets import QInputDialog
        sens, ok = QInputDialog.getItem(self, tr("Nouveau repère"), tr("Sens :"), [tr("Horizontal"), tr("Vertical")],
                                        0, False)
        if not ok:
            return
        h = sens == tr("Horizontal")
        w_, h_ = self.doc.taille()
        v, ok = QInputDialog.getInt(self, tr("Nouveau repère"), tr("Position (pixels depuis le haut)") if h else
                                    tr("Position (pixels depuis la gauche)"), (h_ if h else w_) // 2, 0,
                                    h_ if h else w_)
        if ok:
            self.doc.reperes.append(("h" if h else "v", v))
            self.a_reperes.setChecked(True)
            self.canevas.update()

    def effacer_reperes(self):
        if self.doc:
            self.doc.reperes.clear()
            self.canevas.update()

    # ---------------------------------------------------------------- options des outils de dessin
    def _options_dessin(self, tout):
        from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QSpinBox, QWidget
        from PySide6.QtGui import QColor
        from .panneau_texte import BoutonCouleur
        c = self.canevas
        # dégradé
        self.opt_degrade = QWidget()
        lay = QHBoxLayout(self.opt_degrade)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        forme = QComboBox()
        forme.addItem(tr("Linéaire"), "lineaire")
        forme.addItem(tr("Radial"), "radial")
        forme.setCurrentIndex(max(0, forme.findData(self.reglages.value("degrade_forme", "lineaire"))))
        lay.addWidget(forme)
        from .degrades import BoutonDegrade, deux_couleurs, normaliser
        enregistre = self.reglages.value("degrade_points", "")
        if enregistre:
            depart = normaliser(enregistre)
        else:                                   # réglages d'avant l'éditeur de dégradé
            transp = self.reglages.value("degrade_transparent", "true") == "true"
            depart = deux_couleurs("peinture", None if transp else
                                   QColor(self.reglages.value("degrade_couleur2", "#ffffffff")).name())
        self.opt_degrade_bouton = BoutonDegrade(depart, lambda: QColor(c.couleur_peinture))
        lay.addWidget(self.opt_degrade_bouton)
        garder = QCheckBox(tr("Garder la transparence"))
        garder.setToolTip(tr("Le dégradé ne se pose que sur ce qui est déjà peint dans le calque (un objet détouré, "
                             "des lettres) : le vide autour reste vide."))
        garder.setChecked(self.reglages.value("degrade_garder_transparence", "false") == "true")
        lay.addWidget(garder)
        self.opt_degrade_masque = QLabel(tr("→ dans le masque"))
        self.opt_degrade_masque.setStyleSheet("color: #d97706; font-weight: bold;")
        self.opt_degrade_masque.setToolTip(tr("Le masque du calque est choisi (panneau Calques) : le dégradé y rend "
                                              "le calque plus ou moins transparent, il ne le colore pas. Pour "
                                              "colorer : clique sur la vignette du calque."))
        self.opt_degrade_masque.hide()
        lay.addWidget(self.opt_degrade_masque)

        def maj_degrade(*_):
            import json
            c.forme_degrade = forme.currentData()
            c.degrade = self.opt_degrade_bouton.degrade
            c.garder_transparence = garder.isChecked()
            self.reglages.setValue("degrade_garder_transparence", "true" if garder.isChecked() else "false")
            self.reglages.setValue("degrade_forme", forme.currentData())
            self.reglages.setValue("degrade_points", json.dumps(c.degrade))
        forme.currentIndexChanged.connect(maj_degrade)
        self.opt_degrade_bouton.change.connect(maj_degrade)
        garder.toggled.connect(maj_degrade)
        maj_degrade()
        tout.addWidget(self.opt_degrade)
        # pot de peinture
        self.opt_seau = QWidget()
        lay = QHBoxLayout(self.opt_seau)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tr("Tolérance")))
        tol = QSpinBox()
        tol.setRange(0, 255)
        tol.setValue(int(self.reglages.value("seau_tolerance", 32)))
        tol.setToolTip(tr("Plus haut : la couleur déborde sur des teintes plus éloignées"))

        def maj_seau(v):
            c.tolerance_seau = v
            self.reglages.setValue("seau_tolerance", v)
        tol.valueChanged.connect(maj_seau)
        maj_seau(tol.value())
        lay.addWidget(tol)
        tous = QCheckBox(tr("Tous les calques"))
        tous.setToolTip(tr(
            "Décochée (conseillé) : la zone à remplir est cherchée dans le calque choisi seulement ; sur un calque "
            "vide, un clic remplit tout le calque, quoi qu'il y ait sur les autres calques.\n"
            "Cochée : la zone suit l'image visible (tous les calques ensemble), par exemple pour colorier un dessin "
            "dont les traits sont sur un autre calque. Le remplissage s'arrête alors aux bords de ce qu'on voit, "
            "même si cela vient d'un autre calque (en supprimant ce calque, un trou apparaît)."))
        tous.setChecked(self.reglages.value("seau_tous_calques", False, type=bool))

        def maj_tous(oui):
            c.seau_tous_calques = oui
            self.reglages.setValue("seau_tous_calques", oui)
        tous.toggled.connect(maj_tous)
        maj_tous(tous.isChecked())
        lay.addWidget(tous)
        avec = QComboBox()
        avec.addItem(tr("Couleur"), "couleur")
        avec.addItem(tr("Motif"), "motif")
        avec.setToolTip(tr("Remplir avec : la couleur choisie, ou un motif de la bibliothèque, répété"))
        avec.setCurrentIndex(max(0, avec.findData(self.reglages.value("seau_remplir", "couleur"))))

        def maj_avec(*_):
            c.seau_motif = avec.currentData() == "motif"
            self.reglages.setValue("seau_remplir", avec.currentData())
            if hasattr(self, "opt_motif") and c.outil == "seau":
                self._choisir_outil("seau")          # la barre du haut se remet en page
        avec.currentIndexChanged.connect(maj_avec)
        maj_avec()
        lay.addWidget(avec)
        tout.addWidget(self.opt_seau)
        # motif (pot de peinture en mode motif, tampon de motif)
        from .motifs import BoutonMotif
        self.opt_motif = QWidget()
        lay = QHBoxLayout(self.opt_motif)
        lay.setContentsMargins(0, 0, 0, 0)
        self.bouton_motif = BoutonMotif(self.reglages.value("motif_cle", None), compact=True)
        c.motif_cle = self.bouton_motif.cle

        def maj_motif(cle):
            c.motif_cle = cle
            self.reglages.setValue("motif_cle", cle)
        self.bouton_motif.change.connect(maj_motif)
        lay.addWidget(self.bouton_motif)
        echelle = QSpinBox()
        echelle.setRange(10, 1000)
        echelle.setSuffix(" %")
        echelle.setSingleStep(10)
        echelle.setToolTip(tr("Échelle du motif : 100 % = taille réelle"))
        try:
            echelle.setValue(int(self.reglages.value("motif_echelle", 100)))
        except (TypeError, ValueError):
            echelle.setValue(100)

        def maj_echelle(v):
            c.motif_echelle = v / 100
            self.reglages.setValue("motif_echelle", v)
        echelle.valueChanged.connect(maj_echelle)
        maj_echelle(echelle.value())
        lay.addWidget(echelle)
        tout.addWidget(self.opt_motif)
        for w in (self.opt_degrade, self.opt_seau, self.opt_motif):
            w.hide()

    # ---------------------------------------------------------------- masques
    def basculer_cible_masque(self):
        if self.doc and self.doc.calque_actif.masque is not None:
            self.doc.cible_masque = not self.doc.cible_masque
            self.doc.calques_changes.emit()
            self.statusBar().showMessage(tr("Les outils de peinture travaillent sur le masque (noir cache, blanc "
                                            "montre).") if self.doc.cible_masque else
                                         tr("Les outils de peinture travaillent sur les pixels du calque."), 4000)

    def _masque_ou_message(self):
        if not self.doc:
            return None
        c = self.doc.calque_actif
        if c.masque is None:
            self.statusBar().showMessage(tr("Le calque « {nom} » n'a pas de masque.", nom=c.nom), 4000)
            return None
        return c

    def basculer_masque(self):
        c = self._masque_ou_message()
        if c is not None:
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, masque_actif=not c.masque_actif),
                                   tr("Désactiver le masque") if c.masque_actif else tr("Réactiver le masque"))

    def inverser_masque(self):
        c = self._masque_ou_message()
        if c is not None:
            m = c.masque.copy()
            m.invertPixels()
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, masque=m), tr("Inverser le masque"))

    def masque_vers_selection(self):
        c = self._masque_ou_message()
        if c is not None:
            from .composition import masque_tableau
            from .document import _masque_vers_selection
            avant = self.doc.etat()
            self.doc.selection = _masque_vers_selection(masque_tableau(c.masque)).convertToFormat(
                self.doc.selection.format())
            self.doc.change.emit()
            self._selection_modifiee(avant, tr("Masque vers sélection"))

    def appliquer_masque(self):
        etat = self.doc.etat_appliquer_masque() if self.doc else None
        if etat:
            self.doc.cible_masque = False
            self._commande_calques(etat, tr("Appliquer le masque"))

    def supprimer_masque(self):
        c = self._masque_ou_message()
        if c is not None:
            self.doc.cible_masque = False
            self._commande_calques(self.doc.etat_calque_modifie(self.doc.actif, masque=None), tr("Supprimer le masque"))

    # ---------------------------------------------------------------- aperçu commun
    def _histo_calque(self):
        doc = self.doc
        t = tableau(doc.image.convertToFormat(FORMAT_IMAGE)) if doc.calque_actif.special else \
            tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
        ok = t[..., 3] > 128
        if not doc.selection_vide():
            ok &= masque(doc.selection) > 128
        return histogramme(t[ok][:, :3] if ok.any() else t[..., :3])

    def _verifier_pixels(self, action: str) -> bool:
        if not self.doc or not self._verifier_verrou(action):
            return False
        c = self.doc.calque_actif
        if c.special:
            quoi = tr("un groupe") if c.groupe else tr("un calque de réglage")
            QMessageBox.information(self, action, tr("« {nom} » est {quoi} : il n'a pas de pixels. Choisis un "
                                                     "calque d'image.", nom=c.nom, quoi=quoi))
            return False
        return True

    def _dialogue_pixels(self, titre: str, panneau, neutres: dict, calcul, auto: bool = False,
                         toujours: bool = False, etape=None, seize: str | None = None):
        """Réglage ou filtre appliqué dans les pixels du calque choisi (dans la sélection s'il y en a une), avec un
        aperçu en direct calculé en arrière-plan."""
        from .fenetre import CommandeEtat, Tache
        doc = self.doc
        avant, modifie = doc.etat(), doc.modifie
        index, calque = doc.actif, doc.calque_actif
        selection = None if doc.selection_vide() else doc.selection.copy()
        ou = tr("dans la sélection") if selection is not None else tr("sur tout le calque")
        d = DialogueReglage(self, titre, tr("S'applique au calque « {nom} », {ou}.", nom=calque.nom, ou=ou),
                            panneau, neutres, auto)
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        suivi = {"occupe": False, "attente": None, "ouvert": True}

        def montrer(p, img):
            if not suivi["ouvert"]:
                return
            if img is None:
                doc.apercu_calque(index, calque.image, calque.texte)
            else:
                doc.apercu_calque(index, img)

        def calculer(p):
            if suivi["occupe"]:
                suivi["attente"] = p
                return
            if p is None or (p == neutres and not toujours):
                montrer(p, None)
                return
            suivi["occupe"] = True
            t = Tache(lambda _progres: filtres.appliquer_calque(calque.image, lambda a: calcul(a, p), selection,
                                                                             seize))
            t.fini.connect(lambda img: fini(p, img))
            t.echec.connect(lambda _m: fini(p, None))
            suivi["tache"] = t
            t.lancer()

        def fini(p, img):
            suivi["occupe"] = False
            montrer(p, img)
            if suivi["attente"] is not None:
                p2, suivi["attente"] = suivi["attente"], None
                calculer(p2)

        d.change.connect(calculer)
        d.change.emit(d.valeurs_apercu())
        ok = d.exec() == QDialog.Accepted
        suivi["ouvert"] = False
        p = d.valeurs()
        d.fermer()
        doc.appliquer_etat(avant)
        doc.modifie = modifie
        if ok and (p != neutres or toujours):
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                img = filtres.appliquer_calque(calque.image, lambda a: calcul(a, p), selection, seize)
            finally:
                QApplication.restoreOverrideCursor()
            apres = doc.etat_calque_modifie(index, image=img, texte=None)
            self.historique.push(CommandeEtat(doc, avant, apres, titre))
            if etape is not None:                       # enregistrable dans une action (panneau Actions)
                self.noter_action(etape(p))
        return ok

    # ---------------------------------------------------------------- harmoniser un collage
    def harmoniser(self):
        """Calque > Harmoniser avec l'arrière-plan : l'objet du calque choisi (collé, détouré) prend la lumière de
        la photo en dessous."""
        from . import harmoniser as hm
        from .document import fusionner
        titre = tr("Harmoniser avec l'arrière-plan")
        if not self._verifier_pixels(titre):
            return
        doc = self.doc
        index = doc.actif
        calque = tableau(doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
        w, h = doc.taille()
        dessous = [c for c in doc.calques[:index]]
        fond = tableau(fusionner(dessous, w, h).convertToFormat(FORMAT_IMAGE)) if dessous else None
        if fond is None or fond[..., 3].max() < 128 or calque[..., 3].min() > 250:
            QMessageBox.information(self, titre, tr(
                "Choisis le calque de l'objet collé (détouré, avec de la transparence autour), posé au-dessus de la "
                "photo : il prendra la lumière de la photo qui l'entoure."))
            return
        ref = hm.mesures(hm.lab(fond[..., :3])[hm.reference(fond, calque[..., 3])])
        depart = {k: int(self.reglages.value("harmoniser_" + k, v)) for k, v in hm.DEPART.items()}
        panneau = hm.panneau_harmoniser()(depart, {})

        def calcul(a, p):
            for k, v in p.items():
                self.reglages.setValue("harmoniser_" + k, v)
            return hm.harmoniser(a, ref, p)
        self._dialogue_pixels(titre, panneau, dict(hm.NEUTRES), calcul)

    # ---------------------------------------------------------------- réglages de couleur
    def reglage(self, type_: str):
        """Image > Réglages : le réglage va dans les pixels du calque choisi."""
        titre = ajustements.nom(type_)
        if not self._verifier_pixels(titre):
            return
        neutres = ajustements.defaut(type_)
        panneau = PANNEAUX[type_](neutres, self._histo_calque())
        # Négatif, Seuil, Postérisation, Noir et blanc… changent l'image dès l'ouverture, sans toucher aux curseurs
        self._dialogue_pixels(titre, panneau, neutres,
                              lambda a, p: ajustements.appliquer_rgba(a, type_, p), auto=type_ == "niveaux",
                              toujours=not ajustements.neutre(type_, neutres),
                              etape=lambda p: {"genre": "reglage", "type": type_, "params": p}, seize="entier")

    def nouveau_calque_reglage(self, type_: str):
        """Calque de réglage : modifiable à tout moment (double-clic), sans toucher aux pixels."""
        if not self.doc:
            return
        avant = self.doc.etat()
        etat = self.doc.etat_nouveau_reglage(type_, ajustements.defaut(type_), ajustements.nom(type_))
        self.doc.appliquer_etat(etat)
        if not self._editer_reglage(avant, ajustements.nom(type_), nouveau=True):
            self.doc.appliquer_etat(avant)

    # ---------------------------------------------------------------- calques de remplissage
    def nouveau_calque_remplissage(self, genre: str):
        """Calque > Nouveau calque de remplissage : couleur unie, dégradé ou motif, modifiable (double-clic)."""
        from . import calque_remplissage as cr
        if not self.doc:
            return
        avant = self.doc.etat()
        couleur = self.canevas.couleur_peinture
        hexa = f"#{couleur.red():02x}{couleur.green():02x}{couleur.blue():02x}"
        # comme Photoshop : la couleur de peinture ; dégradé de la couleur de peinture vers le blanc
        from .degrades import deux_couleurs
        r = cr.Remplissage(genre=genre, couleur="#ff" + hexa[1:],
                           degrade=deux_couleurs(hexa, "#ffffff" if couleur.lightnessF() < 0.9 else "#000000"))
        self.doc.appliquer_etat(self.doc.etat_nouveau_remplissage(r, cr.noms_genres()[genre]))
        if not self._editer_remplissage(avant, nouveau=True):
            self.doc.appliquer_etat(avant)

    def _editer_remplissage(self, avant, nouveau: bool = False) -> bool:
        from . import calque_remplissage as cr
        from .dialogue_remplissage import DialogueRemplissage
        from .fenetre import CommandeEtat
        doc = self.doc
        index = doc.actif
        depart = cr.valide(doc.calque_actif)
        if depart is None:
            return False
        modifie = doc.modifie
        d = DialogueRemplissage(depart, self, tr("Calque de remplissage « {nom} » : double-clic dessus pour y "
                                                 "revenir.", nom=doc.calque_actif.nom))
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        etat_depart = doc.etat()

        def montrer(r):
            doc.appliquer_etat(doc.etat_remplissage(index, r))
        d.change.connect(montrer)
        ok = d.exec() == QDialog.Accepted
        r = d.r
        d.deleteLater()
        doc.appliquer_etat(etat_depart)
        doc.modifie = modifie
        if not ok:
            return False
        apres = doc.etat_remplissage(index, r)
        titre = tr("Nouveau calque de remplissage") if nouveau else tr("Modifier le remplissage")
        self.historique.push(CommandeEtat(doc, avant, apres, titre))
        return True

    def modifier_reglage(self):
        if not self.doc:
            return
        c = self.doc.calque_actif
        from . import calque_remplissage
        if calque_remplissage.valide(c) is not None:
            self._editer_remplissage(self.doc.etat())
            return
        if c.reglage is None:
            QMessageBox.information(self, tr("Modifier le réglage"), tr("Choisis d'abord un calque de réglage dans "
                                                                         "le panneau Calques."))
            return
        self._editer_reglage(self.doc.etat(), tr("Modifier le réglage"))

    def _editer_reglage(self, avant, titre: str, nouveau: bool = False) -> bool:
        from .fenetre import CommandeEtat
        doc = self.doc
        index = doc.actif
        c = doc.calque_actif
        type_ = c.reglage["type"]
        depart = copy.deepcopy(c.reglage["params"])
        dessous = doc.calques[:index]
        from .composition import fusionner
        w, h = doc.taille()
        fond = tableau(fusionner(dessous, w, h).convertToFormat(FORMAT_IMAGE))
        histo = histogramme(fond[fond[..., 3] > 128][:, :3] if (fond[..., 3] > 128).any() else fond[..., :3])
        panneau = PANNEAUX[type_](depart, histo)
        neutres = ajustements.defaut(type_)
        d = DialogueReglage(self, ajustements.nom(type_), tr("Calque de réglage « {nom} » : il change tout ce qui est "
                                                             "dessous ; double-clic dessus pour y revenir.",
                                                             nom=c.nom), panneau, neutres,
                            auto=type_ == "niveaux")
        d.b_ok.setText(tr("OK"))
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)

        def montrer(p):
            if p is None:
                p = neutres
            calques = list(doc.calques)
            if index < len(calques) and calques[index].reglage is not None:
                calques[index] = replace(calques[index], reglage={"type": type_, "params": p})
                doc.calques = tuple(calques)
                doc._fusion = None
                doc.change.emit()
        d.change.connect(montrer)
        ok = d.exec() == QDialog.Accepted
        p = d.valeurs()
        d.fermer()
        montrer(depart)
        if not ok:
            return False
        apres = doc.etat_calque_modifie(index, reglage={"type": type_, "params": p})
        self.historique.push(CommandeEtat(doc, avant, apres, ajustements.nom(type_) if nouveau else titre))
        return True

    # ---------------------------------------------------------------- filtres
    def fluidite(self):
        """Filtres > Fluidité : pousser, gonfler, contracter, tourbillon, reconstruire, au pinceau."""
        from .fenetre import CommandeEtat
        from .fluidite import DialogueFluidite
        titre = tr("Fluidité")
        if not self._verifier_pixels(titre):
            return
        doc = self.doc
        index, calque = doc.actif, doc.calque_actif
        selection = None if doc.selection_vide() else doc.selection.copy()
        rgba = tableau(calque.image.convertToFormat(FORMAT_IMAGE))
        d = DialogueFluidite(self, rgba)
        d.resize(1200, 780)
        if d.exec() != QDialog.Accepted or not d.champ.any():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            res = d.resultat()
            img = filtres.appliquer_calque(calque.image, lambda _a: res, selection)
        finally:
            QApplication.restoreOverrideCursor()
        avant = doc.etat()
        apres = doc.etat_calque_modifie(index, image=img, texte=None)
        self.historique.push(CommandeEtat(doc, avant, apres, titre))

    def remplacer_couleur(self):
        """Image > Réglages > Remplacer la couleur : on clique la couleur dans un aperçu du calque."""
        from . import plage_couleurs as pc
        titre = tr("Remplacer la couleur")
        if not self._verifier_pixels(titre):
            return
        rgba = tableau(self.doc.calque_actif.image.convertToFormat(FORMAT_IMAGE))
        neutres = pc.defaut_remplacer()
        panneau = pc.panneau_remplacer(rgba)(neutres, {})
        self._dialogue_pixels(titre, panneau, neutres, pc.remplacer_couleur)

    def plage_couleurs(self):
        """Sélection > Plage de couleurs : tous les points des couleurs cliquées, dans toute l'image visible."""
        from . import plage_couleurs as pc
        from .selection_auto import combiner
        from .selection_ia import _selection
        doc = self.doc
        if doc is None:
            return
        rgba = tableau(doc.image.convertToFormat(FORMAT_IMAGE))
        d = pc.DialoguePlage(self, rgba, getattr(self, "_plage_derniere", None))
        base = None if doc.selection_vide() else masque(doc.selection)

        def montrer(m):
            if m is None:
                self.canevas.apercu_selection = None
            else:
                self.canevas.apercu_selection = _selection(combiner(base, m, d.mode()))
            self.canevas.update()
        d.apercu.connect(montrer)
        d.l_mode.currentIndexChanged.connect(lambda *_: d._plus_tard())
        d.adjustSize()
        coin = self.mapToGlobal(self.rect().topRight())
        d.move(coin.x() - d.width() - 20, coin.y() + 110)
        ok = d.exec() == QDialog.Accepted
        self.canevas.apercu_selection = None
        self.canevas.update()
        if ok:
            p = d.params()
            self._plage_derniere = {"couleurs": [], "retirees": [], "tolerance": p.get("tolerance", 40),
                                    "inverser": p.get("inverser", False)}
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.selection_auto._historique(combiner(base, d.masque(), d.mode()), tr("Plage de couleurs"))
            finally:
                QApplication.restoreOverrideCursor()
        d.deleteLater()

    def filtre(self, type_: str):
        titre = filtres.noms()[type_]
        if not self._verifier_pixels(titre):
            return
        neutres = filtres.defauts(type_)
        panneau = PanneauFiltre(type_, neutres, {})
        fonction = filtres.FONCTIONS[type_]
        self._dialogue_pixels(titre, panneau, neutres, lambda a, p: fonction(a, p), toujours=True,
                              etape=lambda p: {"genre": "filtre", "type": type_, "params": p},
                              seize="flottant")
