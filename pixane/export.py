"""Exporter pour le web (format, taille, qualité, poids estimé, sans métadonnées) et traitement par lot (tout un
dossier : taille, réglage automatique, upscale IA, arrière-plan supprimé, format)."""
from __future__ import annotations

import io
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QProgressBar, QPushButton, QSlider, QSpinBox, QVBoxLayout,
                               QWidget)

from .langue import tr

FORMATS = {"jpg": ("JPEG", ".jpg"), "webp": ("WebP", ".webp"), "png": ("PNG", ".png")}


def taille_lisible(n: int) -> str:
    if n < 1024:
        return f"{n} o"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} Ko"
    return f"{n / 1024 / 1024:.2f} Mo"


def preparer(im: Image.Image, cote_max: int | None) -> Image.Image:
    """Réduit l'image pour que son plus grand côté fasse au plus cote_max (jamais agrandie)."""
    if cote_max and max(im.size) > cote_max:
        k = cote_max / max(im.size)
        im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    return im


def encoder(im: Image.Image, fmt: str, qualite: int, metadonnees: bool = False, exif: bytes | None = None,
            icc: bytes | None = None) -> bytes:
    """Image -> octets du fichier. Sans métadonnées : ni EXIF (appareil, lieu…), ni profil couleur (sRGB supposé)."""
    options = {}
    if metadonnees:
        if exif:
            options["exif"] = exif
        if icc:
            options["icc_profile"] = icc
    opaque = im.mode != "RGBA" or bool(np.all(np.asarray(im)[:, :, 3] == 255))
    if fmt == "jpg":
        if not opaque:                                  # JPEG sans transparence : fond blanc
            fond = Image.new("RGB", im.size, (255, 255, 255))
            fond.paste(im, mask=im.getchannel("A"))
            im = fond
        im = im.convert("RGB")
        options.update(quality=int(qualite), optimize=True, progressive=True,
                       subsampling=0 if qualite >= 90 else 2)
        nom = "JPEG"
    elif fmt == "webp":
        if opaque:
            im = im.convert("RGB")
        options.update(quality=int(qualite), method=6)
        nom = "WEBP"
    else:
        if opaque:
            im = im.convert("RGB")
        options.update(optimize=True)
        nom = "PNG"
    tampon = io.BytesIO()
    im.save(tampon, nom, **options)
    return tampon.getvalue()


class DialogueExport(QDialog):
    """Exporter pour le web : réglages, poids estimé en direct."""

    def __init__(self, fenetre, image: Image.Image, nom: str, exif=None, icc=None):
        super().__init__(fenetre)
        self.setWindowTitle(tr("Exporter pour le web"))
        self.image, self.exif, self.icc = image, exif, icc
        self.nom = nom
        self.reglages = fenetre.reglages
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.format = QComboBox()
        for k, (n, _e) in FORMATS.items():
            self.format.addItem(n, k)
        self.format.setCurrentIndex(max(0, self.format.findData(self.reglages.value("export_format", "jpg"))))
        form.addRow(tr("Format"), self.format)
        ligne = QHBoxLayout()
        self.cote = QSpinBox()
        self.cote.setRange(16, 20000)
        self.cote.setSuffix(" px")
        self.cote.setValue(min(max(image.size), int(self.reglages.value("export_cote", 2048))))
        self.cote_case = QCheckBox(tr("Réduire : plus grand côté"))
        self.cote_case.setChecked(self.reglages.value("export_reduire", "true") == "true")
        ligne.addWidget(self.cote_case)
        ligne.addWidget(self.cote)
        ligne.addStretch(1)
        form.addRow(tr("Taille"), ligne)
        ligne = QHBoxLayout()
        self.qualite = QSlider(Qt.Horizontal)
        self.qualite.setRange(30, 100)
        self.qualite.setValue(int(self.reglages.value("export_qualite", 82)))
        self.v_qualite = QLabel()
        self.v_qualite.setMinimumWidth(40)
        ligne.addWidget(self.qualite, 1)
        ligne.addWidget(self.v_qualite)
        form.addRow(tr("Qualité"), ligne)
        self.meta = QCheckBox(tr("Garder les informations de l'appareil (EXIF) et le profil couleur"))
        self.meta.setChecked(self.reglages.value("export_meta", "false") == "true")
        form.addRow("", self.meta)
        from . import filigrane
        self.reglage_filigrane = filigrane.charger(self.reglages)
        self.filigrane = QCheckBox(tr("Ajouter le filigrane (Fichier > Filigrane…)"))
        self.filigrane.setChecked(bool(self.reglage_filigrane["actif"]))
        form.addRow("", self.filigrane)
        lay.addLayout(form)
        self.estimation = QLabel()
        self.estimation.setObjectName("discret")
        lay.addWidget(self.estimation)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        self.b_ok = QPushButton(tr("Exporter…"))
        self.b_ok.setDefault(True)
        self.b_ok.clicked.connect(self.exporter)
        annuler = QPushButton(tr("Annuler"))
        annuler.clicked.connect(self.reject)
        boutons.addWidget(self.b_ok)
        boutons.addWidget(annuler)
        lay.addLayout(boutons)
        self._minuterie = QTimer(self)
        self._minuterie.setSingleShot(True)
        self._minuterie.setInterval(250)
        self._minuterie.timeout.connect(self._estimer)
        for w in (self.format.currentIndexChanged, self.cote.valueChanged, self.cote_case.toggled,
                  self.qualite.valueChanged, self.meta.toggled, self.filigrane.toggled):
            w.connect(self._change)
        self.dernier: bytes | None = None
        self._change()

    def _change(self, *_):
        self.v_qualite.setText(f"{self.qualite.value()}")
        png = self.format.currentData() == "png"
        self.qualite.setEnabled(not png)
        self.cote.setEnabled(self.cote_case.isChecked())
        self.estimation.setText(tr("Calcul du poids…"))
        self._minuterie.start()

    def octets(self) -> tuple[bytes, tuple[int, int]]:
        im = preparer(self.image, self.cote.value() if self.cote_case.isChecked() else None)
        if self.filigrane.isChecked():
            from . import filigrane
            im = filigrane.appliquer(im, self.reglage_filigrane)
        return encoder(im, self.format.currentData(), self.qualite.value(), self.meta.isChecked(), self.exif,
                       self.icc), im.size

    def _estimer(self):
        donnees, (w, h) = self.octets()
        self.dernier = donnees
        self.estimation.setText(tr("Fichier : {w} × {h} px, environ {poids}.", w=w, h=h,
                                   poids=taille_lisible(len(donnees))))

    def exporter(self):
        fmt = self.format.currentData()
        ext = FORMATS[fmt][1]
        dossier = Path(self.reglages.value("export_dossier", self.reglages.value("dossier", str(Path.home()))))
        chemin, _ = QFileDialog.getSaveFileName(self, tr("Exporter pour le web"),
                                                str(dossier / (self.nom + tr("_web") + ext)),
                                                f"{FORMATS[fmt][0]} (*{ext})")
        if not chemin:
            return
        if not chemin.lower().endswith(ext):
            chemin += ext
        donnees, _taille = self.octets()
        try:
            Path(chemin).write_bytes(donnees)
        except OSError as e:
            QMessageBox.critical(self, tr("Exporter pour le web"), tr("Impossible d'enregistrer :\n{erreur}",
                                                                      erreur=e))
            return
        for cle, v in (("export_format", fmt), ("export_cote", self.cote.value()),
                       ("export_reduire", "true" if self.cote_case.isChecked() else "false"),
                       ("export_qualite", self.qualite.value()),
                       ("export_meta", "true" if self.meta.isChecked() else "false"),
                       ("export_dossier", str(Path(chemin).parent))):
            self.reglages.setValue(cle, v)
        self.chemin = chemin
        self.accept()


# ------------------------------------------------------------------ traitement par lot
EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp")


def traiter_une(chemin: Path, sortie: Path, opts: dict, moteur=None, annuler=None) -> Path:
    """Une photo du lot : ouvrir, (IA), réglage auto, taille, format. -> chemin écrit."""
    from .document import FORMAT_CALQUE, pil_vers_qimage, qimage_vers_pil
    from .reglages_image import ajuster, auto
    from .raw import developper, est_raw
    if est_raw(chemin):                                # RAW d'appareil photo : développé par LibRaw
        rgb, exif = developper(chemin)
        icc = None
        im = Image.fromarray(rgb, "RGB").convert("RGBA")
    else:
        with Image.open(chemin) as im:
            exif = im.info.get("exif")
            icc = im.info.get("icc_profile")
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGBA")
    if opts.get("upscale") and moteur is not None:
        im = _ia(moteur, im, "upscale", opts, annuler)
    if opts.get("arriere_plan") and moteur is not None:
        im = _ia(moteur, im, "arriere_plan", opts, annuler)
    if opts.get("action"):                             # action enregistrée (panneau Actions)
        from .actions_auto import appliquer_tableau
        a = np.asarray(im.convert("RGBA"))
        for e in opts["action"]["etapes"]:
            a = appliquer_tableau(a, e)
        im = Image.fromarray(np.ascontiguousarray(a), "RGBA")
    if opts.get("auto"):
        q = pil_vers_qimage(im).convertToFormat(FORMAT_CALQUE)
        q = ajuster(q, auto(q), None)
        im = qimage_vers_pil(q)
    im = preparer(im, opts.get("cote"))
    if opts.get("filigrane"):
        from . import filigrane
        im = filigrane.appliquer(im, opts["filigrane"])
    fmt = opts.get("format", "jpg")
    if fmt == "garder":
        fmt = {".png": "png", ".webp": "webp"}.get(chemin.suffix.lower(), "jpg")
    if opts.get("arriere_plan") and fmt == "jpg":
        fmt = "png"                                    # garder la transparence
    donnees = encoder(im, fmt, opts.get("qualite", 90), opts.get("meta", False), exif, icc)
    sortie.mkdir(parents=True, exist_ok=True)
    cible = sortie / (chemin.stem + opts.get("suffixe", "") + FORMATS[fmt][1])
    cible.write_bytes(donnees)
    return cible


def _ia(moteur, im: Image.Image, quoi: str, opts: dict, annuler) -> Image.Image:
    from . import recettes
    from .moteur import ErreurMoteur
    rgb = im.convert("RGB")
    tampon = io.BytesIO()
    rgb.save(tampon, "PNG", compress_level=1)
    nom = moteur.envoyer_image(tampon.getvalue())
    if quoi == "upscale":
        prompt, sorties = recettes.upscale_rapide(nom, float(opts.get("facteur", 2)))
    else:
        prompt, sorties = recettes.detourer(nom)
    res = moteur.executer(prompt, sorties, annuler or threading.Event(), lambda *a: None)
    if not res:
        raise ErreurMoteur(tr("Le calcul s'est arrêté sans résultat."))
    out = Image.open(io.BytesIO(res[0][1]))
    if quoi == "upscale":
        return out.convert("RGBA")
    masque = out.convert("L").resize(im.size, Image.LANCZOS)
    res = im.copy()
    a = np.minimum(np.asarray(res.getchannel("A")), np.asarray(masque))
    res.putalpha(Image.fromarray(a))
    return res


class DialogueLot(QDialog):
    """Traitement par lot : choix des dossiers et des opérations, puis avancement."""
    avance = Signal(int, str)
    termine = Signal(int, list)

    def __init__(self, fenetre):
        super().__init__(fenetre)
        self.f = fenetre
        self.setWindowTitle(tr("Traitement par lot"))
        self.setMinimumWidth(560)
        r = fenetre.reglages
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.source = QLineEdit(r.value("lot_source", ""))
        self.sortie = QLineEdit(r.value("lot_sortie", ""))
        for champ, titre in ((self.source, tr("Photos à traiter")), (self.sortie, tr("Résultats dans"))):
            ligne = QHBoxLayout()
            ligne.addWidget(champ, 1)
            b = QPushButton(tr("Parcourir…"))
            b.clicked.connect(lambda _=False, c=champ: self._choisir(c))
            ligne.addWidget(b)
            form.addRow(titre, ligne)
        self.cote_case = QCheckBox(tr("Réduire : plus grand côté"))
        self.cote_case.setChecked(r.value("lot_reduire", "false") == "true")
        self.cote = QSpinBox()
        self.cote.setRange(16, 20000)
        self.cote.setSuffix(" px")
        self.cote.setValue(int(r.value("lot_cote", 2048)))
        ligne = QHBoxLayout()
        ligne.addWidget(self.cote_case)
        ligne.addWidget(self.cote)
        ligne.addStretch(1)
        form.addRow(tr("Taille"), ligne)
        self.auto = QCheckBox(tr("Réglage automatique (luminosité, contraste, température)"))
        self.auto.setChecked(r.value("lot_auto", "false") == "true")
        form.addRow("", self.auto)
        from .actions_auto import charger
        self.action = QComboBox()
        self.action.addItem(tr("(aucune)"), None)
        for a in charger():
            self.action.addItem(a["nom"], a)
        i = self.action.findText(r.value("lot_action", "") or "")
        self.action.setCurrentIndex(max(0, i))
        self.action.setToolTip(tr("Action enregistrée dans le panneau Actions, jouée sur chaque photo"))
        form.addRow(tr("Action"), self.action)
        from . import filigrane
        self.reglage_filigrane = filigrane.charger(r)
        self.filigrane = QCheckBox(tr("Ajouter le filigrane (Fichier > Filigrane…)"))
        self.filigrane.setChecked(bool(self.reglage_filigrane["actif"]))
        form.addRow("", self.filigrane)
        self.upscale = QCheckBox(tr("Upscale IA rapide ×2 (RealESRGAN)"))
        self.upscale.setChecked(r.value("lot_upscale", "false") == "true")
        form.addRow(tr("IA"), self.upscale)
        self.fond = QCheckBox(tr("Supprimer l'arrière-plan (PNG transparent)"))
        self.fond.setChecked(r.value("lot_fond", "false") == "true")
        form.addRow("", self.fond)
        self.format = QComboBox()
        self.format.addItem(tr("Garder le format"), "garder")
        for k, (n, _e) in FORMATS.items():
            self.format.addItem(n, k)
        self.format.setCurrentIndex(max(0, self.format.findData(r.value("lot_format", "jpg"))))
        self.qualite = QSpinBox()
        self.qualite.setRange(30, 100)
        self.qualite.setValue(int(r.value("lot_qualite", 90)))
        ligne = QHBoxLayout()
        ligne.addWidget(self.format)
        ligne.addWidget(QLabel(tr("qualité")))
        ligne.addWidget(self.qualite)
        ligne.addStretch(1)
        form.addRow(tr("Format"), ligne)
        self.suffixe = QLineEdit(r.value("lot_suffixe", ""))
        self.suffixe.setPlaceholderText(tr("ex. _web (vide : même nom)"))
        form.addRow(tr("Ajouter au nom"), self.suffixe)
        lay.addLayout(form)
        self.barre = QProgressBar()
        self.barre.hide()
        self.etat = QLabel()
        self.etat.setObjectName("discret")
        self.etat.setWordWrap(True)
        lay.addWidget(self.barre)
        lay.addWidget(self.etat)
        boutons = QHBoxLayout()
        boutons.addStretch(1)
        self.b_lancer = QPushButton(tr("Lancer"))
        self.b_lancer.setDefault(True)
        self.b_lancer.clicked.connect(self.lancer)
        self.b_fermer = QPushButton(tr("Fermer"))
        self.b_fermer.clicked.connect(self._fermer)
        boutons.addWidget(self.b_lancer)
        boutons.addWidget(self.b_fermer)
        lay.addLayout(boutons)
        self.avance.connect(self._avance)
        self.termine.connect(self._termine)
        self._annuler = threading.Event()
        self._fil = None

    def _choisir(self, champ: QLineEdit):
        d = QFileDialog.getExistingDirectory(self, tr("Choisir un dossier"), champ.text() or str(Path.home()))
        if d:
            champ.setText(d)

    def options(self) -> dict:
        return {"cote": self.cote.value() if self.cote_case.isChecked() else None, "auto": self.auto.isChecked(),
                "upscale": self.upscale.isChecked(), "facteur": 2, "arriere_plan": self.fond.isChecked(),
                "format": self.format.currentData(), "qualite": self.qualite.value(),
                "suffixe": self.suffixe.text().strip(), "action": self.action.currentData(),
                "filigrane": self.reglage_filigrane if self.filigrane.isChecked() else None}

    def photos(self) -> list[Path]:
        src = Path(self.source.text())
        from .raw import EXTENSIONS_RAW
        return sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS + EXTENSIONS_RAW) \
            if src.is_dir() else []

    def lancer(self):
        src, dst = Path(self.source.text()), Path(self.sortie.text())
        if not src.is_dir():
            QMessageBox.information(self, self.windowTitle(), tr("Choisis le dossier des photos à traiter."))
            return
        if not self.sortie.text().strip():
            QMessageBox.information(self, self.windowTitle(), tr("Choisis le dossier où mettre les résultats."))
            return
        if dst.resolve() == src.resolve() and not self.suffixe.text().strip():
            QMessageBox.information(self, self.windowTitle(), tr(
                "Les résultats iraient dans le même dossier, sous le même nom : les photos d'origine seraient "
                "remplacées. Choisis un autre dossier, ou un ajout au nom (ex. _web)."))
            return
        opts = self.options()
        if (opts["upscale"] or opts["arriere_plan"]) and self.f.moteur.etat != "prêt":
            QMessageBox.information(self, self.windowTitle(), tr(
                "L'upscale et la suppression de l'arrière-plan utilisent le moteur IA, qui n'est pas encore prêt. "
                "Attends « Moteur IA prêt » en bas à gauche, ou décoche ces options."))
            return
        photos = self.photos()
        if not photos:
            QMessageBox.information(self, self.windowTitle(), tr("Aucune photo (JPG, PNG, TIFF, WebP, BMP, RAW) "
                                                                 "dans ce dossier."))
            return
        r = self.f.reglages
        for cle, v in (("lot_source", str(src)), ("lot_sortie", str(dst)),
                       ("lot_reduire", "true" if self.cote_case.isChecked() else "false"),
                       ("lot_cote", self.cote.value()), ("lot_auto", "true" if opts["auto"] else "false"),
                       ("lot_upscale", "true" if opts["upscale"] else "false"),
                       ("lot_fond", "true" if opts["arriere_plan"] else "false"), ("lot_format", opts["format"]),
                       ("lot_qualite", opts["qualite"]), ("lot_suffixe", opts["suffixe"]),
                       ("lot_action", self.action.currentText() if opts["action"] else "")):
            r.setValue(cle, v)
        dst.mkdir(parents=True, exist_ok=True)
        self.barre.setRange(0, len(photos))
        self.barre.setValue(0)
        self.barre.show()
        self.b_lancer.setEnabled(False)
        self.b_fermer.setText(tr("Arrêter"))
        self._annuler.clear()
        moteur = self.f.moteur if (opts["upscale"] or opts["arriere_plan"]) else None

        def travail():
            erreurs = []
            fait = 0
            for k, p in enumerate(photos):
                if self._annuler.is_set():
                    break
                self.avance.emit(k, p.name)
                try:
                    traiter_une(p, dst, opts, moteur, self._annuler)
                    fait += 1
                except Exception as e:
                    erreurs.append(f"{p.name} : {e}")
            self.termine.emit(fait, erreurs)
        self._fil = threading.Thread(target=travail, daemon=True)
        self._fil.start()

    def _avance(self, k: int, nom: str):
        self.barre.setValue(k)
        self.etat.setText(tr("En cours : {nom} ({k} / {n})", nom=nom, k=k + 1, n=self.barre.maximum()))

    def _termine(self, fait: int, erreurs: list):
        self.barre.setValue(self.barre.maximum())
        self.b_lancer.setEnabled(True)
        self.b_fermer.setText(tr("Fermer"))
        texte = tr("Terminé : {n} photo(s) traitée(s) dans {dossier}.", n=fait, dossier=self.sortie.text())
        if erreurs:
            texte += "\n" + tr("Problèmes :") + "\n" + "\n".join(erreurs[:8])
        self.etat.setText(texte)
        self._fil = None

    def _fermer(self):
        if self._fil is not None:
            self._annuler.set()
            self.etat.setText(tr("Arrêt après la photo en cours…"))
            return
        self.accept()
