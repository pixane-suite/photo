"""Zone d'affichage : zoom, déplacement, outils de sélection (rectangle, lasso, pinceau, gomme, baguette
magique, sélection rapide, sélection d'objet), texte, recadrage, pinceau de couleur et tampon."""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QImage, QInputDevice, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
                           QTransform)
from PySide6.QtWidgets import QWidget

from . import calque_pinceau, regles
from .composition import argb_vers_masque, masque_vers_argb
from .document import COULEUR_SELECTION, Document, image_entiere, tableau, vectoriel
from .outils_plus import (CRAYON, DEPLACER_IA, ELLIPSE_SEL, LASSO_MAG, LOUPE, MELANGEUR, PIECE, PIPETTE, REGLE,
                          ROTATION_VUE, CanevasPlusMixin)
from .plume import PlumeMixin
from .langue import tr
from .pointe import Pointe, Reglages
from .retouche import GOMME as EFFACER
from .retouche import Trait
from .texte import contient, contour_bloc, rendre, transformation
from .transformation import POIGNEES, Transformation, point_surface

MAIN, RECTANGLE, LASSO, PINCEAU, GOMME = "main", "rectangle", "lasso", "pinceau", "gomme"
TAILLE_MAX = 5000                              # taille maximale du pinceau, en pixels (comme Photoshop)
GOMME_CALQUE = "gomme_calque"                  # efface pour de vrai les pixels du calque actif
TEXTE = "texte"                                # écrire, déplacer, tourner un texte
DEPLACER = "deplacer"                          # déplacer le contenu du calque choisi
RECADRER = "recadrer"                          # garder une partie de la photo
PEINTURE = "peinture"                          # pinceau de couleur sur le calque choisi
TAMPON = "tampon"                              # copier une zone de la photo sur une autre (Alt+clic : source)
TAMPON_MOTIF = "tampon_motif"                  # tampon de motif : peint un motif de la bibliothèque
BAGUETTE = "baguette"                          # baguette magique : zone de couleur proche (glisser = tolérance)
RAPIDE = "rapide"                              # sélection rapide (IA) : peindre sur l'objet
OBJET = "objet"                                # sélection d'objet (IA) : cadre autour, ou clic dessus
SEL_TEXTE = "sel_texte"                        # sélection de texte : cadre autour du texte, clics pour corriger
SUPPRIMER = "supprimer"                        # pinceau Supprimer (IA, LaMa) : le défaut peint disparaît au lâcher
EFFACER_CLIC = "effacer_clic"                  # Effacer d'un clic (IA) : clic sur un objet (ou cadre), il est effacé
YEUX = "yeux_rouges"                           # Yeux rouges : clic sur l'œil (ou cadre), la pupille redevient sombre
CORRECTEUR = "correcteur"                      # pinceau correcteur : comme le tampon, raccordé à la lumière autour
DEGRADE = "degrade"                            # dégradé : glisser du début à la fin
SEAU = "seau"                                  # pot de peinture : remplit une zone de couleur proche
FORMES = "formes"                              # rectangle, ellipse, ligne, flèche (nouveau calque de forme)
PLUME = "plume"                                # tracés en courbes -> calque de forme ou sélection
DENSITE_MOINS = "densite_moins"                # éclaircir au pinceau (ombres, tons moyens ou hautes lumières)
DENSITE_PLUS = "densite_plus"                  # assombrir au pinceau
EPONGE = "eponge"                              # saturer ou désaturer au pinceau
GOUTTE = "goutte"                              # goutte d'eau : flouter au pinceau
NETTETE_PINCEAU = "nettete_pinceau"            # netteté au pinceau
DOIGT = "doigt"                                # étaler la couleur
HISTORIQUE = "historique"                      # pinceau d'historique : repeindre l'état de l'instantané
OUTILS_FILTRE = (DENSITE_MOINS, DENSITE_PLUS, EPONGE, GOUTTE, NETTETE_PINCEAU, DOIGT)
OUTILS_RETOUCHE = (PEINTURE, TAMPON, TAMPON_MOTIF, CORRECTEUR, HISTORIQUE, CRAYON, MELANGEUR) + OUTILS_FILTRE
MODES_TRAIT = {DENSITE_MOINS: "eclaircir", DENSITE_PLUS: "assombrir", EPONGE: "eponge", GOUTTE: "goutte",
               NETTETE_PINCEAU: "nettete", DOIGT: "doigt"}
OUTILS_ROND = (PINCEAU, GOMME, GOMME_CALQUE, PEINTURE, TAMPON, TAMPON_MOTIF, RAPIDE, SUPPRIMER,
               CORRECTEUR, HISTORIQUE, CRAYON, MELANGEUR) + OUTILS_FILTRE                     # curseur rond
OUTILS_AUTO = (BAGUETTE, RAPIDE, OBJET, SEL_TEXTE)                       # sélections calculées
OUTILS_CALQUE = (GOMME_CALQUE, PEINTURE, TAMPON, TAMPON_MOTIF, CORRECTEUR, DEGRADE, SEAU, HISTORIQUE, CRAYON,
                 MELANGEUR) + OUTILS_FILTRE                  # outils qui changent les pixels du calque
GROUPES_PINCEAU = ("peinture", "gomme", "selection")   # un pinceau à forme choisi par groupe d'outils
GROUPE_OUTIL = {PEINTURE: "peinture", GOMME_CALQUE: "gomme", PINCEAU: "selection", GOMME: "selection"}
OPACITE_SELECTION = 0.45

# outils de sélection : les flèches du clavier décalent la sélection (Maj : 10 pixels)
OUTILS_SELECTION = (RECTANGLE, ELLIPSE_SEL, LASSO, LASSO_MAG, PINCEAU, BAGUETTE, RAPIDE, OBJET, SEL_TEXTE)
FORMES_SELECTION = (RECTANGLE, ELLIPSE_SEL, LASSO)          # sélections tracées à la souris
FLECHES = {Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0), Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1)}


def _distance_segment(p: QPointF, a: QPointF, b: QPointF) -> float:
    """Distance du point p au segment ab (écran)."""
    ab = b - a
    long2 = ab.x() ** 2 + ab.y() ** 2
    k = 0.0 if long2 == 0 else max(0.0, min(1.0, ((p - a).x() * ab.x() + (p - a).y() * ab.y()) / long2))
    q = a + ab * k
    return ((p - q).x() ** 2 + (p - q).y() ** 2) ** 0.5


class Canevas(CanevasPlusMixin, PlumeMixin, QWidget):
    selection_modifiee = Signal(object, str)   # (état avant, nom de l'action) -> pour annuler (sélection ou calque)
    infos = Signal(int, int, float)             # largeur, hauteur, zoom
    refus = Signal(str)                         # action impossible (ex. calque verrouillé) : message
    vue_peinte = Signal()                       # le canevas se redessine (les règles suivent)
    cadre_change = Signal(object, object)       # Agrandir : (ajout, bord abîmé), chacun (haut, bas, gauche, droite) px
    cadre_valide = Signal()                     # Entrée pendant Agrandir
    cadre_annule = Signal()                     # Échap pendant Agrandir
    texte_nouveau = Signal(object)              # outil Texte : clic hors des textes -> point (image)
    texte_choisi = Signal(int)                  # outil Texte : clic sur un calque de texte -> son index
    lettres_choisies = Signal(int, int)         # outil Texte : lettres choisies à la souris sur la photo (début, fin)
    texte_edition = Signal(int)                 # double-clic sur un texte de l'image (autre outil) -> son index
    trace_dessine = Signal(list)                # outil Texte, « Dessiner un tracé » : points (image) du tracé
    degrade_masque = Signal()                   # dégradé commencé sur un masque (il rend transparent, ne colore pas)
    couleur_prise = Signal(str)                 # pinceau de couleur : Alt+clic (pipette) -> couleur « #rrggbb »
    recadre_change = Signal(object)             # outil Recadrer : QRect (image) ou None
    recadre_valide = Signal()                   # Entrée ou double-clic dans le cadre
    transfo_change = Signal()                   # Transformer (Ctrl+T) : taille ou angle modifié
    transfo_mode_change = Signal()              # Transformer : passé en « distordre » par Ctrl+coin
    persp_valide = Signal()                     # Recadrage en perspective : Entrée ou double-clic
    persp_annule = Signal()                     # Recadrage en perspective : Échap
    transfo_valide = Signal()                   # Entrée ou double-clic dans le cadre
    transfo_annule = Signal()                   # Échap
    transfo_demandee = Signal()                 # outil Déplacer : poignée du cadre attrapée -> Transformer (Ctrl+T)
    selection_fleche = Signal(int, int)         # outils de sélection : flèche du clavier -> décaler la sélection
    message = Signal(str)                       # information (barre d'état)
    baguette_clic = Signal(object, str)         # point (image), mode « nouvelle » / « ajouter » / « retirer »
    baguette_glisse = Signal(float)             # écart horizontal (écran) depuis le clic -> tolérance
    baguette_lache = Signal()
    trait_ia = Signal(list, bool, bool)         # sélection rapide : points (image), Alt (retirer), Maj (nouvel objet)
    objet_ia = Signal(object, str)              # sélection d'objet : QRectF (cadre) ou QPointF (clic), mode
    effacer_clic = Signal(object)               # Effacer d'un clic : QRectF (cadre) ou QPointF (clic)
    comparaison_finie = Signal()                # Échap pendant Avant / après
    yeux_rouges = Signal(object)                # outil Yeux rouges : QRectF (cadre) ou QPointF (clic)
    texte_sel = Signal(object, str, bool)       # sélection de texte : QRectF (cadre) ou QPointF (clic), mode, Ctrl
    fin_session_ia = Signal()                   # Échap avec la sélection rapide : l'objet suivant repart de zéro
    suppression = Signal(list, float)           # pinceau Supprimer : points (image), taille du pinceau
    travail_change = Signal()                   # travail en cours (Transformer, Agrandir, Recadrer) : gestes changés
    poignee_sol_bouge = Signal(object)          # style « ombre au sol » : bout de l'ombre tiré (point image)
    regle_changee = Signal()                    # outil Règle : nouvelle mesure
    piece_glissee = Signal(int, int)            # outil Pièce : zone à réparer glissée sur une partie saine (dx, dy)
    objet_deplace = Signal(int, int)            # Déplacer un objet (IA) : sélection glissée de (dx, dy)
    menu_rapide_demande = Signal(object)        # clic droit : menu rapide à cette place (écran)
    durete_demandee = Signal(int)               # Alt + clic droit glissé : nouvelle dureté (%)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_plume()
        self._init_plus()
        self._sur_masque = False             # coup de pinceau / gomme en cours sur le masque du calque
        self.doc: Document | None = None
        self.zoom = 1.0
        self.decalage = QPointF(0, 0)
        self.outil = PINCEAU
        self.taille_pinceau = 60
        self._espace = False
        self._glisse = None          # point de départ d'un déplacement
        self._trace = None           # tracé en cours (liste de points image)
        self._soustraire = False
        self._avant = None
        self._souris = None
        self._cache = None           # (clé, pixmap réduite)
        self._ajuste = True          # l'image suit la taille de la fenêtre
        self.mode_retirer = False    # pinceau de sélection : pastilles Ajouter / Retirer
        self.lasso_points = False    # Lasso « Par points » : un clic par point (comme le lasso polygonal)
        self._poly = None            # lasso par points en cours : points posés (image)
        self._poly_souris = None     # lasso par points : position de la souris (image), pour le segment suivant
        self.mode_forme = "nouvelle" # rectangle et lasso : « nouvelle » (remplace), « ajouter » ou « retirer »
        self._nouvelle = False       # tracé en cours qui remplacera la sélection
        self.couleur_fond = QColor(40, 40, 40)
        self.couleur_texte = QColor(150, 150, 150)
        self.couleur_accent = QColor(0, 120, 215)
        self.selection_lettres = (0, 0)   # outil Texte : lettres sélectionnées dans la saisie (début, fin)
        self.cadre = None            # Agrandir : px ajoutés [haut, bas, gauche, droite], sinon None
        self.abime = [0, 0, 0, 0]    # Agrandir : px de bord abîmé à refaire [haut, bas, gauche, droite]
        self.base_cadre = None       # Agrandir : (x0, y0, x1, y1) d'où part le cadre (la photo, sans le vide)
        # gestes du travail en cours (pas encore validé) : retour / suivant de la souris, Ctrl+Z / Ctrl+Y
        self._gestes, self._refaits, self._etat_fixe = [], [], None
        self._poignee = None         # (cible « ext » / « int » / « ? », côtés parmi "h", "b", "g", "d")
        self._depart = None          # point (image) où le glisser du cadre a commencé
        self._texte_glisse = None    # (index, « deplacer » / « tourner », départ, Texte d'origine, état d'avant)
        self.trace_texte = False     # « Dessiner un tracé » du panneau Texte : glisser dessine la ligne du texte
        self._trace_points = None    # tracé en cours (points image)
        self._fleches = None         # outil Déplacer aux flèches : (genre, index, origine, état d'avant, [dx, dy])
        self._calque_glisse = None   # outil Déplacer : (index, départ, image d'origine, état d'avant)
        self._lettres_glisse = None  # outil Texte : (index, texte, boîtes des lettres, ancre) pendant un glisser
        self._lot_glisse = None      # outil Déplacer, groupe ou plusieurs calques : (lot, départ, état d'avant)
        self.calques_choisis = lambda: set()   # calques choisis dans le panneau (Ctrl+clic), donné par la fenêtre
        # pinceau de couleur et tampon
        self.couleur_peinture = QColor(0, 0, 0)
        self.opacite = 1.0           # 0..1
        self.durete = 0.8            # 0 = bord très doux, 1 = bord net
        from .degrades import defaut as degrade_defaut
        self.degrade = degrade_defaut()       # dégradé à plusieurs points (pixane.degrades)
        self.garder_transparence = False      # dégradé seulement sur les pixels déjà peints
        self._degrade_depart = None           # dégradé en cours : (état d'avant, calque, image, sur le masque ?)
        self._minuteur_degrade = QTimer(self, singleShot=True, interval=30)   # aperçu en direct pendant le glissé
        self._minuteur_degrade.timeout.connect(self._apercu_degrade)
        self.masque_explique = False          # message « le dégradé va dans le masque » déjà montré (fenêtre)
        self.forme_degrade = "lineaire"
        self.tolerance_seau = 32
        self.seau_tous_calques = False   # pot de peinture : zone d'après l'image visible (sinon : le calque choisi)
        self.seau_motif = False          # pot de peinture : remplir avec un motif (sinon : la couleur)
        self.motif_cle: str | None = None    # motif choisi (pot de peinture, tampon de motif)
        self.motif_echelle = 1.0             # échelle du motif (1 = taille réelle)
        # pinceaux à forme (bibliothèque) : un choix par groupe d'outils (peinture, gomme, sélection)
        self.pinceaux = {g: {"cle": None, "reglages": Reglages()} for g in GROUPES_PINCEAU}
        self._pointes: dict = {}         # formes prêtes à tamponner (par clé)
        self._trait_forme: Trait | None = None   # gomme de calque / pinceau de sélection avec une forme
        self._tablette = False           # un stylet a servi : la pression compte
        self._pression = 1.0             # dernière pression du stylet (0..1)
        self._pression_evt = 1.0         # pression du geste en cours
        self.forme = "rectangle"
        self.forme_remplie = True
        self.forme_contour = False
        self.forme_couleur = QColor(224, 64, 48)
        self.forme_couleur_contour = QColor(0, 0, 0)
        self.forme_epaisseur = 6
        self.forme_cotes = 5
        self._glisse_dessin = None   # dégradé / forme en cours : [début, fin, Maj]
        self.grille_visible = False
        self.pas_grille = 100
        self.reperes_visibles = True
        self.magnetisme = True
        self.repere_tire = None      # repère qu'on tire : [« h » ou « v », position dans l'image ou None]
        self._trait: Trait | None = None
        # calque de pinceau modifiable (case de la barre du pinceau de couleur) : les traits gardent leur tracé
        self.calque_pinceau = False
        self._pinceau_en_cours = None    # (index du calque, pinceau, graine, points) pendant un coup
        self.source_tampon: QPointF | None = None    # point (image) choisi par Alt+clic
        self._decalage_tampon: QPointF | None = None # source - point peint, fixé au premier coup (aligné)
        # recadrage
        self.recadre: QRectF | None = None           # cadre (image) à garder
        self.proportion: float | None = None         # largeur / hauteur imposée, ou libre
        self._recadre_glisse = None  # (mode « nouveau » / « deplacer » / côtés, point de départ, cadre d'origine)
        # transformer un calque (Ctrl+T)
        self.transfo: Transformation | None = None
        self.gamme_densite = "moyens"               # Densité − / + : tons touchés
        self.eponge_saturer = False                 # Éponge : saturer (sinon désaturer)
        self.source_historique = None               # fonction(calque) -> image de l'instantané (ou None)
        self.persp: list[QPointF] | None = None     # recadrage en perspective : 4 coins (hg, hd, bd, bg)
        self._persp_prise = None                    # (coin attrapé ou -1 = tout, point de départ, coins de départ)
        self.cadre_deplacer = True              # outil Déplacer : cadre à poignées autour du calque (comme Photoshop)
        self._cle_cadre_deplacer = None
        self._rect_cadre_deplacer = None
        self._transfo_index = 0
        self._transfo_glisse = False
        # sélections calculées
        self.comparer = False                       # Affichage > Comparer avant / après : rideau sur la photo
        self.rideau = 0.5                           # place du rideau (fraction de la largeur de la photo)
        self._rideau_glisse = False
        self.indice_effacer: QImage | None = None   # analyse avant Effacer : ombre / bord proposés, en couleur
        self.apercu_selection: QImage | None = None  # baguette pendant le glisser (petite image, étirée)
        self.apercu_plein: QImage | None = None      # aperçu qui cache la photo (Améliorer le contour)
        self.points_ia: list = []                    # sélection rapide : (point image, garder ?)
        self.trait_en_attente = None                 # trait ou cadre envoyé à l'IA, montré pendant le calcul
        self._auto = None                            # geste en cours : (outil, départ écran, données)
        self._transfo_glisse = False
        # fenêtre Style du calque ouverte : seuls le zoom, la main et la poignée de l'ombre au sol répondent
        self.style_ouvert = False
        self.poignee_sol = None                      # ((x, y) du pied, (x, y) du bout), en pixels image
        self._sol_glisse = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(300, 200)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    # ---------------------------------------------------------- document
    def definir_document(self, doc: Document | None):
        if self.doc is not None:
            try:
                self.doc.change.disconnect(self._doc_change)
                self.doc.taille_changee.disconnect(self.ajuster)
            except (RuntimeError, TypeError):
                pass
        self.doc = doc
        self._cache = None
        if doc is not None:
            doc.change.connect(self._doc_change)
            doc.taille_changee.connect(self.ajuster)
        self.ajuster()
        self._curseur()

    def _doc_change(self):
        self.update()

    # ---------------------------------------------------------- coordonnées
    def vers_image(self, p: QPointF) -> QPointF:
        return (p - self.decalage) / self.zoom

    def vers_ecran(self, p: QPointF) -> QPointF:
        return p * self.zoom + self.decalage

    # ---------------------------------------------------------- zoom
    def ajuster(self):
        if not self.doc:
            self.update()
            return
        iw, ih = self.doc.image.width(), self.doc.image.height()
        if self.cadre is not None:   # place pour tirer le cadre : au moins 40 % de chaque côté
            h, b, g, d = self._depasse()
            tw, th = iw + 2 * max(g, d, iw * 0.4), ih + 2 * max(h, b, ih * 0.4)
        else:
            tw, th = iw, ih
        self.zoom = max(0.01, min(self.width() / tw, self.height() / th) * 0.96)
        self._centrer()
        self._ajuste = True

    def zoom_100(self):
        if self.doc:
            self.definir_zoom(1.0, QPointF(self.width() / 2, self.height() / 2))

    def _centrer(self):
        iw, ih = self.doc.image.width() * self.zoom, self.doc.image.height() * self.zoom
        self.decalage = QPointF((self.width() - iw) / 2, (self.height() - ih) / 2)
        if self.cadre is not None:   # centrer le cadre entier plutôt que la photo
            h, b, g, d = self._depasse()
            self.decalage += QPointF((g - d) * self.zoom / 2, (h - b) * self.zoom / 2)
        self._signaler()
        self.update()

    def definir_zoom(self, zoom: float, autour: QPointF):
        zoom = max(0.02, min(32.0, zoom))
        point_image = self.vers_image(autour)
        self.zoom = zoom
        self._ajuste = False
        self.decalage = autour - point_image * zoom
        self._signaler()
        self.update()

    def zoomer(self, facteur: float):
        self.definir_zoom(self.zoom * facteur, QPointF(self.width() / 2, self.height() / 2))

    def _signaler(self):
        if self.doc:
            self.infos.emit(self.doc.image.width(), self.doc.image.height(), self.zoom)

    def resizeEvent(self, e):
        if self.doc and self._ajuste:
            self.ajuster()
        super().resizeEvent(e)

    # ---------------------------------------------------------- dessin
    def _pixmap_reduite(self):
        """Image réduite et lissée, mise en cache, quand le zoom est < 100 %."""
        vue = self.doc.image_affichee()                  # avec l'aperçu d'impression s'il est allumé
        cle = (vue.cacheKey(), round(self.zoom, 4))
        if self._cache is None or self._cache[0] != cle:
            w = max(1, round(vue.width() * self.zoom))
            h = max(1, round(vue.height() * self.zoom))
            self._cache = (cle, QPixmap.fromImage(vue.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)))
        return self._cache[1]

    def paintEvent(self, _):
        self.vue_peinte.emit()
        p = QPainter(self)
        p.fillRect(self.rect(), self.couleur_fond)
        if self.doc and self.angle_vue:                # rotation de la vue : tout le dessin tourne
            p.setTransform(self._transfo_vue())
        if not self.doc:
            p.setPen(self.couleur_texte)
            p.drawText(self.rect(), Qt.AlignCenter, tr("Fichier > Ouvrir…  (ou glisse une photo ici)"))
            return
        # damier sous la photo : les zones transparentes des calques se voient
        photo = QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                              self.doc.image.height()) * self.zoom)
        p.fillRect(photo, QBrush(self._damier()))
        if self.zoom < 1:
            p.drawPixmap(self.decalage, self._pixmap_reduite())
        else:
            p.save()
            p.setTransform(QTransform(self.zoom, 0, 0, self.zoom, self.decalage.x(), self.decalage.y()), True)
            p.drawImage(QPointF(0, 0), self.doc.image_affichee())
            p.restore()
        if self.comparer:
            self._dessiner_avant(p, photo)
            return
        # sélection (calque rouge semi-transparent)
        p.save()
        p.setTransform(QTransform(self.zoom, 0, 0, self.zoom, self.decalage.x(), self.decalage.y()), True)
        p.setOpacity(OPACITE_SELECTION)
        if self.apercu_plein is not None:
            p.setOpacity(1)
            p.drawImage(QRectF(0, 0, self.doc.image.width(), self.doc.image.height()), self.apercu_plein)
        elif self.apercu_selection is not None:
            p.drawImage(QRectF(0, 0, self.doc.image.width(), self.doc.image.height()), self.apercu_selection)
        elif not (self._trace and self._nouvelle):   # nouvelle sélection en cours : l'ancienne va disparaître
            p.drawImage(QPointF(0, 0), self.doc.selection)
        p.setOpacity(1)
        if self.indice_effacer is not None:
            p.drawImage(QPointF(0, 0), self.indice_effacer)
        self._dessiner_auto(p)
        # tracé en cours
        if self._trace and self.outil in FORMES_SELECTION:
            stylo = QPen(QColor(255, 255, 255), 0, Qt.DashLine)
            stylo.setCosmetic(True)
            p.setPen(stylo)
            if self.outil == RECTANGLE:
                p.drawRect(QRectF(self._trace[0], self._trace[-1]).normalized())
            elif self.outil == ELLIPSE_SEL:
                p.drawEllipse(QRectF(self._trace[0], self._trace[-1]).normalized())
            else:
                chemin = QPainterPath(self._trace[0])
                for pt in self._trace[1:]:
                    chemin.lineTo(pt)
                p.drawPath(chemin)
        p.restore()
        self._dessiner_poly(p)
        regles.dessiner(p, self)
        if self.cadre is not None:
            self._dessiner_cadre(p)
            return
        # contour de l'image
        p.setPen(QColor(0, 0, 0, 60))
        p.drawRect(QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                                 self.doc.image.height()) * self.zoom))
        if self.style_ouvert:
            self._dessiner_poignee_sol(p)
            return
        self._dessiner_cadre_texte(p)
        if self.transfo is not None:
            self._dessiner_transfo(p)
            return
        self._dessiner_cadre_hors(p)
        if self.persp is not None:
            self._dessiner_persp(p)
            return
        self._dessiner_cadre_deplacer(p)
        self._dessiner_plus(p)
        if self.outil == PLUME:
            self._dessiner_plume(p)
        if self.outil == RECADRER and self.recadre is not None:
            self._dessiner_recadre(p)
        if self._glisse_dessin is not None:
            self._dessiner_glisse(p)
        if self.outil in (TAMPON, CORRECTEUR) and self.source_tampon is not None and not self._espace:
            if self._trait is not None and self._souris is not None:
                croix = self._souris + self._decalage_tampon * self.zoom
            elif self._trait is None and self._decalage_tampon is not None and self._souris is not None:
                croix = self._souris + self._decalage_tampon * self.zoom
            else:
                croix = self.vers_ecran(self.source_tampon)
            for couleur, epaisseur in ((QColor(0, 0, 0), 3), (QColor(255, 255, 255), 1)):
                p.setPen(QPen(couleur, epaisseur))
                p.drawLine(croix + QPointF(-8, 0), croix + QPointF(8, 0))
                p.drawLine(croix + QPointF(0, -8), croix + QPointF(0, 8))
        # curseur du pinceau
        if self._souris is not None and self.outil in OUTILS_ROND and not self._espace and self.cadre is None:
            r = self.taille_pinceau * self.zoom / 2
            p.setPen(QPen(QColor(0, 0, 0), 3))
            p.drawEllipse(self._souris, r, r)
            p.setPen(QPen(QColor(255, 255, 255), 1))
            p.drawEllipse(self._souris, r, r)

    # ---------------------------------------------------------- Agrandir : deux cadres à poignées
    # Cadre extérieur (accent, poignées carrées) : jusqu'où agrandir, en px ajoutés par côté.
    # Cadre intérieur (rouge, poignées rondes) : limite de la partie saine ; la bande entre ce cadre et le bord
    # de la photo est « abîmée » : elle est jetée et redessinée par l'IA avec l'agrandissement.
    # Ordre des valeurs partout : (haut, bas, gauche, droite).
    def commencer_cadre(self, abime=(0, 0, 0, 0), base=None):
        """base : (x0, y0, x1, y1) de la partie d'où part le cadre (la photo, quand du vide l'entoure)."""
        self.base_cadre = tuple(base) if base is not None else None
        self.cadre = [0, 0, 0, 0]
        self.abime = [int(v) for v in abime]
        self._poignee = None
        self.ajuster()
        self.setCursor(Qt.ArrowCursor)
        self.setFocus()
        self._emettre_cadre()
        self._gestes_depart()

    def definir_cadre(self, ajout, abime):
        """Valeurs venant des cases de la barre (sans changer le zoom)."""
        if self.cadre is not None:
            self.cadre = [int(v) for v in ajout]
            self.abime = [int(v) for v in abime]
            self.update()

    def finir_cadre(self):
        self.cadre = None
        self._poignee = None
        self._curseur()
        self.ajuster()
        self.travail_change.emit()

    # ---------------------------------------------------------- gestes d'un travail pas encore validé
    def travail(self) -> str | None:
        """Travail en cours, pas encore validé : « transfo », « cadre » (Agrandir), « recadre », « persp » ou None."""
        if self.transfo is not None:
            return "transfo"
        if self.persp is not None:
            return "persp"
        if self.cadre is not None:
            return "cadre"
        if self.outil == RECADRER and self.recadre is not None:
            return "recadre"
        return None

    def _etat_travail(self):
        k = self.travail()
        if k == "transfo":
            t = self.transfo
            return (k, QPointF(t.centre), t.sx, t.sy, t.angle, t.mode,
                    tuple(QPointF(c) for c in t.quad) if t.quad is not None else None,
                    tuple(QPointF(c) for c in t.maille) if t.maille is not None else None)
        if k == "persp":
            return k, tuple(QPointF(c) for c in self.persp)
        if k == "cadre":
            return k, tuple(self.cadre), tuple(self.abime)
        if k == "recadre":
            return k, QRectF(self.recadre)
        return None

    def _gestes_depart(self):
        self._gestes, self._refaits = [], []
        self._etat_fixe = self._etat_travail()
        self.travail_change.emit()

    def noter_geste(self):
        """Fin d'un geste (souris lâchée, valeur tapée) : l'état d'avant est gardé pour revenir en arrière."""
        e = self._etat_travail()
        if e is None:
            return
        if self._etat_fixe is None or self._etat_fixe[0] != e[0]:
            self._gestes_depart()
        elif e != self._etat_fixe:
            self._gestes.append(self._etat_fixe)
            self._refaits.clear()
            self._etat_fixe = e
            self.travail_change.emit()

    def peut_refaire_geste(self) -> bool:
        return self.travail() is not None and bool(self._refaits)

    def geste_arriere(self) -> bool:
        """Défait le dernier geste du travail en cours ; au début du travail, l'abandonne. False : pas de travail."""
        k = self.travail()
        if k is None:
            return False
        self.noter_geste()
        if self._gestes:
            self._refaits.append(self._etat_fixe)
            self._remettre(self._gestes.pop())
        elif k == "transfo":
            self.transfo_annule.emit()
        elif k == "persp":
            self.persp_annule.emit()
        elif k == "cadre":
            self.cadre_annule.emit()
        else:
            self.annuler_recadre()
        self.travail_change.emit()
        return True

    def geste_avant(self) -> bool:
        """Refait le geste défait. False : pas de travail en cours."""
        if self.travail() is None:
            return False
        self.noter_geste()
        if self._refaits:
            self._gestes.append(self._etat_fixe)
            self._remettre(self._refaits.pop())
            self.travail_change.emit()
        return True

    def _remettre(self, e):
        self._etat_fixe = e
        if e[0] == "transfo":
            t = self.transfo
            t.centre = QPointF(e[1])
            t.sx, t.sy, t.angle, t.mode = e[2], e[3], e[4], e[5]
            t.quad = [QPointF(c) for c in e[6]] if e[6] is not None else None
            t.maille = [QPointF(c) for c in e[7]] if e[7] is not None else None
            self._apercu_transfo(lisse=True)
            self.transfo_change.emit()
        elif e[0] == "persp":
            self.persp = [QPointF(c) for c in e[1]]
            self.update()
        elif e[0] == "cadre":
            self.cadre, self.abime = list(e[1]), list(e[2])
            self._emettre_cadre()
        else:
            self.recadre = QRectF(e[1])
            self._emettre_recadre()
        self.update()

    def _emettre_cadre(self):
        self.cadre_change.emit(tuple(self.cadre), tuple(self.abime))

    def _base(self) -> tuple:
        """(x0, y0, x1, y1) d'où part le cadre : la photo sans le vide autour, ou toute l'image."""
        return self.base_cadre or (0, 0, self.doc.image.width(), self.doc.image.height())

    def _depasse(self) -> tuple:
        """Ce que le cadre dépasse de l'image (haut, bas, gauche, droite), en px."""
        x0, y0, x1, y1 = self._base()
        h, b, g, d = self.cadre
        iw, ih = self.doc.image.width(), self.doc.image.height()
        return max(0, h - y0), max(0, b - (ih - y1)), max(0, g - x0), max(0, d - (iw - x1))

    def _rect_cadre(self) -> QRectF:
        """Cadre extérieur (photo + ajouts) en coordonnées écran."""
        h, b, g, d = self.cadre
        x0, y0, x1, y1 = self._base()
        return QRectF(self.vers_ecran(QPointF(x0 - g, y0 - h)), self.vers_ecran(QPointF(x1 + d, y1 + b)))

    def _rect_sain(self) -> QRectF:
        """Cadre intérieur (partie saine de la photo) en coordonnées écran."""
        h, b, g, d = self.abime
        x0, y0, x1, y1 = self._base()
        return QRectF(self.vers_ecran(QPointF(x0 + g, y0 + h)), self.vers_ecran(QPointF(x1 - d, y1 - b)))

    @staticmethod
    def _cotes_sous(r: QRectF, pos: QPointF, tol: float = 10) -> set:
        if not r.adjusted(-tol, -tol, tol, tol).contains(pos):
            return set()
        cotes = set()
        if abs(pos.y() - r.top()) <= tol:
            cotes.add("h")
        elif abs(pos.y() - r.bottom()) <= tol:
            cotes.add("b")
        if abs(pos.x() - r.left()) <= tol:
            cotes.add("g")
        elif abs(pos.x() - r.right()) <= tol:
            cotes.add("d")
        return cotes

    def _poignee_sous(self, pos: QPointF):
        """(cible, côtés) : cible « ext », « int », ou « ? » si les deux cadres se touchent à cet endroit
        (on choisit alors au premier mouvement : vers l'extérieur = agrandir, vers l'intérieur = bord abîmé)."""
        ext = self._cotes_sous(self._rect_cadre(), pos)
        sain = self._cotes_sous(self._rect_sain(), pos)
        if ext and sain:
            return ("?", ext)
        if ext:
            return ("ext", ext)
        if sain:
            return ("int", sain)
        return None

    def _curseur_cadre(self, poignee):
        cotes = poignee[1] if poignee else set()
        if cotes in ({"h", "g"}, {"b", "d"}):
            self.setCursor(Qt.SizeFDiagCursor)
        elif cotes in ({"h", "d"}, {"b", "g"}):
            self.setCursor(Qt.SizeBDiagCursor)
        elif cotes & {"h", "b"}:
            self.setCursor(Qt.SizeVerCursor)
        elif cotes:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.OpenHandCursor if self.outil in (MAIN, ROTATION_VUE) else Qt.ArrowCursor)

    def _tirer_cadre(self, pos: QPointF, symetrique: bool):
        pt = self.vers_image(pos)
        x0, y0, x1, y1 = self._base()
        iw, ih = x1 - x0, y1 - y0
        W, H = self.doc.image.width(), self.doc.image.height()
        vide = {"h": y0, "b": H - y1, "g": x0, "d": W - x1}     # vide entre la photo et le bord de l'image
        cible, cotes = self._poignee
        # vecteur « vers l'extérieur » de chaque côté, en px image (positif = on sort de la photo)
        dehors = {"h": y0 - pt.y(), "b": pt.y() - y1, "g": x0 - pt.x(), "d": pt.x() - x1}
        if cible == "?":
            depart = self._depart
            dep = {"h": y0 - depart.y(), "b": depart.y() - y1, "g": x0 - depart.x(), "d": depart.x() - x1}
            cote = next(iter(cotes))
            if abs(dehors[cote] - dep[cote]) < 2 / self.zoom:
                return                                   # pas encore assez bougé pour décider
            cible = "ext" if dehors[cote] > dep[cote] else "int"
            self._poignee = (cible, cotes)
        index = {"h": 0, "b": 1, "g": 2, "d": 3}
        oppose = {"h": "b", "b": "h", "g": "d", "d": "g"}
        taille = {"h": ih, "b": ih, "g": iw, "d": iw}
        for cote in cotes:
            n = taille[cote]
            if cible == "ext":   # agrandir : de 0 à 200 % de la photo (au-delà du vide qui l'entoure)
                v = int(max(0, min(2 * n + vide[cote], round(dehors[cote]))))
                if vide[cote] and abs(v - vide[cote]) <= 8 / self.zoom:
                    v = vide[cote]                       # aimant : juste jusqu'au bord de l'image
                self.cadre[index[cote]] = v
                if symetrique:
                    self.cadre[index[oppose[cote]]] = v
            else:                # bord abîmé : on garde au moins 32 px de photo saine
                autre = 0 if symetrique else self.abime[index[oppose[cote]]]
                maxi = (n - 32) // 2 if symetrique else n - autre - 32
                v = int(max(0, min(maxi, round(-dehors[cote]))))
                self.abime[index[cote]] = v
                if symetrique:
                    self.abime[index[oppose[cote]]] = v
        self._emettre_cadre()
        self.update()

    def _dessiner_cadre(self, p: QPainter):
        r = self._rect_cadre()
        sain = self._rect_sain()
        x0, y0, x1, y1 = self._base()
        photo = QRectF(self.vers_ecran(QPointF(x0, y0)), self.vers_ecran(QPointF(x1, y1)))
        image = QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                              self.doc.image.height()) * self.zoom)

        def chemin(rect: QRectF) -> QPainterPath:
            c = QPainterPath()
            c.addRect(rect)
            return c
        # zone ajoutée : damier gris (comme une zone vide)
        damier = QPixmap(16, 16)
        damier.fill(QColor(205, 205, 205))
        pd = QPainter(damier)
        pd.fillRect(0, 0, 8, 8, QColor(240, 240, 240))
        pd.fillRect(8, 8, 8, 8, QColor(240, 240, 240))
        pd.end()
        p.fillPath(chemin(r).subtracted(chemin(photo)), QBrush(damier))
        if self.base_cadre is not None:          # bord de l'image : repère pour l'aimant
            p.setPen(QPen(QColor(255, 255, 255, 140), 1, Qt.DotLine))
            p.drawRect(image)
        # bord abîmé : rouge hachuré (sera redessiné)
        bande = chemin(photo).subtracted(chemin(sain))
        p.fillPath(bande, QColor(230, 40, 40, 90))
        p.fillPath(bande, QBrush(QColor(255, 255, 255, 120), Qt.BDiagPattern))
        # cadre intérieur (rouge, pointillés) et extérieur (accent, pointillés)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawRect(r)
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawRect(r)
        if sain != photo:
            p.setPen(QPen(QColor(230, 40, 40), 2, Qt.DashLine))
            p.drawRect(sain)

        def points(rect):
            c = rect.center()
            return [rect.topLeft(), QPointF(c.x(), rect.top()), rect.topRight(), QPointF(rect.right(), c.y()),
                    rect.bottomRight(), QPointF(c.x(), rect.bottom()), rect.bottomLeft(), QPointF(rect.left(), c.y())]
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for pt in points(r):
            p.drawRect(QRectF(pt.x() - 5, pt.y() - 5, 10, 10))
        p.setPen(QPen(QColor(255, 255, 255), 1.5))
        p.setBrush(QColor(230, 40, 40))
        for pt in points(sain):
            p.drawEllipse(pt, 4.5, 4.5)

    # ---------------------------------------------------------- outil Texte
    def _texte_actif(self):
        """Réglages du calque choisi s'il est un texte visible, sinon None."""
        c = self.doc.calque_actif if self.doc else None
        return c.texte if c is not None and c.texte is not None and c.visible else None

    def _texte_sous(self, pt: QPointF):
        """Index du calque de texte visible le plus haut sous le point (image), ou None."""
        for i in range(len(self.doc.calques) - 1, -1, -1):
            c = self.doc.calques[i]
            if c.visible and c.texte is not None and contient(c.texte, pt):
                return i
        return None

    def _cadre_texte_ecran(self, t):
        """(polygone du bloc à l'écran, milieu du haut, poignée de rotation) pour le texte t."""
        ecran = QPolygonF([self.vers_ecran(pt) for pt in contour_bloc(t)])
        haut = (ecran[0] + ecran[1]) / 2
        v = QLineF(self.vers_ecran(QPointF(t.x, t.y)), haut)
        if v.length() < 1:
            return ecran, haut, haut + QPointF(0, -28)
        v.setLength(v.length() + 28)
        return ecran, haut, v.p2()

    def _dessiner_cadre_texte(self, p: QPainter):
        if self.outil != TEXTE or self.cadre is not None:
            return
        if self._trace_points:                      # tracé en train d'être dessiné
            p.save()
            p.setRenderHint(QPainter.Antialiasing)
            ligne = QPolygonF([self.vers_ecran(q) for q in self._trace_points])
            p.setPen(QPen(QColor(0, 0, 0, 150), 3))
            p.drawPolyline(ligne)
            p.setPen(QPen(self.couleur_accent, 1.5))
            p.drawPolyline(ligne)
            p.restore()
        t = self._texte_actif()
        if t is None:
            return
        ecran, haut, poignee = self._cadre_texte_ecran(t)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        a, b = self.selection_lettres
        if b > a:                                   # lettres sélectionnées dans la saisie : surlignées
            from .texte import zones_lettres
            fond = QColor(self.couleur_accent)
            fond.setAlpha(90)
            p.setPen(Qt.NoPen)
            p.setBrush(fond)
            for z in zones_lettres(t, a, b):
                p.drawPolygon(QPolygonF([self.vers_ecran(q) for q in z]))
        if t.trace and not self._trace_points:      # le tracé du texte, en pointillés
            tr_ = transformation(t)
            ligne = QPolygonF([self.vers_ecran(tr_.map(QPointF(x, y))) for x, y in t.trace])
            p.setPen(QPen(self.couleur_accent, 1, Qt.DotLine))
            p.drawPolyline(ligne)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 150), 1))
        p.drawPolygon(ecran)
        p.setPen(QPen(self.couleur_accent, 1.5, Qt.DashLine))
        p.drawPolygon(ecran)
        if not self.doc.calque_actif.verrou:
            p.setPen(QPen(self.couleur_accent, 1.5))
            p.drawLine(haut, poignee)
            p.setPen(QPen(QColor(255, 255, 255), 1.5))
            p.setBrush(self.couleur_accent)
            p.drawEllipse(poignee, 6, 6)
        p.restore()

    def _etendue_calque(self, c):
        """Polygone (image) autour du contenu du calque, s'il dépasse de la feuille ; sinon None. Gardé en mémoire
        tant que le calque ne change pas."""
        if c.texte is not None:
            poly = contour_bloc(c.texte)
        elif c.hors is not None and not c.groupe and c.reglage is None:
            cle = (id(c.image), id(c.hors), c.hors_x, c.hors_y)
            memoire = self.__dict__.setdefault("_etendues", {})     # par calque : (clé, rectangle du contenu)
            vu = memoire.get(id(c))
            if vu is None or vu[0] != cle:
                import numpy as np
                img, x, y = image_entiere(c)
                a = tableau(img)[..., 3]
                lignes, colonnes = np.where(a.any(axis=1))[0], np.where(a.any(axis=0))[0]
                vu = (cle, None if len(lignes) == 0 else
                      QRectF(x + colonnes[0], y + lignes[0], colonnes[-1] - colonnes[0] + 1, lignes[-1] - lignes[0] + 1))
                if len(memoire) > 200:
                    memoire.clear()
                memoire[id(c)] = vu
            if vu[1] is None:
                return None
            poly = QPolygonF(vu[1])
        else:
            return None
        feuille = QRectF(0, 0, self.doc.image.width(), self.doc.image.height())
        return None if feuille.contains(poly.boundingRect()) else poly

    def _dessiner_cadre_hors(self, p: QPainter):
        """Textes, et calques qui dépassent de la feuille (image, forme…) : cadre en pointillés autour de chacun, avec
        tous les outils, pour voir où ils sont ; gris pour les autres calques, couleur d'accent pour le calque choisi
        (l'outil Texte a déjà son cadre pour le texte choisi)."""
        if self.doc is None or self.cadre is not None:
            return
        actif = self.doc.actif
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.NoBrush)
        for i, c in enumerate(self.doc.calques):
            if not c.visible or c.special or (i == actif and self.outil == TEXTE and c.texte is not None):
                continue
            try:
                # un texte a toujours son cadre (même dans la feuille) : on voit où sont les textes
                poly = contour_bloc(c.texte) if c.texte is not None else self._etendue_calque(c)
            except Exception:
                continue
            if poly is None:
                continue
            ecran = QPolygonF([self.vers_ecran(q) for q in poly])
            if c.texte is not None and ecran.size() > 2:     # un peu écarté du texte (et de son fond éventuel)
                centre = ecran.boundingRect().center()
                ecart = []
                for q in ecran:
                    d = q - centre
                    n = max(1e-6, (d.x() ** 2 + d.y() ** 2) ** 0.5)
                    ecart.append(q + d * (6 / n))
                ecran = QPolygonF(ecart)
            if i == actif:
                p.setPen(QPen(QColor(0, 0, 0, 150), 1))
                p.drawPolygon(ecran)
                p.setPen(QPen(self.couleur_accent, 1.5, Qt.DashLine))
            else:
                p.setPen(QPen(QColor(255, 255, 255, 140), 1))
                p.drawPolygon(ecran)
                p.setPen(QPen(QColor(90, 90, 90, 200), 1, Qt.DashLine))
            p.drawPolygon(ecran)
        p.restore()

    def _sur_poignee_texte(self, pos: QPointF) -> bool:
        t = self._texte_actif()
        if t is None or self.doc.calque_actif.verrou:
            return False
        return QLineF(pos, self._cadre_texte_ecran(t)[2]).length() <= 10

    def _sur_bord_texte(self, pos: QPointF) -> bool:
        """Souris sur le bord en pointillés du texte choisi (à 8 px près) : on le déplace en glissant."""
        t = self._texte_actif()
        if t is None:
            return False
        ecran = self._cadre_texte_ecran(t)[0]
        n = ecran.size()
        return any(_distance_segment(pos, ecran[k], ecran[(k + 1) % n]) <= 8 for k in range(n))

    def _presser_texte(self, pos: QPointF, ctrl: bool = False):
        pt = self.vers_image(pos)
        if self.trace_texte and self._texte_actif() is not None and not self.doc.calque_actif.verrou:
            self._trace_points = [pt]               # dessiner le tracé du texte
            return
        if self._sur_poignee_texte(pos):
            index, mode = self.doc.actif, "tourner"
        elif self._sur_bord_texte(pos):
            index, mode = self.doc.actif, "deplacer"
        else:
            index, mode = self._texte_sous(pt), "deplacer"
            if index is None:
                self.texte_nouveau.emit(pt)
                return
            self.texte_choisi.emit(index)
            if not ctrl:                            # sur les lettres : choisir des lettres (Ctrl : déplacer)
                from .texte import boites_lettres, index_lettre
                t = self.doc.calques[index].texte
                boites = boites_lettres(t)
                ancre = index_lettre(t, pt, boites)
                self._lettres_glisse = (index, t, boites, ancre)
                self.lettres_choisies.emit(ancre, ancre)
                return
        c = self.doc.calques[index]
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return
        self._texte_glisse = (index, mode, pt, c.texte, self.doc.etat())

    def _glisser_texte(self, pos: QPointF, magnetique: bool):
        index, mode, depart, t0, _ = self._texte_glisse
        pt = self.vers_image(pos)
        if mode == "deplacer":
            t = t0.deplace(pt.x() - depart.x(), pt.y() - depart.y())
        else:
            angle = math.degrees(math.atan2(pt.y() - t0.y, pt.x() - t0.x)) + 90
            if magnetique:                       # Maj : par pas de 15°
                angle = round(angle / 15) * 15
            angle = (angle + 180) % 360 - 180
            t = replace(t0, angle=round(angle, 1))
        w, h = self.doc.taille()
        self.doc.apercu_calque(index, rendre(t, w, h), texte=t)

    def _lacher_texte(self):
        index, mode, _, t0, avant = self._texte_glisse
        self._texte_glisse = None
        if self.doc.calques[index].texte != t0:
            self.selection_modifiee.emit(avant, tr("Déplacer le texte") if mode == "deplacer"
                                         else tr("Tourner le texte"))

    # ---------------------------------------------------------- outil Déplacer
    # ---------------------------------------------------------- déplacer un groupe ou plusieurs calques
    def _a_deplacer(self) -> list[int]:
        """Calques que l'outil Déplacer bouge : le calque choisi ; un groupe -> tout son contenu ; plusieurs calques
        choisis dans le panneau -> tous (groupes compris)."""
        doc = self.doc
        choisis = set(self.calques_choisis())
        # le choix du panneau ne compte que s'il contient le calque actif (sinon il date d'avant : calque choisi
        # autrement, autre image…) ; sinon seul le calque actif bouge
        depart = choisis if doc.actif in choisis else {doc.actif}
        depart = {i for i in depart if 0 <= i < len(doc.calques)}
        idents, changement = set(), True
        for i in depart:
            if doc.calques[i].groupe:
                idents.add(doc.calques[i].ident)
        while changement:                                  # groupes dans les groupes
            changement = False
            for c in doc.calques:
                if c.groupe and c.dans in idents and c.ident not in idents:
                    idents.add(c.ident)
                    changement = True
        return sorted(i for i, c in enumerate(doc.calques)
                      if (i in depart or c.dans in idents) and not c.groupe and c.reglage is None)

    def _lot_debut(self, indexes: list[int]):
        lot = []
        for i in indexes:
            c = self.doc.calques[i]
            lot.append((i, "texte", c.texte) if c.texte is not None else (i, "calque", image_entiere(c)))
        return lot

    def _lot_apercu(self, lot, dx: int, dy: int):
        w, h = self.doc.taille()
        for i, genre, origine in lot:
            if genre == "texte":
                t = origine.deplace(dx, dy)
                self.doc.apercu_calque(i, rendre(t, w, h), texte=t)
            else:
                image, x, y = origine
                nouvelle = QImage(w, h, image.format())
                nouvelle.fill(Qt.transparent)
                p = QPainter(nouvelle)
                p.drawImage(x + dx, y + dy, image)
                p.end()
                self.doc.apercu_calque(i, nouvelle)

    def _lot_fin(self, lot, dx: int, dy: int, avant):
        if (dx, dy) == (0, 0):
            return
        for i, genre, origine in lot:
            if genre == "calque":
                image, x, y = origine
                self.doc.apercu_calque_entier(i, image, x + dx, y + dy, avant=avant[0][i], decalage=(dx, dy))
        self.selection_modifiee.emit(avant, tr("Déplacer les calques"))

    def _lot_verrou(self, indexes) -> bool:
        for i in indexes:
            c = self.doc.calques[i]
            if c.verrou:
                self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                                   "modifier.", nom=c.nom))
                return True
        return False

    def _presser_deplacer(self, pos: QPointF):
        lot = self._a_deplacer()
        if len(lot) > 1 or (lot and self.doc.calque_actif.groupe):
            if not self._lot_verrou(lot):
                self._lot_glisse = (self._lot_debut(lot), self.vers_image(pos), self.doc.etat())
                self._decalage_calque = (0, 0)
            return
        if self.doc.calque_actif.groupe:
            return
        c = self.doc.calque_actif
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return
        if c.texte is not None:              # un texte se déplace comme avec l'outil Texte (il reste modifiable)
            self._texte_glisse = (self.doc.actif, "deplacer", self.vers_image(pos), c.texte, self.doc.etat())
            return
        # le calque entier (même ce qui dépasse de la feuille) : rien n'est coupé en le déplaçant
        self._calque_glisse = (self.doc.actif, self.vers_image(pos), image_entiere(c), self.doc.etat())
        self._decalage_calque = (0, 0)

    def _glisser_calque(self, pos: QPointF):
        index, depart, (image, x, y), _ = self._calque_glisse
        pt = self.vers_image(pos)
        dx, dy = round(pt.x() - depart.x()), round(pt.y() - depart.y())
        w, h = self.doc.taille()
        nouvelle = QImage(w, h, image.format())
        nouvelle.fill(Qt.transparent)
        p = QPainter(nouvelle)
        p.drawImage(x + dx, y + dy, image)
        p.end()
        self.doc.apercu_calque(index, nouvelle)
        self._decalage_calque = (dx, dy)

    def _lacher_calque(self):
        index, _depart, (image, x, y), avant = self._calque_glisse
        self._calque_glisse = None
        dx, dy = getattr(self, "_decalage_calque", (0, 0))
        if (dx, dy) != (0, 0):
            self.doc.apercu_calque_entier(index, image, x + dx, y + dy,      # ce qui sort de la feuille est gardé
                                          avant=avant[0][index], decalage=(dx, dy))
            self.selection_modifiee.emit(avant, tr("Déplacer le calque"))
        self._decalage_calque = (0, 0)

    # ---------------------------------------------------------- outil Déplacer aux flèches (1 px, Maj : 10 px)
    def pousser(self, dx: int, dy: int) -> None:
        """Pousse le calque choisi (ou le texte) ; touche tenue = une seule étape dans Annuler (finie au lâcher)."""
        c = self.doc.calque_actif
        if self._fleches is not None and self._fleches[1] != self.doc.actif:
            self.finir_fleches()
        if self._fleches is None:
            lot = self._a_deplacer()
            if len(lot) > 1 or (lot and c.groupe):
                if self._lot_verrou(lot):
                    return
                self._fleches = ("lot", self.doc.actif, self._lot_debut(lot), self.doc.etat(), [0, 0])
            elif c.groupe:
                return
        if self._fleches is None:
            if c.verrou:
                self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                                   "modifier.", nom=c.nom))
                return
            if c.texte is not None:
                self._fleches = ("texte", self.doc.actif, c.texte, self.doc.etat(), [0, 0])
            else:
                self._fleches = ("calque", self.doc.actif, image_entiere(c), self.doc.etat(), [0, 0])
        genre, index, origine, _avant, dec = self._fleches
        dec[0] += dx
        dec[1] += dy
        w, h = self.doc.taille()
        if genre == "lot":
            self._lot_apercu(origine, dec[0], dec[1])
        elif genre == "texte":
            t = origine.deplace(dec[0], dec[1])
            self.doc.apercu_calque(index, rendre(t, w, h), texte=t)
        else:
            image, x, y = origine
            nouvelle = QImage(w, h, image.format())
            nouvelle.fill(Qt.transparent)
            p = QPainter(nouvelle)
            p.drawImage(x + dec[0], y + dec[1], image)
            p.end()
            self.doc.apercu_calque(index, nouvelle)
        self.update()

    def finir_fleches(self) -> None:
        if self._fleches is None:
            return
        genre, index, origine, avant, (dx, dy) = self._fleches
        self._fleches = None
        if index >= len(self.doc.calques):
            return
        if genre == "lot":
            self._lot_fin(origine, dx, dy, avant)
        elif genre == "texte":
            if self.doc.calques[index].texte != origine:
                self.selection_modifiee.emit(avant, tr("Déplacer le texte"))
        elif (dx, dy) != (0, 0):
            image, x, y = origine
            self.doc.apercu_calque_entier(index, image, x + dx, y + dy, avant=avant[0][index], decalage=(dx, dy))
            self.selection_modifiee.emit(avant, tr("Déplacer le calque"))

    # ---------------------------------------------------------- pinceau de couleur et tampon
    def _presser_retouche(self, pos: QPointF, alt: bool):
        pt = self.vers_image(pos)
        if alt and self.outil in (PEINTURE, CRAYON, MELANGEUR):   # pipette : couleur de la photo visible
            x, y = int(pt.x()), int(pt.y())
            if 0 <= x < self.doc.image.width() and 0 <= y < self.doc.image.height():
                self.couleur_prise.emit(QColor(self.doc.image.pixel(x, y)).name())
            return
        if self.masque_rapide and self._presser_masque_rapide(pt):
            return
        if alt and self.outil in (TAMPON, CORRECTEUR):   # point source
            self.source_tampon = pt
            self._decalage_tampon = None
            self.message.emit(tr("Endroit à copier choisi : peins maintenant là où il doit être recopié."))
            self.update()
            return
        c = self.doc.calque_actif
        if (self.outil == PEINTURE and self.calque_pinceau and not self.sur_masque()
                and calque_pinceau.valide(c) is None):
            self._commencer_calque_pinceau(pt)        # nouveau calque de pinceau : le calque choisi n'est pas touché
            return
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return
        if self.outil in (TAMPON, CORRECTEUR) and self.source_tampon is None:
            self.refus.emit(tr("Fais d'abord Alt+clic sur l'endroit à copier."))
            return
        if self.refus_special():
            return
        self._sur_masque = self.sur_masque()
        if self._sur_masque:
            if self.outil not in (PEINTURE, GOUTTE):
                self.refus.emit(tr("Sur un masque, peins avec le pinceau de couleur (noir cache, blanc montre) "
                                   "ou la gomme de calque (cache) ; la goutte d'eau adoucit le bord du masque."))
                return
            if self.outil == GOUTTE:
                self._avant = self.doc.etat()
                self._trait = Trait("goutte", masque_vers_argb(c.masque), self.taille_pinceau, self.durete,
                                    self.opacite)
                self._trait.ajouter(pt, self._pression_evt)
                self.doc.apercu_masque(self.doc.actif, argb_vers_masque(self._trait.image))
                return
            self._avant = self.doc.etat()
            gris = round(QColor(self.couleur_peinture).lightnessF() * 255)
            self._trait = Trait("peinture", masque_vers_argb(c.masque), self.taille_pinceau, self.durete,
                                self.opacite, couleur=QColor(gris, gris, gris), **self.parametres_pinceau(PEINTURE))
            self._trait.ajouter(pt, self._pression_evt)
            self.doc.apercu_masque(self.doc.actif, argb_vers_masque(self._trait.image))
            return
        if c.texte is not None:
            self.refus.emit(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme texte "
                               "(Ctrl+Z pour revenir).", nom=c.nom))
        p = calque_pinceau.valide(c)
        if p is not None and self.outil == PEINTURE and self.calque_pinceau:
            self._avant = self.doc.etat()
            self._trait_pinceau(p, pt)                 # un trait de plus dans le calque de pinceau
            return
        from .document import vectoriel
        if p is not None or vectoriel(c):
            self.refus.emit(self.texte_devient_image(c))
        self._avant = self.doc.etat()
        if self.outil in MODES_TRAIT:
            self._trait = Trait(MODES_TRAIT[self.outil], c.image, self.taille_pinceau, self.durete, self.opacite,
                                gamme=self.gamme_densite, saturer=self.eponge_saturer)
        elif self.outil == HISTORIQUE:
            source = self.source_historique(c) if self.source_historique is not None else None
            if source is None:
                self.refus.emit(tr("Pas d'instantané pour ce calque : clique sur « Prendre un instantané » dans "
                                   "la barre du haut."))
                self._avant = None
                return
            self._trait = Trait("tampon", c.image, self.taille_pinceau, self.durete, self.opacite,
                                source=source, decalage=QPointF(0, 0))
        elif self.outil in (TAMPON, CORRECTEUR):
            if self._decalage_tampon is None:
                self._decalage_tampon = self.source_tampon - pt
            self._trait = Trait("tampon", c.image, self.taille_pinceau, self.durete, self.opacite,
                                source=self.doc.image_profonde().copy(), decalage=self._decalage_tampon)
        elif self.outil == TAMPON_MOTIF:
            # le motif, répété depuis le coin de l'image : chaque trait se raccorde aux précédents
            from .motifs import DEFAUT, image_pavee
            source = image_pavee(self.motif_cle or DEFAUT, c.image.width(), c.image.height(), self.motif_echelle)
            if source is None:
                self.refus.emit(tr("Aucun motif trouvé : choisis-en un dans la barre du haut."))
                self._avant = None
                return
            self._trait = Trait("tampon", c.image, self.taille_pinceau, self.durete, self.opacite,
                                source=source, decalage=QPointF(0, 0))
        elif self.outil == CRAYON:                       # trait net, pixel par pixel
            self._trait = Trait("peinture", c.image, self.taille_pinceau, 1.0, self.opacite,
                                couleur=self.couleur_peinture)
            self._trait.net = True
        elif self.outil == MELANGEUR:
            self._trait = Trait("melangeur", c.image, self.taille_pinceau, self.durete, self.opacite,
                                couleur=self.couleur_peinture)
            self._trait.melange = self.melange
        else:
            self._trait = Trait("peinture", c.image, self.taille_pinceau, self.durete, self.opacite,
                                couleur=self.couleur_peinture, **self.parametres_pinceau(PEINTURE))
        if self.outil in (PEINTURE, CRAYON, MELANGEUR) + OUTILS_FILTRE:
            self._trait.miroirs = self.miroirs()        # peinture en symétrie
        self._trait.ajouter(pt, self._pression_evt)
        self.doc.apercu_calque(self.doc.actif, self._trait.image)

    def _commencer_calque_pinceau(self, pt: QPointF):
        """Premier coup avec la case « Calque modifiable » : un calque de pinceau est créé au-dessus du calque
        choisi, avec les réglages de la barre."""
        self._avant = self.doc.etat()
        p = self.pinceau_de_la_barre()
        self.doc.appliquer_etat(self.doc.etat_nouveau_pinceau(p, tr("Pinceau")))
        self._trait_pinceau(self.doc.calque_actif.pinceau, pt)

    def _trait_pinceau(self, p, pt: QPointF):
        graine = calque_pinceau.nouvelle_graine()
        self._pinceau_en_cours = (self.doc.actif, p, graine, [(pt.x(), pt.y(), self._pression_evt)])
        self._trait = Trait("peinture", self.doc.calque_actif.image, p.taille, p.durete, p.opacite,
                            couleur=QColor(p.couleur), graine=graine,
                            **calque_pinceau.parametres(p, self._tablette))
        self._trait.ajouter(pt, self._pression_evt)
        self.doc.apercu_calque(self.doc.actif, self._trait.image)

    def pinceau_de_la_barre(self):
        """Réglages actuels du pinceau de couleur (barre du haut), pour un nouveau calque de pinceau."""
        choix = self.pinceaux["peinture"]
        return calque_pinceau.Pinceau(couleur=QColor(self.couleur_peinture).name(QColor.HexArgb),
                                      taille=float(self.taille_pinceau), durete=self.durete, opacite=self.opacite,
                                      cle=choix["cle"], reglages=choix["reglages"].vers_dict())

    @staticmethod
    def texte_devient_image(c) -> str:
        from . import calque_forme, calque_remplissage
        if calque_remplissage.valide(c) is not None:
            return tr("Le calque de remplissage « {nom} » devient une image : il n'est plus modifiable "
                      "(Ctrl+Z pour revenir).", nom=c.nom)
        if calque_forme.valide(c) is not None:
            return tr("Le calque de forme « {nom} » devient une image : sa forme n'est plus modifiable "
                      "(Ctrl+Z pour revenir).", nom=c.nom)
        return tr("Le calque de pinceau « {nom} » devient une image : ses traits ne sont plus modifiables "
                  "(Ctrl+Z pour revenir).", nom=c.nom)

    def _glisser_retouche(self, pos: QPointF):
        if self._glisser_masque_rapide(pos):
            return
        if self._pinceau_en_cours is not None:
            pt = self.vers_image(pos)
            self._pinceau_en_cours[3].append((pt.x(), pt.y(), self._pression_evt))
        self._trait.ajouter(self.vers_image(pos), self._pression_evt)
        if self._sur_masque:
            self.doc.apercu_masque(self.doc.actif, argb_vers_masque(self._trait.image))
        else:
            self.doc.apercu_calque(self.doc.actif, self._trait.image)

    def sur_masque(self) -> bool:
        """Les outils de peinture travaillent sur le masque du calque (choisi dans le panneau Calques)."""
        return bool(self.doc and self.doc.cible_masque and self.doc.calque_actif.masque is not None)

    def refus_special(self) -> bool:
        """Groupe ou calque de réglage : pas de pixels (seulement son masque)."""
        c = self.doc.calque_actif
        if c.special and not self.sur_masque():
            quoi = tr("un groupe") if c.groupe else tr("un calque de réglage")
            self.refus.emit(tr("« {nom} » est {quoi} : il n'a pas de pixels. Choisis un calque d'image, ou son "
                               "masque.", nom=c.nom, quoi=quoi))
            return True
        return False

    def _lacher_retouche(self):
        if self._lacher_masque_rapide():
            return
        if self._pinceau_en_cours is not None:         # calque de pinceau : le trait est gardé, tout est redessiné
            index, p, graine, points = self._pinceau_en_cours
            self._pinceau_en_cours = None
            self._trait = None
            self.doc.appliquer_etat(self.doc.etat_pinceau(index, p.avec_trait(points, graine)))
            self.selection_modifiee.emit(self._avant, tr("Calque de pinceau"))
            self._avant = None
            return
        nom = tr("Tampon") if self._trait.mode == "tampon" else tr("Pinceau de couleur")
        if self.outil == TAMPON_MOTIF:
            nom = tr("Tampon de motif")
        noms = {DENSITE_MOINS: tr("Densité −"), DENSITE_PLUS: tr("Densité +"), EPONGE: tr("Éponge"),
                GOUTTE: tr("Goutte d'eau"), NETTETE_PINCEAU: tr("Netteté (pinceau)"), DOIGT: tr("Doigt"),
                HISTORIQUE: tr("Pinceau d'historique"), CRAYON: tr("Crayon"), MELANGEUR: tr("Pinceau mélangeur")}
        if self.outil in noms:
            nom = noms[self.outil]
        if self._sur_masque:
            nom = tr("Peindre le masque")
        elif self.outil == CORRECTEUR:
            from .outils_dessin import corriger
            t = self._trait
            img = corriger(t.base, t.source, t.decalage, t.masque, t.opacite)
            self.doc.apercu_calque(self.doc.actif, img)
            nom = tr("Pinceau correcteur")
        self._trait = None
        self.selection_modifiee.emit(self._avant, nom)
        self._avant = None

    # ---------------------------------------------------------- repères
    def commencer_repere(self, sens: str):
        self.repere_tire = [sens, None]
        self.reperes_visibles = True

    def bouger_repere(self, pos: QPointF):
        pt = self.vers_image(QPointF(pos))
        sens = self.repere_tire[0]
        self.repere_tire[1] = round(pt.y() if sens == "h" else pt.x())
        self.update()

    def finir_repere(self, pos: QPointF):
        sens, v = self.repere_tire
        self.repere_tire = None
        W, H = self.doc.image.width(), self.doc.image.height()
        dedans = self.rect().contains(QPointF(pos).toPoint()) and v is not None and \
            0 <= v <= (H if sens == "h" else W)
        if dedans:
            self.doc.reperes.append((sens, v))
        self.update()

    def _repere_a(self, pos: QPointF):
        """Repère sous la souris (à 4 pixels d'écran près), ou None."""
        if not self.reperes_visibles or self.doc is None:
            return None
        for r in self.doc.reperes:
            sens, v = r
            e = self.vers_ecran(QPointF(v, v))
            if (sens == "h" and abs(e.y() - pos.y()) <= 4) or (sens == "v" and abs(e.x() - pos.x()) <= 4):
                return r
        return None

    def _repere_sous(self, pos: QPointF) -> bool:
        """Outil Déplacer sur un repère : on le prend (il sera reposé ou enlevé au lâcher)."""
        r = self._repere_a(pos)
        if r is None:
            return False
        self.doc.reperes.remove(r)
        self.repere_tire = list(r)
        return True

    # ---------------------------------------------------------- dégradé, pot de peinture, formes
    def _cible_image(self):
        """(image où dessiner, sur le masque ?) ; None si refusé (verrou, groupe, réglage)."""
        c = self.doc.calque_actif
        if c.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "modifier.", nom=c.nom))
            return None
        if self.refus_special():
            return None
        if self.sur_masque():
            return masque_vers_argb(c.masque), True
        return c.image, False

    def _couleur_cible(self, couleur: QColor, sur_masque: bool) -> QColor:
        if not sur_masque:
            return QColor(couleur)
        g = round(QColor(couleur).lightnessF() * 255)
        return QColor(g, g, g)

    def _poser_dessin(self, img, sur_masque: bool, nom: str, avant):
        if sur_masque:
            self.doc.apercu_masque(self.doc.actif, argb_vers_masque(img))
        else:
            self.doc.apercu_calque(self.doc.actif, img)
        self.selection_modifiee.emit(avant, nom)

    def _presser_dessin(self, pos: QPointF, mods):
        pt = self.vers_image(pos)
        if self.outil == SEAU:
            if bool(mods & Qt.AltModifier):           # pipette
                x, y = int(pt.x()), int(pt.y())
                if 0 <= x < self.doc.image.width() and 0 <= y < self.doc.image.height():
                    self.couleur_prise.emit(QColor(self.doc.image.pixel(x, y)).name())
                return
            cible = self._cible_image()
            if cible is None:
                return
            img, sur_masque = cible
            from .document import FORMAT_IMAGE, tableau
            from .outils_dessin import seau
            sel = None if self.doc.selection_vide() else self.doc.selection
            avant = self.doc.etat()
            # zone à remplir : d'après le calque choisi (comme Photoshop par défaut), ou l'image visible
            reference = self.doc.image if self.seau_tous_calques else img
            remplissage = None
            if self.seau_motif:
                from .motifs import DEFAUT, image_pavee
                remplissage = image_pavee(self.motif_cle or DEFAUT, img.width(), img.height(), self.motif_echelle,
                                          gris=sur_masque)
            res = seau(img, tableau(reference.convertToFormat(FORMAT_IMAGE)), int(pt.x()), int(pt.y()),
                       self.tolerance_seau, self._couleur_cible(self.couleur_peinture, sur_masque), self.opacite, sel,
                       remplissage)
            if res is not None:
                if self.doc.calque_actif.texte is not None and not sur_masque:
                    self.refus.emit(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme "
                                       "texte (Ctrl+Z pour revenir).", nom=self.doc.calque_actif.nom))
                if vectoriel(self.doc.calque_actif) and not sur_masque:
                    self.refus.emit(self.texte_devient_image(self.doc.calque_actif))
                self._poser_dessin(res, sur_masque, tr("Pot de peinture"), avant)
            return
        if self.outil == DEGRADE:
            cible = self._cible_image()
            if cible is None:
                return
            img, sur_masque = cible
            self._degrade_depart = (self.doc.etat(), self.doc.actif, img, sur_masque)
            if sur_masque:
                self.degrade_masque.emit()
        pt = regles.aimanter(self, pt)
        self._glisse_dessin = [pt, pt, bool(mods & Qt.ShiftModifier)]

    def _fin_glisse(self):
        a, b, maj = self._glisse_dessin
        if maj:
            from .outils_dessin import contraindre
            b = contraindre(a, b, "ligne" if self.outil == DEGRADE else self.forme)
        return a, b

    def _calcul_degrade(self, a, b):
        """Résultat du dégradé de a à b, d'après le calque tel qu'il était au début du glissé :
        ("style", style) sur un texte (Incrustation dégradé : les lettres seules, le texte reste modifiable),
        sinon ("pixels", image, sur le masque ?)."""
        _etat, index, img, sur_masque = self._degrade_depart
        calque = _etat[0][index]
        if calque.texte is not None and not sur_masque:
            from .styles import avec_effet, effet_degrade_glisse
            e = effet_degrade_glisse(calque.image, a, b, self.forme_degrade, self.degrade,
                                     QColor(self.couleur_peinture), self.opacite)
            return "style", avec_effet(calque.style, e)
        from .outils_dessin import degrade
        sel = None if self.doc.selection_vide() else self.doc.selection
        res = degrade(img, a, b, self.forme_degrade, self.degrade, QColor(self.couleur_peinture), self.opacite,
                      sel, gris=sur_masque, garder_alpha=self.garder_transparence and not sur_masque)
        return "pixels", res, sur_masque

    def _montrer_degrade(self, r):
        index = self._degrade_depart[1]
        if r[0] == "style":
            self.doc.apercu_style(index, r[1])
        elif r[2]:
            self.doc.apercu_masque(index, argb_vers_masque(r[1]))
        else:
            self.doc.apercu_calque(index, r[1])

    def _apercu_degrade(self):
        """Pendant le glissé : le dégradé montré en direct sur le calque (ou les lettres du texte)."""
        if self._glisse_dessin is None or self._degrade_depart is None or self.outil != DEGRADE:
            return
        a, b = self._fin_glisse()
        if (b - a).manhattanLength() < 2:
            return
        self._montrer_degrade(self._calcul_degrade(a, b))

    def _lacher_dessin(self):
        a, b = self._fin_glisse()
        self._glisse_dessin = None
        if self.outil == DEGRADE and self._degrade_depart is not None:
            self._minuteur_degrade.stop()
            avant = self._degrade_depart[0]
            if (b - a).manhattanLength() < 2:            # simple clic : rien (l'aperçu éventuel est retiré)
                modifie = self.doc.modifie
                self.doc.appliquer_etat(avant)
                self.doc.modifie = modifie
                self._degrade_depart = None
                return
            r = self._calcul_degrade(a, b)
            self._montrer_degrade(r)
            self._degrade_depart = None
            if r[0] == "style":
                self.refus.emit(tr("Dégradé posé sur les lettres (style « Incrustation dégradé ») : le texte reste "
                                   "modifiable. Calque > Style du calque pour le régler."))
                self.selection_modifiee.emit(avant, tr("Dégradé sur le texte"))
            else:
                self.selection_modifiee.emit(avant, tr("Dégradé"))
            return
        if (b - a).manhattanLength() < 2:
            return
        avant = self.doc.etat()
        from . import calque_forme as cf
        ouvert = self.forme in cf.OUVERTS
        remplir = self.forme_remplie and not ouvert
        contour = ouvert or self.forme_contour or not remplir
        f = cf.Forme(cf.traces_depuis_chemin(cf.chemin_genre(self.forme, a, b, self.forme_cotes)),
                     self.forme_couleur.name(QColor.HexArgb) if remplir else "",
                     self.forme_couleur_contour.name(QColor.HexArgb) if contour else "",
                     float(self.forme_epaisseur), self.forme == "fleche", self.forme)
        etat = self.doc.etat_nouvelle_forme(f, cf.noms_genres()[self.forme])
        self.doc.appliquer_etat(etat)
        self.selection_modifiee.emit(avant, tr("Forme"))

    def _dessiner_glisse(self, p: QPainter):
        a, b = self._fin_glisse()
        A, B = self.vers_ecran(a), self.vers_ecran(b)
        for couleur, epaisseur in ((QColor(0, 0, 0), 3), (QColor(255, 255, 255), 1)):
            stylo = QPen(couleur, epaisseur)
            p.setPen(stylo)
            p.setBrush(Qt.NoBrush)
            if self.outil == DEGRADE:
                p.drawLine(A, B)
                p.drawEllipse(A, 4, 4)
                if self.forme_degrade == "radial":
                    r = QLineF(A, B).length()
                    p.drawEllipse(A, r, r)
            else:
                from .calque_forme import _pointe, chemin_genre
                p.drawPath(chemin_genre(self.forme, A, B, self.forme_cotes))
                if self.forme == "fleche":
                    p.drawPolygon(_pointe(A, B, self.forme_epaisseur * self.zoom))

    # ---------------------------------------------------------- recadrer
    def definir_proportion(self, proportion: float | None):
        self.proportion = proportion
        if self.recadre is not None and proportion:
            c = self.recadre.center()
            w = self.recadre.width()
            h = w / proportion
            if h > self.recadre.height():
                h = self.recadre.height()
                w = h * proportion
            self.recadre = self._dans_image(QRectF(c.x() - w / 2, c.y() - h / 2, w, h))
            self._emettre_recadre()
        self.update()

    def annuler_recadre(self):
        self.recadre = None
        self._recadre_glisse = None
        self._emettre_recadre()
        self.travail_change.emit()
        self.update()

    def rect_recadre(self):
        """Cadre arrondi au pixel (QRect), ou None."""
        if self.recadre is None:
            return None
        r = self.recadre.toRect().intersected(self.doc.image.rect())
        return r if r.width() >= 1 and r.height() >= 1 else None

    def _emettre_recadre(self):
        self.recadre_change.emit(self.rect_recadre())

    def _dans_image(self, r: QRectF) -> QRectF:
        """Garde le cadre dans la photo (le déplace, puis le réduit si besoin, en gardant la proportion)."""
        iw, ih = self.doc.image.width(), self.doc.image.height()
        w, h = min(r.width(), iw), min(r.height(), ih)
        if self.proportion:
            if w / max(h, 1e-6) > self.proportion:
                w = h * self.proportion
            else:
                h = w / self.proportion
        x = max(0.0, min(r.center().x() - w / 2, iw - w))
        y = max(0.0, min(r.center().y() - h / 2, ih - h))
        return QRectF(x, y, w, h)

    def _depuis_coin(self, ancre: QPointF, pt: QPointF) -> QRectF:
        """Cadre entre un coin fixe et la souris, avec la proportion, sans sortir de la photo."""
        iw, ih = self.doc.image.width(), self.doc.image.height()
        sx = 1 if pt.x() >= ancre.x() else -1
        sy = 1 if pt.y() >= ancre.y() else -1
        maxw = iw - ancre.x() if sx > 0 else ancre.x()
        maxh = ih - ancre.y() if sy > 0 else ancre.y()
        w = min(abs(pt.x() - ancre.x()), maxw)
        h = min(abs(pt.y() - ancre.y()), maxh)
        if self.proportion:
            if w / max(h, 1e-6) > self.proportion:
                h = w / self.proportion
            else:
                w = h * self.proportion
            f = min(1.0, maxw / max(w, 1e-6), maxh / max(h, 1e-6))
            w, h = w * f, h * f
        return QRectF(ancre, ancre + QPointF(sx * w, sy * h)).normalized()

    def _rect_recadre_ecran(self) -> QRectF:
        return QRectF(self.vers_ecran(self.recadre.topLeft()), self.vers_ecran(self.recadre.bottomRight()))

    def _presser_recadre(self, pos: QPointF):
        pt = self.vers_image(pos)
        if self.recadre is not None:
            cotes = self._cotes_sous(self._rect_recadre_ecran(), pos)
            if cotes:
                self._recadre_glisse = (frozenset(cotes), pt, QRectF(self.recadre))
                return
            if self.recadre.contains(pt):
                self._recadre_glisse = ("deplacer", pt, QRectF(self.recadre))
                return
        iw, ih = self.doc.image.width(), self.doc.image.height()
        pt = QPointF(max(0.0, min(pt.x(), iw)), max(0.0, min(pt.y(), ih)))
        self._recadre_glisse = ("nouveau", pt, None)
        self.recadre = QRectF(pt, pt)

    def _glisser_recadre(self, pos: QPointF):
        mode, depart, r0 = self._recadre_glisse
        pt = self.vers_image(pos)
        if mode == "nouveau":
            self.recadre = self._depuis_coin(depart, pt)
        elif mode == "deplacer":
            r = r0.translated(pt - depart)
            self.recadre = self._dans_image(QRectF(r.topLeft(), r0.size()))
        else:
            cotes = set(mode)
            if len(cotes) == 2:                          # coin : le coin opposé reste fixe
                ancre = QPointF(r0.right() if "g" in cotes else r0.left(),
                                r0.bottom() if "h" in cotes else r0.top())
                self.recadre = self._depuis_coin(ancre, pt)
            else:
                iw, ih = self.doc.image.width(), self.doc.image.height()
                g, h_, d, b = r0.left(), r0.top(), r0.right(), r0.bottom()
                if "g" in cotes:
                    g = max(0.0, min(pt.x(), d - 1))
                elif "d" in cotes:
                    d = min(float(iw), max(pt.x(), g + 1))
                elif "h" in cotes:
                    h_ = max(0.0, min(pt.y(), b - 1))
                else:
                    b = min(float(ih), max(pt.y(), h_ + 1))
                r = QRectF(QPointF(g, h_), QPointF(d, b))
                if self.proportion:                      # l'autre dimension suit, centrée
                    c = r.center()
                    if cotes & {"g", "d"}:
                        hh = r.width() / self.proportion
                        r = QRectF(r.left(), c.y() - hh / 2, r.width(), hh)
                    else:
                        ww = r.height() * self.proportion
                        r = QRectF(c.x() - ww / 2, r.top(), ww, r.height())
                    r = self._dans_image(r)
                self.recadre = r
        self._emettre_recadre()
        self.update()

    def _lacher_recadre(self):
        self._recadre_glisse = None
        if self.recadre is not None and (self.recadre.width() < 4 or self.recadre.height() < 4):
            self.recadre = None
        self._emettre_recadre()
        self.update()

    def _dessiner_recadre(self, p: QPainter):
        r = self._rect_recadre_ecran()
        photo = QRectF(self.decalage, self.decalage + QPointF(self.doc.image.width(),
                                                              self.doc.image.height()) * self.zoom)
        dehors = QPainterPath()
        dehors.addRect(photo)
        dedans = QPainterPath()
        dedans.addRect(r)
        p.save()
        p.fillPath(dehors.subtracted(dedans), QColor(0, 0, 0, 140))       # partie coupée assombrie
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 110), 1))                     # grille des tiers
        for i in (1, 2):
            x = r.left() + r.width() * i / 3
            y = r.top() + r.height() * i / 3
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawRect(r)
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawRect(r)
        c = r.center()
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for pt in (r.topLeft(), QPointF(c.x(), r.top()), r.topRight(), QPointF(r.right(), c.y()),
                   r.bottomRight(), QPointF(c.x(), r.bottom()), r.bottomLeft(), QPointF(r.left(), c.y())):
            p.drawRect(QRectF(pt.x() - 5, pt.y() - 5, 10, 10))
        rr = self.rect_recadre()
        if rr is not None:                               # taille du résultat
            texte = f"{rr.width()} × {rr.height()} px"
            boite = p.fontMetrics().boundingRect(texte).adjusted(-6, -3, 6, 3)
            boite.moveTopLeft(QPointF(r.left(), r.bottom() + 8).toPoint())
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 170))
            p.drawRoundedRect(QRectF(boite), 4, 4)
            p.setPen(QColor(255, 255, 255))
            p.drawText(boite, Qt.AlignCenter, texte)
        p.restore()

    # ---------------------------------------------------------- recadrage en perspective
    def commencer_persp(self):
        """4 coins à poser sur les bords de l'objet vu de biais (façade, tableau, document) ; au départ, un peu en
        retrait des bords de l'image."""
        w, h = self.doc.taille()
        mx, my = w * 0.1, h * 0.1
        self.persp = [QPointF(mx, my), QPointF(w - mx, my), QPointF(w - mx, h - my), QPointF(mx, h - my)]
        self._persp_prise = None
        self.setFocus()
        self._gestes_depart()
        self.update()

    def finir_persp(self):
        self.persp = None
        self._persp_prise = None
        self._curseur()
        self.travail_change.emit()
        self.update()

    def _sous_persp(self, pos: QPointF):
        """Coin sous la souris (0..3), -1 dedans (tout déplacer), None ailleurs."""
        for i, c in enumerate(self.persp):
            if QLineF(self.vers_ecran(c), pos).length() <= 10:
                return i
        if QPolygonF(self.persp).containsPoint(self.vers_image(pos), Qt.OddEvenFill):
            return -1
        return None

    def _dessiner_persp(self, p: QPainter):
        coins = [self.vers_ecran(c) for c in self.persp]
        poly = QPolygonF(coins)
        p.save()
        dehors = QPainterPath()
        dehors.addRect(QRectF(self.rect()))
        dedans = QPainterPath()
        dedans.addPolygon(poly)
        dedans.closeSubpath()
        p.fillPath(dehors.subtracted(dedans), QColor(0, 0, 0, 110))
        p.setRenderHint(QPainter.Antialiasing)
        t = QTransform()
        if QTransform.quadToQuad(QPolygonF([QPointF(0, 0), QPointF(1, 0), QPointF(1, 1), QPointF(0, 1)]), poly, t):
            p.setPen(QPen(QColor(255, 255, 255, 120), 1))
            for k in (0.25, 0.5, 0.75):                       # grille en perspective : aide à aligner les bords
                p.drawLine(t.map(QPointF(k, 0)), t.map(QPointF(k, 1)))
                p.drawLine(t.map(QPointF(0, k)), t.map(QPointF(1, k)))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 170), 1))
        p.drawPolygon(poly)
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawPolygon(poly)
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for c in coins:
            p.drawEllipse(QRectF(c.x() - 6, c.y() - 6, 12, 12))
        p.restore()

    # ---------------------------------------------------------- transformer un calque (Ctrl+T)
    def commencer_transfo(self, t: Transformation, index: int):
        self.transfo = t
        self._transfo_index = index
        self._apercu_transfo(lisse=True)
        self.setFocus()
        self._gestes_depart()
        self.update()

    def finir_transfo(self):
        self.transfo = None
        self._transfo_glisse = False
        self._curseur()
        self.travail_change.emit()
        self.update()

    def _apercu_transfo(self, lisse: bool):
        w, h = self.doc.taille()
        self.doc.apercu_calque(self._transfo_index, self.transfo.rendu(w, h, lisse))

    def _sous_transfo(self, pos: QPointF):
        """Ce qui est sous la souris : nom de poignée, « deplacer » ou « tourner »."""
        proche, nom_proche = 9.0, None
        for nom, pt in self.transfo.poignees().items():
            d = QLineF(self.vers_ecran(pt), pos).length()
            if d <= proche:
                proche, nom_proche = d, nom
        if nom_proche is not None:
            return nom_proche
        return "deplacer" if self.transfo.dedans(self.vers_image(pos)) else "tourner"

    def _curseur_transfo(self, quoi):
        if quoi == "deplacer":
            self.setCursor(Qt.SizeAllCursor)
        elif self.transfo.libre() and quoi != "tourner":
            self.setCursor(Qt.PointingHandCursor)
        else:
            self._curseur_poignee(quoi, self.transfo.angle)

    def _dessiner_transfo(self, p: QPainter):
        t = self.transfo
        bord = QPolygonF([self.vers_ecran(c) for c in t.contour()])
        p.save()
        p.setBrush(Qt.NoBrush)
        p.setRenderHint(QPainter.Antialiasing, t.maille is not None)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.drawPolygon(bord)
        p.setPen(QPen(QColor(255, 255, 255), 1, Qt.DashLine))
        p.drawPolygon(bord)
        if t.maille is not None:                    # déformation : lignes de la grille et bras des poignées
            p.setPen(QPen(QColor(255, 255, 255, 150), 1))
            for k in (1 / 3, 2 / 3):
                p.drawPolyline(QPolygonF([self.vers_ecran(point_surface(t.maille, i / 16, k)) for i in range(17)]))
                p.drawPolyline(QPolygonF([self.vers_ecran(point_surface(t.maille, k, i / 16)) for i in range(17)]))
            p.setPen(QPen(QColor(0, 0, 0, 120), 1))
            m = [self.vers_ecran(c) for c in t.maille]
            for i in range(4):
                p.drawPolyline(QPolygonF([m[i * 4 + j] for j in range(4)]))
                p.drawPolyline(QPolygonF([m[j * 4 + i] for j in range(4)]))
        p.setPen(QPen(QColor(0, 0, 0, 180), 1))
        p.setBrush(self.couleur_accent)
        for nom, pt in t.poignees().items():
            pt = self.vers_ecran(pt)
            r = 4 if nom.startswith("m") and nom not in ("m0", "m3", "m12", "m15") else 5
            if nom.startswith("m") and r == 4:
                p.drawEllipse(QRectF(pt.x() - r, pt.y() - r, 2 * r, 2 * r))
            else:
                p.drawRect(QRectF(pt.x() - r, pt.y() - r, 2 * r, 2 * r))
        c = self.vers_ecran(t.centre_forme())
        p.setPen(QPen(QColor(255, 255, 255), 1))
        p.drawLine(QPointF(c.x() - 6, c.y()), QPointF(c.x() + 6, c.y()))
        p.drawLine(QPointF(c.x(), c.y() - 6), QPointF(c.x(), c.y() + 6))
        p.restore()

    # ---------------------------------------------------------- outil Déplacer : cadre à poignées
    def rect_deplacer(self) -> QRectF | None:
        """Cadre de l'outil Déplacer (coordonnées image) : les pixels visibles du calque choisi, ou seulement ceux de
        la sélection. None quand il n'a pas lieu d'être (autre outil, calque vide, verrouillé, caché, texte…)."""
        if (not self.doc or self.outil != DEPLACER or not self.cadre_deplacer or self.transfo is not None
                or self.cadre is not None or self.style_ouvert or self.sur_masque()):
            return None
        c = self.doc.calque_actif
        if c.verrou or c.special or c.texte is not None or not c.visible:
            return None
        if self._calque_glisse is not None and self._rect_cadre_deplacer is not None:   # pendant un déplacement :
            dx, dy = getattr(self, "_decalage_calque", (0, 0))                           # le cadre suit
            return self._rect_cadre_deplacer.translated(dx, dy)
        cle = (id(self.doc), self.doc.actif, c.image.cacheKey(), self.doc.selection.cacheKey(),
               c.hors.cacheKey() if c.hors is not None else 0, c.hors_x, c.hors_y)
        if cle != self._cle_cadre_deplacer:
            if self.doc.rect_selection() is not None:     # sélection : seulement sa partie (dans la feuille)
                a, ox, oy = np.minimum(tableau(c.image)[:, :, 3], tableau(self.doc.selection)[:, :, 3]), 0, 0
            else:                                         # tout le calque, même ce qui dépasse de la feuille
                entiere, ox, oy = image_entiere(c)
                a = tableau(entiere)[:, :, 3]
            ys, xs = (a > 0).nonzero()
            self._rect_cadre_deplacer = (QRectF(float(xs.min() + ox), float(ys.min() + oy),
                                                float(xs.max() - xs.min() + 1), float(ys.max() - ys.min() + 1))
                                         if len(ys) else None)
            self._cle_cadre_deplacer = cle
        return self._rect_cadre_deplacer

    def _points_cadre_deplacer(self, r: QRectF) -> dict:
        cx, cy, hw, hh = r.center().x(), r.center().y(), r.width() / 2, r.height() / 2
        return {nom: self.vers_ecran(QPointF(cx + gx * hw, cy + gy * hh)) for nom, (gx, gy) in POIGNEES.items()}

    def _sous_cadre_deplacer(self, pos: QPointF):
        """Poignée sous la souris (son nom), « tourner » juste à l'extérieur d'un coin, sinon None."""
        r = self.rect_deplacer()
        if r is None:
            return None
        points = self._points_cadre_deplacer(r)
        for nom, pt in points.items():
            if QLineF(pt, pos).length() <= 8:
                return nom
        dedans = r.contains(self.vers_image(pos))
        if not dedans and any(QLineF(points[n], pos).length() <= 24 for n in ("hg", "hd", "bd", "bg")):
            return "tourner"
        return None

    def _dessiner_cadre_deplacer(self, p: QPainter):
        r = self.rect_deplacer()
        if r is None:
            return
        points = self._points_cadre_deplacer(r)
        coins = QPolygonF([points[n] for n in ("hg", "hd", "bd", "bg")])
        p.save()
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 120), 1))
        p.drawPolygon(coins)
        p.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DashLine))
        p.drawPolygon(coins)
        p.setPen(QPen(QColor(0, 0, 0, 160), 1))
        p.setBrush(QColor(255, 255, 255))
        for pt in points.values():
            p.drawRect(QRectF(pt.x() - 4, pt.y() - 4, 8, 8))
        p.restore()

    def _curseur_poignee(self, quoi, angle: float = 0.0):
        if quoi == "tourner":
            self.setCursor(Qt.CrossCursor)
            return
        gx, gy = POIGNEES[quoi]
        a = (math.degrees(math.atan2(gy, gx)) + angle) % 180
        self.setCursor(Qt.SizeHorCursor if a < 22.5 or a >= 157.5 else
                       Qt.SizeFDiagCursor if a < 67.5 else
                       Qt.SizeVerCursor if a < 112.5 else Qt.SizeBDiagCursor)

    def _damier(self) -> QPixmap:
        if getattr(self, "_motif_damier", None) is None:
            pm = QPixmap(16, 16)
            pm.fill(QColor(255, 255, 255))
            p = QPainter(pm)
            p.fillRect(0, 0, 8, 8, QColor(214, 214, 214))
            p.fillRect(8, 8, 8, 8, QColor(214, 214, 214))
            p.end()
            self._motif_damier = pm
        return self._motif_damier

    # ---------------------------------------------------------- gomme de calque
    def _coup_de_gomme_calque(self, a: QPointF, b: QPointF):
        if self._trait_forme is not None:              # gomme avec une forme (bibliothèque) ou la tablette
            self._trait_forme.ajouter(b, self._pression_evt)
            self._img_calque = self._trait_forme.image
            if self._sur_masque:
                self.doc.apercu_masque(self.doc.actif, argb_vers_masque(self._img_calque))
            else:
                self.doc.apercu_calque(self.doc.actif, QImage(self._img_calque))
            return
        p = QPainter(self._img_calque)
        p.setRenderHint(QPainter.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        if a == b:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0))
            r = self.taille_pinceau / 2
            p.drawEllipse(a, r, r)
        else:
            p.setPen(QPen(QColor(0, 0, 0), self.taille_pinceau, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawLine(a, b)
        p.end()
        if self._sur_masque:
            self.doc.apercu_masque(self.doc.actif, argb_vers_masque(self._img_calque))
        else:
            self.doc.apercu_calque(self.doc.actif, QImage(self._img_calque))

    # ---------------------------------------------------------- peinture de la sélection
    def _peintre_selection(self) -> QPainter:
        p = QPainter(self.doc.selection)
        p.setRenderHint(QPainter.Antialiasing)
        if self._soustraire or self.outil == GOMME:
            p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        return p

    def _coup_de_pinceau(self, a: QPointF, b: QPointF):
        if self._trait_forme is not None:              # pinceau de sélection avec une forme ou la tablette
            zone = self._trait_forme.ajouter(b, self._pression_evt)
            if not zone.isEmpty():
                p = QPainter(self.doc.selection)
                p.setCompositionMode(QPainter.CompositionMode_Source)
                p.drawImage(zone.topLeft(), self._trait_forme.image, zone)
                p.end()
            return
        p = self._peintre_selection()
        p.setPen(QPen(COULEUR_SELECTION, self.taille_pinceau, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if a == b:
            p.setPen(Qt.NoPen)
            p.setBrush(COULEUR_SELECTION)
            r = self.taille_pinceau / 2
            p.drawEllipse(a, r, r)
        else:
            p.drawLine(a, b)
        p.end()

    def image_avant(self) -> QImage | None:
        return getattr(self.doc, "image_ouverture", None) if self.doc is not None else None

    def _rect_avant(self, photo: QRectF) -> QRectF:
        """Où montrer la photo d'avant : sur toute la photo (même proportions, ex. Upscale), sinon centrée en gardant
        ses proportions (recadrée ou agrandie depuis)."""
        av = self.image_avant()
        if av is None or av.width() == 0 or av.height() == 0:
            return photo
        ra, rp = av.width() / av.height(), photo.width() / max(1e-6, photo.height())
        if abs(ra - rp) < 0.01:
            return photo
        if ra > rp:
            h = photo.width() / ra
            return QRectF(photo.left(), photo.center().y() - h / 2, photo.width(), h)
        w = photo.height() * ra
        return QRectF(photo.center().x() - w / 2, photo.top(), w, photo.height())

    def _dessiner_avant(self, p: QPainter, photo: QRectF):
        """Rideau Avant / après : à gauche la photo à l'ouverture, à droite la photo actuelle."""
        av = self.image_avant()
        x = photo.left() + photo.width() * self.rideau
        if av is not None:
            p.save()
            p.setClipRect(QRectF(photo.left(), photo.top(), x - photo.left(), photo.height()))
            p.fillRect(photo, self.couleur_fond)
            p.setRenderHint(QPainter.SmoothPixmapTransform, self.zoom < 1)
            p.drawImage(self._rect_avant(photo), av)
            p.restore()
        haut, bas = max(photo.top(), 0), min(photo.bottom(), self.height())
        for couleur, largeur in ((QColor(0, 0, 0, 120), 4), (QColor(255, 255, 255), 2)):
            p.setPen(QPen(couleur, largeur))
            p.drawLine(QPointF(x, haut), QPointF(x, bas))
        milieu = QPointF(x, (haut + bas) / 2)
        p.setPen(QPen(QColor(0, 0, 0, 120), 1))
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(milieu, 14, 14)
        p.setBrush(QColor(60, 60, 60))
        p.setPen(Qt.NoPen)
        for sens in (-1, 1):
            p.drawPolygon(QPolygonF([milieu + QPointF(sens * 3, -5), milieu + QPointF(sens * 3, 5),
                                     milieu + QPointF(sens * 9, 0)]))
        p.setBrush(Qt.NoBrush)
        f = p.font()
        f.setBold(True)
        p.setFont(f)
        fm = p.fontMetrics()
        for texte, gauche in ((tr("Avant"), True), (tr("Après"), False)):
            w = fm.horizontalAdvance(texte) + 16
            r = QRectF(x - w - 10 if gauche else x + 10, haut + 10, w, fm.height() + 8)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 150))
            p.drawRoundedRect(r, 4, 4)
            p.setPen(QColor(255, 255, 255))
            p.drawText(r, Qt.AlignCenter, texte)
        p.setBrush(Qt.NoBrush)

    def _placer_rideau(self, pos: QPointF):
        w = self.doc.image.width() * self.zoom
        if w > 0:
            self.rideau = min(1.0, max(0.0, (pos.x() - self.decalage.x()) / w))
            self.update()

    def _dessiner_auto(self, p: QPainter):
        """Trait de la sélection rapide, cadre de la sélection d'objet (en cours ou en calcul), points de l'IA.
        Appelé avec la transformation de l'image (coordonnées image)."""
        trait = None
        if self._auto is not None and self._auto[0] in (RAPIDE, OBJET, SUPPRIMER, SEL_TEXTE, EFFACER_CLIC, YEUX):
            trait = (self._auto[0], self._auto[2])
        elif self.trait_en_attente is not None:
            trait = self.trait_en_attente
        if trait is not None:
            genre, d = trait
            if genre in (RAPIDE, SUPPRIMER) and len(d["points"]) > 0:
                c = QColor(self.couleur_accent)
                c.setAlpha(110)
                if genre == SUPPRIMER:
                    c = QColor(255, 60, 150, 120)
                if d.get("alt"):
                    c = QColor(255, 255, 255, 130)
                p.setPen(QPen(c, d.get("taille", self.taille_pinceau), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                if len(d["points"]) == 1:
                    p.drawPoint(d["points"][0])
                else:
                    p.drawPolyline(QPolygonF(d["points"]))
            elif genre in (OBJET, SEL_TEXTE, EFFACER_CLIC, YEUX) and d.get("fin") is not None:
                r = QRectF(d["debut"], d["fin"]).normalized()
                for couleur, style in ((QColor(0, 0, 0), Qt.SolidLine), (QColor(255, 255, 255), Qt.DashLine)):
                    stylo = QPen(couleur, 0, style)
                    stylo.setCosmetic(True)
                    stylo.setWidth(2 if style == Qt.SolidLine else 1)
                    p.setPen(stylo)
                    p.drawRect(r)
        if self.points_ia:
            rayon = 5 / self.zoom
            for pt, garder in self.points_ia:
                p.setPen(QPen(QColor(255, 255, 255), 1.5 / self.zoom))
                p.setBrush(QColor(40, 180, 90) if garder else QColor(220, 50, 50))
                p.drawEllipse(pt, rayon, rayon)
            p.setBrush(Qt.NoBrush)

    def _presser_auto(self, e, pos: QPointF):
        mods = e.modifiers()
        pt = self.vers_image(pos)
        alt, maj = bool(mods & Qt.AltModifier), bool(mods & Qt.ShiftModifier)
        mode = "retirer" if alt else "ajouter" if maj else self.mode_forme
        if self.outil == BAGUETTE:
            self._auto = (BAGUETTE, pos, {})
            self.baguette_clic.emit(pt, mode)
        elif self.outil == RAPIDE:
            self._auto = (RAPIDE, pos, {"points": [pt], "alt": alt, "maj": maj})
        elif self.outil == SUPPRIMER:
            self._auto = (SUPPRIMER, pos, {"points": [pt], "taille": float(self.taille_pinceau)})
        else:
            self._auto = (self.outil if self.outil in (SEL_TEXTE, EFFACER_CLIC, YEUX) else OBJET, pos,
                          {"debut": pt, "fin": None, "mode": mode, "ctrl": bool(mods & Qt.ControlModifier)})
        self.update()

    def _glisser_auto(self, pos: QPointF):
        outil, depart, d = self._auto
        if outil == BAGUETTE:
            self.baguette_glisse.emit(pos.x() - depart.x())
        elif outil in (RAPIDE, SUPPRIMER):
            d["points"].append(self.vers_image(pos))
        elif (pos - depart).manhattanLength() > 4:
            d["fin"] = self.vers_image(pos)
        self.update()

    def _lacher_auto(self):
        outil, depart, d = self._auto
        self._auto = None
        if outil == BAGUETTE:
            self.baguette_lache.emit()
        elif outil == SUPPRIMER:
            self.trait_en_attente = (SUPPRIMER, d)
            self.suppression.emit([(pt.x(), pt.y()) for pt in d["points"]], d["taille"])
        elif outil == RAPIDE:
            self.trait_en_attente = (RAPIDE, d)
            self.trait_ia.emit([(pt.x(), pt.y()) for pt in d["points"]], d["alt"], d["maj"])
        elif outil == SEL_TEXTE:
            quoi = QRectF(d["debut"], d["fin"]).normalized() if d["fin"] is not None else d["debut"]
            self.texte_sel.emit(quoi, d["mode"], d["ctrl"])
        elif outil == YEUX:
            self.yeux_rouges.emit(QRectF(d["debut"], d["fin"]).normalized() if d["fin"] is not None else d["debut"])
        elif outil == EFFACER_CLIC:
            self.trait_en_attente = (EFFACER_CLIC, d)
            quoi = QRectF(d["debut"], d["fin"]).normalized() if d["fin"] is not None else d["debut"]
            self.effacer_clic.emit(quoi)
        else:
            self.trait_en_attente = (OBJET, d)
            quoi = QRectF(d["debut"], d["fin"]).normalized() if d["fin"] is not None else d["debut"]
            self.objet_ia.emit(quoi, d["mode"])
        self.update()

    # ---------------------------------------------------------- lasso par points
    def _presser_poly(self, e, pos: QPointF):
        """Un clic = un point. Clic sur le premier point (ou double-clic, Entrée) : la sélection se ferme."""
        pt = self.vers_image(pos)
        if self._poly is None:
            mods = e.modifiers()
            mode = ("retirer" if mods & Qt.AltModifier else "ajouter" if mods & Qt.ShiftModifier
                    else self.mode_forme)
            self._soustraire = mode == "retirer"
            self._nouvelle = mode == "nouvelle"
            self._avant = self.doc.etat()
            self._poly = [pt]
        elif len(self._poly) >= 3 and QLineF(self.vers_ecran(self._poly[0]), pos).length() <= 8:
            self.finir_poly()
            return
        else:
            self._poly.append(pt)
        self._poly_souris = pt
        self.update()

    def finir_poly(self):
        """Ferme le lasso par points : la sélection est faite (une étape dans Annuler)."""
        if self._poly is None:
            return
        points, self._poly, self._poly_souris = self._poly, None, None
        if len(points) < 3:
            self._avant = None
            self.update()
            return
        if self._nouvelle:
            self.doc.selection.fill(0)
        outil, self.outil = self.outil, LASSO
        self._trace = points
        self._remplir_forme()
        self._trace = None
        self.outil = outil
        self._nouvelle = False
        self.selection_modifiee.emit(self._avant, tr("Lasso par points"))
        self._avant = None
        self.update()

    def annuler_poly(self):
        if self._poly is not None:
            self._poly, self._poly_souris, self._avant = None, None, None
            self.update()

    def _dessiner_poly(self, p: QPainter):
        if self._poly is None:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        ecran = [self.vers_ecran(q) for q in self._poly]
        if self._poly_souris is not None:
            ecran_s = ecran + [self.vers_ecran(self._poly_souris)]
        else:
            ecran_s = ecran
        for couleur, epaisseur, style in ((QColor(0, 0, 0, 160), 3, Qt.SolidLine), (QColor(255, 255, 255), 1, Qt.DashLine)):
            p.setPen(QPen(couleur, epaisseur, style))
            p.drawPolyline(QPolygonF(ecran_s))
        pres = (len(self._poly) >= 3 and self._poly_souris is not None
                and QLineF(ecran[0], self.vers_ecran(self._poly_souris)).length() <= 8)
        p.setPen(QPen(QColor(0, 0, 0), 1))
        for k, q in enumerate(ecran):
            p.setBrush(self.couleur_accent if (k == 0 and pres) else QColor(255, 255, 255))
            r = 6 if (k == 0 and pres) else 3.5
            p.drawRect(QRectF(q.x() - r, q.y() - r, 2 * r, 2 * r))
        p.restore()

    def _remplir_forme(self):
        chemin = QPainterPath()
        if self.outil == RECTANGLE:
            chemin.addRect(QRectF(self._trace[0], self._trace[-1]).normalized())
        elif self.outil == ELLIPSE_SEL:
            chemin.addEllipse(QRectF(self._trace[0], self._trace[-1]).normalized())
        else:
            chemin.moveTo(self._trace[0])
            for pt in self._trace[1:]:
                chemin.lineTo(pt)
            chemin.closeSubpath()
        p = self._peintre_selection()
        p.fillPath(chemin, COULEUR_SELECTION)
        p.end()

    # ---------------------------------------------------------- souris
    def _deplacement_actif(self, e) -> bool:
        return self.outil == MAIN or self._espace or e.buttons() & Qt.MiddleButton

    def definir_poignee_sol(self, points):
        self.poignee_sol = points
        self.update()

    def _bout_sol_ecran(self):
        if self.poignee_sol is None:
            return None
        return self.vers_ecran(QPointF(*self.poignee_sol[1]))

    def _dessiner_poignee_sol(self, p: QPainter):
        if self.poignee_sol is None:
            return
        a, b = self.vers_ecran(QPointF(*self.poignee_sol[0])), self._bout_sol_ecran()
        for couleur, epaisseur in ((QColor(0, 0, 0, 160), 3), (QColor(255, 255, 255), 1)):
            p.setPen(QPen(couleur, epaisseur, Qt.DashLine))
            p.drawLine(a, b)
        p.setPen(QPen(QColor(255, 255, 255), 2))
        p.setBrush(self.couleur_accent)
        p.drawEllipse(b, 7, 7)
        p.setBrush(Qt.NoBrush)

    # ---------------------------------------------------------- pinceaux à forme, tablette
    def tabletEvent(self, e):
        """Stylet : on note la pression ; Qt envoie ensuite l'événement souris habituel."""
        self._tablette = True
        self._pression = max(0.0, min(1.0, e.pressure()))
        e.ignore()

    def _pression_de(self, e) -> float:
        dev = e.pointingDevice() if hasattr(e, "pointingDevice") else None
        if self._tablette and dev is not None and dev.type() in (QInputDevice.DeviceType.Stylus,
                                                                  QInputDevice.DeviceType.Airbrush):
            return self._pression if self._pression > 0 else 1.0
        return 1.0

    def parametres_pinceau(self, outil: str) -> dict:
        """Ce que Trait reçoit pour l'outil : forme choisie, réglages, texture, double pinceau. {} : le rond
        simple d'avant (aucune forme, aucun réglage, pas de tablette)."""
        groupe = GROUPE_OUTIL.get(outil)
        if groupe is None:
            return {}
        choix = self.pinceaux[groupe]
        r, cle = choix["reglages"], choix["cle"]
        if cle is None and r == Reglages() and not self._tablette:
            return {}
        from .bibliotheque import MOTIFS, bibliotheque
        kw = {"reglages": r, "fond": QColor(255, 255, 255)}
        if cle:
            p = self._pointe(cle)
            if p is not None:
                kw["pointe"] = p
        if r.texture:
            m = bibliotheque().trouver(MOTIFS, r.texture)
            if m is not None:
                kw["texture"] = m.image
        if r.double:
            d = self._pointe(r.double)
            if d is not None:
                kw["double"] = d
        return kw

    def _pointe(self, cle: str) -> Pointe | None:
        from .bibliotheque import PINCEAUX, bibliotheque
        if cle not in self._pointes:
            if not bibliotheque().pret(PINCEAUX, cle):
                # pinceau d'un gros fichier pas encore lu (lecture en arrière-plan) : rond en attendant
                self.message.emit(tr("Le pinceau choisi est encore en chargement : pinceau rond en attendant."))
                bibliotheque().charger_en_fond(PINCEAUX, cle, lambda: None)
                return None
            e = bibliotheque().trouver(PINCEAUX, cle)
            self._pointes[cle] = Pointe(e.formes, e.espacement) if e is not None else None
        p = self._pointes[cle]
        if p is not None:
            p.indice = 0                  # pinceau animé : chaque trait repart de la première forme
        return p

    def mousePressEvent(self, e):
        if not self.doc:
            return
        if self.comparer and e.button() == Qt.LeftButton:
            self._rideau_glisse = True
            self._placer_rideau(e.position())
            return
        self.finir_fleches()
        self.noter_geste()           # valeurs tapées avant ce geste : un geste à part
        pos = e.position()
        self._pression_evt = self._pression_de(e)
        if self.style_ouvert:
            b = self._bout_sol_ecran()
            if e.button() == Qt.LeftButton and b is not None and (pos - b).manhattanLength() < 16:
                self._sol_glisse = True
                return
            if e.button() == Qt.MiddleButton or e.button() == Qt.LeftButton:
                self._glisse = pos                     # pendant le style : glisser = se déplacer dans la photo
                self.setCursor(Qt.ClosedHandCursor)
            return
        if self.cadre is not None and e.button() == Qt.LeftButton:   # Agrandir : les poignées d'abord
            self._poignee = self._poignee_sous(pos)
            if self._poignee:
                self._depart = self.vers_image(pos)
                return
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and (self.outil == MAIN or self._espace)):
            self._glisse = pos
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() == Qt.RightButton and self._presser_droit(e, pos):
            return
        if e.button() != Qt.LeftButton:
            return
        if self.cadre is not None:
            return
        if self.persp is not None:
            quoi = self._sous_persp(pos)
            if quoi is not None:
                self._persp_prise = (quoi, self.vers_image(pos), [QPointF(c) for c in self.persp])
            return
        if self.transfo is not None:
            quoi = self._sous_transfo(pos)
            if (e.modifiers() & Qt.ControlModifier and not self.transfo.libre() and quoi in ("hg", "hd", "bd", "bg")):
                self.transfo.passer_mode("distordre")         # Ctrl+coin : le coin bouge seul (comme Photoshop)
                self.transfo_mode_change.emit()
            self.transfo.commencer(quoi, self.vers_image(pos))
            self._transfo_glisse = True
            return
        if self._presser_plus(e, pos):
            return
        if self.outil == TEXTE:
            self._presser_texte(pos, bool(e.modifiers() & Qt.ControlModifier))
            self.update()
            return
        if self.outil == DEPLACER and self._repere_sous(pos):
            return
        if self.outil == DEPLACER:
            quoi = self._sous_cadre_deplacer(pos)
            if quoi is not None:                         # poignée attrapée : on passe en Transformer (Ctrl+T)
                self.transfo_demandee.emit()
                if self.transfo is not None:
                    self.transfo.commencer(quoi, self.vers_image(pos))
                    self._transfo_glisse = True
                    self._curseur_transfo(quoi)
                return
            self._presser_deplacer(pos)
            return
        if self.outil == RECADRER:
            self._presser_recadre(pos)
            self.update()
            return
        if self.outil in OUTILS_RETOUCHE:
            self._presser_retouche(pos, bool(e.modifiers() & Qt.AltModifier))
            self.update()
            return
        if self.outil == PLUME:
            self._presser_plume(pos, e.modifiers())
            return
        if self.outil in (DEGRADE, SEAU, FORMES):
            self._presser_dessin(pos, e.modifiers())
            self.update()
            return
        if self.outil in OUTILS_AUTO or self.outil in (SUPPRIMER, EFFACER_CLIC, YEUX):
            self._presser_auto(e, pos)
            return
        if self.outil == GOMME_CALQUE and self.doc.calque_actif.verrou:
            self.refus.emit(tr("Le calque « {nom} » est verrouillé : clique sur son cadenas pour pouvoir le "
                               "gommer.", nom=self.doc.calque_actif.nom))
            return
        if self.outil == GOMME_CALQUE and self.refus_special():
            return
        if self.outil == LASSO and (self.lasso_points or self._poly is not None):
            self._presser_poly(e, pos)
            return
        mods = e.modifiers()
        self._nouvelle = False
        if self.outil in FORMES_SELECTION:             # comme Photoshop : Maj ajoute, Alt retire
            mode = ("retirer" if mods & Qt.AltModifier else "ajouter" if mods & Qt.ShiftModifier
                    else self.mode_forme)
            self._soustraire = mode == "retirer"
            self._nouvelle = mode == "nouvelle"
        else:
            self._soustraire = self.mode_retirer != bool(mods & Qt.AltModifier)
        self._avant = self.doc.etat()
        pt = self.vers_image(pos)
        if self.outil in (RECTANGLE, ELLIPSE_SEL):
            pt = regles.aimanter(self, pt)
        self._trace = [pt]
        if self.outil == GOMME_CALQUE:
            self._sur_masque = self.sur_masque()
            if self._sur_masque:                       # sur le masque : la gomme cache (peint du noir)
                self._img_calque = masque_vers_argb(self.doc.calque_actif.masque)
            else:
                if self.doc.calque_actif.texte is not None:
                    self.refus.emit(tr("Le texte « {nom} » devient une image : il n'est plus modifiable comme "
                                       "texte (Ctrl+Z pour revenir).", nom=self.doc.calque_actif.nom))
                if vectoriel(self.doc.calque_actif):
                    self.refus.emit(self.texte_devient_image(self.doc.calque_actif))
                self._img_calque = self.doc.calque_actif.image.copy()   # copie : l'état d'avant reste intact
            kw = self.parametres_pinceau(GOMME_CALQUE)
            self._trait_forme = (Trait(EFFACER, self._img_calque, self.taille_pinceau, 1.0, 1.0, **kw)
                                 if kw else None)
            self._coup_de_gomme_calque(pt, pt)
        elif self.outil in (PINCEAU, GOMME):
            kw = self.parametres_pinceau(self.outil)
            efface = self._soustraire or self.outil == GOMME
            self._trait_forme = (Trait(EFFACER if efface else "peinture", self.doc.selection.copy(),
                                       self.taille_pinceau, 1.0, 1.0, couleur=COULEUR_SELECTION, **kw)
                                 if kw else None)
            self._coup_de_pinceau(pt, pt)
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self.comparer:
            if self._rideau_glisse:
                self._placer_rideau(pos)
            self.setCursor(Qt.SplitHCursor)
            return
        self._souris = pos
        self._pression_evt = self._pression_de(e)
        if self.style_ouvert and self._sol_glisse:
            self.poignee_sol_bouge.emit(self.vers_image(pos))
            return
        if self.style_ouvert and self._glisse is None:
            b = self._bout_sol_ecran()
            self.setCursor(Qt.SizeAllCursor if b is not None and (pos - b).manhattanLength() < 16
                           else Qt.OpenHandCursor)
            return
        if self._glisse is not None:
            self.decalage += pos - self._glisse
            self._glisse = pos
            self._ajuste = False
            self.update()
            return
        if self.cadre is not None:
            if self._poignee:
                self._tirer_cadre(pos, bool(e.modifiers() & Qt.ShiftModifier))
            else:
                self._curseur_cadre(self._poignee_sous(pos))
            return
        if self.persp is not None:
            if self._persp_prise is not None:
                quoi, p0, depart = self._persp_prise
                d = self.vers_image(pos) - p0
                if quoi == -1:
                    self.persp = [c + d for c in depart]
                else:
                    self.persp[quoi] = depart[quoi] + d
            else:
                quoi = self._sous_persp(pos)
                self.setCursor(Qt.PointingHandCursor if quoi is not None and quoi >= 0 else
                               Qt.SizeAllCursor if quoi == -1 else Qt.ArrowCursor)
            self.update()
            return
        if self.transfo is not None:
            if self._transfo_glisse:
                self.transfo.glisser(self.vers_image(pos), bool(e.modifiers() & Qt.ShiftModifier))
                self._apercu_transfo(lisse=False)        # rapide pendant le geste, lissé au lâcher
                self.transfo_change.emit()
            else:
                self._curseur_transfo(self._sous_transfo(pos))
            self.update()
            return
        if self._glisser_plus(e, pos):
            return
        if self._trace_points is not None:
            pt = self.vers_image(pos)
            if QLineF(pt, self._trace_points[-1]).length() * self.zoom >= 2:
                self._trace_points.append(pt)
                self.update()
            return
        if self.outil == PLUME and self.doc is not None and self._glisser_plume(pos, e.modifiers()):
            return
        if self._lettres_glisse is not None:
            from .texte import index_lettre
            _i, t, boites, ancre = self._lettres_glisse
            self.lettres_choisies.emit(ancre, index_lettre(t, self.vers_image(pos), boites))
            return
        if self._texte_glisse is not None:
            self._glisser_texte(pos, bool(e.modifiers() & Qt.ShiftModifier))
            return
        if self._calque_glisse is not None:
            self._glisser_calque(pos)
            return
        if self._lot_glisse is not None:
            lot, depart, _avant = self._lot_glisse
            pt = self.vers_image(pos)
            self._decalage_calque = (round(pt.x() - depart.x()), round(pt.y() - depart.y()))
            self._lot_apercu(lot, *self._decalage_calque)
            return
        if self._recadre_glisse is not None:
            self._glisser_recadre(pos)
            return
        if self._trait is not None:
            self._glisser_retouche(pos)
            self.update()
            return
        if self._auto is not None:
            self._glisser_auto(pos)
            return
        if self.outil == RECADRER and self.doc and not self._espace:
            if self.recadre is not None:
                cotes = self._cotes_sous(self._rect_recadre_ecran(), pos)
                if cotes:
                    self._curseur_cadre((None, cotes))
                elif self.recadre.contains(self.vers_image(pos)):
                    self.setCursor(Qt.SizeAllCursor)
                else:
                    self.setCursor(Qt.CrossCursor)
            else:
                self.setCursor(Qt.CrossCursor)
        if self.outil == TEXTE and self.doc and not self._espace:
            if self._sur_poignee_texte(pos):
                self.setCursor(Qt.PointingHandCursor)
            elif self._sur_bord_texte(pos) or (e.modifiers() & Qt.ControlModifier
                                               and self._texte_sous(self.vers_image(pos)) is not None):
                self.setCursor(Qt.SizeAllCursor)        # bord du cadre ou Ctrl : déplacer
            else:
                self.setCursor(Qt.IBeamCursor)          # sur les lettres : les choisir
        if self.repere_tire is not None:
            self.bouger_repere(pos)
            self.setCursor(Qt.SplitVCursor if self.repere_tire[0] == "h" else Qt.SplitHCursor)
        elif self.outil == DEPLACER and self.doc and not self._espace and not e.buttons():
            r = self._repere_a(pos)
            quoi = self._sous_cadre_deplacer(pos) if r is None else None
            if r is not None:
                self.setCursor(Qt.SplitVCursor if r[0] == "h" else Qt.SplitHCursor)
            elif quoi is not None:
                self._curseur_poignee(quoi)
            else:
                self._curseur()
        if self._glisse_dessin is not None:
            self._glisse_dessin[1] = regles.aimanter(self, self.vers_image(pos))
            self._glisse_dessin[2] = bool(e.modifiers() & Qt.ShiftModifier)
            if self.outil == DEGRADE and not self._minuteur_degrade.isActive():
                self._minuteur_degrade.start()
        if self._poly is not None:
            self._poly_souris = self.vers_image(pos)
        if self._trace is not None:
            pt = self.vers_image(pos)
            if self.outil == GOMME_CALQUE:
                self._coup_de_gomme_calque(self._trace[-1], pt)
                self._trace.append(pt)
            elif self.outil in (PINCEAU, GOMME):
                self._coup_de_pinceau(self._trace[-1], pt)
                self._trace.append(pt)
            elif self.outil in (RECTANGLE, ELLIPSE_SEL):
                self._trace = [self._trace[0], regles.aimanter(self, pt)]
            else:
                self._trace.append(pt)
        self.update()

    def mouseReleaseEvent(self, e):
        if self.comparer:
            self._rideau_glisse = False
            return
        QTimer.singleShot(0, self.noter_geste)      # le geste fini peut être défait (retour, Ctrl+Z)
        if self.style_ouvert and self._sol_glisse:
            self._sol_glisse = False
            return
        if self._glisse is not None:
            self._glisse = None
            self._curseur()
            return
        if self.cadre is not None:
            self._poignee = None
            return
        if self.persp is not None:
            self._persp_prise = None
            return
        if self.transfo is not None:
            if self._transfo_glisse:
                self._transfo_glisse = False
                self.transfo.finir()
                self._apercu_transfo(lisse=True)
                self.transfo_change.emit()
            return
        if self._lacher_plus():
            return
        if self._trace_points is not None:
            points, self._trace_points = self._trace_points, None
            self.update()
            if len(points) >= 2:
                self.trace_dessine.emit(points)
            return
        if self._plume_prise is not None:
            self._lacher_plume()
            return
        if self._lettres_glisse is not None:
            self._lettres_glisse = None
            return
        if self._texte_glisse is not None:
            self._lacher_texte()
            return
        if self._calque_glisse is not None:
            self._lacher_calque()
            return
        if self._lot_glisse is not None:
            lot, _depart, avant = self._lot_glisse
            self._lot_glisse = None
            self._lot_fin(lot, *getattr(self, "_decalage_calque", (0, 0)), avant)
            self._decalage_calque = (0, 0)
            return
        if self._recadre_glisse is not None:
            self._lacher_recadre()
            return
        if self.repere_tire is not None:
            self.finir_repere(e.position())
            return
        if self._glisse_dessin is not None:
            self._lacher_dessin()
            self.update()
            return
        if self._trait is not None:
            self._lacher_retouche()
            self.update()
            return
        if self._auto is not None:
            self._lacher_auto()
            return
        if self._trace is None:
            return
        if self.outil in FORMES_SELECTION:
            if self._nouvelle:                         # un simple clic, sans tracé, désélectionne
                self.doc.selection.fill(0)
            if len(self._trace) > 1:
                self._remplir_forme()
        self._nouvelle = False
        noms = {PINCEAU: "Pinceau de sélection", GOMME: "Gomme de sélection", RECTANGLE: "Sélection rectangle",
                ELLIPSE_SEL: "Sélection elliptique",
                LASSO: "Lasso", GOMME_CALQUE: "Gomme de calque"}
        self._img_calque = None
        self._trace = None
        nom = tr("Peindre le masque") if self.outil == GOMME_CALQUE and self._sur_masque else tr(noms[self.outil])
        self.selection_modifiee.emit(self._avant, nom)
        self._avant = None
        self.update()

    def mouseDoubleClickEvent(self, e):
        if self.style_ouvert:
            return
        if self.outil == LASSO_MAG and self.magnetique_en_cours() and e.button() == Qt.LeftButton:
            self.finir_magnetique()                   # double-clic : le lasso magnétique se ferme
            return
        if self.outil == ROTATION_VUE and e.button() == Qt.LeftButton:
            self.definir_angle_vue(0)                 # double-clic : vue droite
            return
        if self._poly is not None and e.button() == Qt.LeftButton:
            self.finir_poly()                         # double-clic : le lasso par points se ferme
            return
        if self.transfo is not None and e.button() == Qt.LeftButton:
            if self.transfo.dedans(self.vers_image(e.position())):
                self.transfo_valide.emit()
            return
        if self.persp is not None and e.button() == Qt.LeftButton:
            if self._sous_persp(e.position()) == -1:
                self.persp_valide.emit()
            return
        if self.outil == PLUME and self.plume_points is not None and e.button() == Qt.LeftButton:
            self._plume_prise = None
            self.finir_plume(fermer=False)            # double-clic : le tracé reste ouvert
            return
        if (self.outil == RECADRER and self.recadre is not None and e.button() == Qt.LeftButton
                and self.recadre.contains(self.vers_image(e.position()))):
            self.recadre_valide.emit()
            return
        if self.outil == TEXTE and self.doc is not None and e.button() == Qt.LeftButton and self.cadre is None:
            index = self._texte_sous(self.vers_image(e.position()))
            if index is not None and index == self.doc.actif:   # double-clic sur un mot : il est choisi
                from .texte import index_lettre, mot_autour
                t = self.doc.calques[index].texte
                self.lettres_choisies.emit(*mot_autour(t.texte, index_lettre(t, self.vers_image(e.position()))))
                return
        if (self.doc is not None and e.button() == Qt.LeftButton and self.outil != PLUME
                and self.cadre is None):
            index = self._texte_sous(self.vers_image(e.position()))
            if index is not None:                     # double-clic sur un texte : on l'édite (outil Texte)
                self.texte_edition.emit(index)
                return
        super().mouseDoubleClickEvent(e)

    def leaveEvent(self, e):
        self._souris = None
        self.update()

    def wheelEvent(self, e):
        if not self.doc:
            return
        facteur = 1.2 if e.angleDelta().y() > 0 else 1 / 1.2
        self.definir_zoom(self.zoom * facteur, self.derotation(e.position()))

    # ---------------------------------------------------------- clavier
    def keyPressEvent(self, e):
        if self.comparer and e.key() == Qt.Key_Escape:
            self.comparaison_finie.emit()
            return
        if self.outil == PLUME and self.touche_plume(e):
            return
        if self.outil == LASSO_MAG and self.magnetique_en_cours():
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.finir_magnetique()
                return
            if e.key() == Qt.Key_Escape:
                self.annuler_magnetique()
                return
            if e.key() == Qt.Key_Backspace:
                self.retirer_ancre_magnetique()
                return
        if self.outil == REGLE and self.regle is not None and e.key() == Qt.Key_Escape:
            self.regle = None
            self.regle_changee.emit()
            self.update()
            return
        if self._poly is not None:                   # lasso par points : Entrée ferme, Échap annule, Retour arrière
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.finir_poly()
                return
            if e.key() == Qt.Key_Escape:
                self.annuler_poly()
                return
            if e.key() == Qt.Key_Backspace:
                self._poly.pop()
                if not self._poly:
                    self.annuler_poly()
                self.update()
                return
        if self.persp is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.persp_valide.emit()
            return
        if self.persp is not None and e.key() == Qt.Key_Escape:
            self.persp_annule.emit()
            return
        if self.transfo is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.transfo_valide.emit()
        elif self.transfo is not None and e.key() == Qt.Key_Escape:
            self.transfo_annule.emit()
        elif self.cadre is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.cadre_valide.emit()
        elif self.cadre is not None and e.key() == Qt.Key_Escape:
            self.cadre_annule.emit()
        elif self.outil == RECADRER and self.recadre is not None and e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.recadre_valide.emit()
        elif self.outil == RECADRER and self.recadre is not None and e.key() == Qt.Key_Escape:
            self.annuler_recadre()
        elif self.outil == RAPIDE and e.key() == Qt.Key_Escape:
            self.fin_session_ia.emit()
        elif e.key() in FLECHES and self.doc is not None and self.transfo is not None and not self._transfo_glisse:
            pas = 10 if e.modifiers() & Qt.ShiftModifier else 1          # cadre de transformation : poussé
            dx, dy = FLECHES[e.key()]
            self.transfo.centre += QPointF(dx * pas, dy * pas)
            self._apercu_transfo(lisse=True)
            self.transfo_change.emit()
            self.update()
        elif (e.key() in FLECHES and self.doc is not None and self.outil == DEPLACER and self.cadre is None
              and not self.style_ouvert and self._calque_glisse is None and self._texte_glisse is None):
            pas = 10 if e.modifiers() & Qt.ShiftModifier else 1
            dx, dy = FLECHES[e.key()]
            self.pousser(dx * pas, dy * pas)
        elif (e.key() in FLECHES and self.doc is not None and self.outil in OUTILS_SELECTION
              and self.transfo is None and self.cadre is None and not self.doc.selection_vide()):
            pas = 10 if e.modifiers() & Qt.ShiftModifier else 1
            dx, dy = FLECHES[e.key()]
            self.selection_fleche.emit(dx * pas, dy * pas)
        elif e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._espace = True
            self.setCursor(Qt.OpenHandCursor)
        elif e.key() == Qt.Key_BracketLeft:
            self.definir_taille(self.taille_pinceau / 1.2)
        elif e.key() == Qt.Key_BracketRight:
            self.definir_taille(self.taille_pinceau * 1.2)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() in FLECHES and not e.isAutoRepeat() and self._fleches is not None:
            self.finir_fleches()
        elif e.key() == Qt.Key_Space and not e.isAutoRepeat():
            self._espace = False
            self._curseur()
        else:
            super().keyReleaseEvent(e)

    def focusOutEvent(self, e):
        self.finir_fleches()             # touche lâchée ailleurs : le déplacement est quand même gardé
        super().focusOutEvent(e)

    taille_changee = Signal(int)

    def definir_taille(self, taille: float):
        self.taille_pinceau = int(max(2, min(TAILLE_MAX, taille)))
        self.taille_changee.emit(self.taille_pinceau)
        self.update()

    def definir_couleurs(self, fond: str, texte: str, accent: str | None = None):
        self.couleur_fond, self.couleur_texte = QColor(fond), QColor(texte)
        if accent:
            self.couleur_accent = QColor(accent)
        self.update()

    def definir_mode_retirer(self, oui: bool):
        self.mode_retirer = oui

    def definir_outil(self, outil: str):
        if outil != RECADRER and self.recadre is not None:
            self.annuler_recadre()
        self.outil = outil
        self._curseur()
        self.update()

    def _curseur(self):
        if self.style_ouvert:
            self.setCursor(Qt.OpenHandCursor)
            return
        if self.cadre is not None or self.doc is None:     # sans image : pas de rond de pinceau, donc la flèche
            self.setCursor(Qt.ArrowCursor)
            return
        self.setCursor(Qt.OpenHandCursor if self.outil in (MAIN, ROTATION_VUE) else
                       Qt.BlankCursor if self.outil in OUTILS_ROND else
                       Qt.IBeamCursor if self.outil == TEXTE else
                       Qt.SizeAllCursor if self.outil == DEPLACER else Qt.CrossCursor)
