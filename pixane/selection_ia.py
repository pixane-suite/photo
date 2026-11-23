"""Baguette magique (W), sélection rapide (Q) et sélection d'objet (O) : ce que font ces outils quand le canevas
signale un clic, un trait ou un cadre. Le calcul de la baguette est local (selection_auto) ; les deux autres
demandent l'objet au modèle SAM 3.1 par le moteur IA (environ 1 s par demande, 3 s la première fois)."""
from __future__ import annotations

import threading

import numpy as np
from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox

from . import recettes
from .document import FORMAT_IMAGE, _masque_vers_selection, a_plat, masque, tableau
from .langue import tr
from .moteur import ErreurMoteur
from .selection_auto import apercu_baguette, baguette, combiner, nettoyer, points_du_trait
from .selection_texte import Analyse

COTE_IA = 1536            # l'image envoyée à SAM : au plus 1536 px de côté (SAM travaille de toute façon en ~1000 px)
MAX_POINTS = 40


def _empreinte(selection: QImage) -> tuple:
    """Pour savoir si la sélection a changé depuis le dernier trait (Ctrl+D, Ctrl+Z, autre outil…)."""
    m = masque(selection)
    return m.shape, int(m.sum(dtype=np.int64)), int(m[::7, ::5].sum(dtype=np.int64))


def _selection(a: np.ndarray) -> QImage:
    return _masque_vers_selection(a).convertToFormat(QImage.Format_ARGB32_Premultiplied)


class SelectionAuto(QObject):
    def __init__(self, fenetre):
        super().__init__(fenetre)
        self.f = fenetre
        self.c = fenetre.canevas
        # baguette
        self._b = None               # dict : source, point, mode, base, tolérance de départ
        # IA
        self._image_ia = None        # (clé de l'image, nom chez ComfyUI, échelle)
        self._session = None         # sélection rapide : base, mode, points +/-, clé de la sélection produite
        self._occupe = False
        self._en_attente = None      # dernière demande arrivée pendant un calcul
        self.c.baguette_clic.connect(self.baguette_clic)
        self.c.baguette_glisse.connect(self.baguette_glisse)
        self.c.baguette_lache.connect(self.baguette_lache)
        self.c.trait_ia.connect(self.trait_rapide)
        self.c.objet_ia.connect(self.objet)
        self.c.effacer_clic.connect(self.effacer_clic)
        self.c.texte_sel.connect(self.texte)
        self._t = None               # sélection de texte : dernier cadre (pour les clics de correction)

    # ------------------------------------------------------------------ outils communs
    def _historique(self, a: np.ndarray, titre: str):
        doc = self.f.doc
        from .fenetre import CommandeEtat
        avant = doc.etat()
        self.f.historique.push(CommandeEtat(doc, avant, (doc.calques, doc.actif, _selection(a)), titre))

    def options(self) -> dict:
        f = self.f
        return {"contigu": f.opt_contigu.isChecked(), "doux": f.opt_doux.isChecked(),
                "trous": f.opt_trous.isChecked()}

    def _source(self) -> np.ndarray:
        doc = self.f.doc
        img = doc.calque_actif.image if self.f.opt_echantillon.currentData() == "calque" else doc.image
        return tableau(img.convertToFormat(FORMAT_IMAGE))

    # ------------------------------------------------------------------ baguette magique
    def baguette_clic(self, pt: QPointF, mode: str):
        doc = self.f.doc
        if doc is None:
            return
        rgba = self._source()
        h, w = rgba.shape[:2]
        x, y = int(pt.x()), int(pt.y())
        if not (0 <= x < w and 0 <= y < h):
            return
        base = None if mode == "nouvelle" else masque(doc.selection)
        self._b = {"rgba": rgba, "x": x, "y": y, "mode": mode, "base": base,
                   "tol0": self.f.opt_tolerance.value(), "tol": self.f.opt_tolerance.value(), "bouge": False}
        self._apercu()

    def _apercu(self):
        b = self._b
        petit, fct = apercu_baguette(b["rgba"], b["x"], b["y"], b["tol"], **self.options())
        base = b["base"][::fct, ::fct][:petit.shape[0], :petit.shape[1]] if b["base"] is not None else None
        self.c.apercu_selection = _selection(combiner(base, petit, b["mode"]))
        self.c.update()

    def baguette_glisse(self, dx: float):
        if self._b is None:
            return
        tol = int(max(0, min(255, self._b["tol0"] + dx / 2)))
        if tol != self._b["tol"]:
            self._b["tol"], self._b["bouge"] = tol, True
            self.f.opt_tolerance.blockSignals(True)
            self.f.opt_tolerance.setValue(tol)
            self.f.opt_tolerance.blockSignals(False)
            self._apercu()
        self.f.statusBar().showMessage(tr("Tolérance : {t} (glisse à droite pour agrandir, à gauche pour réduire)",
                                          t=tol), 3000)

    def baguette_lache(self):
        b, self._b = self._b, None
        if b is None:
            return
        if b["bouge"]:
            self.f.reglages.setValue("baguette_tolerance", b["tol"])
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            a = baguette(b["rgba"], b["x"], b["y"], b["tol"], **self.options())
            self._historique(combiner(b["base"], a, b["mode"]), tr("Baguette magique"))
        finally:
            QApplication.restoreOverrideCursor()
            self.c.apercu_selection = None
            self.c.update()

    # ------------------------------------------------------------------ IA (SAM 3.1)
    def _verifier(self, titre: str) -> bool:
        if self.f.doc is None:
            return False
        if not recettes.sam_disponible():
            QMessageBox.information(self.f, titre, tr(
                "Cet outil a besoin du modèle SAM 3.1 (1,75 Go), qui n'est pas installé, ou le moteur IA n'est pas "
                "encore prêt. Menu IA > Installer le moteur IA permet de l'ajouter."))
            return False
        return True

    def trait_rapide(self, points: list, retirer: bool, nouveau: bool):
        """Comme Photoshop : chaque trait trouve SON objet, qui s'ajoute à la sélection (un trait sur un titre puis
        un trait autour d'une personne = le titre + la personne, pas un mélange des deux). Un trait avec Alt donne
        des points à exclure, appliqués à tous les objets de la sélection en cours."""
        titre = tr("Sélection rapide")
        if not points or not self._verifier(titre):
            self.c.trait_en_attente = None
            self.c.update()
            return
        doc = self.f.doc
        s = self._session
        if (s is None or nouveau or s["doc"] is not doc or s["taille"] != doc.taille()
                or s["empreinte"] != _empreinte(doc.selection)):
            # sélection changée ailleurs (Ctrl+D, Ctrl+Z, autre outil…) : nouvel objet
            mode = "ajouter" if nouveau else self.c.mode_forme
            s = self._session = {"doc": doc, "mode": mode, "groupes": [], "neg": [], "taille": doc.taille(),
                                 "empreinte": _empreinte(doc.selection),
                                 "base": None if mode == "nouvelle" else masque(doc.selection)}
        pas = max(8.0, self.c.taille_pinceau / 2)
        nouveaux = points_du_trait(points, pas, 16)
        if retirer:
            if not s["groupes"]:                # rien à corriger encore : un trait Alt seul ne fait rien
                self.c.trait_en_attente = None
                self.c.update()
                return
            s["neg"] = (s["neg"] + nouveaux)[-MAX_POINTS:]
        else:
            s["groupes"].append({"pos": nouveaux, "masque": None, "neg_n": 0})
        self.c.points_ia = [(QPointF(x, y), True) for g in s["groupes"] for x, y in g["pos"]] + \
                           [(QPointF(x, y), False) for x, y in s["neg"]]
        self._demander({"titre": titre, "doc": doc, "session": s, "mode": s["mode"], "base": s["base"]})

    # ------------------------------------------------------------------ sélection de texte (sans IA)
    def texte(self, quoi, mode: str, ctrl: bool):
        """Cadre : les lettres du cadre deviennent la sélection. Clic dans ce cadre ensuite : correction
        (Alt+clic enlève le morceau, Maj+clic l'ajoute ; Ctrl en plus : toute cette couleur du cadre)."""
        doc = self.f.doc
        if doc is None:
            return
        W, H = doc.taille()
        if isinstance(quoi, QRectF):
            r = quoi.normalized()
            x0, y0 = max(0, int(r.left())), max(0, int(r.top()))
            x1, y1 = min(W, int(np.ceil(r.right()))), min(H, int(np.ceil(r.bottom())))
            if x1 - x0 < 8 or y1 - y0 < 8:
                self.f.statusBar().showMessage(tr("Cadre trop petit : tire un cadre autour du texte, avec un peu de "
                                                  "fond tout autour."), 6000)
                return
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                rgba = tableau(doc.image.convertToFormat(FORMAT_IMAGE))[y0:y1, x0:x1]
                an = Analyse(a_plat(np.ascontiguousarray(rgba)))
            finally:
                QApplication.restoreOverrideCursor()
            base = None if mode == "nouvelle" else masque(doc.selection).copy()
            self._t = {"doc": doc, "rect": (x0, y0, x1, y1), "an": an, "base": base, "mode": mode}
            self._appliquer_texte(tr("Sélection de texte"))
            self.f.statusBar().showMessage(tr("Texte sélectionné. Pour corriger : Alt+clic sur un morceau en trop, "
                                              "Maj+clic sur un morceau oublié (Ctrl en plus : toute cette couleur)."),
                                           10000)
            return
        t = self._t
        x, y = int(quoi.x()), int(quoi.y())
        if t is None or t["doc"] is not doc or t.get("empreinte") != _empreinte(doc.selection) or not (
                t["rect"][0] <= x < t["rect"][2] and t["rect"][1] <= y < t["rect"][3]):
            self.f.statusBar().showMessage(tr("Tire d'abord un cadre autour du texte. Les clics servent ensuite à "
                                              "corriger, dans ce cadre : Alt+clic enlève un morceau, Maj+clic en "
                                              "ajoute un."), 10000)
            return
        if mode == "nouvelle":
            self.f.statusBar().showMessage(tr("Alt+clic : enlever ce morceau. Maj+clic : l'ajouter. Ctrl en plus : "
                                              "toute cette couleur du cadre."), 8000)
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            t["an"].corriger(x - t["rect"][0], y - t["rect"][1], ajouter=(mode == "ajouter"), toute_couleur=ctrl)
            self._appliquer_texte(tr("Sélection de texte : correction"))
        finally:
            QApplication.restoreOverrideCursor()

    def _appliquer_texte(self, titre: str):
        t, doc = self._t, self.f.doc
        x0, y0, x1, y1 = t["rect"]
        W, H = doc.taille()
        a = np.zeros((H, W), np.uint8)
        a[y0:y1, x0:x1] = t["an"].calculer(self.f.opt_pleines.isChecked())
        self._historique(combiner(t["base"], a, t["mode"]), titre)
        t["empreinte"] = _empreinte(doc.selection)

    def texte_relancer(self):
        """Case « Lettres pleines » changée : le dernier cadre est recalculé (s'il est toujours la sélection)."""
        t, doc = self._t, self.f.doc
        if t is not None and t["doc"] is doc and t.get("empreinte") == _empreinte(doc.selection):
            self._appliquer_texte(tr("Sélection de texte"))

    def fin_session(self):
        """Échap, autre outil, autre photo : la prochaine sélection rapide commence un nouvel objet."""
        self._session = None
        self.c.points_ia = []
        self.c.update()

    def objet(self, quoi, mode: str):
        titre = tr("Sélection d'objet")
        if not self._verifier(titre):
            self.c.trait_en_attente = None
            self.c.update()
            return
        doc = self.f.doc
        base = None if mode == "nouvelle" else masque(doc.selection)
        if isinstance(quoi, QRectF):
            r = quoi.normalized()
            g = {"pos": [], "cadre": (r.x(), r.y(), r.width(), r.height())}
        else:
            g = {"pos": [(int(quoi.x()), int(quoi.y()))]}
        g.update(masque=None, neg_n=0)
        session = {"doc": doc, "groupes": [g], "neg": []}       # demande seule, sans suite
        self._demander({"titre": titre, "doc": doc, "session": session, "mode": mode, "base": base, "seule": True})

    def effacer_clic(self, quoi):
        """Outil Effacer d'un clic : l'objet est détouré (SAM), un peu élargi (bord flou, cheveux), puis Effacer
        (analyse de l'ombre, propositions au choix)."""
        titre = tr("Effacer d'un clic")
        if not self._verifier(titre) or not self.f._verifier_verrou(tr("Effacer")):
            self.c.trait_en_attente = None
            self.c.update()
            return
        doc = self.f.doc
        if isinstance(quoi, QRectF):
            r = quoi.normalized()
            g = {"pos": [], "cadre": (r.x(), r.y(), r.width(), r.height())}
        else:
            g = {"pos": [(int(quoi.x()), int(quoi.y()))]}
        g.update(masque=None, neg_n=0)
        session = {"doc": doc, "groupes": [g], "neg": []}
        self._demander({"titre": titre, "doc": doc, "session": session, "mode": "nouvelle", "base": None,
                        "seule": True, "marge": True, "ensuite": self.f.ia_effacer})

    def _image(self, doc):
        """Image visible envoyée au moteur (une fois par version de l'image), réduite pour aller vite."""
        img = doc.image
        cle = (doc, doc.calques)                 # mêmes calques (objets fixes) = même image visible
        if self._image_ia is not None and self._image_ia[0][0] is doc and len(self._image_ia[0][1]) == len(
                doc.calques) and all(a is b for a, b in zip(self._image_ia[0][1], doc.calques)):
            return self._image_ia[1], self._image_ia[2]
        w, h = img.width(), img.height()
        e = min(1.0, COTE_IA / max(w, h))
        petit = img if e >= 1 else img.scaled(round(w * e), round(h * e), Qt.IgnoreAspectRatio,
                                              Qt.SmoothTransformation)
        import io
        from PIL import Image
        t = tableau(petit.convertToFormat(FORMAT_IMAGE))[:, :, :3]
        buf = io.BytesIO()
        Image.fromarray(np.ascontiguousarray(t), "RGB").save(buf, "PNG", compress_level=1)
        nom = self.f.moteur.envoyer_image(buf.getvalue())
        self._image_ia = (cle, nom, e)
        return nom, e

    def _demander(self, d: dict):
        if self._occupe:
            self._en_attente = d
            return
        self._occupe = True
        self._numero = getattr(self, "_numero", 0) + 1
        numero = self._numero
        self.f.statusBar().showMessage(tr("L'IA cherche l'objet…"))

        def lent():                              # autre calcul en cours (Effacer, Remplir…) : on attend son tour
            if self._occupe and self._numero == numero:
                self.f.statusBar().showMessage(tr("Le moteur IA finit un autre calcul (Effacer, Remplir…) : la "
                                                  "sélection arrivera juste après."))
        QTimer.singleShot(4000, lent)
        QApplication.setOverrideCursor(Qt.BusyCursor)
        doc = d["doc"]
        w, h = doc.taille()

        session = d["session"]
        # à calculer : les objets nouveaux, et ceux qui n'ont pas encore les derniers points à exclure
        neg_n = len(session["neg"])
        a_faire = [(k, dict(g)) for k, g in enumerate(session["groupes"])
                   if g["masque"] is None or (g["neg_n"] != neg_n and k >= len(session["groupes"]) - 8)]
        deja = [g["masque"] for g in session["groupes"]]
        neg_tous = list(session["neg"])

        def calcul(_progres):
            nom, e = self._image(doc)
            neg = [(x * e, y * e) for x, y in neg_tous]
            nouveaux = {}
            for k, g in a_faire:
                pos = [(x * e, y * e) for x, y in g["pos"]]
                cadre = None if g.get("cadre") is None else tuple(v * e for v in g["cadre"])
                prompt, sorties = recettes.segmenter(nom, pos, neg if pos else [], cadre)
                res = self.f.moteur.executer(prompt, sorties, threading.Event(), lambda *a: None)
                if not res:
                    raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
                img = QImage.fromData(res[0][1])
                if img.isNull():
                    raise ErreurMoteur(tr("Résultat illisible."))
                m = tableau(img.convertToFormat(FORMAT_IMAGE))[:, :, 0] > 127
                sh, sw = m.shape
                fx, fy = sw / (w * e), sh / (h * e)
                nouveaux[k] = nettoyer(m, [(int(x * fx), int(y * fy)) for x, y in pos])
            masques = [nouveaux.get(k, m) for k, m in enumerate(deja)]
            masques = [m for m in masques if m is not None]
            union = masques[0].copy()
            for m in masques[1:]:
                if m.shape == union.shape:
                    union |= m
            sh, sw = union.shape
            # retour à la taille de la photo, bord adouci par l'agrandissement
            q = QImage(np.ascontiguousarray(union.astype(np.uint8) * 255).data, sw, sh, sw, QImage.Format_Grayscale8)
            q = q.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(FORMAT_IMAGE)
            return nouveaux, tableau(q)[:, :, 0].copy()

        def fini():
            self._occupe = False
            QApplication.restoreOverrideCursor()
            suivant, self._en_attente = self._en_attente, None
            if suivant is not None:
                self._demander(suivant)
            else:
                self.c.trait_en_attente = None
                self.c.update()

        def ok(resultat):
            nouveaux, a = resultat
            for k, m in nouveaux.items():
                if k < len(session["groupes"]):
                    session["groupes"][k]["masque"] = m
                    session["groupes"][k]["neg_n"] = neg_n
            if doc is self.f.doc and a.any():
                if d.get("marge"):                   # Effacer d'un clic : un peu de marge autour de l'objet
                    from .choix_personnes import union
                    from .selection_auto import boucher_trous
                    h, w = a.shape
                    # l'objet entier : un détourage en anneau (contour d'un logo…) garde sinon son intérieur
                    a = union([boucher_trous(a > 127)], [True], max(4.0, max(w, h) / 200))
                self._historique(combiner(d["base"], a, d["mode"]), d["titre"])
                session["empreinte"] = _empreinte(doc.selection)
                self.f.statusBar().showMessage(tr("{titre} : fait. Ctrl+Z pour revenir.", titre=d["titre"]), 5000)
            elif doc is self.f.doc:
                self.f.statusBar().showMessage(tr("L'IA n'a rien trouvé à cet endroit."), 6000)
            fini()
            if d.get("ensuite") is not None and doc is self.f.doc and a.any():
                QTimer.singleShot(0, d["ensuite"])  # ex. Effacer d'un clic : Effacer, une fois la sélection posée

        def echec(message):
            fini()
            if message:
                QMessageBox.warning(self.f, d["titre"], message)

        self.f._tache(calcul, ok, echec).lancer()
