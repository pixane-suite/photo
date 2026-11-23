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

## Corrections

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
