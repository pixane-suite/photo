"""Thème clair / sombre, mêmes couleurs que TwinPanel (fond gris-bleu, panneaux, coins arrondis, accent)."""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

AUTO, CLAIR, SOMBRE = "auto", "clair", "sombre"


@dataclass(frozen=True)
class Couleurs:
    fond: str          # fond de la fenêtre
    panneau: str       # panneaux, cartes
    bordure: str
    texte: str
    discret: str       # texte secondaire
    pastille: str      # fond des pastilles, champs
    survol: str
    canevas: str       # autour de la photo
    accent: str
    accent_texte: str
    accent_doux: str   # fond d'un outil choisi
    vert: str
    orange: str
    rouge: str
    sombre: bool


CLAIR_C = Couleurs(fond="#EEF1F5", panneau="#FFFFFF", bordure="#DDE2EA", texte="#1F2328", discret="#6B7280",
                   pastille="#E6EAF0", survol="#E9EDF3", canevas="#DCE1E8", accent="#0F6CBD",
                   accent_texte="#FFFFFF", accent_doux="#D6E6F7", vert="#1F9D55", orange="#C77700",
                   rouge="#C42B1C", sombre=False)
SOMBRE_C = Couleurs(fond="#16181D", panneau="#1E2128", bordure="#2C313A", texte="#E6E8EB", discret="#9AA3AF",
                    pastille="#2A2F38", survol="#262A32", canevas="#111317", accent="#4A9FE8",
                    accent_texte="#0B1220", accent_doux="#203A57", vert="#3FB96E", orange="#E3A341",
                    rouge="#F06A5C", sombre=True)


_ACCENT_QT: list = []
CLE_ACCENT = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Accent"
CLE_THEME = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def _registre(cle: str, nom: str):
    """Valeur lue dans HKEY_CURRENT_USER (None si absente ou hors Windows)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cle) as k:
            return winreg.QueryValueEx(k, nom)[0]
    except (ImportError, OSError):
        return None


def palette_accent() -> list[QColor] | None:
    """Les 8 nuances de l'accent préparées par Windows (de la plus claire à la plus foncée)."""
    brut = _registre(CLE_ACCENT, "AccentPalette")
    if not isinstance(brut, (bytes, bytearray)) or len(brut) < 28:
        return None
    return [QColor(brut[i], brut[i + 1], brut[i + 2]) for i in range(0, 32, 4)]


def windows_sombre() -> bool:
    valeur = _registre(CLE_THEME, "AppsUseLightTheme")
    if valeur is None:  # hors Windows : on demande à Qt
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    return valeur == 0


def signature_windows() -> tuple:
    """Change quand l'utilisateur modifie la couleur d'accent ou le thème de Windows."""
    return _registre(CLE_ACCENT, "AccentPalette"), _registre(CLE_THEME, "AppsUseLightTheme")


def accent_windows(sombre: bool) -> QColor | None:
    """La couleur d'accent exacte choisie dans Windows (nuance centrale de la palette), dans les deux thèmes."""
    nuances = palette_accent()
    if nuances:
        return nuances[3]
    if not _ACCENT_QT:  # repli : accent fourni par Qt, lu une seule fois
        try:
            c = QGuiApplication.palette().color(QPalette.Accent)
            _ACCENT_QT.append(QColor(c) if c.isValid() else None)
        except AttributeError:
            _ACCENT_QT.append(None)
    return _ACCENT_QT[0]


def choisir(mode: str) -> Couleurs:
    sombre = windows_sombre() if mode == AUTO else mode == SOMBRE
    return SOMBRE_C if sombre else CLAIR_C


def _fleches(couleur: str) -> tuple[str, str]:
    """Petites flèches des cases à chiffres, dessinées dans la couleur du texte (fichiers SVG temporaires)."""
    import tempfile
    from pathlib import Path
    dossier = Path(tempfile.gettempdir()) / "pixane_theme"
    dossier.mkdir(exist_ok=True)
    chemins = []
    for nom, trace in (("haut", "M2 7 5 3 8 7"), ("bas", "M2 3 5 7 8 3")):
        f = dossier / f"fleche_{nom}_{couleur.lstrip('#')}.svg"
        if not f.exists():
            f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="{trace}" '
                         f'fill="none" stroke="{couleur}" stroke-width="1.6" stroke-linecap="round" '
                         f'stroke-linejoin="round"/></svg>', encoding="utf-8")
        chemins.append(f.as_posix())
    return chemins[0], chemins[1]


def feuille_de_style(c: Couleurs) -> str:
    haut, bas = _fleches(c.texte)
    return f"""
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", sans-serif; font-size: 10pt; }}
QMainWindow, QDialog {{ background: {c.fond}; }}
QWidget {{ color: {c.texte}; }}
QToolTip {{ background: {c.panneau}; color: {c.texte}; border: 1px solid {c.bordure}; border-radius: 6px;
            padding: 4px 8px; }}

/* menus */
QMenuBar {{ background: {c.fond}; padding: 2px 4px; }}
QMenuBar::item {{ background: transparent; padding: 5px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {c.survol}; }}
QMenu {{ background: {c.panneau}; border: 1px solid {c.bordure}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 28px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {c.accent_doux}; }}
QMenu::item:disabled {{ color: {c.discret}; }}
QMenu::separator {{ height: 1px; background: {c.bordure}; margin: 4px 8px; }}

/* barres d'outils */
QToolBar {{ background: {c.fond}; border: none; spacing: 4px; padding: 4px; }}
QToolBar::separator {{ background: {c.bordure}; width: 1px; height: 1px; margin: 6px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 5px; }}
QToolButton:hover {{ background: {c.survol}; }}
QToolButton:pressed {{ background: {c.pastille}; }}
QToolButton:checked {{ background: {c.accent_doux}; border-color: {c.accent}; }}
QToolButton:disabled {{ color: {c.discret}; }}

/* panneaux et cartes */
QDockWidget {{ color: {c.discret}; font-weight: 600; }}
QDockWidget::title {{ background: {c.fond}; padding: 8px 10px 4px 10px; text-align: left; }}
/* onglets des panneaux (Calques, Historique, Nuancier, Actions) : celui qui est ouvert se voit */
QMainWindow > QTabBar {{ background: {c.fond}; }}
QMainWindow > QTabBar::tab {{ background: {c.fond}; color: {c.discret}; padding: 5px 8px 4px 8px;
    border: none; border-top: 3px solid transparent; }}
QMainWindow > QTabBar::tab:hover {{ background: {c.survol}; color: {c.texte}; }}
QMainWindow > QTabBar::tab:selected {{ background: {c.panneau}; color: {c.texte}; font-weight: 700;
    border-top: 3px solid {c.accent}; }}
QFrame#panneau {{ background: {c.panneau}; border: 1px solid {c.bordure}; border-radius: 8px; }}
QLabel#discret {{ color: {c.discret}; }}
QLabel#titre_section {{ color: {c.discret}; font-size: 9pt; font-weight: 600; }}
QPushButton#carte {{ background: {c.panneau}; border: 1px solid {c.bordure}; border-radius: 8px;
                     padding: 10px 12px; text-align: left; }}
QPushButton#carte:hover {{ border-color: {c.accent}; background: {c.survol}; }}
QPushButton#carte:pressed {{ background: {c.accent_doux}; }}
QPushButton#carte:disabled {{ color: {c.discret}; background: {c.fond}; }}

/* boutons */
QPushButton {{ background: {c.pastille}; border: 1px solid {c.bordure}; border-radius: 6px; padding: 6px 14px; }}
QPushButton:hover {{ background: {c.survol}; border-color: {c.accent}; }}
QPushButton:pressed {{ background: {c.accent_doux}; }}
QPushButton:disabled {{ color: {c.discret}; }}
QPushButton:default, QPushButton#principal {{ background: {c.accent}; color: {c.accent_texte}; border-color: {c.accent};
                                              font-weight: 600; }}
QPushButton:default:hover, QPushButton#principal:hover {{ background: {c.accent}; border-color: {c.texte}; }}
QPushButton#pastille {{ border-radius: 12px; padding: 3px 12px; background: {c.pastille}; border: 1px solid transparent; }}
QPushButton#pastille:checked {{ background: {c.accent}; color: {c.accent_texte}; }}

/* champs */
QLineEdit, QSpinBox, QDoubleSpinBox {{ background: {c.panneau}; border: 1px solid {c.bordure}; border-radius: 6px;
                                       padding: 5px 8px; selection-background-color: {c.accent}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {c.accent}; }}
QRadioButton, QCheckBox {{ spacing: 8px; }}
QSpinBox, QDoubleSpinBox {{ padding-right: 22px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; width: 18px; border: none; border-left: 1px solid {c.bordure}; }}
QSpinBox::up-button, QDoubleSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 6px; }}
QSpinBox::down-button, QDoubleSpinBox::down-button {{ subcontrol-position: bottom right;
                                                      border-bottom-right-radius: 6px; }}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::down-button:hover {{ background: {c.survol}; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{haut}"); width: 9px; height: 9px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{bas}"); width: 9px; height: 9px; }}

/* curseur */
QSlider::groove:horizontal {{ height: 4px; background: {c.pastille}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {c.accent}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {c.panneau}; border: 2px solid {c.accent}; width: 12px; height: 12px;
                              margin: -6px 0; border-radius: 8px; }}

/* barre de progression */
QProgressBar {{ background: {c.pastille}; border: none; border-radius: 6px; height: 12px; text-align: center;
                color: {c.texte}; font-size: 8pt; }}
QProgressBar::chunk {{ background: {c.accent}; border-radius: 6px; }}

/* listes (vignettes) */
QListWidget {{ background: {c.panneau}; border: 1px solid {c.bordure}; border-radius: 8px; padding: 4px; }}
QListWidget::item {{ border-radius: 6px; padding: 4px; }}
QListWidget::item:selected {{ background: {c.accent_doux}; color: {c.texte}; border: 1px solid {c.accent}; }}
QListWidget::item:hover {{ background: {c.survol}; }}

/* barre d'état en pastilles */
QStatusBar {{ background: {c.fond}; }}
QStatusBar::item {{ border: none; }}
QLabel#pastille_etat {{ background: {c.pastille}; border-radius: 10px; padding: 2px 10px; }}

/* défilement fin */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {c.bordure}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {c.discret}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def _luminance(c: QColor) -> float:
    return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()


def appliquer(app: QApplication, mode: str) -> Couleurs:
    c = choisir(mode)
    a = accent_windows(c.sombre)
    if a is not None:
        # même accent que Windows, dans tous les modes (comme TwinPanel)
        fond = QColor(c.panneau)
        melange = QColor((a.red() + fond.red() * 4) // 5, (a.green() + fond.green() * 4) // 5,
                         (a.blue() + fond.blue() * 4) // 5)
        c = Couleurs(**{**c.__dict__, "accent": a.name(), "accent_doux": melange.name(),
                        "accent_texte": "#000000" if _luminance(a) > 0.45 else "#FFFFFF"})
    app.setStyle("Fusion")
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark if c.sombre else Qt.ColorScheme.Light)
    except AttributeError:
        pass
    p = QPalette()
    for role, couleur in ((QPalette.Window, c.fond), (QPalette.WindowText, c.texte), (QPalette.Base, c.panneau),
                          (QPalette.AlternateBase, c.pastille), (QPalette.Text, c.texte),
                          (QPalette.Button, c.pastille), (QPalette.ButtonText, c.texte),
                          (QPalette.Highlight, c.accent), (QPalette.HighlightedText, c.accent_texte),
                          (QPalette.ToolTipBase, c.panneau), (QPalette.ToolTipText, c.texte),
                          (QPalette.PlaceholderText, c.discret)):
        p.setColor(role, QColor(couleur))
    for role in (QPalette.ButtonText, QPalette.WindowText, QPalette.Text):
        p.setColor(QPalette.Disabled, role, QColor(c.discret))
    app.setPalette(p)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(feuille_de_style(c))
    return c
