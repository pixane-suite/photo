# À publier — changements depuis la dernière publication

Carnet tenu à chaque modification (consigne de Christophe, 11/11/2026) : on ne publie que quand il le dit, après
plusieurs modifications. Ce jour-là, tout ce qui est listé ici sert à mettre à jour le README, les notes de version,
etc. ; puis le carnet est vidé (en gardant la « Dernière publication » à jour).

**Dernière publication : 0.26.0** (16/11/2026, GitHub pixane-suite/photo v0.26.0, version normale).
Les installateurs fabriqués depuis portent toujours le numéro 0.26.0 (non publiés).

## Nouveautés

- (rien pour l'instant)

## Corrections

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
