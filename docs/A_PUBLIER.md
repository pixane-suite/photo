# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.26.0** (16/11/2026, GitHub pixane-suite/photo v0.26.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.26.0 (non publiés).

## Nouveautés

- **Édition > Préférences…** (Ctrl+,), comme Pixane Video : tous les réglages durables en onglets
  (Affichage, Fonctions installées, Intelligence artificielle, Enregistrement, Mises à jour), appliqués à OK ; les
  menus restent. Nouveaux réglages visibles : fréquence de la copie de récupération (ou jamais), dossier des images.
- **Agrandir l'image : description facultative** (ligne « Description » de la barre) : guide ce que l'IA ajoute
  (moins d'objets ou de personnages hors sujet). **Décrire (IA)** : l'IA écrit elle-même la description, modifiable ;
  modèle facultatif **Qwen3.5 2B** (4,2 Go, Apache-2.0, Hugging Face Comfy-Org), case dans l'installateur et dans
  Installer / Compléter le moteur IA.
- **Polices gratuites Google Fonts dans « Trouver une police semblable »** (option, décochée d'office ; case dans
  l'installateur, Affichage et Préférences) : environ 1 960 polices gratuites (surtout OFL), téléchargées une fois en
  arrière-plan (environ 100 Mo, depuis Fontsource), comparées comme les polices installées. Une police Google pas
  installée est marquée comme telle ; **Télécharger et installer** l'installe dans Windows pour l'utilisateur.

- **Outil Texte plus pratique** : double-clic sur un texte de la photo ou sur un calque de texte pour l'éditer ;
  lettres sélectionnées surlignées sur la photo ; couleur (texte, contour, ombre, fond) montrée sur la photo pendant
  le choix ; liste des polices filtrée par **style** (avec / sans empattements, manuscrites, fantaisie, chasse fixe)
  et de **taille** réglable (petite, moyenne, grande) ; **panneau Texte élargissable** à la souris (largeur retenue).
- **Nouvelle image en 16 ou 32 bits par couche** (choix retenu).

- **Calques** : l'outil Déplacer bouge un **groupe entier** (ou plusieurs calques choisis) ; **cadre en pointillés**
  autour du calque choisi quand il dépasse de l'image ; **Calque > Pixelliser** (texte, forme, style, objet
  dynamique, tout), aussi au clic droit.
- **Lasso par points** (choix « Libre / Par points » dans la barre du Lasso).
- **Outil Texte** : choisir des lettres en glissant sur le texte de la photo, double-clic = un mot ; déplacer par le
  bord du cadre ou Ctrl + glisser.
- **Polices installées pendant que Pixane est ouvert** : visibles tout de suite.
- **Effacer : analyse de la zone** avant de lancer (ombre de l'objet, bord oublié), montrés en couleur et proposés
  (désactivable dans les Préférences).
- **Onglets Calques / Historique / Nuancier / Actions** : l'onglet ouvert se voit (gras, trait de couleur).

## Corrections

- Outil Texte : **Ctrl+Z** ne retirait pas un texte posé par erreur d'un clic (la case de saisie gardait le
  raccourci).

- **Trouver une police semblable** donnait des polices sans rapport :
  - comparaison **lettre par lettre** : les lettres espacées (« C O L D P L A Y ») et les textes gras retrouvent leur
    police (essai sur 92 textes : 1re dans 46 cas sur 92 au lieu de 26, dans les 3 premières 59 fois au lieu de 28) ;
  - la mémoire des polices rangeait, pour certaines polices, des morceaux d'autres lettres à la place des bonnes
    (refaite une fois, automatiquement) ;
  - les lettres prises sont montrées en noir sur blanc (un texte blanc était invisible) ;
  - la case ne reprend plus le mot de la recherche d'avant ; **Windows lit les lettres** et la remplit (OCR intégré
    à Windows, rien à télécharger) ; Pixane prévient si le nombre de lettres ne correspond pas, et essaie les
    majuscules quand l'image l'est.
- **Souris invisible à l'ouverture** : sans image ouverte, la flèche disparaissait au-dessus de la fenêtre (le
  pinceau, choisi d'office, cache la flèche pour dessiner son rond, qui n'existe pas sans image). La flèche reste
  visible tant qu'aucune image n'est ouverte.
- **Agrandir l'image** en pleine définition : l'ajout ressortait sous un voile brumeux, et des personnages ou
  objets de la proposition choisie pouvaient changer. Flux voit maintenant l'image comme modèle au lieu d'une zone
  grise. Même correction pour « Partir de celle-ci » (variantes d'une proposition).
- Désinstallation, « Supprimer aussi les réglages » : n'efface plus que les réglages de Pixane Photo (avant :
  toute la clé Software\Pixane, donc aussi les réglages de Pixane Video). Signalé par le projet Video.

## À mettre à jour le jour de la publication

- [ ] Numéro de version (`pixane\__init__.py`) selon la règle A.B.C.
- [ ] README.md et README.en.md, liste « Ce que Pixane sait faire » (écrite à la main).
- [ ] Recopier le guide dans les README : `.venv\Scripts\python outils\readme.py`.
- [ ] FEUILLE_DE_ROUTE : ligne « Dernière version d'essai ».
- [ ] Issue n°1 « Feuille de route » sur GitHub (`gh issue edit 1 -R pixane-suite/photo`) : Ajouté récemment, En
      cours, Prévu.
- [ ] Notes de version (« ## Nouveautés », « ## Corrections ») à partir des listes ci-dessus, sans pied « Generated
      with Claude Code ».
- [ ] Installateur, push, release GitHub, ligne au JOURNAL ; puis vider ce carnet.
