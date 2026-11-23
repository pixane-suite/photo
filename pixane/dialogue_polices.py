"""Fenêtre « Trouver une police semblable » : les lettres sélectionnées dans l'image, les lettres tapées par
l'utilisateur, puis les polices installées les plus proches (écrites avec ces lettres, pour comparer d'un coup
d'œil). Un clic applique la police au texte choisi, ou crée un texte avec elle."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QProgressBar, QPushButton, QVBoxLayout)

from . import polices_semblables as ps
from .langue import tr

ECHANTILLON = QSize(460, 64)


def echantillon(texte: str, r: ps.Resultat, taille: QSize = ECHANTILLON) -> QPixmap:
    """Le texte écrit avec cette police, noir sur blanc, ajusté à la case."""
    img = QImage(taille, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor(255, 255, 255))
    p = QPainter(img)
    p.setRenderHint(QPainter.TextAntialiasing)
    f = r.police(48)
    p.setFont(f)
    rect = p.boundingRect(QRect(0, 0, 10000, 1000), Qt.AlignLeft | Qt.AlignTop, texte)
    k = min((taille.width() - 16) / max(1, rect.width()), (taille.height() - 8) / max(1, rect.height()), 1.5)
    f.setPixelSize(max(6, int(48 * k)))
    p.setFont(f)
    p.setPen(QColor(20, 20, 20))
    p.drawText(QRect(8, 0, taille.width() - 16, taille.height()), Qt.AlignVCenter | Qt.AlignLeft, texte)
    p.end()
    return QPixmap.fromImage(img)


class FenetrePolices(QDialog):
    def __init__(self, lettres_image: QImage, masque: np.ndarray, texte_depart: str, peut_appliquer: bool,
                 parent=None, remplacer: bool = False):
        super().__init__(parent)
        self.remplacer = remplacer             # IA > Remplacer un texte : nouveau texte + bouton Remplacer
        self.setWindowTitle(tr("Remplacer un texte") if remplacer else tr("Trouver une police semblable"))
        self.masque = masque
        self.resultats: list[ps.Resultat] = []
        self.choisi: ps.Resultat | None = None
        self.action = None                     # "appliquer" ou "creer"
        self._arret = False
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("Les lettres de l'image :")))
        vue = QLabel()
        pm = QPixmap.fromImage(lettres_image)
        if pm.height() > 90 or pm.width() > 560:
            pm = pm.scaled(560, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        vue.setPixmap(pm)
        vue.setStyleSheet("background: white; padding: 6px;")
        vue.setAlignment(Qt.AlignCenter)
        lay.addWidget(vue)
        ligne = QHBoxLayout()
        ligne.addWidget(QLabel(tr("Tape les mêmes lettres :")))
        self.texte = QLineEdit(texte_depart)
        self.texte.setPlaceholderText(tr("ex. DISCO"))
        self.texte.returnPressed.connect(self.chercher)
        ligne.addWidget(self.texte, 1)
        self.b_chercher = QPushButton(tr("Chercher"))
        self.b_chercher.setDefault(True)
        self.b_chercher.clicked.connect(self.chercher)
        ligne.addWidget(self.b_chercher)
        lay.addLayout(ligne)
        aide = QLabel(tr("Ci-dessus, en noir : les lettres que Pixane Photo a prises (vérifie qu'elles sont "
                         "complètes). Tape exactement ces lettres, dans le même ordre, avec les majuscules et les "
                         "minuscules ; sépare les lignes par « / »."))
        aide.setObjectName("discret")
        aide.setWordWrap(True)
        lay.addWidget(aide)
        self.nouveau = QLineEdit()
        if remplacer:
            ligne2 = QHBoxLayout()
            ligne2.addWidget(QLabel(tr("Nouveau texte :")))
            self.nouveau.setPlaceholderText(tr("ex. SUMMER / 2026"))
            self.nouveau.setToolTip(tr("Le texte qui remplacera celui de la photo ; sépare les lignes par « / »."))
            self.nouveau.textChanged.connect(self._maj_boutons)
            ligne2.addWidget(self.nouveau, 1)
            lay.addLayout(ligne2)
        self.progres = QProgressBar()
        self.progres.setVisible(False)
        lay.addWidget(self.progres)
        self.etat = QLabel()
        self.etat.setWordWrap(True)
        self.etat.setObjectName("discret")
        lay.addWidget(self.etat)
        self.liste = QListWidget()
        self.liste.setIconSize(ECHANTILLON)
        self.liste.setMinimumSize(ECHANTILLON.width() + 220, 380)
        self.liste.currentRowChanged.connect(self._maj_boutons)
        self.liste.itemDoubleClicked.connect(lambda _it: self._finir(
            "remplacer" if remplacer else "appliquer" if peut_appliquer else "creer"))
        lay.addWidget(self.liste, 1)
        bas = QHBoxLayout()
        self.b_appliquer = QPushButton(tr("Appliquer au texte choisi"))
        self.b_appliquer.setVisible(peut_appliquer)
        self.b_appliquer.clicked.connect(lambda: self._finir("appliquer"))
        self.b_creer = QPushButton(tr("Créer un texte avec cette police"))
        self.b_creer.setToolTip(tr("Nouveau calque de texte, à la place des lettres sélectionnées, avec les lettres "
                                   "tapées. Les lettres de l'image restent : efface-les ensuite si besoin."))
        self.b_creer.clicked.connect(lambda: self._finir("creer"))
        self.b_copier = QPushButton(tr("Copier le nom"))
        self.b_copier.clicked.connect(self._copier)
        self.b_installer = QPushButton(tr("Télécharger et installer"))
        self.b_installer.setToolTip(tr("Police gratuite de Google Fonts : tous ses styles sont téléchargés et installés "
                                       "dans Windows pour ton compte (utilisables aussi dans tes autres programmes)."))
        self.b_installer.clicked.connect(self._installer)
        fermer = QPushButton(tr("Fermer"))
        fermer.clicked.connect(self.reject)
        self.b_remplacer = QPushButton(tr("Effacer et remplacer"))
        self.b_remplacer.setObjectName("principal")
        self.b_remplacer.setToolTip(tr("L'IA efface le texte de la photo (choix parmi ses propositions), puis le "
                                       "nouveau texte est posé à sa place, dans cette police, en calque Texte "
                                       "modifiable."))
        self.b_remplacer.clicked.connect(lambda: self._finir("remplacer"))
        self.b_remplacer.setVisible(remplacer)
        if remplacer:
            self.b_appliquer.setVisible(False)
            self.b_creer.setVisible(False)
            self.b_chercher.setDefault(False)    # un seul bouton principal : Effacer et remplacer
            self.b_chercher.setAutoDefault(False)
            self.nouveau.setFocus()
        self.b_chercher.setMinimumWidth(self.b_chercher.fontMetrics().horizontalAdvance(self.b_chercher.text()) + 40)
        for b in (self.b_remplacer, self.b_appliquer, self.b_creer, self.b_copier, self.b_installer):
            bas.addWidget(b)
        bas.addStretch(1)
        bas.addWidget(fermer)
        lay.addLayout(bas)
        self._maj_boutons()
        self.resize(760, 700 if remplacer else 640)
        # case vide : Windows lit les lettres de l'image (OCR intégré, sans téléchargement) ; l'utilisateur vérifie
        self._lecteur = None
        from . import lecture_texte
        if not texte_depart.strip() and lecture_texte.disponible():
            self._lecteur = lecture_texte.Lecteur(self)
            self._lecteur.fini.connect(self._lu)
            if self._lecteur.lire(masque):
                self.texte.setPlaceholderText(tr("Lecture des lettres…"))
                self.etat.setText(tr("Windows lit les lettres de l'image…"))

    def _lu(self, texte: str) -> None:
        self.texte.setPlaceholderText(tr("ex. DISCO"))
        if texte and not self.texte.text().strip():
            self.texte.setText(texte)
            self.etat.setText(tr("Lettres lues par Windows : vérifie-les (et corrige si besoin), puis Chercher."))
            if self.remplacer:                   # tout de suite : la police est trouvée pendant qu'on tape
                self.chercher()
        elif not self.texte.text().strip():
            self.etat.setText(tr("Windows n'a pas pu lire les lettres : tape-les."))

    def done(self, r: int) -> None:
        if self._lecteur is not None:
            self._lecteur.arreter()
        from . import polices_google
        polices_google.liberer()                 # polices Google chargées pour la recherche : retirées
        super().done(r)

    def texte_nouveau(self) -> str:
        return "\n".join(l.strip() for l in self.nouveau.text().split("/") if l.strip())

    def lettres(self) -> str:
        return "\n".join(l.strip() for l in self.texte.text().split("/") if l.strip())

    def chercher(self) -> None:
        texte = self.lettres()
        if not texte:
            self.etat.setText(tr("Tape d'abord les lettres que tu vois dans l'image."))
            return
        if self.b_chercher.text() == tr("Arrêter"):
            self._arret = True
            return
        self._arret = False
        self.b_chercher.setText(tr("Arrêter"))
        self.texte.setEnabled(False)
        self.liste.clear()
        vues = ps.compter_lettres(self.masque)
        tapees = [len(l) for l in ps.sans_espaces(texte)]
        avertir = []
        if vues and vues != tapees:
            if len(vues) != len(tapees):
                avertir.append(tr("L'image semble avoir {n} ligne(s), tu en as tapé {m}.", n=len(vues), m=len(tapees)))
            else:
                avertir.append(tr("L'image semble avoir {n} lettres, tu en as tapé {m} (sans les espaces) : "
                                  "vérifie les lettres tapées, la comparaison est moins précise.",
                                  n=sum(vues), m=sum(tapees)))
        self.progres.setVisible(True)
        self.progres.setValue(0)
        manquantes = sum(1 for f in ps.familles() if f not in ps.memoire())
        self.etat.setText(tr("Première fois : Pixane Photo prépare tes {n} polices, une seule fois. La durée dépend de leur "
                             "nombre (environ 1 min 20 pour 1 200 polices)…",
                             n=manquantes) if manquantes > 50 else tr("Recherche…"))
        from . import polices_google
        if polices_google.active() and polices_google.en_preparation():
            avertir.append(tr("Polices Google Fonts encore en préparation : celles déjà prêtes sont comparées."))

        def progres(fait, total):
            self.progres.setMaximum(total)
            self.progres.setValue(fait)
            QApplication.processEvents()
            return not self._arret
        infos = {}
        try:
            self.resultats = ps.chercher(self.masque, texte, 12, progres, infos=infos)
        finally:
            self.b_chercher.setText(tr("Chercher"))
            self.texte.setEnabled(True)
            self.progres.setVisible(False)
        if self._arret:
            self.etat.setText(tr("Recherche arrêtée."))
            return
        compare = infos.get("texte", texte)
        if compare != texte:
            avertir.append(tr("Les lettres de l'image semblent en majuscules : recherche faite avec « {t} ».",
                              t=compare.replace("\n", " / ")))
            self.texte.setText(compare.replace("\n", " / "))     # « Créer un texte » écrira ces lettres
        for r in self.resultats:
            it = QListWidgetItem(QIcon(echantillon(compare, r)), self._libelle(r))
            it.setData(Qt.UserRole, r)
            self.liste.addItem(it)
        if self.resultats:
            self.liste.setCurrentRow(0)
            self.etat.setText(" ".join(avertir + [tr("Les plus proches d'abord. Double-clic pour l'utiliser.")]))
        else:
            self.etat.setText(" ".join(avertir + [tr("Rien trouvé : vérifie les lettres tapées et la sélection "
                                                     "(les lettres seules).")]))

    @staticmethod
    def _libelle(r: ps.Resultat) -> str:
        style = " ".join(x for x in (tr("gras") if r.gras else "", tr("italique") if r.italique else "") if x)
        texte = f"{r.famille}{'  ·  ' + style if style else ''}\n" + tr("ressemblance : {n} %", n=round(r.score))
        if r.google:
            texte += "\n" + tr("gratuite, pas installée (Google Fonts, {licence})", licence=r.licence or "OFL")
        return texte

    def _maj_boutons(self, *_a) -> None:
        it = self.liste.currentItem()
        self.choisi = it.data(Qt.UserRole) if it is not None else None
        for b in (self.b_appliquer, self.b_creer, self.b_copier):
            b.setEnabled(self.choisi is not None)
        self.b_remplacer.setEnabled(self.choisi is not None and bool(self.texte_nouveau()))
        self.b_installer.setVisible(self.choisi is not None and bool(self.choisi.google))

    def _installer(self) -> bool:
        """Police Google choisie : téléchargée et installée pour l'utilisateur ; elle devient une police installée."""
        r = self.choisi
        if r is None or not r.google:
            return True
        from . import polices_google
        self.etat.setText(tr("Téléchargement et installation de {nom}…", nom=r.famille))
        self.progres.setVisible(True)
        self.progres.setValue(0)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        def progres(fait, total):
            self.progres.setMaximum(total)
            self.progres.setValue(fait)
            QApplication.processEvents()
        try:
            famille, fichiers = polices_google.installer(r.google, progres)
        except OSError as e:
            self.etat.setText(tr("Installation impossible : {erreur}", erreur=str(e)))
            return False
        finally:
            QApplication.restoreOverrideCursor()
            self.progres.setVisible(False)
        if not fichiers:
            self.etat.setText(tr("Installation impossible : aucun fichier de police reçu."))
            return False
        r.famille, r.google = famille, ""
        it = self.liste.currentItem()
        if it is not None:
            it.setText(self._libelle(r))
        self._maj_boutons()
        self.etat.setText(tr("{nom} est installée ({n} styles) : utilisable dans Pixane Photo et tes autres "
                             "programmes.", nom=famille, n=len(fichiers)))
        return True

    def _copier(self) -> None:
        if self.choisi is not None:
            QApplication.clipboard().setText(self.choisi.famille)
            self.etat.setText(tr("Nom copié : {nom}", nom=self.choisi.famille))

    def _finir(self, action: str) -> None:
        if action == "remplacer" and not self.texte_nouveau():
            self.etat.setText(tr("Tape d'abord le nouveau texte."))
            self.nouveau.setFocus()
            return
        if self.choisi is not None:
            if self.choisi.google and not self._installer():     # police Google : installée d'abord
                return
            self.action = action
            self.accept()
