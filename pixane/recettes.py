"""Les recettes ComfyUI (format API), avec les réglages validés à l'étape 1.

Chaque fonction renvoie (prompt, sorties) : sorties = {numéro de nœud: libellé affiché}.
"""
from __future__ import annotations

import math
import random

from .langue import tr

NB_EFFACER = 2      # propositions Flux (plus la version LaMa seule)
NB_REMPLIR = 3
NB_AGRANDIR = 3

# Modèle Flux Fill utilisé : version complète (.safetensors, réduite à 8 bits au chargement) ou version GGUF
# (même modèle, compressé ; extension ComfyUI-GGUF). Choisi par configurer() selon ce qui est installé.
FILL_COMPLET = "flux1-fill-dev.safetensors"
FILL_GGUF = "flux1-fill-dev-Q8_0.gguf"
PREFERENCE_FILL = ("complet", "gguf")    # ordre de préférence quand les deux sont présents
_fill = {"type": "complet", "fichier": FILL_COMPLET}
# Flux Schnell (Upscale net) : version complète si elle est là, sinon GGUF (installée par Pixane, facultative)
SCHNELL_COMPLET = "flux1-schnell.safetensors"
_schnell: dict = {"type": "complet", "fichier": SCHNELL_COMPLET}
# Détourage (sujet / arrière-plan) : nœuds intégrés à ComfyUI + modèle BiRefNet (MIT)
BIREFNET = "birefnet.safetensors"
_detourage = {"ok": False}
# Sélection rapide et sélection d'objet : nœud SAM3_Detect intégré à ComfyUI + modèle SAM 3.1 (SAM License, Meta)
SAM = "sam3.1_multiplex_fp16.safetensors"
_sam: dict = {"fichier": None}
# Réduction du bruit : SCUNet (Apache-2.0), chargé comme un modèle d'upscale (facteur 1)
SCUNET = "scunet_color_real_psnr.pth"
_scunet = {"ok": False}
# Restaurer une vieille photo : Flux Kontext dev (licence FLUX.1 [dev], non commerciale)
KONTEXT = "flux1-dev-kontext_fp8_scaled.safetensors"
_kontext: dict = {"type": None, "fichier": None}
NB_RESTAURER = 2
TEXTE_RESTAURER = ("Restore this old damaged photo: remove scratches, dust, creases, stains and film grain, repair "
                   "torn or missing parts, fix faded contrast, make faces and details sharp and natural. Keep exactly "
                   "the same people, faces, expressions, clothes, pose, framing and composition.")
TEXTE_COLORISER = (" Colorize it with natural, realistic colors.")
TEXTE_GARDER_COULEURS = (" Keep exactly the original colors: if the photo is black and white or sepia, keep it so, "
                         "do not colorize it.")


# Flou selon la profondeur : Depth Anything 3 Small (Apache-2.0), nœuds intégrés à ComfyUI (LoadDA3Model…)
PROFONDEUR = "depth_anything_3_small.safetensors"
_profondeur: dict = {"fichier": None}
# Coloriser, changer la lumière (Flux Kontext) ; remplacer le ciel (Flux Fill) : consignes en anglais
TEXTE_COLORISER_SEUL = ("Colorize this black and white photo with natural, realistic colors. Keep exactly the same "
                        "people, faces, expressions, objects, details, lighting, framing and composition.")
TEXTE_LUMIERE = ("Relight this photo: {lumiere}. Keep exactly the same people, faces, expressions, objects, details, "
                 "colors of the objects, framing and composition; only the lighting changes. Do not add any new object, lamp or "
                 "light fixture to the picture.")
LUMIERES = {
    "doree": "warm golden hour sunlight, low sun, soft long shadows",
    "studio": "soft, even and flattering light like in a professional portrait studio, gentle shadows, clean bright "
              "look (the light sources stay outside the picture)",
    "gauche": "strong warm directional light coming from the left side: the left side of every person and object is "
              "brightly lit, contrasted shadows on the right side; same overall brightness, still daytime",
    "droite": "strong warm directional light coming from the right side: the right side of every person and object "
              "is brightly lit, contrasted shadows on the left side; same overall brightness, still daytime",
    "contre_jour": "backlight: a low bright sun just behind the subject, glowing halo of light around the hair and "
                   "shoulders, warm hazy bright sky, the front of the subject softly in shadow",
    "nuit": "night time, lit by warm street lamps, dark blue ambient light",
    "neon": "colorful neon lights, pink and blue glow",
    "nuageux": "overcast day, soft diffuse light, no hard shadows",
}
TEXTE_CIEL = ("Replace the sky with {ciel}. Keep everything else exactly the same: the ground, the trees, the "
              "buildings, the people, their shapes and positions.")
CIELS = {
    "bleu": "a beautiful clear blue sky with a few white fluffy clouds",
    "nuages": "a dramatic sky with large white and grey clouds",
    "coucher": "a colorful sunset sky, orange, pink and purple clouds, warm glow near the horizon",
    "orage": "a dark stormy sky with heavy grey clouds",
    "nuit": "a clear night sky full of stars, deep blue",
    "aube": "a soft pastel dawn sky, light pink and pale blue",
}


class ModeleManquant(Exception):
    pass


def _options(infos: dict, noeud: str, entree: str) -> list:
    """Choix possibles d'une entrée : ancien format [[...], {...}] ou nouveau ["COMBO", {"options": [...]}]."""
    try:
        d = infos[noeud]["input"]["required"][entree]
    except (KeyError, IndexError, TypeError):
        return []
    if d and isinstance(d[0], list):
        return list(d[0])
    if len(d) > 1 and isinstance(d[1], dict):
        return list(d[1].get("options") or [])
    return []


def configurer(infos: dict) -> str | None:
    """Choisit le modèle Flux Fill d'après /object_info de ComfyUI. Renvoie le fichier choisi (None si aucun)."""
    trouves = {}
    if FILL_COMPLET in _options(infos, "UNETLoader", "unet_name"):
        trouves["complet"] = FILL_COMPLET
    ggufs = [f for f in _options(infos, "UnetLoaderGGUF", "unet_name") if "fill" in f.lower()]
    if ggufs:
        trouves["gguf"] = FILL_GGUF if FILL_GGUF in ggufs else sorted(ggufs)[-1]
    if SCHNELL_COMPLET in _options(infos, "UNETLoader", "unet_name"):
        _schnell.update(type="complet", fichier=SCHNELL_COMPLET)
    else:
        schnells = sorted(f for f in _options(infos, "UnetLoaderGGUF", "unet_name") if "schnell" in f.lower())
        _schnell.update(type="gguf" if schnells else None, fichier=schnells[-1] if schnells else None)
    _detourage["ok"] = ("RemoveBackground" in infos
                        and BIREFNET in _options(infos, "LoadBackgroundRemovalModel", "bg_removal_name"))
    sams = [f for f in _options(infos, "CheckpointLoaderSimple", "ckpt_name") if "sam3" in f.lower()]
    _sam["fichier"] = (SAM if SAM in sams else sorted(sams)[-1] if sams else None) if "SAM3_Detect" in infos \
        else None
    _scunet["ok"] = SCUNET in _options(infos, "UpscaleModelLoader", "model_name")
    da3 = sorted(f for f in _options(infos, "LoadDA3Model", "model_name") if "depth_anything_3" in f.lower())
    _profondeur["fichier"] = (PROFONDEUR if PROFONDEUR in da3 else da3[0] if da3 else None) \
        if "DA3Inference" in infos and "DA3Render" in infos else None
    kontext_gguf = sorted(f for f in _options(infos, "UnetLoaderGGUF", "unet_name") if "kontext" in f.lower())
    if "ReferenceLatent" not in infos:
        _kontext.update(type=None, fichier=None)
    elif KONTEXT in _options(infos, "UNETLoader", "unet_name"):
        _kontext.update(type="complet", fichier=KONTEXT)
    elif kontext_gguf:
        _kontext.update(type="gguf", fichier=kontext_gguf[-1])
    else:
        _kontext.update(type=None, fichier=None)
    for t in PREFERENCE_FILL:
        if t in trouves:
            _fill.update(type=t, fichier=trouves[t])
            return trouves[t]
    return None


def detourage_disponible() -> bool:
    return _detourage["ok"]


def detourer(image: str):
    """Masque du sujet principal (blanc = sujet, noir = arrière-plan), de la taille de l'image."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("LoadBackgroundRemovalModel", bg_removal_name=BIREFNET),
         "12": _n("RemoveBackground", bg_removal_model=["11", 0], image=["10", 0]),
         "13": _n("MaskToImage", mask=["12", 0]),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Sujet")}


def profondeur_disponible() -> bool:
    return _profondeur["fichier"] is not None


def profondeur(image: str, cote: int = 1008, sujet: bool = False):
    """Carte de profondeur (gris, proche = clair) de l'image envoyée, à sa taille ; avec sujet : en plus, le masque
    du sujet (détourage BiRefNet), dans le même calcul."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("LoadDA3Model", model_name=_profondeur["fichier"] or PROFONDEUR, weight_dtype="default"),
         "12": _n("DA3Inference", da3_model=["11", 0], image=["10", 0], resolution=cote,
                  resize_method="upper_bound_resize", mode="mono"),
         "13": _n("DA3Render", da3_geometry=["12", 0], output="depth", **{"output.normalization": "min_max",
                                                                          "output.apply_sky_clip": False}),
         "14": _n("PreviewImage", images=["13", 0])}
    if not sujet:
        return p, {"14": tr("Profondeur")}
    p.update({"21": _n("LoadBackgroundRemovalModel", bg_removal_name=BIREFNET),
              "22": _n("RemoveBackground", bg_removal_model=["21", 0], image=["10", 0]),
              "23": _n("MaskToImage", mask=["22", 0]),
              "24": _n("PreviewImage", images=["23", 0])})
    return p, {"14": tr("Profondeur"), "24": tr("Sujet")}


def ciel(image: str):
    """Masque du ciel (blanc = ciel) : SAM 3.1 cherche « sky » dans l'image envoyée."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("CheckpointLoaderSimple", ckpt_name=_sam["fichier"] or SAM),
         "15": _n("CLIPTextEncode", text="sky", clip=["11", 1]),
         "12": _n("SAM3_Detect", model=["11", 0], image=["10", 0], conditioning=["15", 0], threshold=0.4,
                  refine_iterations=2, individual_masks=False),
         "13": _n("MaskToImage", mask=["12", 0]),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Ciel")}


def personnes(image: str):
    """Masques des personnes (blanc = personne), un par personne trouvée : SAM 3.1 cherche « person »."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("CheckpointLoaderSimple", ckpt_name=_sam["fichier"] or SAM),
         "15": _n("CLIPTextEncode", text="person:40", clip=["11", 1]),
         "12": _n("SAM3_Detect", model=["11", 0], image=["10", 0], conditioning=["15", 0], threshold=0.25,
                  refine_iterations=2, individual_masks=True),
         "13": _n("MaskToImage", mask=["12", 0]),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Personne")}


PARTIES_VISAGE = (("visage", "face:10"), ("cou", "neck:10"), ("yeux", "eye:20"), ("sourcils", "eyebrow:20"),
                  ("levres", "lips:10"), ("dents", "teeth:10"))


def visage(image: str):
    """Masques des parties du visage pour la retouche portrait (un par partie, toutes personnes ensemble), dans
    l'ordre de PARTIES_VISAGE : SAM 3.1 les cherche une à une (le modèle n'est chargé qu'une fois)."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("CheckpointLoaderSimple", ckpt_name=_sam["fichier"] or SAM)}
    sorties = {}
    for k, (nom, texte) in enumerate(PARTIES_VISAGE):
        b = 20 + 10 * k
        p[str(b)] = _n("CLIPTextEncode", text=texte, clip=["11", 1])
        p[str(b + 1)] = _n("SAM3_Detect", model=["11", 0], image=["10", 0], conditioning=[str(b), 0], threshold=0.3,
                           refine_iterations=2, individual_masks=False)
        p[str(b + 2)] = _n("MaskToImage", mask=[str(b + 1), 0])
        p[str(b + 3)] = _n("PreviewImage", images=[str(b + 2), 0])
        sorties[str(b + 3)] = nom
    return p, sorties


def sam_disponible() -> bool:
    return _sam["fichier"] is not None


def segmenter(image: str, positifs=(), negatifs=(), cadre=None):
    """Masque de l'objet désigné (blanc = objet) par des points (x, y) à garder ou à exclure, et / ou par un
    cadre (x, y, largeur, hauteur), en pixels de l'image envoyée."""
    import json
    det = {"model": ["11", 0], "image": ["10", 0], "threshold": 0.5, "refine_iterations": 2,
           "individual_masks": False}
    if positifs:
        det["positive_coords"] = json.dumps([{"x": int(x), "y": int(y)} for x, y in positifs])
    if negatifs:
        det["negative_coords"] = json.dumps([{"x": int(x), "y": int(y)} for x, y in negatifs])
    p = {"10": _n("LoadImage", image=image),
         "11": _n("CheckpointLoaderSimple", ckpt_name=_sam["fichier"] or SAM)}
    if cadre is not None:
        x, y, w, h = (int(v) for v in cadre)
        p["15"] = _n("PrimitiveBoundingBox", x=max(0, x), y=max(0, y), width=max(1, w), height=max(1, h))
        det["bboxes"] = ["15", 0]
    p["12"] = _n("SAM3_Detect", **det)
    p["13"] = _n("MaskToImage", mask=["12", 0])
    p["14"] = _n("PreviewImage", images=["13", 0])
    return p, {"14": tr("Objet")}


def schnell_disponible() -> bool:
    return _schnell["type"] is not None


def chargeur_schnell() -> dict:
    if _schnell["type"] is None:
        raise ModeleManquant(tr("« Upscale net » a besoin du modèle Flux Schnell, qui n'est pas installé. "
                                "Menu IA > Installer le moteur IA permet de l'ajouter ; l'upscale simple marche "
                                "sans."))
    if _schnell["type"] == "gguf":
        return _n("UnetLoaderGGUF", unet_name=_schnell["fichier"])
    return _n("UNETLoader", unet_name=_schnell["fichier"], weight_dtype="fp8_e4m3fn")


def chargeur_fill(type_: str | None = None, fichier: str | None = None) -> dict:
    """Nœud qui charge Flux Fill (type_ et fichier : pour forcer un choix, ex. comparaison)."""
    type_ = type_ or _fill["type"]
    fichier = fichier or _fill["fichier"]
    if type_ == "gguf":
        return _n("UnetLoaderGGUF", unet_name=fichier)
    return _n("UNETLoader", unet_name=fichier, weight_dtype="fp8_e4m3fn")


def _graine() -> int:
    return random.randint(1, 2**48)


def _decoupe(**reglages) -> dict:
    r = {"downscale_algorithm": "bilinear", "upscale_algorithm": "bicubic", "preresize": False,
         "preresize_mode": "ensure minimum resolution", "preresize_min_width": 1024, "preresize_min_height": 1024,
         "preresize_max_width": 16384, "preresize_max_height": 16384, "mask_fill_holes": True,
         "mask_expand_pixels": 16, "mask_invert": False, "mask_blend_pixels": 32, "mask_hipass_filter": 0.1,
         "extend_for_outpainting": False, "extend_up_factor": 1.0, "extend_down_factor": 1.0,
         "extend_left_factor": 1.0, "extend_right_factor": 1.0, "context_from_mask_extend_factor": 1.6,
         "output_resize_to_target_size": True, "output_target_width": 1024, "output_target_height": 1024,
         "output_padding": "32", "device_mode": "gpu (much faster)"}
    r.update(reglages)
    return r


def _n(classe: str, **entrees) -> dict:
    return {"class_type": classe, "inputs": entrees}


def _flux_fill(p: dict, pixels, masque, assembleur, nb: int, texte: str = "", denoise: float = 1.0,
               steps: int = 24, graine: int | None = None, chargeur: dict | None = None, voir: bool = False) -> None:
    """Ajoute la chaîne Flux Fill (nœuds 20 à 33) au prompt p.
    voir : retravailler une image déjà dessinée (force < 1 : Pleine définition, Partir de celle-ci). Flux Fill
    reçoit alors l'image entière comme modèle, et seule la zone du masque est recalculée. Sans cela, il voit la zone
    en gris uni (« à inventer ») et, à force partielle, ce gris restait : voile brumeux, personnages changés
    (Agrandir, 23/11/2026)."""
    p["20"] = chargeur or chargeur_fill()
    p["21"] = _n("DualCLIPLoader", clip_name1="clip_l.safetensors", clip_name2="t5xxl_fp8_e4m3fn_scaled.safetensors",
                 type="flux", device="default")
    p["22"] = _n("VAELoader", vae_name="ae.safetensors")
    p["23"] = _n("DifferentialDiffusion", model=["20", 0], strength=1.0)
    p["24"] = _n("CLIPTextEncode", text=texte, clip=["21", 0])
    p["25"] = _n("FluxGuidance", conditioning=["24", 0], guidance=30.0)
    p["26"] = _n("ConditioningZeroOut", conditioning=["24", 0])
    if voir:
        p["33"] = _n("ThresholdMask", mask=masque, value=1.0)          # (> 1 : jamais) masque vide : Flux voit toute l'image
        p["27"] = _n("InpaintModelConditioning", positive=["25", 0], negative=["26", 0], vae=["22", 0],
                     pixels=pixels, mask=["33", 0], noise_mask=False)
        p["34"] = _n("SetLatentNoiseMask", samples=["27", 2], mask=masque)   # seule la zone est recalculée
        latent = ["34", 0]
    else:
        p["27"] = _n("InpaintModelConditioning", positive=["25", 0], negative=["26", 0], vae=["22", 0],
                     pixels=pixels, mask=masque, noise_mask=True)
        latent = ["27", 2]
    p["28"] = _n("RepeatLatentBatch", samples=latent, amount=nb)
    p["29"] = _n("KSampler", model=["23", 0], seed=graine or _graine(), steps=steps, cfg=1.0, sampler_name="euler",
                 scheduler="simple", positive=["27", 0], negative=["27", 1], latent_image=["28", 0], denoise=denoise)
    p["30"] = _n("VAEDecode", samples=["29", 0], vae=["22", 0])
    if assembleur is None:   # pas de découpe : on garde l'image entière
        p["32"] = _n("PreviewImage", images=["30", 0])
    else:
        p["31"] = _n("InpaintStitchImproved", stitcher=assembleur, inpainted_image=["30", 0])
        p["32"] = _n("PreviewImage", images=["31", 0])


def effacer(image: str, nb: int = NB_EFFACER, graine: int | None = None, chargeur: dict | None = None):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe()),
         "12": _n("INPAINT_LoadInpaintModel", model_name="big-lama.pt"),
         # LaMa ne traite que les pixels sélectionnés à 100 % : sur une zone fine (lettres), le bord adouci
         # laissait une partie du texte, que LaMa redessinait. Zone franche : tout pixel touché compte.
         "16": _n("ThresholdMask", mask=["11", 2], value=0.02),
         "13": _n("INPAINT_InpaintWithModel", inpaint_model=["12", 0], image=["11", 1], mask=["16", 0],
                  seed=graine or _graine()),
         "14": _n("InpaintStitchImproved", stitcher=["11", 0], inpainted_image=["13", 0]),
         "15": _n("PreviewImage", images=["14", 0])}
    _flux_fill(p, ["13", 0], ["11", 2], ["11", 0], nb, denoise=0.6, steps=20, graine=graine, chargeur=chargeur)
    return p, {"32": "Flux", "15": tr("LaMa seul")}


def supprimer(image: str):
    """Pinceau Supprimer : LaMa seul, sur un petit morceau de la photo (zone à refaire = transparente)."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("ThresholdMask", mask=["10", 1], value=0.02),
         "12": _n("INPAINT_LoadInpaintModel", model_name="big-lama.pt"),
         "13": _n("INPAINT_InpaintWithModel", inpaint_model=["12", 0], image=["10", 0], mask=["11", 0],
                  seed=_graine()),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": "LaMa"}


def remplir(image: str, texte: str = "", nb: int = NB_REMPLIR, graine: int | None = None,
            chargeur: dict | None = None):
    if not texte.strip():
        # Sans texte, Flux devine d'après les alentours : près d'un titre, il réinventait des lettres. On part
        # donc du fond nettoyé par LaMa, que Flux refait presque entièrement (0,85) : vrai remplissage, sans texte.
        p, _ = effacer(image, nb, graine, chargeur)
        del p["15"]
        p["29"]["inputs"]["denoise"] = 0.85
        p["29"]["inputs"]["steps"] = 24
        return p, {"32": tr("Proposition")}
    p = {"10": _n("LoadImage", image=image),
         "11": _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe())}
    _flux_fill(p, ["11", 1], ["11", 2], ["11", 0], nb, texte=texte, denoise=1.0, graine=graine, chargeur=chargeur)
    return p, {"32": tr("Proposition")}


def agrandir(image: str, nb: int = NB_AGRANDIR, graine: int | None = None, chargeur: dict | None = None):
    """image : toile déjà préparée par Pixane (raccord.preparer), zone à peindre en transparent."""
    p = {"10": _n("LoadImage", image=image)}
    _flux_fill(p, ["10", 0], ["10", 1], None, nb, denoise=1.0, graine=graine, chargeur=chargeur)
    return p, {"32": tr("Proposition")}


FORCE_PROCHE, FORCE_LIBRE = 0.25, 0.85     # « Partir de celle-ci » : glissière Proche ↔ Libre


def force_variante(curseur: int) -> float:
    """Glissière 0 (Proche) .. 100 (Libre) -> force de Flux (part de la proposition refaite)."""
    return round(FORCE_PROCHE + (FORCE_LIBRE - FORCE_PROCHE) * max(0, min(100, curseur)) / 100, 3)


def variante(image: str, force: float, texte: str = "", nb: int = NB_REMPLIR, decoupe: bool = True,
             graine: int | None = None, chargeur: dict | None = None):
    """« Partir de celle-ci » : image = la proposition choisie, avec la même zone à refaire (transparente) que la
    première fois. Flux Fill ne la refait qu'en partie (force < 1) : la forme générale reste, les détails changent.
    decoupe : Effacer / Remplir (découpe autour de la zone, puis recollage) ; Agrandir : toile entière."""
    p = {"10": _n("LoadImage", image=image)}
    if decoupe:
        p["11"] = _n("InpaintCropImproved", image=["10", 0], mask=["10", 1], **_decoupe())
        _flux_fill(p, ["11", 1], ["11", 2], ["11", 0], nb, texte=texte, denoise=force, graine=graine,
                   chargeur=chargeur, voir=True)
    else:
        _flux_fill(p, ["10", 0], ["10", 1], None, nb, texte=texte, denoise=force, graine=graine, chargeur=chargeur,
                   voir=True)
    return p, {"32": tr("Variante")}


def affiner(image: str, force: float = 0.4, steps: int = 20, graine: int | None = None,
            chargeur: dict | None = None):
    """Agrandir en pleine définition : un morceau de 1024 px à la vraie taille ; la partie transparente (ajout de
    la première passe) est redessinée légèrement par Flux Fill (force), le reste sert de modèle."""
    p = {"10": _n("LoadImage", image=image)}
    _flux_fill(p, ["10", 0], ["10", 1], None, 1, denoise=force, steps=steps, graine=graine, chargeur=chargeur,
               voir=True)
    return p, {"32": tr("Pleine définition")}


NB_CREER = 4         # propositions de « Créer une image » (Flux Schnell : ~30 s chacune)


def taille_creation(taille: tuple[int, int], pixels: int = 1024 * 1024) -> tuple[int, int]:
    """Taille de calcul de Flux Schnell : les proportions voulues, environ 1 mégapixel, multiples de 16."""
    w, h = taille
    k = (pixels / max(1, w * h)) ** 0.5
    return max(256, round(w * k / 16) * 16), max(256, round(h * k / 16) * 16)


def creer(texte: str, taille: tuple[int, int], nb: int = NB_CREER, graine: int | None = None,
          image: str | None = None, force: float = 1.0):
    """Flux Schnell : une image d'après un texte (en anglais), aux proportions de `taille`, remise à cette taille.
    image + force < 1 : « Partir de celle-ci » (la proposition choisie, redessinée en partie)."""
    cw, ch = taille_creation(taille)
    p = {"20": chargeur_schnell(),
         "21": _n("DualCLIPLoader", clip_name1="clip_l.safetensors",
                  clip_name2="t5xxl_fp8_e4m3fn_scaled.safetensors", type="flux", device="default"),
         "22": _n("VAELoader", vae_name="ae.safetensors"),
         "24": _n("CLIPTextEncode", text=texte, clip=["21", 0]),
         "27": _n("ConditioningZeroOut", conditioning=["24", 0])}
    if image is not None:
        p["10"] = _n("LoadImage", image=image)
        p["11"] = _n("ImageScale", image=["10", 0], upscale_method="lanczos", width=cw, height=ch, crop="disabled")
        p["23"] = _n("VAEEncode", pixels=["11", 0], vae=["22", 0])
    else:
        p["23"] = _n("EmptySD3LatentImage", width=cw, height=ch, batch_size=1)
    graine = graine or _graine()
    sorties = {}
    for k in range(nb):
        b = 40 + 10 * k
        p[str(b)] = _n("KSampler", model=["20", 0], seed=graine + k, steps=4, cfg=1.0, sampler_name="euler",
                       scheduler="simple", positive=["24", 0], negative=["27", 0], latent_image=["23", 0],
                       denoise=force if image is not None else 1.0)
        p[str(b + 1)] = _n("VAEDecode", samples=[str(b), 0], vae=["22", 0])
        p[str(b + 2)] = _n("ImageScale", image=[str(b + 1), 0], upscale_method="lanczos", width=taille[0],
                           height=taille[1], crop="disabled")
        p[str(b + 3)] = _n("PreviewImage", images=[str(b + 2), 0])
        sorties[str(b + 3)] = tr("Proposition")
    return p, sorties


def upscale_rapide(image: str, facteur: float = 2.0):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "12": _n("ImageUpscaleWithModel", upscale_model=["11", 0], image=["10", 0]),
         "13": _n("ImageScaleBy", image=["12", 0], upscale_method="lanczos", scale_by=facteur / 4),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Upscale rapide")}


def nb_morceaux(largeur: int, hauteur: int, facteur: float, tuile: int = 1024) -> int:
    """Nombre de morceaux de 1024 px que Flux redessine (pour la barre de progression)."""
    return math.ceil(largeur * facteur / tuile) * math.ceil(hauteur * facteur / tuile)


def upscale_net(image: str, facteur: float = 2.0, force: float = 0.35, taille: tuple[int, int] | None = None):
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "20": chargeur_schnell(),
         "21": _n("DualCLIPLoader", clip_name1="clip_l.safetensors",
                  clip_name2="t5xxl_fp8_e4m3fn_scaled.safetensors", type="flux", device="default"),
         "22": _n("VAELoader", vae_name="ae.safetensors"),
         "24": _n("CLIPTextEncode", clip=["21", 0],
                  text="high quality photo, sharp focus, fine details, natural texture"),
         "26": _n("ConditioningZeroOut", conditioning=["24", 0]),
         "30": _n("UltimateSDUpscale", image=["10", 0], model=["20", 0], positive=["24", 0], negative=["26", 0],
                  vae=["22", 0], upscale_model=["11", 0], upscale_by=facteur, seed=_graine(), steps=6, cfg=1.0,
                  sampler_name="euler", scheduler="simple", denoise=force, mode_type="Chess", tile_width=1024,
                  tile_height=1024, mask_blur=16, tile_padding=64, seam_fix_mode="None", seam_fix_denoise=1.0,
                  seam_fix_width=64, seam_fix_mask_blur=8, seam_fix_padding=16, force_uniform_tiles=True,
                  tiled_decode=False, batch_size=1),
         "31": _n("PreviewImage", images=["30", 0])}
    if taille:
        return p, {"31": tr("Upscale net")}, nb_morceaux(*taille, facteur)
    return p, {"31": tr("Upscale net")}


# ------------------------------------------------------------------ améliorer (bruit, netteté), restaurer
def debruitage_disponible() -> bool:
    return _scunet["ok"]


def debruiter(image: str):
    """SCUNet : enlève le bruit (grain, compression JPEG) en gardant les détails ; même taille."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name=SCUNET),
         "12": _n("ImageUpscaleWithModel", upscale_model=["11", 0], image=["10", 0]),
         "13": _n("PreviewImage", images=["12", 0])}
    return p, {"13": tr("Bruit réduit")}


def nettete_ia(image: str):
    """RealESRGAN ×4 puis retour à la taille d'origine : contours et détails plus nets, bruit lissé."""
    p = {"10": _n("LoadImage", image=image),
         "11": _n("UpscaleModelLoader", model_name="RealESRGAN_x4plus.pth"),
         "12": _n("ImageUpscaleWithModel", upscale_model=["11", 0], image=["10", 0]),
         "13": _n("ImageScaleBy", image=["12", 0], upscale_method="lanczos", scale_by=0.25),
         "14": _n("PreviewImage", images=["13", 0])}
    return p, {"14": tr("Plus net")}


def restauration_disponible() -> bool:
    return _kontext["fichier"] is not None


def taille_kontext(taille: tuple[int, int], pixels: int = 1024 * 1024) -> tuple[int, int]:
    """Taille de travail de Flux Kontext : environ un million de pixels, côtés multiples de 16, en gardant les
    proportions de la photo (FluxKontextImageScale prend le format « préféré » le plus proche : la photo
    revenait ensuite étirée)."""
    w, h = taille
    ratio = w / h
    meilleur = None
    for lw in range(256, 2049, 16):                      # entre 0,8 et 1,25 million de pixels
        base = max(16, int(lw / ratio) // 16 * 16)
        for lh in (base, base + 16):
            if not 0.8 * pixels <= lw * lh <= 1.25 * pixels:
                continue
            note = (round(abs(lw / lh / ratio - 1), 3), abs(lw * lh - pixels))
            if meilleur is None or note < meilleur[0]:
                meilleur = (note, (lw, lh))
    if meilleur is None:                                 # photo très allongée
        k = (pixels / (w * h)) ** 0.5
        return max(16, round(w * k / 16) * 16), max(16, round(h * k / 16) * 16)
    return meilleur[1]


def restaurer(image: str, taille: tuple[int, int], coloriser: bool = False, nb: int = NB_RESTAURER,
              graine: int | None = None, texte: str = ""):
    """Flux Kontext : la photo est redessinée d'après une consigne (restaurer, coloriser). Une sortie par
    proposition, remise à la taille de la photo."""
    if _kontext["type"] == "gguf":
        chargeur = _n("UnetLoaderGGUF", unet_name=_kontext["fichier"])
    else:
        chargeur = _n("UNETLoader", unet_name=_kontext["fichier"] or KONTEXT, weight_dtype="default")
    consigne = texte.strip() or (TEXTE_RESTAURER + (TEXTE_COLORISER if coloriser else TEXTE_GARDER_COULEURS))
    p = {"10": _n("LoadImage", image=image),
         "20": chargeur,
         "21": _n("DualCLIPLoader", clip_name1="clip_l.safetensors",
                  clip_name2="t5xxl_fp8_e4m3fn_scaled.safetensors", type="flux", device="default"),
         "22": _n("VAELoader", vae_name="ae.safetensors"),
         "11": _n("ImageScale", image=["10", 0], upscale_method="lanczos", width=taille_kontext(taille)[0],
                  height=taille_kontext(taille)[1], crop="disabled"),
         "12": _n("VAEEncode", pixels=["11", 0], vae=["22", 0]),
         "24": _n("CLIPTextEncode", text=consigne, clip=["21", 0]),
         "25": _n("ReferenceLatent", conditioning=["24", 0], latent=["12", 0]),
         "26": _n("FluxGuidance", conditioning=["25", 0], guidance=2.5),
         "27": _n("ConditioningZeroOut", conditioning=["24", 0])}
    graine = graine or _graine()
    sorties = {}
    for k in range(nb):
        b = 40 + 10 * k
        p[str(b)] = _n("KSampler", model=["20", 0], seed=graine + k, steps=20, cfg=1.0, sampler_name="euler",
                       scheduler="simple", positive=["26", 0], negative=["27", 0], latent_image=["12", 0],
                       denoise=1.0)
        p[str(b + 1)] = _n("VAEDecode", samples=[str(b), 0], vae=["22", 0])
        p[str(b + 2)] = _n("ImageScale", image=[str(b + 1), 0], upscale_method="lanczos", width=taille[0],
                           height=taille[1], crop="disabled")
        p[str(b + 3)] = _n("PreviewImage", images=[str(b + 2), 0])
        sorties[str(b + 3)] = tr("Proposition")
    return p, sorties
