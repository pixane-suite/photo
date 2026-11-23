"""Onglets : plusieurs photos ouvertes à la fois, chacune avec son propre historique (Annuler / Rétablir).
Partie de la classe Fenetre (classe « mixin »)."""
from __future__ import annotations

from PySide6.QtGui import QUndoGroup, QUndoStack
from PySide6.QtWidgets import QMessageBox, QTabBar, QVBoxLayout, QWidget

from .langue import tr


class Onglets:
    def _init_onglets(self):
        self.groupe_historique = QUndoGroup(self)
        self._vide = QUndoStack(self)                  # historique quand aucune photo n'est ouverte
        self.groupe_historique.addStack(self._vide)
        self.groupe_historique.setActiveStack(self._vide)
        self._piles: dict = {}                        # id(doc) -> QUndoStack
        self._docs: list = []                         # documents, dans l'ordre des onglets
        self.barre_onglets = QTabBar()
        self.barre_onglets.setObjectName("onglets")
        self.barre_onglets.setTabsClosable(True)
        self.barre_onglets.setMovable(True)
        self.barre_onglets.setDocumentMode(True)
        self.barre_onglets.setExpanding(False)
        self.barre_onglets.setElideMode(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ElideMiddle)
        self.barre_onglets.currentChanged.connect(self._onglet_choisi)
        self.barre_onglets.tabCloseRequested.connect(self.fermer_onglet)
        self.barre_onglets.tabMoved.connect(self._onglet_deplace)
        self.barre_onglets.hide()

    def _centre_avec_onglets(self, canevas) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.barre_onglets)
        lay.addWidget(canevas, 1)
        return w

    @property
    def historique(self) -> QUndoStack:
        """Historique de la photo affichée."""
        return self.groupe_historique.activeStack() or self._vide

    def pile_de(self, doc) -> QUndoStack:
        return self._piles.get(id(doc), self._vide)

    @property
    def documents(self) -> list:
        return list(self._docs)

    def _installer_document(self, doc):
        """Nouvelle photo : un nouvel onglet (ou retour à son onglet si elle est déjà ouverte)."""
        if doc in self._docs:
            self.barre_onglets.setCurrentIndex(self._docs.index(doc))
            return
        pile = QUndoStack(self)
        pile.setUndoLimit(30)
        self.groupe_historique.addStack(pile)
        self._piles[id(doc)] = pile
        self._docs.append(doc)
        if getattr(doc, "instantane", None) is None:   # pinceau d'historique : la photo telle qu'à l'ouverture
            from PySide6.QtGui import QImage
            doc.instantane = (tuple(doc.calques), QImage(doc.image))
        if getattr(doc, "image_ouverture", None) is None:   # Avant / après : la photo telle qu'à l'ouverture
            from PySide6.QtGui import QImage
            doc.image_ouverture = QImage(doc.image)
        doc.change.connect(self._titres_onglets)
        self.barre_onglets.blockSignals(True)
        k = self.barre_onglets.addTab(self._nom_onglet(doc))
        self.barre_onglets.blockSignals(False)
        self.barre_onglets.setVisible(len(self._docs) > 1)
        self.barre_onglets.setCurrentIndex(k)
        self._onglet_choisi(k)

    def _nom_onglet(self, doc) -> str:
        nom = doc.nom_affiche()
        return nom + (" •" if doc.modifie else "")

    def _titres_onglets(self, *_):
        for k, d in enumerate(self._docs):
            t = self._nom_onglet(d)
            if self.barre_onglets.tabText(k) != t:
                self.barre_onglets.setTabText(k, t)
            self.barre_onglets.setTabToolTip(k, str(d.chemin) if d.chemin else d.nom_affiche())

    def _onglet_choisi(self, k: int):
        if not (0 <= k < len(self._docs)):
            return
        doc = self._docs[k]
        if doc is self.doc:
            return
        self.groupe_historique.setActiveStack(self._piles[id(doc)])
        self._montrer_document(doc)

    def _onglet_deplace(self, de: int, vers: int):
        d = self._docs.pop(de)
        self._docs.insert(vers, d)

    def fermer_onglet(self, k: int | None = None) -> bool:
        """Ferme la photo (en proposant d'enregistrer si elle a changé)."""
        if k is None:
            k = self._docs.index(self.doc) if self.doc in self._docs else -1
        if not (0 <= k < len(self._docs)):
            return True
        doc = self._docs[k]
        if doc is not self.doc:
            self.barre_onglets.setCurrentIndex(k)
        if not self._peut_fermer():
            return False
        if hasattr(self, "_recuperation"):
            self._recuperation.oublier(doc)
        pile = self._piles.pop(id(doc))
        self.groupe_historique.removeStack(pile)
        pile.deleteLater()
        self._docs.pop(k)
        self.barre_onglets.blockSignals(True)
        self.barre_onglets.removeTab(k)
        self.barre_onglets.blockSignals(False)
        self.barre_onglets.setVisible(len(self._docs) > 1)
        if self._docs:
            k = min(k, len(self._docs) - 1)
            self.barre_onglets.setCurrentIndex(k)
            self.doc = None
            self._onglet_choisi(k)
        else:
            self.groupe_historique.setActiveStack(self._vide)
            self._montrer_document(None)
        return True

    def _peut_fermer_tout(self) -> bool:
        """Avant de quitter : chaque photo modifiée, l'une après l'autre."""
        for doc in list(self._docs):
            if doc.modifie:
                self.barre_onglets.setCurrentIndex(self._docs.index(doc))
                if not self._peut_fermer():
                    return False
                doc.modifie = False
        return True

    def onglet_suivant(self, sens: int = 1):
        n = len(self._docs)
        if n > 1:
            self.barre_onglets.setCurrentIndex((self.barre_onglets.currentIndex() + sens) % n)
