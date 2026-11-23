"""Lire les lettres d'une image avec l'OCR intégré à Windows 10 / 11 (Windows.Media.Ocr), sans rien installer :
un petit script PowerShell est lancé en arrière-plan (QProcess), le texte lu revient en quelques secondes.
Sert à pré-remplir « Tape les mêmes lettres » de Trouver une police semblable ; l'utilisateur vérifie."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QProcess, Signal

SCRIPT = r'''param([string]$Chemin)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Attendre($op, [Type]$type) {
    $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
    $t.Wait() | Out-Null
    $t.Result
}
$f = Attendre ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Chemin)) ([Windows.Storage.StorageFile])
$flux = Attendre ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$dec = Attendre ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($flux)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Attendre ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$moteur = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$res = Attendre ($moteur.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$flux.Dispose()
[Console]::OutputEncoding = [Text.Encoding]::UTF8
foreach ($l in $res.Lines) { $l.Text }
'''


def disponible() -> bool:
    return sys.platform == "win32"


def _seuil_mots(ecarts: list[int], h: int) -> float:
    """Écart au-delà duquel deux lettres sont dans deux mots : le plus grand saut entre les écarts triés (les écarts
    entre les lettres d'un côté, entre les mots de l'autre), sinon un écart d'un tiers de la hauteur."""
    t = sorted(e for e in ecarts)
    fixe = 0.35 * h
    if len(t) < 2:
        return fixe
    meilleur, seuil = 1.0, fixe
    for a, b in zip(t, t[1:]):
        r = (b + 1) / (max(a, 0) + 1)
        if r > meilleur and b > 0.2 * h:
            meilleur, seuil = r, (a + b) / 2
    return seuil if meilleur > 1.4 else (fixe if t[-1] > fixe else float("inf"))


def image_pour_lecture(masque: np.ndarray) -> np.ndarray:
    """Les lettres du masque en noir sur blanc, à une hauteur que l'OCR lit bien, et resserrées : un texte très
    espacé (« M a n   I n ») est mal lu tel quel. Les espaces entre les mots restent."""
    from . import polices_semblables as ps
    m = masque.astype(np.float32)
    if m.max() > 1:
        m /= 255
    c = ps._recadrer(m)
    if c is None:
        return np.full((40, 40), 255, np.uint8)
    lignes = []
    for y0, y1 in ps._lignes(c):
        bloc = c[y0:y1]
        lettres, xs = ps._lettres_ligne(bloc, avec_x=True)
        if not lettres:
            continue
        h = lettres[0].shape[0]
        ecarts = [xs[k + 1][0] - xs[k][1] for k in range(len(xs) - 1)]   # pour retrouver les espaces entre les mots
        seuil = _seuil_mots(ecarts, h)
        morceaux = []
        for k, l in enumerate(lettres):
            morceaux.append(l)
            if k < len(lettres) - 1:
                larg = round(0.45 * h) if ecarts[k] > seuil else min(ecarts[k], round(0.08 * h))
                morceaux.append(np.zeros((h, max(1, larg)), np.float32))
        lignes.append(np.hstack(morceaux))
    if not lignes:
        return np.full((40, 40), 255, np.uint8)
    from PIL import Image
    H = 60
    res = []
    for l in lignes:
        w = max(1, round(l.shape[1] * H / l.shape[0]))
        res.append(np.asarray(Image.fromarray((l * 255).astype(np.uint8)).resize((w, H), Image.LANCZOS)))
    W = max(r.shape[1] for r in res) + 2 * H
    toile = np.zeros((len(res) * int(H * 1.6) + H, W), np.uint8)
    for n, r in enumerate(res):
        y = H // 2 + n * int(H * 1.6)
        toile[y:y + H, H:H + r.shape[1]] = r
    return 255 - toile


class Lecteur(QObject):
    """lire(masque) : lit en arrière-plan ; fini(texte) ("" si rien lu ou si la lecture n'est pas possible)."""
    fini = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: QProcess | None = None
        self._dossier = Path(tempfile.mkdtemp(prefix="pixane-lecture-"))

    def lire(self, masque: np.ndarray) -> bool:
        if not disponible():
            return False
        from PIL import Image
        try:
            (self._dossier / "lire.ps1").write_text(SCRIPT, encoding="utf-8-sig")
            Image.fromarray(image_pour_lecture(masque)).save(self._dossier / "lettres.png")
        except OSError:
            return False
        self._proc = QProcess(self)
        self._proc.finished.connect(self._fin)
        self._proc.errorOccurred.connect(lambda *_: self.fini.emit(""))
        self._proc.start("powershell.exe", ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                            "-File", str(self._dossier / "lire.ps1"),
                                            str(self._dossier / "lettres.png")])
        return True

    def _fin(self, code, _etat):
        texte = ""
        if code == 0 and self._proc is not None:
            sortie = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
            texte = " / ".join(" ".join(l.split()) for l in sortie.splitlines() if l.strip())
        self.fini.emit(texte)

    def arreter(self) -> None:
        if self._proc is not None and self._proc.state() != QProcess.NotRunning:
            self._proc.kill()
            self._proc.waitForFinished(2000)
        for f in self._dossier.glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            os.rmdir(self._dossier)
        except OSError:
            pass
