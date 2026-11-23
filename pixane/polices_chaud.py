"""Polices ajoutées pendant que Pixane Photo tourne : les dossiers de polices de Windows (C:\\Windows\\Fonts et celui
du compte, %LOCALAPPDATA%\\Microsoft\\Windows\\Fonts) sont surveillés ; un fichier de police qui arrive est chargé
tout de suite (QFontDatabase.addApplicationFont) : il apparaît dans la liste des polices sans redémarrer."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal
from PySide6.QtGui import QFontDatabase

from . import styles_polices

EXTENSIONS = (".ttf", ".otf", ".ttc", ".otc")


def _fichiers(dossiers) -> set[str]:
    vus = set()
    for d in dossiers:
        try:
            vus |= {str(f).lower() for f in Path(d).iterdir() if f.suffix.lower() in EXTENSIONS}
        except OSError:
            pass
    return vus


class Surveillance(QObject):
    """nouvelles(list[str]) : familles ajoutées (après le chargement)."""
    nouvelles = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dossiers = [str(d) for d in styles_polices._dossiers() if d.is_dir()]
        self.connus = _fichiers(self.dossiers)
        self.chargees: dict[str, int] = {}            # fichier -> identifiant Qt (pour le retirer s'il disparaît)
        self.veille = QFileSystemWatcher(self.dossiers, self)
        self.attente = QTimer(self)
        self.attente.setSingleShot(True)
        self.attente.setInterval(1500)                # l'installation copie puis inscrit : on attend qu'elle finisse
        self.attente.timeout.connect(self.verifier)
        self.veille.directoryChanged.connect(lambda _d: self.attente.start())

    def verifier(self) -> list[str]:
        maintenant = _fichiers(self.dossiers)
        familles = []
        for f in sorted(maintenant - self.connus):
            ident = QFontDatabase.addApplicationFont(f)
            if ident >= 0:
                self.chargees[f] = ident
                familles += QFontDatabase.applicationFontFamilies(ident)
        for f in self.connus - maintenant:            # police retirée : retirée aussi de Pixane (si chargée ici)
            if f in self.chargees:
                QFontDatabase.removeApplicationFont(self.chargees.pop(f))
        changement = maintenant != self.connus
        self.connus = maintenant
        if changement:
            styles_polices.oublier()
        if familles:
            self.nouvelles.emit(sorted(set(familles)))
        return familles
