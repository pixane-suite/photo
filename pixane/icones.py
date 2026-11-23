"""Icônes vectorielles dessinées pour Pixane (traits arrondis, couleur du thème)."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Tracés sur une grille de 24 × 24, trait de 1,8 ; « C » = couleur du texte, « A » = couleur d'accent.
DESSINS = {
    "main": '<path d="M8 12V6.5a1.5 1.5 0 0 1 3 0V11M11 10V4.5a1.5 1.5 0 0 1 3 0V11M14 10.5V6a1.5 1.5 0 0 1 3 0v6.5'
            'M8 11.5V9.5a1.5 1.5 0 0 0-3 0V14c0 4 2.8 7 6.5 7h1c3.3 0 5.5-2.7 5.5-6V12a1.5 1.5 0 0 0-3 0"/>',
    "rectangle": '<rect x="4" y="5" width="16" height="14" rx="1.5" stroke-dasharray="3 2.4"/>',
    "lasso": '<path d="M7.5 16.5C4.5 15.3 3 13.4 3 11c0-4.1 4-7 9-7s9 2.9 9 7-4 7-9 7c-1 0-2-.1-2.9-.3"/>'
             '<path d="M8.5 15.5a2 2 0 1 0 1.2 2.6M8.2 19.8 7 21.5"/>',
    "pinceau": '<path d="M14.5 4.5l5 5-7.8 7.8-5-5z"/><path d="M6.7 12.3l5 5" />'
               '<path d="M6.5 13.5C4 14 3.2 16 3.5 18.5c.2 1.4-.6 2-1 2.5 3.5.5 6.5-.5 7.5-3.5"/>',
    "gomme": '<path d="M8.5 20 3.6 15.1a1.6 1.6 0 0 1 0-2.3L13 3.4a1.6 1.6 0 0 1 2.3 0l5.3 5.3a1.6 1.6 0 0 1 0 2.3'
             'L11.2 20z"/><path d="M8.5 20H21M8 9l7 7"/>',
    "effacer": '<path d="M7.5 19.5 3.6 15.6a1.5 1.5 0 0 1 0-2.1l7.3-7.3a1.5 1.5 0 0 1 2.1 0l3.9 3.9a1.5 1.5 0 0 1 0 2.1'
               'L10 19.5z"/><path d="M7.5 19.5H14"/>'
               '<path stroke="A" d="M18.5 3v4M16.5 5h4M20.5 13.5v3M19 15h3"/>',
    "remplir": '<path d="M5 13 11.5 6.5l6 6L11 19a1.5 1.5 0 0 1-2.1 0L5 15.1a1.5 1.5 0 0 1 0-2.1z"/>'
               '<path d="M9 4l3.5 3.5M5 13h12.5"/>'
               '<path stroke="A" d="M20 15.5c0 1.4-.9 2.5-2 2.5s-2-1.1-2-2.5 2-4 2-4 2 2.6 2 4z"/>',
    "modifier": '<path d="M4 5.5h16v10.5h-9l-4.5 3.5V16H4z"/>'
                '<path stroke="A" d="M14.5 7.5l.8 1.7 1.7.8-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8z"/>',
    "agrandir": '<rect x="8" y="8" width="8" height="8" rx="1"/>'
                '<path stroke="A" d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5"/>',
    "upscale": '<rect x="3" y="11" width="10" height="10" rx="1.5"/>'
               '<path stroke="A" d="M10 14 20 4M14 4h6v6"/>',
    "ouvrir": '<path d="M3.5 18.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2.5h7.5A1.5 1.5 0 0 1 20 8.5V10"/>'
              '<path d="M3.5 18.5 6 11.5a1.5 1.5 0 0 1 1.4-1h13a1 1 0 0 1 1 1.3l-2.2 6.4a1.5 1.5 0 0 1-1.4 1H5'
              'a1.5 1.5 0 0 1-1.5-1.2z"/>',
    "enregistrer": '<path d="M5 3.5h11l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 3.5 19V5A1.5 1.5 0 0 1 5 3.5z"/>'
                   '<path d="M7.5 3.5V8h7V3.5M7 20.5v-6.5h10v6.5"/>',
    "annuler": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "retablir": '<path d="M15 14l5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    "zoom_plus": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21M10.5 7.5v6M7.5 10.5h6"/>',
    "zoom_moins": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M15.5 15.5 21 21M7.5 10.5h6"/>',
    "ajuster": '<path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4"/>'
               '<rect x="8" y="8" width="8" height="8" rx="1"/>',
    "soleil": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6 6 6M18 18l1.4 1.4M2.5 12h2'
              'M19.5 12h2M4.6 19.4 6 18M18 6l1.4-1.4"/>',
    "lune": '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    "ajouter": '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v8M8 12h8"/>',
    "retirer": '<circle cx="12" cy="12" r="8.5"/><path d="M8 12h8"/>',
    # calques
    "calque_nouveau": '<path d="M12 4 3 8.5l9 4.5 9-4.5z"/><path d="M3 13l9 4.5 3-1.5"/>'
                      '<path stroke="A" d="M19 14v6M16 17h6"/>',
    "dupliquer": '<rect x="8" y="8" width="12" height="12" rx="1.5"/>'
                 '<path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8"/>',
    "supprimer": '<path d="M4 7h16M9.5 7V4.5h5V7M6 7l1 12.5a1.5 1.5 0 0 0 1.5 1.5h7a1.5 1.5 0 0 0 1.5-1.5L18 7"/>'
                 '<path d="M10 11v6M14 11v6"/>',
    "monter": '<path d="M12 19V5M6 11l6-6 6 6"/>',
    "descendre": '<path d="M12 5v14M6 13l6 6 6-6"/>',
    "fusionner": '<path d="M12 3 3 7.5 12 12l9-4.5z"/><path stroke="A" d="M12 14.5v6.5M9 18l3 3 3-3"/>',
    "aplatir": '<path d="M12 4 3 8.5l9 4.5 9-4.5z"/><path d="M3 12.5l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5"/>',
    "oeil": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
            '<circle cx="12" cy="12" r="3"/>',
    "oeil_ferme": '<path d="M4 9.5c2 2.2 4.8 3.5 8 3.5s6-1.3 8-3.5M6.5 12.2 5 14.5M12 13v2.8M17.5 12.2l1.5 2.3"/>',
    "cadenas": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>'
               '<path stroke="A" d="M12 14.5v2"/>',
    "cadenas_ouvert": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 7.6-1.7"/>',
    "gomme_calque": '<path d="M8.5 20 3.6 15.1a1.6 1.6 0 0 1 0-2.3L13 3.4a1.6 1.6 0 0 1 2.3 0l5.3 5.3a1.6 1.6 0 0 1 '
                    '0 2.3L11.2 20z"/><path d="M8.5 20H14"/><path stroke="A" d="M16.5 15.5l4 4M20.5 15.5l-4 4"/>',
    "deplacer": '<path d="M12 3v18M3 12h18M12 3 9.5 5.5M12 3l2.5 2.5M12 21l-2.5-2.5M12 21l2.5-2.5'
                'M3 12l2.5-2.5M3 12l2.5 2.5M21 12l-2.5-2.5M21 12l-2.5 2.5"/>',
    # retouche
    "recadrer": '<path d="M6.5 2.5v13.5a1.5 1.5 0 0 0 1.5 1.5h13.5M2.5 6.5h13.5a1.5 1.5 0 0 1 1.5 1.5v13.5"/>'
                '<path stroke="A" d="M11 11h2.5v2.5"/>',
    "peinture": '<path d="M19.5 3.5c-1.7.6-7 5.6-8.6 7.6l2 2c2-1.6 7-6.9 7.6-8.6a.8.8 0 0 0-1-1z"/>'
                '<path stroke="A" d="M10.9 11.1C8.6 11 7 12.6 7 15c0 1.5-.8 2.4-2.5 3 3.7 1.6 9 .7 8.4-4.9z"/>',
    "tampon": '<path d="M9.5 3.5h5l-1 7h-3z"/><path d="M5 14.5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2H5z"/>'
              '<path stroke="A" d="M5 20.5h14"/>',
    "tampon_motif": '<path d="M9.5 3.5h5l-1 7h-3z"/><path d="M5 14.5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2H5z"/>'
                    '<path stroke="A" d="M5 20.5h2M9 20.5h2M13 20.5h2M17 20.5h2"/>',
    "baguette": '<path d="M4 20 14.5 9.5"/><path d="M13 8l3 3"/>'
                '<path stroke="A" d="M17 3v3M15.5 4.5h3M20.5 8v2.5M19.2 9.2h2.6M11 3.5v2M10 4.5h2"/>',
    "rapide": '<path d="M5 15c2-4 5-6 9-6 2.5 0 4 1.3 4 3s-2 3.5-5 4.5"/>'
              '<circle cx="12" cy="17.5" r="3.2" stroke-dasharray="2 1.8"/>'
              '<path stroke="A" d="M18.5 3.5v3M17 5h3"/>',
    "objet": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5" stroke-dasharray="3 2.4"/>'
             '<path stroke="A" d="M9 16.5c-1.5 0-2-1.2-1.5-2.4l1.6-3.6c.6-1.3 2.4-1.6 3.4-.4l3.3 3.9c.9 1.1.2 2.5-1.2 '
             '2.5z"/>',
    "sel_texte": '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5" stroke-dasharray="3 2.4"/>'
                 '<path stroke="A" d="M8 9h8M12 9v7.5"/>',
    "arriere_plan": '<rect x="3.5" y="4.5" width="17" height="15" rx="2" stroke-dasharray="2.5 2.2"/>'
                    '<path stroke="A" d="M12 8a2.3 2.3 0 1 1 0 4.6A2.3 2.3 0 0 1 12 8zM7.5 19.5c.6-3 2.3-4.6 4.5-4.6s3.9 1.6 4.5 4.6"/>',
    "reglages": '<path d="M4 6.5h9M17 6.5h3M4 12h3M11 12h9M4 17.5h11M19 17.5h1"/>'
                '<path stroke="A" d="M15 4.5v4M9 10v4M17 15.5v4"/>',
    "suppression": '<path d="M5 19c3-1 4-3.5 6.5-6l5-5a2 2 0 0 1 3 3l-5 5c-2.5 2.5-5 3.5-6 6.5"/>'
                   '<path stroke="A" d="M4 5v3M2.5 6.5h3M9 3v2M8 4h2"/>',
    "style": '<path d="M9 20V9.5A3.5 3.5 0 0 1 12.5 6H13M5.5 11.5H12"/><path stroke="A" d="M14.5 12l6 7.5M20.5 12l-6 7.5"/>',
    # calques : groupes, masques, réglages
    "dossier": '<path d="M3.5 18.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2.5h8A1.5 1.5 0 0 1 20.5 8.5v10A1.5 1.5 0 0 1 19 20H5'
               'a1.5 1.5 0 0 1-1.5-1.5z"/>',
    "groupe": '<path d="M3.5 18.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2.5h8A1.5 1.5 0 0 1 20.5 8.5v10A1.5 1.5 0 0 1 19 20H5'
              'a1.5 1.5 0 0 1-1.5-1.5z"/><path stroke="A" d="M12 10.5v6M9 13.5h6"/>',
    "masque": '<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><circle stroke="A" cx="12" cy="12" r="4"/>',
    "reglage": '<circle cx="12" cy="12" r="8"/><path stroke="A" d="M12 4a8 8 0 0 1 0 16z"/>',
    "reglage_calque": '<circle cx="12" cy="12" r="8"/><path stroke="A" d="M12 4a8 8 0 0 1 0 16zM12 8h4M12 12h6M12 16h4"/>',
    # outils de dessin
    "degrade": '<rect x="3.5" y="5" width="17" height="14" rx="1.5"/><path stroke="A" d="M7 8v8M10.5 8v8M13.5 9v6M16 10v4"/>',
    "seau": '<path d="M5 12 11 6l6.5 6.5-5.8 5.8a1.5 1.5 0 0 1-2.1 0L5 13.8a1.3 1.3 0 0 1 0-1.8zM8.5 3.5 11 6"/>'
            '<path stroke="A" d="M20 15.5c0 1.4-.9 2.5-2 2.5s-2-1.1-2-2.5 2-4 2-4 2 2.6 2 4z"/>',
    "formes": '<rect x="3.5" y="10" width="9" height="9" rx="1"/><circle stroke="A" cx="15.5" cy="8.5" r="5"/>',
    "plume": '<path d="M12 3 18 11l-3.5 8h-5L6 11z"/><path d="M12 3v8"/><circle stroke="A" cx="12" cy="12.5" r="1.6"/>'
             '<path stroke="A" d="M9 21h6"/>',
    "yeux_rouges": '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/>'
                   '<circle stroke="A" cx="12" cy="12" r="3.2"/>',
    "correcteur": '<path d="M7.5 16.5 16.5 7.5a2.6 2.6 0 0 0-3.7-3.7L3.8 12.8a2.6 2.6 0 0 0 3.7 3.7z"/>'
                  '<path stroke="A" d="M17 14.5l3 3-3 3-3-3zM9 8.5l.01 0M11 10.5l.01 0M8.5 11l.01 0M10.5 6.5l.01 0"/>',
    "regles": '<path d="M3.5 3.5h17v5h-12v12h-5z"/><path stroke="A" d="M7 3.5v2.5M10.5 3.5v2.5M14 3.5v2.5M17.5 3.5v2.5'
              'M3.5 12H6M3.5 15.5H6"/>',
    "onglet": '<path d="M3.5 19.5V7a1.5 1.5 0 0 1 1.5-1.5h5l1.5 2H19a1.5 1.5 0 0 1 1.5 1.5v10.5z"/>',
    "lot": '<rect x="7" y="3.5" width="13" height="10" rx="1.5"/><path d="M4 7v10a1.5 1.5 0 0 0 1.5 1.5H17"/>'
           '<path stroke="A" d="M10 10l2.5-2.5L15 10l2-2"/>',
    "filtre": '<path d="M4 5h16l-6.5 7.5v6L10.5 20v-7.5z"/>',
    # pinceaux de retouche
    "densite_moins": '<circle cx="14.5" cy="9.5" r="5"/><path d="M11 13 4 20"/>'
                     '<path stroke="A" d="M12.5 9.5h4"/>',
    "densite_plus": '<circle cx="14.5" cy="9.5" r="5"/><path d="M11 13 4 20"/>'
                    '<path stroke="A" d="M12.5 9.5h4M14.5 7.5v4"/>',
    "eponge": '<rect x="4" y="6" width="16" height="12" rx="4"/>'
              '<path stroke="A" d="M8.5 10l.01 0M12.5 9l.01 0M15.5 11.5l.01 0M9.5 14l.01 0M13.5 14.5l.01 0"/>',
    "goutte": '<path d="M12 3.5c3 4 6 7 6 10.5a6 6 0 0 1-12 0c0-3.5 3-6.5 6-10.5z"/>'
              '<path stroke="A" d="M9.5 14.5a2.5 2.5 0 0 0 2.5 2.5"/>',
    "nettete_pinceau": '<path d="M12 3.5 20 19H4z"/><path stroke="A" d="M12 9.5v5"/>',
    "doigt": '<path d="M10 13V5.5a1.5 1.5 0 0 1 3 0V12l4.5 1c1.3.3 2 1.5 1.7 2.8l-.9 3.5a1.5 1.5 0 0 1-1.5 1.2H11'
             'a2 2 0 0 1-1.6-.8L6.3 15.5a1.4 1.4 0 0 1 2.1-1.8z"/>'
             '<path stroke="A" d="M16 4.5c1.5.5 2.5 1.5 3 3"/>',
    "historique": '<path d="M19.5 3.5c-1.7.6-7 5.6-8.6 7.6l2 2c2-1.6 7-6.9 7.6-8.6a.8.8 0 0 0-1-1z"/>'
                  '<path d="M10.9 11.1C8.6 11 7 12.6 7 15c0 1.5-.8 2.4-2.5 3 3.7 1.6 9 .7 8.4-4.9z"/>'
                  '<path stroke="A" d="M3.5 7a5 5 0 0 1 8-3.5M3.5 3v4h4"/>',
    # texte
    "texte": '<path d="M5 6.5V4.5h14v2M12 4.5v15M9 19.5h6"/>',
    "aligner_gauche": '<path d="M4 6h16M4 10h10M4 14h16M4 18h10"/>',
    "aligner_centre": '<path d="M4 6h16M7 10h10M4 14h16M7 18h10"/>',
    "aligner_droite": '<path d="M4 6h16M10 10h10M4 14h16M10 18h10"/>',
    "aligner_justifie": '<path d="M4 6h16M4 10h16M4 14h16M4 18h10"/>',
    # aligner / répartir les calques : la ligne d'alignement en couleur d'accent
    "al_gauche": '<path stroke="A" d="M4 3v18"/><rect x="7" y="6" width="12" height="4" rx="1"/>'
                 '<rect x="7" y="14" width="7" height="4" rx="1"/>',
    "al_centre_h": '<path stroke="A" d="M12 3v18"/><rect x="5" y="6" width="14" height="4" rx="1"/>'
                   '<rect x="8.5" y="14" width="7" height="4" rx="1"/>',
    "al_droite": '<path stroke="A" d="M20 3v18"/><rect x="5" y="6" width="12" height="4" rx="1"/>'
                 '<rect x="10" y="14" width="7" height="4" rx="1"/>',
    "al_haut": '<path stroke="A" d="M3 4h18"/><rect x="6" y="7" width="4" height="12" rx="1"/>'
               '<rect x="14" y="7" width="4" height="7" rx="1"/>',
    "al_centre_v": '<path stroke="A" d="M3 12h18"/><rect x="6" y="5" width="4" height="14" rx="1"/>'
                   '<rect x="14" y="8.5" width="4" height="7" rx="1"/>',
    "al_bas": '<path stroke="A" d="M3 20h18"/><rect x="6" y="5" width="4" height="12" rx="1"/>'
              '<rect x="14" y="10" width="4" height="7" rx="1"/>',
    "rep_h": '<rect x="3" y="7" width="4" height="10" rx="1"/><rect x="10" y="5" width="4" height="14" rx="1"/>'
             '<rect x="17" y="8" width="4" height="8" rx="1"/>',
    # barre d'accès rapide
    "transformer": '<rect x="5.5" y="5.5" width="13" height="13" stroke-dasharray="2.6 2.2"/>'
                   '<path stroke="A" d="M3.5 3.5h3v3h-3zM17.5 3.5h3v3h-3zM3.5 17.5h3v3h-3zM17.5 17.5h3v3h-3z"/>',
    "pivoter_d": '<rect x="3.5" y="10.5" width="10" height="10" rx="1.2"/>'
                 '<path stroke="A" d="M7.5 6.5C12 3.5 17.5 5 19.5 10.5M16.5 9.5l3 1.5 1.5-3"/>',
    "pivoter_g": '<g transform="matrix(-1 0 0 1 24 0)"><rect x="3.5" y="10.5" width="10" height="10" rx="1.2"/>'
                 '<path stroke="A" d="M7.5 6.5C12 3.5 17.5 5 19.5 10.5M16.5 9.5l3 1.5 1.5-3"/></g>',
    "miroir_h": '<rect x="2.5" y="3.5" width="19" height="17" rx="1.5"/><path stroke="A" d="M12 3.5v17"/>'
                '<path d="M9.5 8v8l-5 0zM14.5 8v8l5 0z"/>',
    "miroir_v": '<g transform="rotate(90 12 12)"><rect x="3.5" y="2.5" width="17" height="19" rx="1.5"/>'
                '<path stroke="A" d="M12 2.5v19"/><path d="M9.5 8v8l-5 0zM14.5 8v8l5 0z"/></g>',
    "sym_h": '<path stroke="A" stroke-dasharray="2 2" d="M12 3v18"/><path d="M9.5 6v12L3.5 18zM14.5 6v12l6 0z"/>',
    "sym_v": '<g transform="rotate(90 12 12)"><path stroke="A" stroke-dasharray="2 2" d="M12 3v18"/>'
             '<path d="M9.5 6v12L3.5 18zM14.5 6v12l6 0z"/></g>',
    "grouper": '<path d="M3.5 18.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2.5h8A1.5 1.5 0 0 1 20.5 8.5v10A1.5 1.5 0 0 1 19 20H5'
               'a1.5 1.5 0 0 1-1.5-1.5z"/><path stroke="A" d="M8 11h8M8 15h8"/>',
    "degrouper": '<path stroke-dasharray="2.6 2.2" d="M3.5 18.5V6a1.5 1.5 0 0 1 1.5-1.5h4l2 2.5h8A1.5 1.5 0 0 1 '
                 '20.5 8.5v10A1.5 1.5 0 0 1 19 20H5a1.5 1.5 0 0 1-1.5-1.5z"/><path stroke="A" d="M8 11h8M8 15h8"/>',
    # outils ajoutés
    "pipette": '<path d="M14.5 6.5l3 3-9 9H5.5v-3z"/><path d="M13 5l6 6M16.5 3.5a2.1 2.1 0 0 1 3 0l1 1a2.1 2.1 0 0 1 0 3'
               'L18.5 9.5 14.5 5.5z"/><path stroke="A" d="M7 17l.01 0"/>',
    "ellipse_sel": '<ellipse cx="12" cy="12" rx="8.5" ry="6.5" stroke-dasharray="3 2.4"/>',
    "lasso_mag": '<path d="M7.5 16.5C4.5 15.3 3 13.4 3 11c0-4.1 4-7 9-7s9 2.9 9 7c0 1.3-.4 2.4-1.1 3.3"/>'
                 '<path stroke="A" d="M12 14.5v4a3 3 0 0 0 6 0v-4M12 16.5h2M16 16.5h2"/>',
    "piece": '<path d="M4 9.5h5.5V4h5v5.5H20v5h-5.5V20h-5v-5.5H4z" stroke-dasharray="2.6 2"/>'
             '<path stroke="A" d="M15 15l5 5M20 16v4h-4"/>',
    "deplacer_ia": '<circle cx="9" cy="10" r="4.5"/><path stroke="A" d="M14 15l6 6M20 16.5V21h-4.5"/>'
                   '<path d="M17.5 3.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z"/>',
    "loupe": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5.5 5.5"/><path stroke="A" d="M8 10.5h5M10.5 8v5"/>',
    "rotation_vue": '<rect x="6.5" y="6.5" width="11" height="11" rx="1.2" transform="rotate(-15 12 12)"/>'
                    '<path stroke="A" d="M4 9a9 9 0 0 1 14-4.5M18.5 2v3h-3M20 15a9 9 0 0 1-14 4.5M5.5 22v-3h3"/>',
    "regle": '<rect x="2.5" y="8" width="19" height="8" rx="1.2" transform="rotate(-25 12 12)"/>'
             '<path stroke="A" d="M6.3 12.7l-1-2.2M9.5 11.2l-.6-1.4M12.7 9.7l-1-2.2M15.9 8.2l-.6-1.4M19.1 6.7l-1-2.2"/>',
    "crayon": '<path d="M16 3.5l4.5 4.5L9 19.5l-5.5 1 1-5.5z"/><path d="M13.5 6l4.5 4.5"/>'
              '<path stroke="A" d="M4.5 15l4.5 4.5"/>',
    "melangeur": '<path d="M14.5 4.5l5 5-7.8 7.8-5-5z"/><path d="M6.7 12.3l5 5"/>'
                 '<circle stroke="A" cx="5.5" cy="18.5" r="2.5"/><path stroke="A" d="M3 3.5c3 0 4 2 7 2"/>',
    "rep_v": '<rect x="7" y="3" width="10" height="4" rx="1"/><rect x="5" y="10" width="14" height="4" rx="1"/>'
             '<rect x="8" y="17" width="8" height="4" rx="1"/>',
}


def svg(nom: str, couleur: str, accent: str) -> bytes:
    corps = DESSINS[nom].replace('stroke="A"', f'stroke="{accent}"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{couleur}" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{corps}</svg>').encode()


def icone(nom: str, couleur: str, accent: str, taille: int = 24) -> QIcon:
    rendu = QSvgRenderer(QByteArray(svg(nom, couleur, accent)))
    ic = QIcon()
    for echelle in (1, 2):
        pm = QPixmap(taille * echelle, taille * echelle)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        rendu.render(p, QRectF(0, 0, taille * echelle, taille * echelle))
        p.end()
        pm.setDevicePixelRatio(echelle)
        ic.addPixmap(pm)
    return ic
