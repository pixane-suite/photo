"""Calques de texte : réglages (police, couleur, effets…) et dessin du texte sur un calque.

Un calque de texte garde ses réglages (`Texte`) en plus de son image : on peut le modifier à tout moment.
Les tailles des effets (contour, ombre, fond) sont en % de la taille des lettres : ils suivent le texte
quand on change sa taille ou qu'on agrandit l'image.

Mise en page (comme le panneau Caractère et Paragraphe de Photoshop) : le moteur de texte de Qt (QTextLayout)
place les lettres (crénage, ligatures, majuscules, petites capitales, retours à la ligne, justifié) ; Pixane
ajoute l'étirement des lettres, l'exposant / indice, la ligne de base, le style par lettre, le crénage à la
main, le texte vertical, le texte en cadre, l'arc, le texte sur un tracé et la déformation.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields, replace
from functools import lru_cache

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPainterPathStroker, QPen,
                           QPolygonF, QTextCharFormat, QTextLayout, QTextOption, QTransform)

GAUCHE, CENTRE, DROITE, JUSTIFIE = "gauche", "centre", "droite", "justifie"
CASSES = ("normale", "majuscules", "minuscules", "petites_capitales", "titre")
POSITIONS = ("normale", "exposant", "indice")
DEFORMATIONS = ("aucune", "arc", "arc_inferieur", "arc_superieur", "arche", "renflement", "drapeau", "vague",
                "poisson", "montee", "oeil_de_poisson", "gonflement", "compression", "torsion")
# réglages qui peuvent changer d'une lettre à l'autre (style par lettre)
CHAMPS_LETTRE = ("police", "taille", "gras", "italique", "souligne", "barre", "couleur", "lettres", "echelle_h",
                 "echelle_v", "position", "ligne_base", "casse")
TAILLE_EXPOSANT = 0.62           # exposant / indice : taille des lettres
MONTEE_EXPOSANT = 0.36           # exposant : monté de 36 % de la taille ; indice : descendu de 14 %
DESCENTE_INDICE = 0.14
TIRET_CONDITIONNEL = "­"    # césure : coupure possible, tiret montré seulement en fin de ligne


@dataclass(frozen=True)
class Texte:
    texte: str = "Texte"
    police: str = "Segoe UI"
    taille: float = 80.0             # hauteur des lettres, en px de l'image
    gras: bool = False
    italique: bool = False
    souligne: bool = False
    barre: bool = False
    couleur: str = "#ffffffff"       # #AARRGGBB
    alignement: str = GAUCHE
    x: float = 0.0                   # centre du bloc de texte, en px de l'image
    y: float = 0.0
    angle: float = 0.0               # rotation, en degrés (sens des aiguilles d'une montre)
    lettres: float = 0.0             # espacement des lettres, en % de la taille
    interligne: float = 1.2          # écart entre les lignes, × la taille
    courbe: float = 0.0              # arc en degrés : > 0 en voûte, < 0 en creux, 360 = cercle
    contour: bool = False
    contour_couleur: str = "#ff000000"
    contour_epaisseur: float = 6.0   # % de la taille
    ombre: bool = False
    ombre_couleur: str = "#b4000000"
    ombre_distance: float = 8.0      # % de la taille
    ombre_direction: float = 45.0    # degrés : 0 = vers la droite, 90 = vers le bas
    ombre_flou: float = 8.0          # % de la taille
    fond: bool = False
    fond_couleur: str = "#b4000000"
    fond_marge: float = 25.0         # % de la taille
    fond_arrondi: float = 20.0       # % de la taille
    # ---- caractère (comme Photoshop)
    casse: str = "normale"           # normale, majuscules, minuscules, petites_capitales, titre
    echelle_h: float = 100.0         # largeur des lettres, %
    echelle_v: float = 100.0         # hauteur des lettres, %
    position: str = "normale"        # normale, exposant, indice
    ligne_base: float = 0.0          # décalage de la ligne de base, % de la taille (> 0 : vers le haut)
    crenage: bool = True             # crénage de la police (paires de lettres) ; False : aucun
    ligatures: bool = True           # fi, fl… (si la police en a)
    fractions: bool = False          # 1/2 -> ½ (si la police le permet)
    chiffres_anciens: bool = False   # chiffres elzéviriens (si la police en a)
    lissage: bool = True             # bords lissés ; False : pixels nets (crénelés)
    # ---- paragraphe
    vertical: bool = False           # lettres les unes sous les autres, colonnes de droite à gauche
    cadre_l: float = 0.0             # texte en cadre : largeur du cadre en px (0 : texte libre)
    cadre_h: float = 0.0             # hauteur du cadre en px (0 : selon le texte)
    cesure: bool = False             # couper les longs mots en fin de ligne (texte en cadre)
    langue: str = ""                 # langue du texte (orthographe, césure) : "fr", "en" ; "" = celle de Pixane
    retrait: float = 0.0             # alinéa de la première ligne de chaque paragraphe, % de la taille
    espace_paragraphe: float = 0.0   # espace entre les paragraphes, % de la taille
    # ---- forme
    deformation: str = "aucune"      # voir DEFORMATIONS
    flexion: float = 50.0            # force de la déformation, -100..100
    distorsion_h: float = 0.0        # -100..100
    distorsion_v: float = 0.0        # -100..100
    trace: tuple = ()                # texte sur un tracé : points (x, y) relatifs au centre, avant rotation
    trace_debut: float = 0.0         # départ du texte le long du tracé, %
    # ---- style par lettre et crénage à la main
    styles: tuple = ()               # ((début, fin, ((champ, valeur), …)), …) : réglages de certaines lettres
    crenages: tuple = ()             # ((index, valeur), …) : espace ajouté avant la lettre index, ‰ de la taille

    # ---------------------------------------------------------- fichiers (.piximg)
    def vers_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def depuis_dict(d: dict) -> "Texte":
        connus = {f.name for f in fields(Texte)}
        v = {k: val for k, val in d.items() if k in connus}
        if "trace" in v:
            v["trace"] = tuple((float(a), float(b)) for a, b in v["trace"] or ())
        if "styles" in v:
            v["styles"] = tuple((int(a), int(b), tuple((str(k), _fige(x)) for k, x in ch))
                                for a, b, ch in v["styles"] or ())
        if "crenages" in v:
            v["crenages"] = tuple((int(i), float(x)) for i, x in v["crenages"] or ())
        return Texte(**v)

    # ---------------------------------------------------------- géométrie
    def deplace(self, dx: float, dy: float) -> "Texte":
        return replace(self, x=self.x + dx, y=self.y + dy)

    def mis_a_l_echelle(self, fx: float, fy: float) -> "Texte":
        k = (fx + fy) / 2
        styles = tuple((a, b, tuple((c, v * k if c == "taille" else v) for c, v in ch)) for a, b, ch in self.styles)
        return replace(self, x=self.x * fx, y=self.y * fy, taille=self.taille * k, cadre_l=self.cadre_l * k,
                       cadre_h=self.cadre_h * k, trace=tuple((px * k, py * k) for px, py in self.trace),
                       styles=styles)

    def pct(self, valeur: float) -> float:
        """% de la taille des lettres -> px."""
        return self.taille * valeur / 100

    # ---------------------------------------------------------- style par lettre
    def par_lettre(self) -> list[dict]:
        """Réglages propres à chaque lettre (seulement ceux qui diffèrent du texte entier)."""
        n = len(self.texte)
        res = [{} for _ in range(n)]
        for a, b, ch in self.styles:
            for i in range(max(0, a), min(n, b)):
                res[i].update(dict(ch))
        return res

    def style_de(self, i: int) -> dict:
        """Tous les réglages de caractère de la lettre i (ceux du texte, sauf ceux propres à la lettre)."""
        base = {c: getattr(self, c) for c in CHAMPS_LETTRE}
        if 0 <= i < len(self.texte):
            base.update(self.par_lettre()[i])
        return base

    def avec_style(self, debut: int, fin: int, **champs) -> "Texte":
        """Réglages de caractère donnés aux lettres debut..fin (exclue) seulement."""
        liste = self.par_lettre()
        for i in range(max(0, debut), min(len(liste), fin)):
            for c, v in champs.items():
                if v == getattr(self, c):
                    liste[i].pop(c, None)       # comme le texte entier : plus besoin de le noter
                else:
                    liste[i][c] = v
        return replace(self, styles=_compresser(liste))

    def avec_texte(self, nouveau: str) -> "Texte":
        """Texte changé à la saisie : les styles par lettre et les crénages suivent les lettres (les lettres
        tapées prennent le style de celle d'avant, comme dans un traitement de texte)."""
        ancien = self.texte
        if nouveau == ancien:
            return self
        p = 0
        while p < min(len(ancien), len(nouveau)) and ancien[p] == nouveau[p]:
            p += 1
        s = 0
        while s < min(len(ancien), len(nouveau)) - p and ancien[-1 - s] == nouveau[-1 - s]:
            s += 1
        liste = self.par_lettre()
        modele = dict(liste[p - 1]) if p > 0 and liste else (dict(liste[p]) if p < len(liste) else {})
        ajoutes = len(nouveau) - p - s
        liste = liste[:p] + [dict(modele) for _ in range(ajoutes)] + liste[len(ancien) - s:]
        decalage = len(nouveau) - len(ancien)
        crenages = []
        for i, v in self.crenages:
            if i <= p:
                crenages.append((i, v))
            elif i >= len(ancien) - s:
                crenages.append((i + decalage, v))
        return replace(self, texte=nouveau, styles=_compresser(liste), crenages=tuple(crenages))

    def crenage_a(self, i: int) -> float:
        return dict(self.crenages).get(i, 0.0)

    def avec_crenage(self, i: int, valeur: float) -> "Texte":
        d = dict(self.crenages)
        if abs(valeur) < 1e-9:
            d.pop(i, None)
        else:
            d[i] = float(valeur)
        return replace(self, crenages=tuple(sorted(d.items())))

    def sans_styles_lettres(self) -> "Texte":
        return replace(self, styles=(), crenages=())


# réglages qui ne font pas partie d'un « style de texte » (copier / coller le style, styles enregistrés)
HORS_STYLE = ("texte", "x", "y", "angle", "styles", "crenages", "trace", "trace_debut", "cadre_l", "cadre_h")


def style_texte(t: Texte) -> dict:
    """Style du texte (police, couleur, effets, réglages de caractère et de paragraphe), sans le texte ni sa place."""
    return {k: v for k, v in t.vers_dict().items() if k not in HORS_STYLE}


def avec_style_texte(t: Texte, style: dict) -> Texte:
    """Le style donné appliqué au texte entier (les styles propres à certaines lettres sont retirés)."""
    d = t.vers_dict()
    d.update({k: v for k, v in style.items() if k not in HORS_STYLE})
    d["styles"] = []
    return Texte.depuis_dict(d)


def _fige(v):
    return tuple(v) if isinstance(v, list) else v


def _compresser(liste: list[dict]) -> tuple:
    res = []
    i = 0
    while i < len(liste):
        if not liste[i]:
            i += 1
            continue
        j = i + 1
        while j < len(liste) and liste[j] == liste[i]:
            j += 1
        res.append((i, j, tuple(sorted(liste[i].items()))))
        i = j
    return tuple(res)


def nom_calque(t: Texte, defaut: str) -> str:
    """Nom automatique d'un calque de texte : sa première ligne (comme Photoshop)."""
    ligne = next((l.strip() for l in t.texte.splitlines() if l.strip()), "")
    return (ligne[:30] + "…") if len(ligne) > 30 else (ligne or defaut)


_CAPITALES = {"normale": QFont.MixedCase, "majuscules": QFont.AllUppercase, "minuscules": QFont.AllLowercase,
              "petites_capitales": QFont.SmallCaps, "titre": QFont.Capitalize}


def police_lettre(t: Texte, st: dict, cren: float = 0.0) -> QFont:
    """Police d'un morceau de texte (réglages st, voir Texte.style_de) ; cren : espace ajouté après, en px."""
    f = QFont(st["police"])
    px = st["taille"] * (TAILLE_EXPOSANT if st["position"] != "normale" else 1.0)
    f.setPixelSize(max(1, round(px)))
    f.setBold(bool(st["gras"]))
    f.setItalic(bool(st["italique"]))
    f.setLetterSpacing(QFont.AbsoluteSpacing, st["taille"] * st["lettres"] / 100 + cren)
    f.setCapitalization(_CAPITALES.get(st["casse"], QFont.MixedCase))
    if abs(st["echelle_h"] - 100) > 0.05:
        f.setStretch(max(1, min(4000, round(st["echelle_h"]))))
    f.setKerning(t.crenage)
    f.setFeature(QFont.Tag("liga"), int(t.ligatures))
    f.setFeature(QFont.Tag("clig"), int(t.ligatures))
    if t.fractions:
        f.setFeature(QFont.Tag("frac"), 1)
    if t.chiffres_anciens:
        f.setFeature(QFont.Tag("onum"), 1)
    f.setHintingPreference(QFont.PreferNoHinting)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def police(t: Texte) -> QFont:
    """Police du texte entier (réglages de base)."""
    return police_lettre(t, t.style_de(-1))


# ------------------------------------------------------------------ mise en page
@dataclass
class Lettre:
    chemin: QPainterPath     # dessin de la lettre (soulignement compris), posé à sa place
    couleur: str
    x: float                 # début de la lettre sur sa ligne
    avance: float
    base: float              # ligne de base
    ligne: int


@dataclass
class Mise:
    morceaux: list           # [(chemin, couleur)] : un chemin par couleur
    chemin: QPainterPath     # toutes les lettres (contour, ombre)
    bloc: QRectF             # rectangle du bloc (cadre, ou autour des lettres), avant rotation
    fond: QPainterPath | None


def _segments(t: Texte, debut: int, fin: int, lettres: list[dict]) -> list[tuple[int, int, dict, float]]:
    """Morceaux de même style dans t.texte[debut:fin] : (début, fin, style, 0). Le crénage à la main n'y coupe pas
    le texte (Qt perdrait le crénage de la police à cet endroit) : il est ajouté après, voir _crenages_main."""
    base = t.style_de(-1)
    res = []
    i = debut
    while i < fin:
        st = dict(base, **lettres[i])
        j = i + 1
        while j < fin and lettres[j] == lettres[i]:
            j += 1
        res.append((i, j, st, 0.0))
        i = j
    return res


def _crenages_main(t: Texte, dispo, lettres: list[Lettre], libre: bool):
    """Crénage à la main : les lettres qui suivent sur la même ligne sont décalées ; texte libre centré ou à droite :
    la ligne est recentrée."""
    if not t.crenages:
        return
    n0 = 0
    total = {}
    for lay, _segs, a, lignes, places in dispo:
        longueur = len(places) - 1
        for idx, v in t.crenages:
            pos = idx - a
            if not (0 < pos < longueur) or not v:
                continue
            pos = places[pos]
            ligne = lay.lineForTextPosition(pos)
            if not ligne.isValid() or pos == ligne.textStart():
                continue
            x = ligne.cursorToX(pos)
            x = (x[0] if isinstance(x, tuple) else x) + ligne.x()
            n = n0 + ligne.lineNumber()
            d = t.taille * v / 1000
            total[n] = total.get(n, 0.0) + d
            for l in lettres:
                if l.ligne == n and l.x >= x - 1e-3:
                    l.chemin.translate(d, 0)
                    l.x += d
        n0 += len(lignes)
    if libre and t.alignement in (CENTRE, DROITE):
        for l in lettres:
            d = total.get(l.ligne, 0.0) * (0.5 if t.alignement == CENTRE else 1.0)
            if d:
                l.chemin.translate(-d, 0)
                l.x -= d


def _justifie_sans_espace(dispo, lettres: list[Lettre]):
    """Justifié : une ligne d'un seul mot n'est pas étirée lettre par lettre (Qt le fait) ; elle reste à gauche,
    comme dans Photoshop."""
    n0 = 0
    for lay, _segs, _a, lignes, _p in dispo:
        texte = lay.text()
        for k, (ligne, _ind) in enumerate(lignes):
            morceau = texte[ligne.textStart():ligne.textStart() + ligne.textLength()].replace("­", "")
            if k < len(lignes) - 1 and not any(c.isspace() for c in morceau.strip()):
                dans = sorted((l for l in lettres if l.ligne == n0 + k), key=lambda l: l.x)
                if len(dans) > 1:
                    plus = (dans[-1].x + dans[-1].avance - dans[0].x - ligne.naturalTextWidth()) / (len(dans) - 1)
                    if plus > 1e-3:
                        for i, l in enumerate(dans):
                            l.chemin.translate(-i * plus, 0)
                            l.x -= i * plus
        n0 += len(lignes)


def _cesure(t: Texte, morceau: str) -> tuple[str, list[int]]:
    """Césure : le paragraphe avec ses coupures possibles (tirets conditionnels, montrés seulement en fin de ligne) ;
    et pour chaque caractère d'origine (plus la fin), sa place dans ce texte."""
    try:
        from .orthographe import active, couper
        nouveau = couper(morceau, t.langue) if active() else morceau      # option « Orthographe et césure »
    except Exception:                       # césure indisponible : texte tel quel
        nouveau = morceau
    places = []
    j = 0
    for ch in morceau:
        while j < len(nouveau) and nouveau[j] != ch:
            j += 1
        places.append(j)
        j += 1
    places.append(len(nouveau))
    return nouveau, places


def _glyphes(t: Texte, lay: QTextLayout, segs, p0: int, ligne_de, lettres_out: list, cache_fm: dict):
    """Les lettres du paragraphe mis en page (lay), morceau par morceau (style connu de chacun)."""
    for a, b, st, _c in segs:
        sx, sy = st["echelle_h"] / 100, st["echelle_v"] / 100
        dy = -t.taille * st["ligne_base"] / 100
        if st["position"] == "exposant":
            dy -= st["taille"] * MONTEE_EXPOSANT
        elif st["position"] == "indice":
            dy += st["taille"] * DESCENTE_INDICE
        cle = (st["police"], st["taille"], st["gras"], st["italique"], st["position"])
        if cle not in cache_fm:
            cache_fm[cle] = QFontMetricsF(police_lettre(t, st))
        fm = cache_fm[cle]
        trait = max(1.0, fm.lineWidth())
        for run in lay.glyphRuns(a - p0, b - a):
            raw = run.rawFont()
            idx = run.glyphIndexes()
            pos = run.positions()
            avances = raw.advancesForGlyphIndexes(idx)
            for k, (g, q) in enumerate(zip(idx, pos)):
                if k + 1 < len(pos) and abs(pos[k + 1].y() - q.y()) < 1e-3:
                    av = pos[k + 1].x() - q.x()
                else:
                    av = avances[k].x() * sx
                c = raw.pathForGlyph(g)
                tr = QTransform()
                tr.translate(q.x(), q.y() + dy)
                tr.scale(sx, sy)
                c = tr.map(c)
                base = q.y() + dy
                if st["souligne"]:
                    c.addRect(QRectF(q.x(), base + fm.underlinePos(), av, trait))
                if st["barre"]:
                    c.addRect(QRectF(q.x(), base - fm.strikeOutPos() * sy - trait / 2, av, trait))
                lettres_out.append(Lettre(c, st["couleur"], q.x(), av, base, ligne_de(q.y())))


def _horizontal(t: Texte) -> tuple[list[Lettre], QRectF, list[float]]:
    """Texte libre ou en cadre, lignes horizontales. Renvoie (lettres, bloc, lignes de base), origine en haut à
    gauche du bloc."""
    lettres = t.par_lettre()
    fmb = QFontMetricsF(police(t))
    h_ref = max(1e-3, fmb.height())
    en_cadre = t.cadre_l > 0 and not t.vertical
    largeur = max(1.0, t.cadre_l)
    retrait = t.pct(t.retrait)
    esp = t.pct(t.espace_paragraphe)
    align = {GAUCHE: Qt.AlignLeft, CENTRE: Qt.AlignHCenter, DROITE: Qt.AlignRight,
             JUSTIFIE: Qt.AlignJustify}.get(t.alignement, Qt.AlignLeft)
    paragraphes = []
    i = 0
    for morceau in t.texte.split("\n"):
        paragraphes.append((i, i + len(morceau), morceau))
        i += len(morceau) + 1

    def disposer(lineaire: float | None):
        """Une passe de mise en page ; lineaire : largeur des lignes (None : sans retour à la ligne)."""
        res = []                      # (layout, segments, début, [(ligne, retrait)], places des caractères)
        bases = []
        y = None
        cache_fm = {}
        for n_par, (a, b, morceau) in enumerate(paragraphes):
            if en_cadre and t.cesure:
                dans_lay, places = _cesure(t, morceau)
            else:
                dans_lay, places = morceau, list(range(len(morceau) + 1))
            segs = [(places[sa - a], places[sb - a], st, c) for sa, sb, st, c in _segments(t, a, b, lettres)]
            lay = QTextLayout(dans_lay, police(t))
            opt = QTextOption()
            opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere if en_cadre else QTextOption.NoWrap)
            opt.setAlignment(align if (en_cadre or lineaire is not None) else Qt.AlignLeft)
            lay.setTextOption(opt)
            formats = []
            for sa, sb, st, c in segs:
                fr = QTextLayout.FormatRange()
                fr.start, fr.length = sa, sb - sa
                cf = QTextCharFormat()
                cf.setFont(police_lettre(t, st, c))
                fr.format = cf
                formats.append(fr)
            lay.setFormats(formats)
            lay.beginLayout()
            premiere = True
            lignes = []
            while True:
                ligne = lay.createLine()
                if not ligne.isValid():
                    break
                ind = retrait if premiere else 0.0
                ligne.setLineWidth(max(1.0, (lineaire if lineaire is not None else 1e7) - ind))
                k = max(1.0, ligne.height() / h_ref)
                if y is None:
                    y = ligne.ascent()
                else:
                    y += t.taille * t.interligne * k + (esp if premiere and n_par > 0 else 0.0)
                ligne.setPosition(QPointF(ind, y - ligne.ascent()))
                bases.append(y)
                lignes.append((ligne, ind))
                premiere = False
            lay.endLayout()
            res.append((lay, segs, a, lignes, places))
        return res, bases

    if en_cadre:
        dispo, bases = disposer(largeur)
        L = largeur
    else:
        dispo, bases = disposer(None)
        larg = [ind + l.naturalTextWidth() for _lay, _s, _a, lignes, _p in dispo for l, ind in lignes]
        L = max(larg + [1.0])
        if t.alignement != GAUCHE and len(larg) > 1:
            dispo, bases = disposer(L)               # aligné sur la ligne la plus longue
    sortie: list[Lettre] = []
    cache_fm = {}
    toutes = [(l.y(), l.height()) for _lay, _s, _a, lignes, _p in dispo for l, _ind in lignes]

    def ligne_de(yb: float) -> int:
        for n, (top, h) in enumerate(toutes):
            if top - 1e-3 <= yb <= top + h + 1e-3:
                return n
        return len(toutes) - 1
    for lay, segs, _a, _lignes, _p in dispo:
        _glyphes(t, lay, segs, 0, ligne_de, sortie, cache_fm)
    _crenages_main(t, dispo, sortie, not en_cadre)
    if en_cadre and t.alignement == JUSTIFIE:
        _justifie_sans_espace(dispo, sortie)
    if not bases:
        bases = [fmb.ascent()]
    haut = 0.0
    bas = bases[-1] + fmb.descent()
    if en_cadre and t.cadre_h > 0:
        bas = t.cadre_h
        sortie = [l for l in sortie if l.base <= t.cadre_h + 1e-3]      # ce qui dépasse du cadre est caché
    bloc = QRectF(0, haut, L, max(1.0, bas - haut))
    return sortie, bloc, bases


def _vertical(t: Texte) -> tuple[list[Lettre], QRectF]:
    """Texte vertical (comme l'outil Texte vertical de Photoshop) : chaque paragraphe est une colonne, lettres
    les unes sous les autres, colonnes de droite à gauche."""
    lettres = t.par_lettre()
    pas_col = t.taille * t.interligne
    colonnes = []
    i = 0
    for morceau in t.texte.split("\n"):
        col = []
        y = 0.0
        for j, ch in enumerate(morceau):
            k = i + j
            st = dict(t.style_de(-1), **lettres[k])
            f = police_lettre(t, st)
            fm = QFontMetricsF(f)
            hauteur = st["taille"] * st["echelle_v"] / 100 * 1.05 + st["taille"] * st["lettres"] / 100 \
                + t.taille * t.crenage_a(k + 1) / 1000
            if ch.isspace():
                y += hauteur * 0.6
                continue
            c = QPainterPath()
            c.addText(0, 0, f, ch)
            r = c.boundingRect()
            tr = QTransform()
            sx, sy = st["echelle_h"] / 100, st["echelle_v"] / 100
            dy = -t.taille * st["ligne_base"] / 100
            tr.translate(0, y + fm.ascent() * sy + dy)
            tr.scale(sx, sy)
            tr.translate(-r.center().x(), 0)
            col.append(Lettre(tr.map(c), st["couleur"], -fm.horizontalAdvance(ch) * sx / 2,
                              fm.horizontalAdvance(ch) * sx, y + fm.ascent() * sy, len(colonnes)))
            y += hauteur
        colonnes.append((col, y))
        i += len(morceau) + 1
    H = max([h for _c, h in colonnes] + [t.taille])
    sortie = []
    for n, (col, h) in enumerate(colonnes):
        dx = -n * pas_col
        dy = {GAUCHE: 0.0, CENTRE: (H - h) / 2, DROITE: H - h}.get(t.alignement, 0.0)
        for l in col:
            l.chemin.translate(dx, dy)
            l.x += dx
            l.base += dy
            sortie.append(l)
    larg = pas_col * (len(colonnes) - 1) + t.taille
    bloc = QRectF(-(pas_col * (len(colonnes) - 1)) - t.taille / 2, 0, larg, H)
    return sortie, bloc


# ------------------------------------------------------------------ arc, tracé, déformation
class _Courbe:
    """Ligne le long de laquelle les lettres sont posées : point et angle à une distance s du départ."""

    def __init__(self, points: list[QPointF]):
        self.points = points
        self.cumul = [0.0]
        for a, b in zip(points, points[1:]):
            self.cumul.append(self.cumul[-1] + math.hypot(b.x() - a.x(), b.y() - a.y()))
        self.longueur = self.cumul[-1]

    def en(self, s: float) -> tuple[QPointF, float]:
        p = self.points
        if len(p) < 2:
            return (p[0] if p else QPointF()), 0.0
        s = max(0.0, min(self.longueur, s))
        k = 1
        while k < len(self.cumul) - 1 and self.cumul[k] < s:
            k += 1
        a, b = p[k - 1], p[k]
        seg = max(1e-9, self.cumul[k] - self.cumul[k - 1])
        f = (s - self.cumul[k - 1]) / seg
        return a + (b - a) * f, math.degrees(math.atan2(b.y() - a.y(), b.x() - a.x()))


def _sur_courbe(t: Texte, lettres: list[Lettre], bases: list[float], L: float) -> list[Lettre]:
    """Lettres posées une à une sur l'arc (courbe) ou sur le tracé, tournées comme la ligne."""
    base0 = bases[0] if bases else 0.0
    if t.trace:
        courbe = _Courbe([QPointF(x, y) for x, y in t.trace])
        depart = courbe.longueur * t.trace_debut / 100
        reste = courbe.longueur - depart
        decal = {GAUCHE: 0.0, CENTRE: (reste - L) / 2, DROITE: reste - L}.get(t.alignement, 0.0)
        res = []
        for l in lettres:
            s = depart + max(0.0, decal) + l.x + l.avance / 2
            pt, angle = courbe.en(s)
            lettre = QTransform().translate(-(l.x + l.avance / 2), -base0).map(l.chemin)
            tr = QTransform()
            tr.translate(pt.x(), pt.y())
            tr.rotate(angle)
            res.append(Lettre(tr.map(lettre), l.couleur, l.x, l.avance, l.base, l.ligne))
        return res
    k = 1 if t.courbe > 0 else -1                       # 1 = voûte (∩), -1 = creux (∪)
    R = L / math.radians(min(360.0, abs(t.courbe)))     # rayon de la ligne la plus longue
    res = []
    for l in lettres:
        dyl = l.base - base0
        r = max(t.taille * t.interligne * 0.5, R - k * dyl)
        s = l.x + l.avance / 2 - L / 2
        theta = s / r
        px, py = r * math.sin(theta), k * (R - r * math.cos(theta))
        lettre = QTransform().translate(-(l.x + l.avance / 2), -l.base).map(l.chemin)
        tr = QTransform()
        tr.translate(px, py)
        tr.rotate(math.degrees(k * theta))
        res.append(Lettre(tr.map(lettre), l.couleur, l.x, l.avance, l.base, l.ligne))
    return res


def _deformer_point(t: Texte, x: float, y: float, bloc: QRectF) -> tuple[float, float]:
    """Déformation (comme « Déformer le texte » de Photoshop) d'un point du bloc."""
    w, h = max(1e-6, bloc.width()), max(1e-6, bloc.height())
    cx, cy = bloc.center().x(), bloc.center().y()
    nx, ny = (x - cx) / (w / 2), (y - cy) / (h / 2)          # -1..1
    u, v = (nx + 1) / 2, (ny + 1) / 2                         # 0..1
    f = t.flexion / 100
    A = f * max(h, w * 0.25) * 0.6                            # amplitude des courbures
    d = t.deformation
    if d == "arc" and abs(f) > 1e-3:
        # lignes en arc de cercle, lettres ouvertes en éventail (100 % = demi-cercle)
        theta_max = abs(f) * math.pi / 2
        R = (w / 2) / theta_max
        k = 1 if f > 0 else -1
        theta = nx * theta_max
        r = R - k * (y - cy)
        x, y = cx + r * math.sin(theta), cy + k * (R - r * math.cos(theta))
    elif d == "arc_inferieur":
        y += A * (1 - nx * nx) * v
    elif d == "arc_superieur":
        y -= A * (1 - nx * nx) * (1 - v)
    elif d == "arche":
        y -= A * (1 - nx * nx)
    elif d == "renflement":
        y = cy + (y - cy) * (1 + f * 0.9 * (1 - nx * nx))
    elif d == "drapeau":
        y += A * 0.5 * math.sin(2 * math.pi * u)
    elif d == "vague":
        y += A * 0.5 * math.sin(2 * math.pi * u + math.pi * v * 0.5)
    elif d == "poisson":
        y = cy + (y - cy) * (1 + f * 0.9 * math.sin(math.pi * u)) + A * 0.3 * math.sin(2 * math.pi * u) * ny
    elif d == "montee":
        y -= A * nx
    elif d == "oeil_de_poisson":
        r = min(1.0, math.hypot(nx, ny) / math.sqrt(2))
        k = 1 + f * 0.5 * (1 - r) ** 2                       # grossit le centre, sans replier les bords
        x, y = cx + (x - cx) * k, cy + (y - cy) * k
    elif d == "gonflement":
        y = cy + (y - cy) * (1 + f * 0.8 * (1 - nx * nx))
        x = cx + (x - cx) * (1 + f * 0.15 * (1 - ny * ny))
    elif d == "compression":
        y = cy + (y - cy) * (1 - f * 0.6 * (1 - nx * nx))
    elif d == "torsion":
        a = f * math.pi / 4 * nx
        dy = y - cy
        y = cy + dy * math.cos(a)
        x = x + dy * math.sin(a) * 0.5
    # distorsions : perspective horizontale (un côté plus haut) et verticale (le haut plus large)
    if t.distorsion_h:
        y = cy + (y - cy) * (1 + t.distorsion_h / 100 * 0.6 * nx)
    if t.distorsion_v:
        x = cx + (x - cx) * (1 + t.distorsion_v / 100 * 0.6 * ny)
    return x, y


def _deformer(t: Texte, c: QPainterPath, bloc: QRectF, pas: float) -> QPainterPath:
    """Chemin déformé point par point ; les segments droits sont recoupés (ils deviennent courbes)."""
    res = QPainterPath()
    res.setFillRule(c.fillRule())
    n = c.elementCount()
    i = 0
    dernier = QPointF()
    while i < n:
        e = c.elementAt(i)
        if e.type == QPainterPath.MoveToElement:
            res.moveTo(*_deformer_point(t, e.x, e.y, bloc))
            dernier = QPointF(e.x, e.y)
            i += 1
        elif e.type == QPainterPath.LineToElement:
            fin = QPointF(e.x, e.y)
            m = max(1, int(math.hypot(fin.x() - dernier.x(), fin.y() - dernier.y()) / pas))
            for k in range(1, m + 1):
                q = dernier + (fin - dernier) * (k / m)
                res.lineTo(*_deformer_point(t, q.x(), q.y(), bloc))
            dernier = fin
            i += 1
        else:                                     # courbe : 2 points de contrôle + le point d'arrivée
            c1, c2, fin = c.elementAt(i), c.elementAt(i + 1), c.elementAt(i + 2)
            res.cubicTo(QPointF(*_deformer_point(t, c1.x, c1.y, bloc)),
                        QPointF(*_deformer_point(t, c2.x, c2.y, bloc)),
                        QPointF(*_deformer_point(t, fin.x, fin.y, bloc)))
            dernier = QPointF(fin.x, fin.y)
            i += 3
    return res


# ------------------------------------------------------------------ assemblage
@lru_cache(maxsize=64)
def mise(t: Texte) -> Mise:
    """Les lettres en place (par couleur), le bloc et le fond, centrés sur (0, 0), avant rotation."""
    if t.vertical:
        lettres, bloc = _vertical(t)
        bases = []
    else:
        lettres, bloc, bases = _horizontal(t)
        if t.trace or abs(t.courbe) >= 0.5:
            lettres = _sur_courbe(t, lettres, bases, bloc.width())
    chemin = QPainterPath()
    chemin.setFillRule(Qt.WindingFill)
    for l in lettres:
        chemin.addPath(l.chemin)
    if not t.vertical and not t.trace and abs(t.courbe) < 0.5:
        centre = bloc.center()
    else:
        r = chemin.boundingRect()
        if t.trace:                                 # le tracé reste à sa place (il est relatif au centre)
            centre = QPointF(0, 0)
            bloc = r if not r.isEmpty() else QRectF(-t.taille / 2, -t.taille / 2, t.taille, t.taille)
        else:
            if r.isEmpty():
                r = QRectF(bloc)
            if abs(t.courbe) >= 0.5:
                bloc = r
            centre = bloc.center()
    tr = QTransform().translate(-centre.x(), -centre.y())
    bloc = bloc.translated(-centre)
    fond = None
    if t.fond:
        m, a = t.pct(t.fond_marge), t.pct(t.fond_arrondi)
        fond = QPainterPath()
        fond.addRoundedRect(bloc.adjusted(-m, -m, m, m), a, a)
    couleurs: dict[str, QPainterPath] = {}
    for l in lettres:
        c = couleurs.get(l.couleur)
        if c is None:
            c = couleurs[l.couleur] = QPainterPath()
            c.setFillRule(Qt.WindingFill)
        c.addPath(tr.map(l.chemin))
    chemin = tr.map(chemin)
    if t.deformation != "aucune" or t.distorsion_h or t.distorsion_v:
        pas = max(1.0, t.taille / 10)
        ref = QRectF(bloc)
        couleurs = {k: _deformer(t, c, ref, pas) for k, c in couleurs.items()}
        chemin = _deformer(t, chemin, ref, pas)
        if fond is not None:
            fond = _deformer(t, fond, ref, pas)
        r = chemin.boundingRect()
        if fond is not None:
            r = r.united(fond.boundingRect())
        if not r.isEmpty():
            bloc = r
    return Mise([(c, k) for k, c in couleurs.items()], chemin, bloc, fond)


def forme(t: Texte) -> tuple[QPainterPath, QRectF]:
    """(tracé des lettres, rectangle du bloc), centrés sur (0, 0), avant rotation."""
    m = mise(t)
    return m.chemin, m.bloc


def trace_depuis(t: Texte, points: list[QPointF]) -> tuple:
    """Ligne dessinée à la souris (points de l'image) -> tracé du texte : points réguliers et lissés (la main tremble),
    relatifs au texte (avant sa rotation)."""
    inv, _ok = transformation(t).inverted()
    pts = [inv.map(QPointF(p)) for p in points]
    pas = max(2.0, t.taille / 12)
    regulier = [pts[0]]
    reste = 0.0
    for a, b in zip(pts, pts[1:]):                      # un point tous les `pas` px le long de la ligne
        d = math.hypot(b.x() - a.x(), b.y() - a.y())
        s = pas - reste
        while s <= d:
            regulier.append(a + (b - a) * (s / d))
            s += pas
        reste = d - (s - pas)
    if regulier[-1] != pts[-1]:
        regulier.append(pts[-1])
    n = 4                                               # moyenne glissante (bouts gardés)
    lisse = []
    for i in range(len(regulier)):
        a, b = max(0, i - n), min(len(regulier), i + n + 1)
        if i == 0 or i == len(regulier) - 1:
            q = regulier[i]
        else:
            k = min(i - a, b - 1 - i)
            voisins = regulier[i - k:i + k + 1]
            q = QPointF(sum(v.x() for v in voisins) / len(voisins), sum(v.y() for v in voisins) / len(voisins))
        lisse.append((round(q.x(), 2), round(q.y(), 2)))
    return tuple(lisse)


def ajuster_a_zone(t: Texte, anciennes: str, zone: QRectF) -> Texte:
    """Texte qui remplace des lettres de la photo : taille telle que les anciennes lettres (dans cette police)
    auraient la hauteur de la zone, puis bloc centré sur la zone (centre de l'encre, pas du cadre)."""
    from dataclasses import replace as _remplacer
    lignes = max(1, anciennes.count("\n") + 1)
    essai = _remplacer(t, texte=anciennes or t.texte, taille=100.0, angle=0.0, x=0.0, y=0.0)
    encre = forme(essai)[0].boundingRect()
    if encre.height() > 1:
        taille = 100.0 * zone.height() / encre.height()
    else:
        taille = zone.height() / lignes
    t = _remplacer(t, taille=max(4.0, round(taille, 1)), angle=0.0, x=0.0, y=0.0)
    encre = forme(t)[0].boundingRect()
    c = zone.center()
    return _remplacer(t, x=round(c.x() - encre.center().x(), 1), y=round(c.y() - encre.center().y(), 1))


def transformation(t: Texte) -> QTransform:
    tr = QTransform()
    tr.translate(t.x, t.y)
    tr.rotate(t.angle)
    return tr


MARQUE = "#fe010203"          # couleur improbable : repère les lettres sélectionnées dans la mise en place


def zones_lettres(t: Texte, debut: int, fin: int) -> list[QPolygonF]:
    """Lettres t.texte[debut:fin] : un rectangle par morceau de lettre (tourné), en coordonnées de l'image, pour
    montrer la sélection de la saisie sur la photo."""
    if fin <= debut or not t.texte:
        return []
    m = mise(t.avec_style(max(0, debut), min(len(t.texte), fin), couleur=MARQUE))
    chemin = next((c for c, k in m.morceaux if k.lower() == MARQUE), None)
    if chemin is None:
        return []
    rects = [poly.boundingRect() for poly in chemin.toSubpathPolygons()]
    rects = sorted((r for r in rects if r.width() * r.height() > 0), key=lambda r: r.center().y())
    lignes: list[QRectF] = []                # une bande par ligne : les morceaux qui se chevauchent en hauteur
    for r in rects:
        if lignes and r.top() < lignes[-1].bottom() - min(r.height(), lignes[-1].height()) * 0.3:
            lignes[-1] = lignes[-1].united(r)
        else:
            lignes.append(QRectF(r))
    tr = transformation(t)
    marge = t.taille * 0.08
    zones = []
    for r in lignes:
        haut = max(r.height(), t.taille * 0.9) / 2
        c = r.center()
        zones.append(tr.map(QPolygonF(QRectF(r.left() - marge, c.y() - haut - marge, r.width() + 2 * marge,
                                             2 * (haut + marge)))))
    return zones


def boites_lettres(t: Texte) -> dict[int, QRectF]:
    """{index du caractère: rectangle de sa lettre} (repère du texte, avant rotation), en une seule mise en place :
    chaque caractère prend une couleur à lui, improbable, qui le repère. Les espaces n'ont pas de rectangle."""
    if not t.texte:
        return {}
    marque = t
    for i in range(len(t.texte)):
        marque = marque.avec_style(i, i + 1, couleur=f"#fe01{(i >> 8) & 255:02x}{i & 255:02x}")
    boites = {}
    for chemin, k in mise(marque).morceaux:
        k = k.lower()
        if len(k) == 9 and k.startswith("#fe01"):
            r = chemin.boundingRect()
            if not r.isEmpty():
                boites[int(k[5:7], 16) * 256 + int(k[7:9], 16)] = r
    return boites


def index_lettre(t: Texte, pt: QPointF, boites: dict | None = None) -> int:
    """Position du curseur (0..len) la plus proche du point pt (image) : avant ou après la lettre la plus proche,
    sur la ligne la plus proche."""
    boites = boites_lettres(t) if boites is None else boites
    if not boites:
        return len(t.texte)
    inv, _ok = transformation(t).inverted()
    q = inv.map(QPointF(pt))

    def distance(r: QRectF) -> float:
        dx = max(r.left() - q.x(), 0.0, q.x() - r.right())
        dy = max(r.top() - q.y(), 0.0, q.y() - r.bottom())
        return dy * 4 + dx                             # la bonne ligne d'abord
    i, r = min(boites.items(), key=lambda kv: distance(kv[1]))
    return i if q.x() < r.center().x() else i + 1


def mot_autour(texte: str, i: int) -> tuple[int, int]:
    """(début, fin) du mot autour de la position i."""
    def est(c):
        return c.isalnum() or c in "'’-_"
    a = b = max(0, min(i, len(texte)))
    if (a >= len(texte) or not est(texte[a])) and a > 0 and est(texte[a - 1]):
        a = b = a - 1
    while a > 0 and est(texte[a - 1]):
        a -= 1
    while b < len(texte) and est(texte[b]):
        b += 1
    return a, b


def contour_bloc(t: Texte) -> QPolygonF:
    """Rectangle du bloc (fond compris), tourné, en coordonnées de l'image : pour le cadre et les clics."""
    m = mise(t)
    deforme = t.deformation != "aucune" or t.distorsion_h or t.distorsion_v
    # déformé : le bloc contient déjà le fond déformé ; sinon, le fond déborde du bloc de sa marge
    marge = max(t.pct(t.fond_marge) if t.fond and not deforme else 0.0, t.taille * 0.1)
    bloc = m.bloc
    return transformation(t).map(QPolygonF(bloc.adjusted(-marge, -marge, marge, marge)))


def contient(t: Texte, pt: QPointF) -> bool:
    return contour_bloc(t).containsPoint(pt, Qt.OddEvenFill)


# ------------------------------------------------------------------ dessin
def _flou_alpha(a: np.ndarray, rayon: float) -> np.ndarray:
    """Flou proche d'un flou gaussien (3 flous en boîte) sur un tableau 2D float."""
    r = int(round(rayon / 1.7))
    if r < 1:
        return a
    for _ in range(3):
        for axe in (0, 1):
            b = np.moveaxis(a, axe, 0)
            p = np.pad(b, ((r + 1, r), (0, 0)), mode="constant")
            c = np.cumsum(p, axis=0)
            b = (c[2 * r + 1:] - c[:-2 * r - 1]) / (2 * r + 1)
            a = np.moveaxis(b, 0, axe)
    return a


def _silhouette(t: Texte, m: Mise) -> QPainterPath:
    """Forme complète (fond, contour, lettres) : sert à l'ombre."""
    s = QPainterPath()
    s.setFillRule(Qt.WindingFill)
    if m.fond is not None:
        s.addPath(m.fond)
    s.addPath(m.chemin)
    if t.contour and t.contour_epaisseur > 0:
        st = QPainterPathStroker()
        st.setWidth(2 * t.pct(t.contour_epaisseur))
        st.setJoinStyle(Qt.RoundJoin)
        st.setCapStyle(Qt.RoundCap)
        s.addPath(st.createStroke(m.chemin))
    return s


def _dessiner_ombre(p: QPainter, t: Texte, silhouette: QPainterPath, largeur: int, hauteur: int):
    flou = t.pct(t.ombre_flou)
    d = t.pct(t.ombre_distance)
    a = math.radians(t.ombre_direction)
    dx, dy = d * math.cos(a), d * math.sin(a)
    zone = transformation(t).map(silhouette).boundingRect().translated(dx, dy)
    marge = flou * 1.6 + 2
    zone = zone.adjusted(-marge, -marge, marge, marge).toAlignedRect()
    zone = zone.intersected(QRectF(0, 0, largeur, hauteur).toAlignedRect())
    if zone.isEmpty():
        return
    masque = QImage(zone.width(), zone.height(), QImage.Format_Alpha8)
    masque.fill(0)
    q = QPainter(masque)
    q.setRenderHint(QPainter.Antialiasing, t.lissage)
    tr = QTransform()
    tr.translate(-zone.x() + dx, -zone.y() + dy)
    q.setTransform(transformation(t) * tr)
    q.fillPath(silhouette, QColor(0, 0, 0, 255))
    q.end()
    lb = masque.bytesPerLine()
    brut = np.frombuffer(masque.constBits(), np.uint8, count=zone.height() * lb).reshape(zone.height(), lb)
    alpha = _flou_alpha(brut[:, :zone.width()].astype(np.float32), flou)
    c = QColor(t.ombre_couleur)
    alpha = np.clip(alpha * (c.alpha() / 255), 0, 255).astype(np.uint8)
    rgba = np.empty((zone.height(), zone.width(), 4), np.uint8)
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2], rgba[:, :, 3] = c.red(), c.green(), c.blue(), alpha
    img = QImage(rgba.data, zone.width(), zone.height(), zone.width() * 4, QImage.Format_RGBA8888)
    p.save()
    p.resetTransform()
    p.drawImage(zone.topLeft(), img)
    p.restore()


def dessiner(p: QPainter, t: Texte, largeur: int, hauteur: int):
    """Dessine le texte et ses effets avec le peintre `p` (coordonnées de l'image)."""
    m = mise(t)
    p.setRenderHint(QPainter.Antialiasing, t.lissage)
    if t.ombre:
        _dessiner_ombre(p, t, _silhouette(t, m), largeur, hauteur)
    p.save()
    p.setTransform(transformation(t), True)
    if m.fond is not None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.fond_couleur))
        p.drawPath(m.fond)
    if t.contour and t.contour_epaisseur > 0:
        p.strokePath(m.chemin, QPen(QColor(t.contour_couleur), 2 * t.pct(t.contour_epaisseur), Qt.SolidLine,
                                    Qt.RoundCap, Qt.RoundJoin))
    for chemin, couleur in m.morceaux:
        p.fillPath(chemin, QColor(couleur))
    p.restore()


def rendre(t: Texte, largeur: int, hauteur: int) -> QImage:
    """Image du calque de texte (transparente autour), à la taille du document."""
    img = QImage(largeur, hauteur, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    dessiner(p, t, largeur, hauteur)
    p.end()
    return img
