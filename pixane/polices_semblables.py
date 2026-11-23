"""Trouver, parmi les polices installées, celles qui ressemblent le plus aux lettres d'une image.

Sans téléchargement : l'utilisateur tape les lettres de l'image (ex. « DISCO ») ; Pixane les écrit avec chaque police
(normal, gras, italique, gras italique) et compare avec la forme des lettres (masque : la sélection du texte).

Comparaison, sur des images ramenées à la même hauteur :
- la forme générale du bloc de texte (largeur / hauteur : polices étroites ou larges) ;
- le recouvrement des lettres (adouci, pour pardonner les petits décalages) ;
- l'épaisseur des traits (part d'encre).
Quand les lettres de l'image sont bien séparées (le cas courant), la comparaison se fait **lettre par lettre** : chaque
lettre de l'image avec la même lettre de la police, à la même hauteur de ligne. L'espacement entre les lettres
(souvent agrandi sur les pochettes : « C O L D P L A Y ») ne compte donc pas. Sinon (lettres collées, nombre de
lettres différent du texte tapé), le bloc entier est comparé.
Trois passes : un tri rapide de toutes les polices (style normal, petite taille), puis les 4 styles des meilleures,
puis une comparaison plus fine des toutes meilleures.

Le tri rapide n'ouvre pas les polices : il assemble les lettres d'une « mémoire des polices » (alphabet et chiffres de
chaque police, écrits une fois ; fichier polices.memoire dans le dossier de Pixane, environ 15 Mo). Les polices
ajoutées ensuite sont mises en mémoire à la recherche suivante.
"""
from __future__ import annotations

import os
import pickle
import string
import time
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics, QImage, QPainter

HAUT_RAPIDE, HAUT_FIN = 32, 72          # hauteur des images comparées (passe rapide, passe fine)
GARDER = 40                             # polices gardées pour la passe fine
PREMIERS = 100                          # polices gardées après le tri rapide (style normal seul)
TAILLE_TRI, HAUT_TRI = 40, 24           # tri rapide : taille d'écriture, hauteur comparée
STYLES = ((QFont.Normal, False), (QFont.Bold, False), (QFont.Normal, True), (QFont.Bold, True))


@dataclass
class Resultat:
    famille: str
    gras: bool
    italique: bool
    score: float                        # 0 à 100 (100 : identique)
    google: str = ""                    # police gratuite de Google Fonts pas installée : son identifiant
    licence: str = ""

    def police(self, taille: int = 40) -> QFont:
        f = QFont(self.famille)
        f.setPixelSize(taille)
        f.setBold(self.gras)
        f.setItalic(self.italique)
        return f


def _recadrer(m: np.ndarray) -> np.ndarray | None:
    ys, xs = np.nonzero(m > 0.5)
    if not len(ys):
        return None
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _vers_hauteur(m: np.ndarray, h: int, w: int | None = None) -> np.ndarray:
    """Masque (0..1) redimensionné à la hauteur h (largeur w, ou proportionnelle)."""
    from PIL import Image
    hh, ww = m.shape
    if w is None:
        w = max(1, round(ww * h / hh))
    im = Image.fromarray((m * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    return np.asarray(im, np.float32) / 255


def _adoucir(m: np.ndarray, r: int) -> np.ndarray:
    """Flou en boîte (rayon r) : deux formes presque superposées se recouvrent bien."""
    if r <= 0:
        return m
    k = 2 * r + 1
    p = np.pad(m, r, mode="constant")
    c = np.cumsum(np.cumsum(p, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def masque_texte(texte: str, police: QFont) -> np.ndarray | None:
    """Les lettres écrites avec cette police : masque 0..1 recadré sur l'encre."""
    fm = QFontMetrics(police)
    lignes = texte.split("\n")
    larg = max(fm.horizontalAdvance(l) for l in lignes) + fm.height()
    haut = fm.lineSpacing() * len(lignes) + fm.height()
    if larg <= 0 or haut <= 0 or larg * haut > 40_000_000:
        return None
    img = QImage(larg, haut, QImage.Format_Grayscale8)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setFont(police)
    p.setPen(Qt.white)
    p.drawText(QRect(0, 0, larg, haut), Qt.AlignCenter, texte)
    p.end()
    a = np.frombuffer(img.constBits(), np.uint8).reshape(haut, img.bytesPerLine())[:, :larg]
    return _recadrer(a.astype(np.float32) / 255)


def _comparer(cible: np.ndarray, essai: np.ndarray, h: int, epaisseur: bool = True) -> float:
    """Ressemblance 0..1 entre deux masques recadrés. epaisseur=False : seule la forme compte (tri rapide, fait
    avec le style normal : une lettre grasse de l'image doit quand même retrouver sa police) ; les traits de l'essai
    sont alors épaissis ou amincis jusqu'à avoir autant d'encre que la cible."""
    rc = cible.shape[1] / cible.shape[0]
    re = essai.shape[1] / essai.shape[0]
    forme = min(rc, re) / max(rc, re)                       # même allure générale (étroite, large)
    w = max(1, round(h * rc))
    a = _vers_hauteur(cible, h, w)
    b = _vers_hauteur(essai, h, w)
    ea, eb = float(a.mean()), float(b.mean())
    if not epaisseur and 0.01 < ea < 0.95 and eb > 0.005:
        bs = _adoucir(b, max(1, h // 16))
        b = (bs > np.quantile(bs, 1 - ea)).astype(np.float32)
    r = max(1, h // 24)
    fa, fb = _adoucir(a, r), _adoucir(b, r)
    recouvrement = float((fa * fb).sum() / max(1e-6, np.sqrt((fa * fa).sum() * (fb * fb).sum())))
    if not epaisseur:
        return recouvrement ** 2 * forme ** 0.5
    ressemblance_traits = min(ea, eb) / max(ea, eb, 1e-6)    # épaisseur des traits
    return recouvrement ** 2 * forme ** 0.5 * ressemblance_traits ** 0.5


# ------------------------------------------------------------------ lettre par lettre
SEUIL_ENCRE = 0.35


def _plages(profil: np.ndarray) -> list[tuple[int, int]]:
    """Plages [début, fin) où le profil est non nul."""
    v = np.concatenate(([0], (profil > 0).astype(np.int8), [0]))
    d = np.diff(v)
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]))


def _lignes(m: np.ndarray) -> list[tuple[int, int]]:
    """Lignes de texte du masque (plages de rangées) ; les petits morceaux (points, accents) vont à la ligne la plus
    proche."""
    pl = _plages((m > SEUIL_ENCRE).sum(axis=1))
    if not pl:
        return []
    grande = max(b - a for a, b in pl)
    lignes = [list(x) for x in pl if x[1] - x[0] >= 0.35 * grande]
    for a, b in pl:
        if b - a < 0.35 * grande:
            j = min(range(len(lignes)), key=lambda i: min(abs(a - lignes[i][1]), abs(lignes[i][0] - b)))
            lignes[j] = [min(lignes[j][0], a), max(lignes[j][1], b)]
    return [tuple(x) for x in lignes]


def _lettres_ligne(bloc: np.ndarray, attendu: int | None = None, avec_x: bool = False):
    """Lettres d'une ligne : morceaux d'un seul tenant, regroupés (point du i, lettre en deux morceaux) ; les taches
    à l'écart (restes du fond) sont oubliées. attendu : nombre de lettres du texte tapé ; deux lettres collées (ex.
    empattements de « ll ») sont alors séparées, une lettre coupée en deux est recollée. Chaque lettre : sa partie
    du masque, sur toute la hauteur des lettres de la ligne."""
    from .selection_auto import etiquettes
    lab, tailles = etiquettes(bloc > SEUIL_ENCRE)
    n = len(tailles)
    if not n:
        return ([], []) if avec_x else []
    ys, xs = np.nonzero(lab >= 0)
    l = lab[ys, xs]
    x0 = np.full(n, 1 << 30)
    np.minimum.at(x0, l, xs)
    x1 = np.zeros(n, int)
    np.maximum.at(x1, l, xs + 1)
    y0 = np.full(n, 1 << 30)
    np.minimum.at(y0, l, ys)
    y1 = np.zeros(n, int)
    np.maximum.at(y1, l, ys + 1)
    t = np.asarray(tailles, float)
    ref = float(np.median(t[t >= 0.05 * t.max()]))
    grands = [i for i in np.argsort(x0) if t[i] >= 0.12 * ref]
    bas, haut = (float(np.median(y0[grands])), float(np.median(y1[grands]))) if grands else (0.0, bloc.shape[0])
    if len(grands) >= 3:                         # à l'écart de la bande des lettres (au-dessus, en dessous) : du fond
        dans = [i for i in grands if min(y1[i], haut) - max(y0[i], bas) > 0.3 * min(y1[i] - y0[i], haut - bas)]
        ecartes = set(grands) - set(dans)
        grands = dans
        t = np.where(np.isin(np.arange(n), list(ecartes)), 0, t)    # ni lettre, ni petit morceau rattaché
    groupes: list[list] = []                     # [x0, x1, [morceaux], y0, y1]
    for i in grands:
        if groupes:
            # regroupés seulement s'ils sont l'un au-dessus de l'autre (lettre en deux morceaux, accent) ; côte à
            # côte (une lettre et une tache, ou deux lettres crénées comme « To »), ils restent séparés
            g = groupes[-1]
            recouvre = min(g[1], x1[i]) - max(g[0], x0[i])
            vertical = min(g[4], y1[i]) - max(g[3], y0[i])
            if recouvre > 0.6 * min(g[1] - g[0], x1[i] - x0[i]) and vertical < 0.3 * min(g[4] - g[3], y1[i] - y0[i]):
                g[0], g[1] = min(g[0], x0[i]), max(g[1], x1[i])
                g[3], g[4] = min(g[3], y0[i]), max(g[4], y1[i])
                g[2].append(i)
                continue
        groupes.append([int(x0[i]), int(x1[i]), [i], int(y0[i]), int(y1[i])])
    for i in range(n):                           # petits morceaux : au groupe qu'ils touchent en largeur, sinon oubliés
        if t[i] >= 0.12 * ref or t[i] == 0:
            continue
        rec = [min(g[1], x1[i]) - max(g[0], x0[i]) for g in groupes]
        j = int(np.argmax(rec))
        marge = 0.4 * (haut - bas)
        if rec[j] >= 0.5 * (x1[i] - x0[i]) and y0[i] >= bas - marge and y1[i] <= haut + marge:
            groupes[j][2].append(i)              # juste au-dessus ou au-dessous de la lettre (point, accent)
    if attendu:
        for _ in range(max(2, attendu // 5)):
            if len(groupes) == attendu:
                break
            larg = [g[1] - g[0] for g in groupes]
            med = float(np.median(larg))
            if len(groupes) < attendu:           # la plus large, coupée là où il y a le moins d'encre
                j = int(np.argmax(larg))
                if larg[j] < 1.35 * med:
                    break
                g = groupes[j]
                dedans = np.isin(lab, g[2])
                encre = (np.where(dedans, bloc, 0)).sum(axis=0)[g[0]:g[1]]
                a_, b_ = int(len(encre) * 0.25), int(len(encre) * 0.75)
                c = g[0] + a_ + int(np.argmin(encre[a_:b_]))
                groupes[j:j + 1] = [[g[0], c, g[2], g[3], g[4]], [c, g[1], g[2], g[3], g[4]]]
            else:
                encres = [float(t[g[2]].sum()) for g in groupes]
                hauts = [g[4] - g[3] for g in groupes]
                k = int(np.argmin(hauts))
                if hauts[k] < 0.5 * float(np.median(hauts)):     # bien trop bas pour une lettre : tache, tiret
                    del groupes[k]
                    continue
                k = int(np.argmin(encres))
                if encres[k] < 0.3 * float(np.median(encres)):    # bien trop petit pour une lettre : du fond
                    del groupes[k]
                    continue
                # sinon une lettre coupée en deux : les deux voisines les plus proches, recollées
                ecarts = [groupes[k + 1][0] - groupes[k][1] for k in range(len(groupes) - 1)]
                k = int(np.argmin(ecarts))
                g, h = groupes[k], groupes[k + 1]
                groupes[k:k + 2] = [[g[0], h[1], g[2] + h[2], min(g[3], h[3]), max(g[4], h[4])]]
    res = []
    rangs = np.zeros(bloc.shape[0], bool)
    for g in groupes:
        dedans = np.isin(lab, g[2])
        dedans = _adoucir(dedans.astype(np.float32), 1) > 0           # avec le bord adouci des lettres
        part = np.where(dedans, bloc, 0)[:, g[0]:g[1]]
        rangs |= (part > SEUIL_ENCRE).any(axis=1)
        res.append(part)
    if not rangs.any():
        return ([], []) if avec_x else []
    yy = np.nonzero(rangs)[0]
    res = [r[yy[0]:yy[-1] + 1] for r in res]
    return (res, [(g[0], g[1]) for g in groupes]) if avec_x else res


def lettres_image(m: np.ndarray, attendu: list[int] | None = None) -> list[list[np.ndarray]]:
    """Les lettres du masque (0..1), ligne par ligne (attendu : nombre de lettres tapées par ligne)."""
    lignes = _lignes(m)
    if attendu is not None and len(attendu) != len(lignes):
        attendu = None
    return [_lettres_ligne(m[y0:y1], attendu[k] if attendu else None) for k, (y0, y1) in enumerate(lignes)]


def compter_lettres(masque: np.ndarray) -> list[int]:
    """Nombre de lettres vues dans chaque ligne du masque (0..1 ou 0..255)."""
    m = masque.astype(np.float32)
    if m.max() > 1:
        m /= 255
    c = _recadrer(m)
    return [] if c is None else [len(l) for l in lettres_image(c)]


def sans_espaces(texte: str) -> list[str]:
    """Les lignes du texte, en lettres et chiffres seulement (ce qui se compare lettre par lettre)."""
    return ["".join(c for c in l if _lettre(c) in CARACTERES) for l in texte.split("\n")]


def _recadrer_ligne(glyphes: list[np.ndarray]) -> list[np.ndarray] | None:
    """Lettres d'une ligne écrites séparément (même hauteur, même ligne de base) : coupées à la hauteur de l'encre
    de toute la ligne, et à la largeur de l'encre de chacune."""
    rangs = np.zeros(glyphes[0].shape[0], bool)
    for g in glyphes:
        rangs |= (g > SEUIL_ENCRE).any(axis=1)
    if not rangs.any():
        return None
    ys = np.nonzero(rangs)[0]
    res = []
    for g in glyphes:
        g = g[ys[0]:ys[-1] + 1]
        xs = np.nonzero((g > SEUIL_ENCRE).any(axis=0))[0]
        if not len(xs):
            return None                          # lettre absente de la police
        res.append(g[:, xs[0]:xs[-1] + 1])
    return res


def glyphes_memoire(texte: str, fam: str, mem: dict | None = None) -> list[list[np.ndarray]] | None:
    """Les lettres du texte (sans les espaces), d'après la mémoire des polices (ou celle donnée)."""
    lettres = (memoire() if mem is None else mem)[fam][2]
    res = []
    for l in sans_espaces(texte):
        gs = []
        for c in l:
            c = _lettre(c)
            if c not in lettres:
                return None
            gs.append(lettres[c][2].astype(np.float32) / 255)
        r = _recadrer_ligne(gs) if gs else None
        if r is None:
            return None
        res.append(r)
    return res


def glyphes_police(texte: str, police: QFont) -> list[list[np.ndarray]] | None:
    """Les lettres du texte (sans les espaces), écrites une à une avec cette police."""
    fm = QFontMetrics(police)
    haut = fm.ascent() + fm.descent() + 2
    res = []
    for l in sans_espaces(texte):
        gs = []
        for c in l:
            larg = fm.horizontalAdvance(c) + 2 * fm.height()
            if larg <= 0 or haut <= 0 or larg * haut > 4_000_000:
                return None
            img = QImage(larg, haut, QImage.Format_Grayscale8)
            img.fill(0)
            p = QPainter(img)
            p.setRenderHint(QPainter.TextAntialiasing)
            p.setFont(police)
            p.setPen(Qt.white)
            p.drawText(fm.height(), fm.ascent() + 1, c)
            p.end()
            a = np.frombuffer(img.constBits(), np.uint8).reshape(haut, img.bytesPerLine())[:, :larg]
            gs.append(a.astype(np.float32) / 255)
        r = _recadrer_ligne(gs) if gs else None
        if r is None:
            return None
        res.append(r)
    return res


def _comparer_lettres(cible: list[list[np.ndarray]], essai: list[list[np.ndarray]], h: int,
                      epaisseur: bool = True) -> float:
    """Ressemblance 0..1, moyenne des lettres comparées une à une."""
    notes = [_comparer(a, b, h, epaisseur) for la, lb in zip(cible, essai) for a, b in zip(la, lb)]
    return float(np.mean(notes)) if notes else 0.0


def familles() -> list[str]:
    """Polices installées utilisables pour du texte (sans les polices de symboles ni les variantes cachées)."""
    db = QFontDatabase
    res = []
    for f in db.families():
        if f.startswith("@") or db.isPrivateFamily(f):
            continue
        if QFontDatabase.WritingSystem.Latin not in db.writingSystems(f):
            continue
        if db.isSmoothlyScalable(f) is False:
            continue
        res.append(f)
    return res


# ------------------------------------------------------------------ mémoire des polices
CARACTERES = string.ascii_letters + string.digits
VERSION_MEMOIRE = 4             # 4 : lettres écrites une par une (mémoire refaite)
LENTE = 1.0                     # s : police très décorée (ex. St. Andrew, 30 s) : jamais réécrite pendant une recherche
_memoire: dict | None = None
_date_memoire = None


def fichier_memoire() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Pixane"
    nom = "polices.memoire"
    if os.environ.get("PIXANE_REGLAGES"):                 # essais : à part
        nom = f"polices-{os.environ['PIXANE_REGLAGES']}.memoire"
    return base / nom


def memoire() -> dict:
    """{famille: (hauteur de ligne, ligne de base, {caractère: (avance, décalage, lettre uint8)}, espace, durée)}.
    Relue si le fichier a changé (complété par le processus d'arrière-plan)."""
    global _memoire, _date_memoire
    try:
        date = fichier_memoire().stat().st_mtime
    except OSError:
        date = None
    if _memoire is None or (date is not None and date != _date_memoire):
        ancienne = _memoire or {}
        _memoire = {}
        try:
            d = pickle.loads(zlib.decompress(fichier_memoire().read_bytes()))
            if d.get("version") == VERSION_MEMOIRE and d.get("taille") == TAILLE_TRI:
                _memoire = d["familles"]
        except Exception:                                  # absente ou abîmée : refaite
            _memoire = {}
        for k, v in ancienne.items():                      # ce qui a été fait ici entre-temps reste
            _memoire.setdefault(k, v)
        _date_memoire = date
    return _memoire


def lente(fam: str) -> bool:
    v = memoire().get(fam)
    return v is not None and v[4] > LENTE


def enregistrer_memoire() -> None:
    global _date_memoire
    f = fichier_memoire()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f"{f.name}.{os.getpid()}.part")
    tmp.write_bytes(zlib.compress(pickle.dumps({"version": VERSION_MEMOIRE, "taille": TAILLE_TRI,
                                                "familles": memoire()}, protocol=4), 6))
    os.replace(tmp, f)
    _date_memoire = f.stat().st_mtime


def mettre_en_memoire(fam: str) -> None:
    memoire()[fam] = lettres_police(fam)


def lettres_police(fam: str) -> tuple:
    """Écrit chaque lettre de l'alphabet à sa place (une par une : écrit d'un seul trait, l'alphabet se décalait
    peu à peu dans certaines polices, et des lettres voisines étaient rangées à la place des bonnes), avec de la
    marge : les lettres penchées ou qui débordent restent entières."""
    debut = time.time()
    f = QFont(fam)
    f.setPixelSize(TAILLE_TRI)
    fm = QFontMetrics(f)
    marge = max(4, fm.horizontalAdvance("   ") // 2, fm.height() // 2)
    avances = [fm.horizontalAdvance(c) for c in CARACTERES]
    larg, haut = sum(avances) + 2 * marge * len(CARACTERES), fm.ascent() + fm.descent() + 2
    lettres = {}
    if 0 < larg < 60000 and haut > 0:
        img = QImage(larg, haut, QImage.Format_Grayscale8)
        img.fill(0)
        p = QPainter(img)
        p.setFont(f)
        p.setPen(Qt.white)
        x = 0
        for c, av in zip(CARACTERES, avances):
            p.drawText(x + marge, fm.ascent() + 1, c)
            x += av + 2 * marge
        p.end()
        a = np.frombuffer(img.constBits(), np.uint8).reshape(haut, img.bytesPerLine())[:, :larg]
        x = 0
        for c, av in zip(CARACTERES, avances):
            lettres[c] = (av, -marge, a[:, x:x + av + 2 * marge].copy())
            x += av + 2 * marge
    return fm.lineSpacing(), fm.ascent() + 1, lettres, fm.horizontalAdvance(" "), time.time() - debut


def _lettre(c: str) -> str:
    """É -> E, ç -> c… (le tri rapide n'a que les lettres sans accent)."""
    return unicodedata.normalize("NFD", c)[0] if c not in CARACTERES else c


def assembler(texte: str, fam: str, mem: dict | None = None) -> np.ndarray | None:
    """Le texte écrit avec les lettres en mémoire (sans crénage : assez pour un premier tri)."""
    ligne_h, _base, lettres, espace, _duree = (memoire() if mem is None else mem)[fam]
    if not lettres:
        return None
    lignes = texte.split("\n")
    haut = next(iter(lettres.values()))[2].shape[0]
    larg = [sum(lettres[_lettre(c)][0] if _lettre(c) in lettres else espace for c in l) for l in lignes]
    bord = max(g.shape[1] for _a, _d, g in lettres.values()) + 4
    W = max(larg) + 2 * bord
    toile = np.zeros((ligne_h * (len(lignes) - 1) + haut, W), np.uint8)
    for n, l in enumerate(lignes):
        x, y = bord + (max(larg) - larg[n]) // 2, n * ligne_h
        for c in l:
            c = _lettre(c)
            if c in lettres:
                av, dec, g = lettres[c]
                x0 = max(0, x + dec)
                x1 = min(W, x0 + g.shape[1])
                if x1 > x0:
                    zone = toile[y:y + haut, x0:x1]
                    np.maximum(zone, g[:, :x1 - x0], out=zone)
                x += av
            else:
                x += espace
    return _recadrer(toile.astype(np.float32) / 255)


def chercher(masque: np.ndarray, texte: str, nombre: int = 10, progres=None, liste: list | None = None,
             infos: dict | None = None, google: dict | None = None) -> list[Resultat]:
    """Les `nombre` polices les plus proches des lettres du masque (0..1 ou 0..255). progres(fait, total) peut
    renvoyer False pour arrêter. google : mémoire des polices Google (par défaut celle de l'option, vide si
    l'option est désactivée). infos (dict) reçoit : "texte" (le texte vraiment comparé : en majuscules si l'image
    semble l'être), "lettre_par_lettre" (bool)."""
    texte = texte.strip()
    m = masque.astype(np.float32)
    if m.max() > 1:
        m /= 255
    cible = _recadrer(m)
    if cible is None or not texte:
        return []
    infos = {} if infos is None else infos
    tapees = [len(l) for l in sans_espaces(texte)]
    lettres_cible = lettres_image(cible, tapees)
    par_lettre = [len(l) for l in lettres_cible] == tapees and sum(tapees) > 0
    infos["lettre_par_lettre"] = par_lettre
    variantes = [texte] + ([texte.upper()] if texte.upper() != texte else [])

    def note_memoire(t: str, fam: str, mem: dict | None = None) -> float | None:
        if par_lettre:
            e = glyphes_memoire(t, fam, mem)
            return None if e is None else _comparer_lettres(lettres_cible, e, HAUT_TRI, epaisseur=False)
        e = assembler(t, fam, mem)
        return None if e is None else _comparer(cible, e, HAUT_TRI, epaisseur=False)

    def note_police(t: str, f: QFont, h: int):
        """(note, empreinte du rendu) : deux styles au même rendu (style absent de la police) ont la même."""
        if par_lettre:
            e = glyphes_police(t, f)
            if e is None:
                return None
            return _comparer_lettres(lettres_cible, e, h), tuple((g.shape, round(float(g.sum()), 1))
                                                                 for l in e for g in l)
        e = masque_texte(t, f)
        return None if e is None else (_comparer(cible, e, h), (e.shape, float(e.sum())))

    liste = familles() if liste is None else liste
    # polices gratuites de Google Fonts (option) : celles qui ne sont pas déjà installées
    from . import polices_google
    google = polices_google.memoire() if google is None else google
    installees = set(liste) | set(familles())
    google = {f: v for f, v in google.items() if f not in installees}
    total = len(liste) + len(google) + PREMIERS * (len(STYLES) - 1)
    fait = 0
    # passe 1 : toutes les polices, style normal, petite taille (le texte tapé, et aussi en majuscules)
    tris = {t: [] for t in variantes}
    mem = memoire()
    nouvelles = False
    for fam in liste:
        fait += 1
        if fam not in mem:                              # première fois : la police est mise en mémoire
            mettre_en_memoire(fam)
            nouvelles = True
        for t in variantes:
            n = note_memoire(t, fam)
            if n is not None:
                tris[t].append((n, fam))
        if progres is not None and fait % 20 == 0 and progres(fait, total) is False:
            if nouvelles:
                enregistrer_memoire()
            return []
    if nouvelles:
        enregistrer_memoire()
    for fam in google:
        fait += 1
        for t in variantes:
            n = note_memoire(t, fam, google)
            if n is not None:
                tris[t].append((n, fam))
        if progres is not None and fait % 20 == 0 and progres(fait, total) is False:
            return []

    def niveau(t: str) -> float:                        # note moyenne des 20 meilleures polices
        tris[t].sort(reverse=True)
        return float(np.mean([n for n, _f in tris[t][:20]])) if tris[t] else 0.0
    # en majuscules seulement si les lettres de l'image le sont nettement plus que le texte tapé
    texte = max(variantes, key=lambda t: niveau(t) * (1.0 if t == variantes[0] else 0.95))
    infos["texte"] = texte
    tri = tris[texte]
    infos["tri"] = [f for _n, f in tri]
    # passe 2 : les meilleures, avec gras, italique, gras italique (les polices Google : chargées pour l'occasion)
    noms_google = {}
    for _n, fam in tri[:PREMIERS]:
        if fam in google:
            vrai = polices_google.charger(fam)
            if vrai:
                noms_google[fam] = vrai
    notes, lentes = [], []
    for n_tri, fam in tri[:PREMIERS]:
        if fam in google and fam not in noms_google:
            continue
        fam = noms_google.get(fam, fam)
        if fam not in google and fam not in noms_google.values() and lente(fam):
            # très lente à écrire : on garde sa note du tri
            lentes.append((n_tri, Resultat(fam, False, False, 0)))
            continue
        vus = set()
        for poids, ital in STYLES:
            fait += 1
            f = QFont(fam)
            f.setPixelSize(HAUT_RAPIDE * 2)
            f.setWeight(poids)
            f.setItalic(ital)
            r = note_police(texte, f, HAUT_RAPIDE)
            if r is None or r[1] in vus:
                continue
            vus.add(r[1])
            notes.append((r[0], fam, poids == QFont.Bold, ital))
        if progres is not None and progres(fait, total) is False:
            return []
    notes.sort(reverse=True)
    fins = []
    for _n, fam, gras, ital in notes[:GARDER]:
        r = Resultat(fam, gras, ital, 0)
        x = note_police(texte, r.police(HAUT_FIN * 2), HAUT_FIN)
        if x is not None:
            # à ressemblance presque égale, une police déjà installée passe avant une police Google à installer
            fins.append((x[0] * (0.99 if fam in noms_google.values() else 1.0), r))
    fins += lentes
    fins.sort(key=lambda t: -t[0])
    res, familles_vues = [], set()
    inverse = {v: k for k, v in noms_google.items()}
    for n, r in fins:                    # une famille une fois (sa meilleure variante)
        if r.famille in familles_vues:
            continue
        familles_vues.add(r.famille)
        r.score = round(n * 100, 1)
        if r.famille in inverse:
            r.google, r.licence = polices_google.source(inverse[r.famille])
        res.append(r)
        if len(res) >= nombre:
            break
    return res


def completer_memoire() -> int:
    """Met en mémoire les polices qui n'y sont pas encore (enregistré toutes les 100). Renvoie leur nombre."""
    faites = 0
    for fam in familles():
        if fam in memoire():
            continue
        mettre_en_memoire(fam)
        faites += 1
        if faites % 100 == 0:
            enregistrer_memoire()
    if faites:
        enregistrer_memoire()
    return faites


def lancer_en_fond() -> None:
    """Complète la mémoire dans un processus à part, en priorité basse et sans fenêtre (le calcul garde Python
    occupé : dans Pixane même, la fenêtre se figerait). Rien ne se passe si c'est déjà fait."""
    import subprocess
    import sys
    racine = Path(__file__).resolve().parents[1]
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe" and (exe.parent / "pythonw.exe").is_file():
        exe = exe.parent / "pythonw.exe"
    drapeaux = 0
    if os.name == "nt":
        drapeaux = subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW
    try:
        subprocess.Popen([str(exe), "-m", "pixane.polices_semblables", "--memoire"], cwd=str(racine),
                         creationflags=drapeaux, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)
    except OSError:
        pass


if __name__ == "__main__":                       # mesure rapide : python -m pixane.polices_semblables
    import sys
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication(sys.argv)
    if "--memoire" in sys.argv:                  # processus d'arrière-plan lancé par Pixane
        verrou = fichier_memoire().with_suffix(".verrou")
        try:
            verrou.parent.mkdir(parents=True, exist_ok=True)
            if verrou.exists() and time.time() - verrou.stat().st_mtime < 1800:
                sys.exit(0)                      # un autre est déjà en route
            verrou.write_text(str(os.getpid()))
            completer_memoire()
        finally:
            verrou.unlink(missing_ok=True)
        sys.exit(0)
    for fam, gras in (("Impact", False), ("Times New Roman", True), ("Comic Sans MS", False), ("Consolas", False)):
        f = QFont(fam)
        f.setPixelSize(90)
        f.setBold(gras)
        cible = masque_texte("DISCO Night", f)
        t = time.time()
        r = chercher(cible, "DISCO Night", 5)
        print(f"{fam}{' gras' if gras else ''} : {time.time() - t:.1f} s ->",
              ", ".join(f"{x.famille}{' G' if x.gras else ''}{' I' if x.italique else ''} {x.score}" for x in r))
