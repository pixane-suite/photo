"""Enregistrement automatique et récupération après un plantage.

Toutes les quelques minutes, chaque photo modifiée est copiée (format .piximg : calques, textes, styles, masques…)
dans %LOCALAPPDATA%\\Pixane\\recuperation, en arrière-plan. La copie est effacée quand la photo est enregistrée ou
fermée, et quand Pixane se ferme normalement. Au démarrage, s'il reste des copies d'un Pixane qui ne s'est pas
fermé (plantage, coupure de courant), Pixane propose de les rouvrir.
Chaque copie porte le numéro du processus qui l'a faite : deux Pixane ouverts en même temps ne se gênent pas.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

from .langue import tr


def dossier() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "recuperation"
    if os.environ.get("PIXANE_REGLAGES"):            # essais : à part
        nom += "-" + os.environ["PIXANE_REGLAGES"]
    return base / nom


def processus_vivant(pid: int) -> bool:
    if pid == os.getpid():
        return True
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    ok = k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return bool(ok) and code.value == 259          # STILL_ACTIVE


class Recuperation(QObject):
    ecrit = Signal(str)                             # chemin de la copie (pour les essais)

    def __init__(self, fenetre, minutes: float | None = None):
        super().__init__(fenetre)
        self.f = fenetre
        self.dossier = dossier()
        self._vus: dict = {}                       # id(doc) -> (ident du fichier, calques déjà copiés)
        self._en_cours = False
        if minutes is None:
            minutes = float(fenetre.reglages.value("recuperation_minutes", 3))
        self.minuterie = QTimer(self)
        self.minuterie.setInterval(max(10, int(minutes * 60 * 1000)))
        self.minuterie.timeout.connect(self.copier)
        if minutes > 0:
            self.minuterie.start()

    def definir_minutes(self, minutes: float):
        """Préférences > Enregistrement : fréquence de la copie (0 : jamais)."""
        self.minuterie.stop()
        if minutes > 0:
            self.minuterie.setInterval(max(10, int(minutes * 60 * 1000)))
            self.minuterie.start()

    def _ident(self, doc) -> str:
        if id(doc) not in self._vus:
            self._vus[id(doc)] = (f"{os.getpid()}-{uuid.uuid4().hex[:8]}", None)
        return self._vus[id(doc)][0]

    def copier(self):
        """Copie les photos modifiées depuis la dernière copie (l'écriture se fait en arrière-plan)."""
        if self._en_cours:
            return
        travail = []
        for doc in self.f.documents:
            ident = self._ident(doc)
            deja = self._vus[id(doc)][1]
            if not doc.modifie or deja is doc.calques:
                continue
            self._vus[id(doc)] = (ident, doc.calques)
            infos = {"chemin": str(doc.chemin) if doc.chemin else None,
                     "nom": doc.nom_affiche(),
                     "date": time.strftime("%d/%m/%Y %H:%M"), "pid": os.getpid(),
                     "dpi": doc.dpi, "mode": doc.mode, "reperes": [list(r) for r in doc.reperes]}
            travail.append((ident, doc.calques, doc.image.copy(), infos))
        if not travail:
            return
        self._en_cours = True
        threading.Thread(target=self._ecrire, args=(travail,), daemon=True).start()

    def _ecrire(self, travail):
        from .document import ecrire_ora
        try:
            self.dossier.mkdir(parents=True, exist_ok=True)
            for ident, calques, fusion, infos in travail:
                chemin = self.dossier / f"{ident}.piximg"
                try:
                    ecrire_ora(chemin, calques, fusion, natif=True, reperes=infos.get("reperes"),
                               dpi=infos.get("dpi", 72.0), mode=infos.get("mode", "rvb"))
                    (self.dossier / f"{ident}.json").write_text(json.dumps(infos, ensure_ascii=False),
                                                                encoding="utf-8")
                    self.ecrit.emit(str(chemin))
                except Exception:
                    pass                               # disque plein, droits… : on réessaiera plus tard
        finally:
            self._en_cours = False

    def oublier(self, doc):
        """Photo enregistrée ou fermée : sa copie ne sert plus."""
        v = self._vus.pop(id(doc), None)
        if v is not None:
            self._effacer(v[0])

    def enregistree(self, doc):
        v = self._vus.get(id(doc))
        if v is not None:
            self._effacer(v[0])
            self._vus[id(doc)] = (v[0], doc.calques)

    def _effacer(self, ident: str):
        for ext in (".piximg", ".json", ".piximg.tmp"):
            try:
                (self.dossier / f"{ident}{ext}").unlink()
            except OSError:
                pass

    def tout_effacer(self):
        """Fermeture normale de Pixane."""
        self.minuterie.stop()
        for ident, _c in list(self._vus.values()):
            self._effacer(ident)
        self._vus.clear()

    # ---------------------------------------------------------------- au démarrage
    def restes(self) -> list[tuple[Path, dict]]:
        """Copies laissées par un Pixane qui ne tourne plus."""
        res = []
        if not self.dossier.is_dir():
            return res
        for j in sorted(self.dossier.glob("*.json")):
            try:
                infos = json.loads(j.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            chr_ = j.with_suffix(".piximg")
            if chr_.is_file() and not processus_vivant(int(infos.get("pid", 0))):
                res.append((chr_, infos))
        return res

    def proposer(self):
        restes = self.restes()
        if not restes:
            return
        liste = "\n".join(f"• {i.get('nom')}  ({tr('copie du {date}', date=i.get('date', '?'))})" for _c, i in restes)
        rep = QMessageBox.question(self.f, tr("Récupération"), tr(
            "Pixane Photo ne s'est pas fermé normalement la dernière fois.\n\nPhotos récupérées (copies automatiques) :\n"
            "{liste}\n\nLes rouvrir ?\n(« Non » les efface.)", liste=liste),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        for chemin, infos in restes:
            if rep == QMessageBox.Yes:
                self.rouvrir(chemin, infos)
            ident = chemin.stem
            self._effacer(ident)

    def rouvrir(self, chemin: Path, infos: dict):
        from .document import Document
        try:
            doc = Document.ouvrir(chemin)
        except Exception as e:
            QMessageBox.warning(self.f, tr("Récupération"), tr("Impossible de rouvrir la copie :\n{erreur}",
                                                               erreur=e))
            return
        doc.chemin = Path(infos["chemin"]) if infos.get("chemin") else None
        doc.modifie = True
        self.f._installer_document(doc)
        self.f.statusBar().showMessage(tr("Photo récupérée : {nom}. Pense à l'enregistrer.",
                                          nom=infos.get("nom", "")), 10000)
