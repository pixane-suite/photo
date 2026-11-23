# Guide d'utilisation de Pixane Photo

Pixane Photo est un éditeur photo pour Windows qui retouche les images avec une IA qui tourne **sur votre PC**
(pas d'abonnement, pas d'envoi de photos sur Internet). Il fait partie de la **Suite Pixane**.
Ce guide explique chaque outil et chaque réglage : **à quoi il sert** et **comment s'en servir**. Il est complété
à chaque nouvelle fonction.

**Pour qui ?** Pixane Photo est pensé pour celles et ceux qui débutent en retouche photo, ou qui en ont peu l'expérience : les outils vont à l'essentiel, l'IA se charge du travail difficile et l'aide explique chaque réglage pas à pas. Pixane Photo n'a pas la prétention de remplacer des programmes comme Photoshop, GIMP ou Krita, qui restent la référence pour un travail poussé : il veut rendre la retouche accessible à tous.

## Avant de commencer : une IA 100 % sur votre PC

- **Aucune IA en ligne.** Toutes les actions IA de Pixane Photo (Effacer, Remplir, Agrandir, Upscale, sélection d'objet,
  arrière-plan, réduction du bruit, netteté, restauration…) tournent **sur votre ordinateur**, avec des modèles
  installés sur votre disque. **Aucune photo n'est envoyée sur Internet** ; pas de compte, pas d'abonnement, pas de
  limite d'utilisation. Internet sert seulement à télécharger le moteur IA une fois (et ses mises à jour, si vous
  les acceptez). Ensuite, Pixane Photo marche même sans connexion.
- **La vitesse dépend de votre PC, surtout de la carte graphique** : c'est elle qui fait les calculs de l'IA. **Plus
  elle est puissante et plus elle a de mémoire, plus les traitements vont vite.** Une carte récente avec 12, 16 ou
  24 Go de mémoire va nettement plus vite que celle du PC d'essai ; une carte plus modeste, plus lentement. La
  mémoire vive (RAM) compte aussi : quand la carte graphique manque de mémoire, une partie du modèle passe par la RAM,
  ce qui ralentit.
- **Durées mesurées** sur le PC d'essai (NVIDIA RTX 3060 Ti 8 Go, 32 Go de mémoire vive) :

| Action | Durée |
|---|---|
| Démarrage du moteur IA (à l'ouverture de Pixane Photo) | environ 20 secondes |
| Sélection d'objet, sélection rapide | environ 1 seconde |
| Supprimer l'arrière-plan, sélectionner le sujet, outil Supprimer (J), Réduire le bruit | quelques secondes |
| Netteté (IA) | 15 à 20 secondes |
| Remplir, Agrandir l'image | environ 1 minute par proposition |
| Effacer | environ 2 minutes |
| Upscale net | 20 à 30 secondes par morceau de 1024 px |
| Restaurer une vieille photo | environ 2 minutes par proposition |

La première utilisation d'un modèle après le démarrage est un peu plus longue (il se charge en mémoire).

Pour **Créer une image**, **Modifier avec une consigne** et **Restaurer**, Pixane Photo mesure la durée sur ton PC : ensuite, la fenêtre affiche « environ … chacune, mesuré sur ce PC ». Avant la première mesure, elle donne la durée sur une RTX 3060 Ti, en prévenant que ça dépend du PC.

### Configuration

| | Minimum | Conseillé |
|---|---|---|
| **Système** | Windows 10 ou 11, 64 bits | Windows 11, 64 bits |
| **Carte graphique** | NVIDIA, **8 Go** de mémoire (par exemple RTX 3060 Ti, 3070, 4060) | NVIDIA RTX, **12 Go ou plus** (par exemple RTX 3060 12 Go, 4070, 4080, 4090) |
| **Mémoire vive** | 16 Go (les actions Flux sont alors lentes) | **32 Go** |
| **Disque** | 35 Go libres pour le moteur IA | 60 Go libres (avec Flux Schnell et Flux Kontext), sur un SSD |
| **Processeur** | 4 cœurs récent | 6 cœurs ou plus |

Pixane Photo a été testé sur une **RTX 3060 Ti (8 Go) avec 32 Go de mémoire vive**. Le minimum est une estimation : il
n'a pas été essayé sur d'autres PC. **Sans carte NVIDIA** (carte AMD ou Intel, PC portable sans carte graphique),
Pixane Photo s'ouvre et retouche normalement (calques, texte, réglages, filtres, export…), mais les actions IA ne
marchent pas.

---

## 1. La fenêtre

| Zone | Rôle |
|---|---|
| **Barre du haut** | Ouvrir, Enregistrer, Annuler / Rétablir, réglages de l'outil choisi (taille, Nouvelle / Ajouter / Retirer…), zoom |
| **Outils (à gauche)** | Main, Déplacer, outils de sélection, outils de retouche, Recadrer, Texte. Un petit triangle sur un bouton = plusieurs outils : **clic droit** (ou clic maintenu) pour choisir |
| **Panneau « Texte » (à gauche)** | Réglages du texte, visible avec l'outil Texte (voir chapitre 7) |
| **Onglets (au-dessus de la photo)** | Un onglet par photo ouverte (dès qu'il y en a deux) ; un point « • » marque une photo modifiée |
| **Règles** | En haut et à gauche de la photo, en pixels (Affichage > Règles, Ctrl+R) |
| **Photo (au centre)** | La photo ; la zone sélectionnée apparaît en rouge transparent |
| **Panneau « Intelligence artificielle » (à droite)** | Effacer, Remplir, Agrandir l'image, Upscale |
| **Panneau « Calques » (à droite, en dessous)** | Les calques de l'image (voir chapitre 6) ; onglet **Historique** à côté |
| **Barre d'état (en bas)** | État du moteur IA (point de couleur), taille de la photo |

**Couleurs** : Pixane Photo prend la couleur d'accent choisie dans Windows (Paramètres > Personnalisation > Couleurs)
et suit le mode clair / sombre de Windows. Menu **Affichage > Thème** : *Comme Windows*, *Clair* ou *Sombre*.
Le bouton soleil / lune de la barre du haut bascule aussi entre clair et sombre.

**Langue** : Pixane Photo existe en **français** et en **anglais**. Par défaut, il prend la langue de Windows
(français si Windows est en français, anglais sinon). Menu **Affichage > Langue** : *Comme Windows*, *Français*
ou *English* ; Pixane Photo propose alors de redémarrer pour appliquer la langue (le moteur IA redémarre aussi,
environ 20 secondes). Les boutons standard (Oui / Non / Annuler, menu clic droit) suivent la même langue.
Les noms de calques déjà créés gardent leur langue d'origine. Guide en anglais : `docs\GUIDE_en.md`.

**Taille de l'interface** : menu **Affichage > Taille de l'interface** : de **75 %** (très compacte) à **200 %**.
Tout change ensemble : textes, icônes, boutons, panneaux. Ce pourcentage s'ajoute à la mise à l'échelle de
Windows : sur un petit écran de portable, choisissez 85 % ou 75 % pour gagner de la place ; sur un écran 4K,
125 % à 200 %. Pixane Photo propose de redémarrer pour l'appliquer (l'image ouverte est rouverte).
**Affichage > Taille des icônes des outils** (*Petites*, *Normales*, *Grandes*, *Très grandes*) change seulement la
barre des outils à gauche, tout de suite.

**Préférences** (menu **Édition > Préférences…**, Ctrl+,) : tous les réglages durables au même endroit, en
onglets. Rien ne change avant **OK** ; **Annuler** laisse tout comme avant. Les mêmes réglages restent dans les menus.
- **Affichage** : thème, langue, taille de l'interface, taille des icônes des outils, barre d'accès rapide, écart de
  la grille. La langue et la taille de l'interface changent au prochain démarrage (Pixane Photo propose de
  redémarrer) ; le reste tout de suite.
- **Fonctions installées** : *Recherche de police semblable*, *Orthographe et césure* et ses langues : les options
  choisies à l'installation, modifiables ici.
- **Intelligence artificielle** : *Mettre les résultats dans un nouveau calque*, *Agrandir l'image en pleine
  définition* ; le dossier du moteur IA et le bouton *Installer ou compléter le moteur IA…*.
- **Enregistrement** : fréquence de la **copie de récupération** (toutes les 1, 3, 5 ou 10 minutes, ou jamais) et
  **dossier des images** proposé pour ouvrir et enregistrer.
- **Mises à jour** : *Vérifier les mises à jour au démarrage*, et un bouton pour chercher tout de suite.

**Moteur IA** : au démarrage, Pixane Photo lance l'IA (ComfyUI) en arrière-plan, sans fenêtre. Comptez environ
20 secondes. Le point en bas à gauche passe au vert quand le moteur est prêt ; les actions IA sont grisées avant.

---

## 2. Ouvrir et enregistrer

- **Fichier > Ouvrir** (Ctrl+O) : JPG, PNG, TIFF, WebP, BMP, les images **HDR** **.exr** (OpenEXR) et **.hdr**
  (Radiance), et les fichiers à calques **.piximg**, **.ora** et **.psd** (Photoshop).
  La photo est redressée selon son orientation d'appareil.
- **Fichiers RAW** des appareils photo (Canon .CR2 / .CR3, Nikon .NEF, Sony .ARW, .DNG, Fujifilm .RAF, Olympus
  .ORF, Panasonic .RW2, Pentax .PEF…) : ils s'ouvrent comme une photo, développés avec la balance des blancs de
  l'appareil (bibliothèque LibRaw) ; retouchez ensuite avec les réglages (Niveaux, Courbes, Balance…). Le RAW
  n'est jamais remplacé : **Enregistrer** propose un autre fichier (JPG, ou .piximg s'il y a des calques).
- **Enregistrer** (Ctrl+S), **Enregistrer sous** (Ctrl+Maj+S) :
  - **.piximg** (projet Pixane Photo) : le format de Pixane Photo. Garde **tout** : calques (noms, ordre, visibilité, opacité,
    verrou), **textes modifiables** et **styles de calque modifiables**. Proposé d'office quand l'image a plusieurs calques ou un texte.
  - **.ora** (OpenRaster) : pour **partager avec Krita ou GIMP** (format ouvert). Garde les calques, mais les
    textes y deviennent des images.
  - Bon à savoir : un .piximg est construit comme un .ora ; renommé en .ora, il s'ouvre aussi dans Krita ou GIMP.
  - **.psd** (Photoshop) : pour **travailler avec Photoshop**. Garde les calques (noms, ordre, visibilité,
    opacité, verrou) ; les textes y deviennent des images. Une photo ouverte depuis un PSD est proposée en PSD.
  - **PSD ouverts dans Pixane Photo** : RVB ou niveaux de gris, 8 ou 16 bits, avec les calques, les **groupes**, les
    **masques de calque**, les **modes de fusion** et les **styles** (ombre portée et interne, lueurs, contour,
    biseau, incrustations couleur et dégradé), qui restent modifiables. Pixane Photo ne reproduit pas les calques de
    réglage de Photoshop, les masques d'écrêtage, ni les groupes en mode « traverser » (ouverts en mode Normal) :
    un message le signale à l'ouverture, car l'aspect peut alors différer. Un PSD en CMJN s'ouvre aplati (un seul
    calque). Les grands documents .psb ne sont pas pris en charge.
  - **PSD enregistrés par Pixane Photo** : calques, groupes, masques et modes de fusion sont gardés ; les styles sont mis
    dans les pixels ; un calque de réglage devient un calque d'image (le résultat du réglage).
  - **JPG** (qualité 95), **PNG**, **TIFF**, **WebP** : l'image **à plat** (ce que vous voyez, calques fusionnés).
    Un message le rappelle si l'image a plusieurs calques.
  Les informations de l'appareil (EXIF) et le profil de couleur sont conservés.
- **Annuler** (Ctrl+Z) / **Rétablir** (Ctrl+Y ou Ctrl+Maj+Z) : chaque retouche et chaque sélection peut être annulée
  (30 étapes). Les boutons **retour** et **suivant** de la souris (sur le côté) font la même chose.
- **Pendant un travail pas encore validé** (Transformer, cadre d'Agrandir, Recadrer) : Annuler (ou le bouton retour)
  défait **le dernier geste** de ce travail (ex. la rotation, en gardant la taille) ; arrivé au début, il abandonne
  le travail. Rétablir (ou le bouton suivant) refait le geste défait.
- **Panneau Historique** (onglet à côté de « Calques ») : la liste des étapes. Un clic sur une étape revient à ce
  moment-là ; un clic sur une étape plus bas refait les suivantes. Une nouvelle retouche efface les étapes « en avance ».
- **Fichier > Fichiers récents** : les 10 dernières images ouvertes ou enregistrées (*Effacer la liste* pour la vider).
- **Plusieurs photos à la fois** : *Ouvrir* accepte plusieurs fichiers d'un coup (Ctrl+clic ou Maj+clic dans la
  fenêtre), et on peut en glisser plusieurs sur Pixane Photo. Chaque photo a son **onglet** et son propre **Annuler**
  (Ctrl+Z ne touche que la photo affichée). Changer de photo : clic sur l'onglet, **Ctrl+Tab** / **Ctrl+Maj+Tab**.
  **Fichier > Fermer la photo** (Ctrl+W, ou la croix de l'onglet) demande d'enregistrer si besoin. Rouvrir une photo
  déjà ouverte revient simplement à son onglet.
- **Enregistrement automatique** : toutes les 3 minutes, chaque photo modifiée est copiée (calques, textes, styles,
  masques compris) dans `%LOCALAPPDATA%\Pixane\recuperation`, sans ralentir le travail. Si Pixane Photo se ferme mal
  (plantage, coupure de courant), il propose au démarrage suivant de **rouvrir ces copies** ; elles s'ouvrent
  « à enregistrer », avec le nom du fichier d'origine. Les copies sont effacées quand la photo est enregistrée ou
  fermée, et quand Pixane Photo se ferme normalement.
- **En cas d'erreur** : si une commande échoue, Pixane Photo l'affiche et la note dans
  `%LOCALAPPDATA%\Pixane\erreurs.log` (utile pour signaler le problème).
- **Fichier > Exporter sous…** (Ctrl+Alt+Maj+W) : une copie **pour un envoi normal** (imprimeur, ami, clé USB) :
  pleine taille, pleine qualité, résolution, profil de couleur et informations de l'appareil photo gardés. JPEG, PNG
  (avec la transparence), TIFF ou WebP. La photo ouverte ne change pas (elle reste à enregistrer si elle a été
  modifiée) ; Pixane Photo ne propose jamais d'écraser la photo d'origine et retient le dernier format choisi.
- **Fichier > Exporter pour le web…** (Ctrl+Alt+Maj+S) : une copie légère pour Internet, sans toucher à la photo.
  - **Format** : JPEG (photos), **WebP** (plus léger à qualité égale, garde la transparence), PNG (sans perte).
  - **Réduire : plus grand côté** (par exemple 2048 px) ; jamais agrandie.
  - **Qualité** (30 à 100 ; 80 environ suffit pour le web).
  - Le **poids du fichier** s'affiche en direct.
  - Les informations de l'appareil (EXIF : modèle, date, parfois le lieu) sont **enlevées** par défaut (case pour
    les garder). Nom proposé : `<photo>_web.jpg`.
- **Fichier > Traitement par lot…** : le même travail sur **tout un dossier** de photos.
  - **Photos à traiter** (dossier d'origine, jamais modifié) et **Résultats dans** (un autre dossier).
  - Au choix : **Réduire** (plus grand côté), **Réglage automatique** (luminosité, contraste, température, comme
    le bouton Auto), **Upscale IA ×2** (RealESRGAN), **Supprimer l'arrière-plan** (résultats en PNG transparent),
    **Format** (garder, JPEG, WebP, PNG) et qualité, **Ajouter au nom** (ex. `_web`).
  - Une barre montre l'avancement ; **Arrêter** termine la photo en cours puis s'arrête. Une photo qui pose
    problème est signalée à la fin, les autres sont faites.
  - **Action** : une action enregistrée dans le panneau **Actions** (voir chapitre 9) est jouée sur chaque photo.
  - Les fichiers RAW du dossier sont traités aussi.
  - Sécurité : si les résultats iraient dans le même dossier sous le même nom, Pixane Photo refuse (les originaux
    seraient remplacés).
- **Fichier > Imprimer…** (Ctrl+P) : l'image visible (tous les calques), avec un **aperçu de la page**.
  - **Imprimante**, **Papier** (A4, A5, A3, Letter, 10 × 15, 13 × 18, 20 × 30 cm), **Orientation** (automatique :
    comme l'image), **Marges**, **Copies**.
  - **Taille** : *Remplir la page* (dans les marges), *Taille réelle* (d'après la résolution de l'image) ou
    *Largeur choisie* en cm.
  - Pixane Photo indique la taille sur la feuille et le nombre de points par pouce ; en dessous de 150, il prévient que
    l'impression risque d'être floue (IA > Upscale peut aider).
- **Fichier > Nouvelle image…** (Ctrl+N) : une image vide, comme dans Photoshop. Un **aperçu** montre la forme de
  la feuille, son fond et les repères (fond perdu, zone de sécurité).
  - **Formats tout prêts** (à gauche) : **pochettes** (CD, vinyle 33 et 45 tours, 3000 × 3000 px pour Spotify,
    Deezer, Apple Music), **livres** (poche, roman, Amazon KDP, livre numérique), **réseaux sociaux** (Instagram,
    Story, Facebook, YouTube, X), **impression** (A3, A4, A5, photos, affiches, carte de visite, flyer), **écran**
    (HD, Full HD, 4K). **Enregistrer ce format…** garde vos propres formats dans **Mes formats** (taille, unité, résolution, fond perdu, zone de sécurité, mode et fond) ; le dernier format
    utilisé est proposé la fois suivante.
  - **Largeur, hauteur et unité** : pixels, pouces, centimètres, millimètres, points ou picas (1 pouce = 2,54 cm
    = 72 points = 6 picas). Changer d'unité ne change pas l'image.
  - **Orientation** : Portrait ou Paysage échange largeur et hauteur.
  - **Résolution** (ppp, points par pouce) : **300** pour l'impression, **72** pour l'écran. Elle est **gardée dans
    le fichier** (.piximg, PSD, JPEG, PNG, TIFF) : un imprimeur verra la bonne taille.
  - **Mode** : couleurs RVB ou **niveaux de gris** (voir *Image > Mode*), et **8, 16 ou 32 bits par couche** :
    8 bits (16,7 millions de couleurs, comme le JPEG, le PNG et le web), 16 bits (dégradés et réglages sans
    cassures), 32 bits (HDR : couleurs plus claires que le blanc). Le dernier choix est retenu ; modifiable ensuite
    avec *Image > Mode*.
  - **Fond** : blanc, transparent, noir ou une couleur au choix.
  - **Fond perdu** (impression) : bande ajoutée tout autour, coupée par l'imprimeur (en général 3 mm) : le fond doit
    aller jusqu'au bord de l'image. **Zone de sécurité** : marge à l'intérieur du format fini où ne mettre rien
    d'important (texte, visage). Des **repères** sont posés tout seuls sur ces deux lignes.
  - En bas : la taille en pixels, la taille imprimée et la mémoire utilisée.
- **Fichier > Exporter pour l'impression (CMJN)…** : pour un imprimeur qui demande du CMJN (les quatre encres).
  Pixane Photo travaille en RVB et convertit au moment d'exporter, comme le conseillent les imprimeurs.
  - **Format** : TIFF (le plus sûr), PDF ou JPEG.
  - **Profil CMJN** : ceux installés dans Windows, rien à télécharger. Demandez celui de votre imprimeur ; en Europe,
    c'est souvent **Coated FOGRA39** (papier couché).
  - **Intention de rendu** : *Perceptive* pour les photos, *Colorimétrie relative* pour les logos et les aplats.
    **Compensation du point noir** : cochée, les ombres gardent leurs détails.
  - La **résolution** est notée dans le fichier ; la photo n'est pas modifiée (nom proposé : `<photo>_cmjn.tif`).
  - Avant d'exporter : **Affichage > Aperçu de l'impression (CMJN)** (Ctrl+Alt+Y) montre à l'écran les couleurs
    telles qu'elles sortiront (les bleus et les verts très vifs ternissent souvent). Le recliquer revient à l'écran
    normal ; l'image n'est jamais modifiée.
- **Fichier > Nouvelle image depuis le presse-papiers** (Ctrl+Alt+V) : ouvre l'image copiée (capture d'écran, autre
  logiciel…). **Ctrl+V** sans photo ouverte fait la même chose.

---

## 3. Se déplacer dans la photo

| Action | Comment |
|---|---|
| Zoomer | Molette (autour du curseur), Ctrl++ / Ctrl+-, boutons loupe |
| Ajuster à la fenêtre | Ctrl+0 |
| Taille réelle (100 %) | Ctrl+1 |
| Déplacer la vue | Outil **Main** (H), ou maintenir **Espace** et glisser, ou glisser avec le **bouton du milieu** |
| Déplacer **un calque** | Outil **Déplacer** (V) : seul le calque choisi bouge (la Main, elle, ne déplace que la vue) |
| **Comparer avant / après** | **Affichage > Comparer avant / après** (Ctrl+Alt+B) : un rideau sur la photo, à gauche la photo telle qu'à l'ouverture, à droite la photo actuelle ; glissez pour le déplacer. Rien n'est modifié. Échap ou Ctrl+Alt+B pour finir |

### Règles, repères et grille (menu Affichage)
- **Règles** (Ctrl+R) : graduées en pixels de l'image, le 0 au coin haut-gauche de la photo ; un trait suit la
  souris.
- **Repères** : glissez depuis une règle vers la photo pour poser une ligne bleue (horizontale depuis la règle du
  haut, verticale depuis celle de gauche). Avec l'outil **Déplacer** (V), attrapez un repère pour le bouger (le
  curseur devient une double flèche au-dessus) ; tiré hors de la photo, il disparaît. *Nouveau repère…* le pose à une position exacte, *Effacer les repères* les enlève tous,
  Ctrl+; les cache ou les montre. Ils sont gardés dans le fichier .piximg.
- **Grille** (Ctrl+') : lignes régulières sur la photo ; *Taille de la grille…* règle l'écart (100 px par défaut).
- **Magnétisme** (Ctrl+Maj+;, coché par défaut) : la sélection rectangle, le dégradé et les formes s'accrochent aux
  repères, aux bords de la photo et à la grille (si elle est affichée), à moins de 8 pixels d'écran.

---

## 4. Sélectionner (dire à l'IA où travailler)

La zone sélectionnée apparaît en **rouge transparent**. Il n'est pas nécessaire d'« entourer » un objet :
on peut simplement **peindre dessus**.

Les outils de sélection sont rangés sous **deux boutons** de la barre de gauche (petit triangle) : les outils
« à la main » et les outils « automatiques ». **Clic droit** sur le bouton, ou clic maintenu, pour choisir ; ou
directement leur touche.

| Outil | Touche | Usage |
|---|---|---|
| **Rectangle** | M | Sélection rectangulaire |
| **Lasso** | L | **Libre** : tracer un contour à main levée, bouton appuyé ; la forme est fermée automatiquement. **Par points** (choix dans la barre, retenu) : un clic par point ; clic sur le premier point, double-clic ou Entrée pour fermer, Retour arrière enlève le dernier point, Échap annule |
| **Pinceau de sélection** | B | Peindre la zone. Idéal pour un objet, un texte, un fil… |
| **Gomme de sélection** | E | Retirer de la sélection en peignant |
| **Sélection d'objet** (IA) | O | Tirer un cadre autour d'un objet, ou cliquer dessus : l'IA le détoure |
| **Sélection rapide** (IA) | Q | Peindre grossièrement sur l'objet : l'IA trouve ses contours |
| **Baguette magique** | W | Un clic sur une couleur : toute la zone de couleur proche (sans IA) |
| **Sélection de texte** | Y | Un cadre autour d'un texte : les lettres seules, traits fins compris (sans IA) |

- **Rectangle et lasso**, comme dans Photoshop : une nouvelle sélection **remplace** l'ancienne. Maintenir **Maj** en
  commençant le tracé **ajoute** à la sélection, **Alt** **retire**. Un simple clic sans tracer **désélectionne**.
  Les pastilles **Nouvelle / Ajouter / Retirer** de la barre du haut choisissent le mode sans touche.
- **Pinceau de sélection** : il ajoute toujours à la sélection ; pastille **Retirer** ou **Alt** maintenu : il retire
  (comme la gomme de sélection).
- **Taille du pinceau** : curseur « Taille » de la barre du haut, ou touches `[` et `]`.
- Menu **Sélection** : *Tout sélectionner* (Ctrl+A), *Désélectionner* (Ctrl+D), *Inverser* (Ctrl+Maj+I).
- **Flèches du clavier** (avec un outil de sélection : rectangle, lasso, pinceau de sélection, baguette, sélection
  rapide ou d'objet) : la sélection bouge de **1 pixel** (Maj : **10 pixels**). Seul le contour bouge, pas l'image ;
  un seul Ctrl+Z annule tous les appuis.
- **Sélection > Modifier la sélection** : *Agrandir…* ou *Réduire…* d'un nombre de pixels, *Adoucir les bords…*
  (bord progressif, utile pour les réglages de l'image).
- **Sélection > Sélectionner le sujet (IA)** (Ctrl+Alt+S) : l'IA trouve le sujet principal (personne, animal,
  objet) et le sélectionne. Voir chapitre 5, « Sujet et arrière-plan ».

### Sélection d'objet et sélection rapide (IA)
Elles utilisent le modèle **SAM 3.1** de Meta (1,6 Go, installé avec le moteur IA). L'IA comprend l'**objet entier**
(une personne, une voiture, un meuble…), même quand ses couleurs varient, et suit ses vrais contours. Environ une
seconde par demande (quelques secondes la première fois).
- **Sélection d'objet (O)** : tirer un **cadre** autour de l'objet, ou **cliquer** dessus. Comme le rectangle : la
  nouvelle sélection remplace l'ancienne ; **Maj** ajoute, **Alt** retire (ou les pastilles Nouvelle / Ajouter /
  Retirer).
- **Sélection rapide (Q)** : **peindre** grossièrement sur l'objet (dessus, ou en
  suivant son contour). Comme dans Photoshop, chaque trait trouve **son** objet, qui s'**ajoute** à la sélection : un
  trait sur un titre puis un trait autour d'une personne donnent le titre + la personne entière. Des points verts
  montrent ce que l'IA doit garder. **Alt + peindre** sur une partie à enlever (points rouges) : l'IA corrige les
  objets déjà trouvés. Une sélection vidée (Ctrl+D) ou changée par un autre outil fait repartir de zéro ; **Échap**
  aussi.
- Ctrl+Z annule chaque étape. Le résultat se règle ensuite avec *Modifier la sélection* (agrandir, adoucir…).

### Sélection de texte (Y)
Pour prendre un **texte** (titre de pochette, lettres manuscrites, texte en dégradé ou à contour) sans le fond, même
quand une couleur proche le touche. Sans IA, en moins d'une seconde. Dans le groupe de la baguette (clic droit sur
son bouton) ou touche **Y**.
1. **Tirer un cadre autour du texte**, en laissant un peu de fond tout autour : Pixane Photo regarde ce qui touche le bord
   du cadre (le fond) et sélectionne ce qui s'en distingue (les lettres). Les traits très fins et les bords des
   lettres sont pris en douceur (sélection progressive). Rien n'est pris hors du cadre.
2. **Corriger d'un clic**, dans ce cadre :
   - **Alt + clic** sur un morceau pris en trop (un bout de photo) : il est enlevé ;
   - **Maj + clic** sur un morceau oublié : il est ajouté ;
   - avec **Ctrl** en plus : toute cette couleur du cadre (pratique pour des franges ou des taches nombreuses).
3. **Maj + cadre** : ajoute un autre texte ; **Alt + cadre** : retire le texte de ce cadre.
- **Lettres pleines** (case) : l'intérieur des lettres est pris aussi (motifs dans une lettre, intérieur des O et
  des A). Pratique pour effacer ou déplacer un texte. Sans la case, seuls les petits trous (grain d'un JPEG) sont
  bouchés.
- Conseils : un cadre qui coupe un peu les lettres d'un côté n'est pas grave. Si le fond derrière le texte est une
  photo chargée, un cadre bien serré aide ; une partie de photo entièrement dans le cadre se retire par Alt + clic.
- Ctrl+Z annule le dernier cadre ou la dernière correction.

### Trouver une police semblable
Quelle police a servi pour ce titre ? Pixane Photo cherche parmi **les polices installées sur le PC** celles qui
ressemblent le plus (sans Internet, rien n'est téléchargé).
1. Sélectionnez les lettres avec la **Sélection de texte (Y)** (un bloc plein ne marche pas : il faut les lettres
   seules).
2. **Sélection > Trouver une police semblable…**, ou le bouton **Police semblable…** dans la barre de l'outil.
3. En haut de la fenêtre, **les lettres prises** sont montrées **en noir sur blanc**, quelle que soit leur couleur
   (un texte blanc se voit aussi) : vérifiez qu'elles sont complètes.
4. **Les lettres** : Windows les **lit tout seul** (lecture de texte intégrée à Windows 10 et 11, rien n'est
   téléchargé) et remplit la case en quelques secondes. **Vérifiez-les** : elles doivent être exactement celles de
   l'image, dans le même ordre, avec les majuscules (séparez les lignes par « / ») ; corrigez ou tapez-les si besoin.
   Puis **Chercher**. Quelques secondes (plus il y a de polices installées, plus c'est long).
   - Si le nombre de lettres tapées ne correspond pas à l'image, Pixane Photo le dit (la comparaison est alors moins
     précise) ;
   - si l'image est en majuscules et que vous avez tapé des minuscules, il cherche aussi en majuscules et le dit.
5. Les polices les plus proches s'affichent d'abord, écrites avec vos lettres, avec leur ressemblance en %.
   La comparaison se fait **lettre par lettre** : l'espacement entre les lettres (souvent agrandi sur les pochettes,
   « C O L D P L A Y ») ne compte pas, et un texte gras retrouve aussi sa police.
   - **Appliquer au texte choisi** : si le calque choisi est un texte de Pixane Photo, il prend cette police ;
   - **Créer un texte avec cette police** : nouveau calque de texte à la place des lettres, avec leur couleur (les
     lettres de l'image restent : effacez-les ensuite si besoin) ;
   - **Copier le nom** de la police.
- **Option** (case à l'installation, ou **Affichage > Recherche de police semblable**) : pour aller vite, Pixane Photo
  prépare **une seule fois** la liste de vos polices, en arrière-plan, une minute après le démarrage. La durée dépend
  du **nombre de polices installées** : environ 1 min 20 (et 15 Mo) pour 1 200 polices.
  Décochée : la fonction est cachée, rien ne tourne en fond, et cette liste est effacée.
- **Police installée pendant que Pixane Photo est ouvert** : elle apparaît tout de suite dans la liste des polices
  (message dans la barre du bas), sans redémarrer.
- **Polices gratuites Google Fonts** (option, décochée d'office : case à l'installation, ou **Affichage > Polices
  gratuites Google Fonts**, ou Édition > Préférences) : la recherche compare aussi les **polices gratuites de Google
  Fonts** (environ 1 960 familles, licences libres, surtout OFL : usage commercial compris).
  - Une seule fois, en arrière-plan : Pixane Photo télécharge le style normal de chacune (**environ 100 Mo**, depuis
    Fontsource : api.fontsource.org et cdn.jsdelivr.net) dans `%LOCALAPPDATA%\Pixane\polices-google`, puis prépare
    leur liste (quelques minutes). Elles ne sont **pas installées** dans Windows : elles servent à comparer.
  - Dans les résultats, une police Google pas installée est marquée **« gratuite, pas installée (Google Fonts,
    licence) »**. **Télécharger et installer** : tous ses styles (gras, italique…) sont installés dans Windows pour
    ton compte (sans droits d'administrateur), utilisables tout de suite dans Pixane Photo et tes autres programmes.
    *Créer un texte* ou *Appliquer* avec une police Google l'installe d'abord.
  - **Mise à jour** : toute seule tous les 30 jours (nouvelles polices et polices modifiées téléchargées, polices
    retirées de Google Fonts effacées), ou tout de suite avec **Édition > Préférences > Fonctions installées >
    Mettre à jour les polices Google maintenant**.
  - Décochée : le dossier des polices Google est effacé (les polices installées restent installées).

### Baguette magique (W)
Un clic sur une couleur sélectionne la zone de couleur proche. Sans IA, instantané.
- **Régler en glissant** : après le clic, **garder le bouton appuyé et glisser à droite** (plus large) **ou à gauche**
  (plus étroit) : la sélection suit en direct. La tolérance trouvée reste pour le clic suivant.
- **Tolérance** (0 à 255, 32 par défaut) : écart de couleur accepté. Les couleurs sont comparées comme l'œil les
  voit, et la couleur de départ est prise sur 3 × 3 pixels : le bruit d'une photo gêne moins.
- **Contiguë** (coché) : seulement la zone touchée ; décoché : toutes les couleurs proches de l'image.
- **Bords doux** (coché) : bord progressif, sans escalier.
- **Boucher les trous** : ajoute ce qui est entièrement entouré (oiseaux dans un ciel, reflets sur un objet…).
- **Image visible** ou **Calque choisi** : sur quoi les couleurs sont comparées.
- Maj ajoute, Alt retire, comme le rectangle.

### Plage de couleurs (menu Sélection)
Sélectionne **tous les points d'une couleur**, dans toute l'image (la baguette ne prend que les voisins).
- **Clic** dans l'aperçu sur la couleur voulue ; **Maj+clic** : ajouter une couleur ; **Alt+clic** : en retirer une.
- **Tolérance** : jusqu'où les couleurs voisines sont prises (bords doux). Un rouge plus sombre (à l'ombre) compte
  comme du rouge.
- L'aperçu montre la **sélection** (blanc = pris) ou l'**image** ; la sélection est aussi montrée sur la photo.
- *Inverser* : tout sauf ces couleurs. **Sélection** : nouvelle, ajouter à la sélection ou en retirer.

### Améliorer le contour (Ctrl+Alt+R, menu Sélection)
Pour une sélection grossière autour de **cheveux, poils, feuillage ou bords flous** (par exemple après *Sélectionner
le sujet* ou un lasso rapide) : Pixane Photo recalcule le bord d'après les couleurs de la photo.
- **Rayon** : largeur de la bande recalculée autour du bord. Augmentez-le jusqu'à ce que les mèches apparaissent ;
  hors de cette bande, rien ne change.
- **Lissage** : adoucit un bord irrégulier. **Contraste du bord** : bord plus net. **Décaler le bord** : négatif le
  rentre (enlève un liseré de l'ancien fond), positif le sort.
- **Voir** : le sujet **sur noir**, **sur blanc**, le masque en **noir et blanc**, ou la sélection en rouge.
  Choisissez un fond qui contraste avec l'ancien fond pour bien juger les bords.
- **Résultat** : une **nouvelle sélection**, ou le **masque du calque choisi** (le fond est alors caché sans être
  effacé, voir *Masques de calque*).
Une seule étape dans Annuler. Le calcul prend une à trois secondes sur une grande photo.

### Couper, copier, coller, supprimer (menu Édition)
Ils agissent sur le **calque choisi** dans le panneau Calques :
- **Copier** (Ctrl+C) : copie ce qui est sélectionné (tout le calque s'il n'y a pas de sélection). La copie garde sa
  transparence ; on peut aussi la coller dans un autre logiciel.
- **Couper** (Ctrl+X) : copie, puis efface la zone sélectionnée (elle devient transparente).
- **Coller** (Ctrl+V) : met l'image copiée dans un **nouveau calque**, à **la même place** si elle vient de Pixane Photo,
  au centre si elle vient d'ailleurs (capture d'écran, autre logiciel…). Bougez-la ensuite avec l'outil Déplacer (V).
  Pour l'agrandir ou la réduire : **Ctrl+T** (voir *Transformer le calque*).
  - L'image garde toujours **sa taille réelle** (une image de 2048 px collée dans une photo de 1027 px reste en
    2048 px). Ce qui dépasse de la feuille est gardé dans le calque (cadre en pointillés autour, voir *Pixels hors de
    la feuille*) ; pour la réduire : **Ctrl+T**.
- **Glisser une image** (fichier depuis l'Explorateur, ou image depuis un navigateur) **sur la photo ouverte** : elle
  arrive dans un **nouveau calque**, à sa taille réelle, centrée là où vous lâchez. Un projet (.piximg, .psd, .ora),
  ou un fichier lâché hors de la photo, s'ouvre dans son propre onglet.
- **Supprimer la sélection** (Suppr) : efface la zone sélectionnée du calque (transparente).

Un calque **verrouillé** est protégé ; un **texte** coupé ou supprimé devient une image. Ctrl+Z annule tout.

Les autres outils : **Déplacer** (V) bouge le contenu du **calque choisi** (un texte déplacé reste modifiable ; ce qui
sort de la feuille est gardé, on peut le faire revenir ; refusé sur un calque verrouillé).
- **Flèches du clavier** (outil Déplacer) : poussent le calque choisi (ou le texte) de **1 px**, **10 px** avec Maj.
  Touche tenue : une seule étape dans Annuler. Elles marchent aussi juste après un clic dans le panneau Calques, et
  poussent le cadre de Transformer (Ctrl+T) en cours.
- Un **cadre à poignées** entoure ce qu'il y a sur le calque (ou seulement la partie sélectionnée, s'il y a une
  sélection) : **glisser au milieu** déplace ; **un coin** change la taille en gardant les proportions (Maj : libre) ;
  **un milieu de côté**, seulement la largeur ou la hauteur ; **juste à l'extérieur d'un coin** (curseur en croix),
  on tourne. Dès qu'une poignée est touchée, c'est le mode *Transformer* (comme Ctrl+T) : **Entrée** pour garder,
  **Échap** pour annuler.
- **Qualité** : le calque est redimensionné comme dans Photoshop, chaque pixel tenant compte
  de tous ceux qu'il remplace : une image réduite (même beaucoup, par exemple après un Upscale) reste propre, sans
  traits hachés ni grain. Sans rotation, le calque est posé sur des pixels entiers : un simple déplacement ne le
  floute jamais. Pendant le geste, l'aperçu est rapide ; **dès que la souris est lâchée**, le calque est en pleine
  qualité, même si l'on passe à autre chose sans valider. Même qualité pour *Image > Taille de l'image* et pour
  l'Upscale (calque ramené à sa taille, autres calques agrandis). Un simple déplacement ne change aucun pixel.
- **Aucune perte en réduisant puis en réagrandissant** (comme un *objet dynamique* de Photoshop, sans rien à faire) :
  chaque calque garde sa **meilleure version** (par exemple celle d'après un Upscale). Réduire, valider, faire autre
  chose, enregistrer, rouvrir le projet… puis réagrandir : Pixane Photo repart de cette meilleure version, l'image revient
  **telle qu'elle était, pixel pour pixel**, jusqu'à sa taille d'origine. Valable avec Déplacer (poignées), Ctrl+T,
  *Image > Taille de l'image*, pivoter, retourner, recadrer, aligner. Elle est enregistrée dans le projet **.piximg**
  (qui grossit un peu).
  - Si l'on **modifie les pixels** du calque (pinceau, gomme, IA, filtre…), la version modifiée devient la nouvelle
    référence (l'ancienne effacerait le travail).
  - Agrandir **au-delà** de la meilleure version rend l'image plus douce : ces pixels n'ont jamais existé (pour
    cela, l'Upscale).
  - Transformer seulement une **partie sélectionnée** du calque : la version actuelle devient la référence.
  - Dans Ctrl+T, les pourcentages sont comptés par rapport à la meilleure version (100 % = sa taille d'origine).
- La case **Afficher le cadre de transformation** (en haut) le cache s'il gêne. Pas de cadre sur un calque vide,
  verrouillé, caché ou de texte (un texte change de taille avec l'outil Texte).

La **Gomme de calque** (G) efface **pour de vrai** les
pixels du calque choisi (voir chapitre 6) ; elle est rangée avec le pinceau de couleur et le tampon.

**Conseil (texte, cursive, objet fin)** : couvrez bien chaque lettre, bords compris, avec un pinceau un peu plus large
que le trait ; n'oubliez pas l'ombre ou le contour s'il y en a. Pixane Photo élargit déjà un peu la zone (environ 16 px)
pour attraper les bords flous.

---

## 5. Les actions IA

Chaque action propose **plusieurs résultats** : on choisit le meilleur, comme dans Photoshop.
Le résultat gardé va **dans le calque choisi** (celui surligné dans le panneau Calques) : il en fait partie et le
suit quand on le déplace, le transforme ou change sa taille. Ctrl+Z revient en arrière. L'IA travaille toujours sur
l'image **telle qu'on la voit** (tous les calques visibles ensemble) : choisissez donc le calque de la photo avant
de lancer.
- Le résultat **ne sort pas de la sélection** : l'IA retouche un peu autour pour le raccord, mais Pixane Photo ne garde
  que l'intérieur, plus un fondu de quelques pixels, pour qu'aucun bord ne se voie.
- Les zones **transparentes** (fond transparent, logo détouré, texte seul) **restent transparentes** : aucun noir
  n'est ajouté, ni dans les propositions ni dans le résultat (Upscale aussi). Pour que l'IA voie bien ce qu'il y a
  dessus, Pixane Photo lui montre ces zones sur un fond uni qui contraste (sombre derrière un texte blanc, blanc derrière
  un logo foncé), puis retire ce fond du résultat, bords des lettres compris.
- Il va dans un **nouveau calque** (« Effacer 1 », « Remplir 2 »…) quand le calque choisi ne peut pas le recevoir
  (texte, groupe, calque de réglage, calque caché ou verrouillé), ou quand il n'y a pas de sélection et que
  l'image a plusieurs calques (sinon les autres y seraient recopiés). Un message le dit en bas.
- **IA > Mettre les résultats dans un nouveau calque** (à cocher) : chaque résultat va dans un nouveau calque,
  comme avant ; pratique pour comparer avec l'original en masquant le calque.
- **Ce que l'IA regarde** : l'**image visible** (tous les calques ensemble, comme Photoshop), pour que le résultat
  aille avec ce qu'on voit autour. Le résultat, lui, va **seulement** dans le calque choisi (ou un nouveau calque).
  Un calque caché n'est pas vu par l'IA : pour qu'elle ne tienne pas compte d'un calque, cachez-le avant de lancer.
- **Trous transparents** (par exemple les lettres d'un texte coupé dans une pochette) : avec **Effacer** et
  **Remplir**, les trous qui sont dans la sélection et entourés par l'image sont **remplis**, opaques, avec ce qui
  les entoure. Le transparent qui continue hors de la sélection (autour d'une photo détourée, au-delà du bord
  d'une pochette) reste transparent.

### Fenêtre de choix du résultat
- Cliquez sur une vignette pour la voir en grand.
- **Zoomer pour voir les détails** : **molette** (le zoom se fait sous la souris), **glisser** pour se déplacer,
  **double-clic** pour passer de l'image entière à la taille réelle (100 %) et revenir. Boutons **Ajuster** et
  **100 %** en bas ; touches **+** / **-**, **0** (ajuster) et **1** (100 %). Le zoom est affiché en bas à gauche.
- Le zoom et l'endroit regardé **restent les mêmes** quand on passe d'une vignette à l'autre ou qu'on maintient
  « voir l'original » : on compare exactement le même détail (même après un Upscale, où l'original est plus petit).
- **Maintenir pour voir l'original** : tant que le bouton est enfoncé, la photo d'avant s'affiche.
- **Autres propositions** : relance l'IA pour de nouvelles versions (elles s'ajoutent aux précédentes). Elles
  repartent toujours de **l'image d'origine** : la vignette choisie ne sert pas de point de départ.
- **Partir de celle-ci** (Effacer, Remplir, Agrandir) : quand une proposition est **presque bonne**, choisissez-la
  puis cliquez ici. L'IA repart de cette proposition, sur la même zone, et ne la refait qu'en partie : elle garde
  la forme générale et change les détails. La glissière **Proche ↔ Libre** règle combien elle peut changer
  (Proche : petites retouches, presque la même image ; Libre : la même idée, retravaillée davantage ; au milieu par
  défaut, puis votre dernier réglage). Les variantes s'ajoutent aux vignettes (« Variante de 2 »…) : on peut
  toujours revenir à une proposition d'avant, ou repartir d'une variante. Même durée qu'une proposition (environ
  1 min chacune). Un gros défaut de forme (objet mal placé) ne se corrige qu'en poussant vers **Libre**.
- **Garder ce résultat** : applique la version choisie (annulable par Ctrl+Z). La sélection (pinceau, lasso,
  rectangle) disparaît alors ; Ctrl+Z la fait revenir avec la photo d'avant.

### Pendant le calcul
Une fenêtre affiche l'étape en cours, une **barre de progression**, le temps écoulé et le **temps restant estimé**.
**Annuler** arrête le calcul.

### Effacer (Maj+E)
Enlève ce qui est peint en rouge et reconstruit le fond.
- Deux méthodes combinées : **LaMa** (rapide, efface proprement) puis une finition par **Flux Fill** (plus réaliste).
- Résultats proposés : 2 versions Flux + la version « LaMa seul ».
- Marche aussi sur une sélection fine (lettres prises à la baguette magique) : tout pixel touché par la sélection est
  effacé, même sur un bord adouci.
- Durée indicative : environ 2 minutes (carte graphique 8 Go).
- **Analyse avant d'effacer** : Pixane Photo regarde autour de la zone peinte. S'il trouve **l'ombre de l'objet**
  (montrée en violet : sinon une tache sombre resterait) ou un **bord de l'objet oublié** (en orange : l'IA le
  redessinerait), il les propose, cochés ; décochez ce que vous ne voulez pas, puis **Effacer**. La zone agrandie
  est une étape d'Annuler. « Ne plus analyser » : réglable dans Édition > Préférences > Intelligence artificielle.

### Remplir (Maj+R)
Redessine la zone peinte en rouge.
- **Sans texte** (recommandé) : l'IA invente ce qui va bien avec le reste de la photo. Elle part du fond nettoyé
  par LaMa : même près d'un titre, elle ne réinvente pas de lettres.
- **Avec un texte** (champ « Texte facultatif », en anglais de préférence) : décrit ce qu'on veut voir à la place.
- 3 propositions, environ 1 minute chacune.

### Modifier avec une consigne (Maj+M)
Change la zone sélectionnée d'après ce que tu écris, en gardant le style de l'image : « remplace le texte « brûler
le feu » par « Flamme » », « change la couleur du pull en rouge », « remplace la tasse par un verre », « enlève les
lunettes »… (modèle **Flux Kontext**, à ajouter dans Installer le moteur IA).
- Sélectionne la zone (pinceau, lasso, sélection d'objet…), puis **Modifier** (carte du panneau IA ou menu IA).
  Sans sélection : toute l'image.
- Écris la consigne. **Exemples** : choisis-en un, il est inséré ; remplace les « … ».
- **Entre guillemets** (« … » ou "…") : un texte à écrire tel quel (il n'est jamais traduit).
- **Important : l'IA ne comprend bien que l'anglais.** Une consigne en français, en polonais ou dans une autre
  langue, envoyée sans traduction, marche mal : l'IA devine, et le résultat est souvent au hasard (rien ne change,
  le texte est recopié au lieu d'être remplacé, ou remplacé deux fois…). Deux solutions, au choix :
  - installer le **traducteur** (français → anglais, 290 Mo, sur ton PC, rien n'est envoyé sur Internet) : tu
    écris en français, **Traduire** montre la phrase anglaise, que tu peux corriger ;
  - ou écrire la consigne **directement en anglais** (seule solution pour les autres langues pour l'instant).

  Si ta consigne n'a pas l'air d'être en anglais et n'est pas traduite, Pixane Photo te prévient au clic sur Modifier ;
  tu choisis : **Installer le traducteur…**, **Corriger**, ou **Envoyer quand même**.
- Écris dans les guillemets le texte **exactement comme sur l'image** (accents, majuscules) : « Brûler le Feu »,
  pas « bruler le feu ».
- Le traducteur s'installe par le
  **programme d'installation de Pixane Photo** (page « Traducteur des consignes »), par le bouton « Installer le
  traducteur… », ou par sa case dans **IA > Installer le moteur IA** (fenêtre « Installer »
  ou « Compléter le moteur IA » si ComfyUI était déjà là) : cochée tant qu'il n'est pas installé, grisée ensuite.
  **Dossier du traducteur… Changer…** : tu choisis où le ranger (par défaut,
  `%LOCALAPPDATA%\Pixane\traducteur`). Pas dans le dossier où Pixane Photo est
  installé (D:\Programmes\Pixane\Pixane Photo…) : il est remplacé à chaque mise à jour, Pixane Photo le refuse.
- Le traducteur démarre en arrière-plan dès l'ouverture de la fenêtre (une dizaine de secondes, le temps que tu écrives), puis il reste prêt jusqu'à la fermeture de Pixane Photo : chaque traduction est alors presque immédiate.
- L'IA travaille sur un morceau autour de la sélection (plus de détail qu'avec toute l'image) ; le résultat n'est
  gardé que dans la sélection et là où il change vraiment : le reste garde ses pixels d'origine.
- **Calque avec de la transparence** (texte, logo sans fond) : l'IA voit ce calque seul, et le résultat garde un
  fond transparent. Sinon, elle voit l'image visible et le résultat est opaque.
- Propositions : 1 à 4, environ 2 à 3 minutes chacune sur une RTX 3060 Ti (la fenêtre affiche la durée mesurée sur ton PC). Les écritures très travaillées sont bien imitées, mais un
  peu moins fines que l'original ; les accents et les longs textes sont parfois mal écrits : demande d'autres
  propositions.

### Agrandir l'image (Maj+A)
Étend la photo au-delà de ses bords : l'IA invente la suite du décor.

Deux cadres apparaissent sur la photo :

| Cadre | Aspect | Rôle |
|---|---|---|
| **Cadre d'agrandissement** | pointillés blancs, **poignées carrées** couleur d'accent | Tirez-le **vers l'extérieur** : la zone ajoutée s'affiche en damier gris |
| **Cadre « bord abîmé »** | pointillés **rouges**, **poignées rondes** rouges | Tirez-le **vers l'intérieur** : la bande hachurée rouge est un bord abîmé (liseré, trait, flou, coin déchiré…) qui sera **jeté puis redessiné** par l'IA |

- Quand les deux cadres sont l'un sur l'autre (au départ), le **sens du geste** décide : vers l'extérieur = agrandir,
  vers l'intérieur = bord abîmé.
- **Maj** en tirant : le côté opposé bouge pareil (agrandir à gauche et à droite en même temps, par exemple).
- **Détection automatique** : à l'ouverture, Pixane Photo repère les bords abîmés et place déjà le cadre rouge dessus :
  liserés clairs ou foncés, **cadre** ou bordure d'une autre couleur, **bord flou**, bande unie (barre de miniature,
  bord d'une capture d'écran), jusqu'à 4 % du côté. Vous pouvez l'ajuster ou le remettre à 0.
- **Barre en haut de la photo** :
  - ligne **Agrandir** : ce qui est ajouté de chaque côté, en % de la photo (0 à 200 %) ;
  - ligne **Bord abîmé** : la bande à refaire de chaque côté, en pixels ;
  - **taille finale** de l'image ;
  - **Lancer** (ou Entrée) / **Annuler** (ou Échap) ;
  - ligne **Description** (facultative) : ce que l'IA doit ajouter, par exemple « foule, fumée, ciel nuageux ».
    Vide, l'IA devine d'après l'image et peut inventer des objets ou des personnages hors sujet ; une description
    la guide (sans tout empêcher : « foule » peut amener un personnage au premier plan). En français ou en anglais
    (traduite sur ce PC si le traducteur est installé). **Décrire (IA)** : l'IA regarde la photo et écrit elle-même
    la description (en anglais : genre d'image, style, scène, fond, lumière, couleurs), que tu peux corriger avant
    de lancer ; quelques secondes. Ce bouton demande le modèle **Qwen3.5 2B** (4,2 Go, Apache-2.0), facultatif :
    case dans l'installateur et dans *IA > Installer le moteur IA* ; sans lui, le bouton propose de l'installer.
  Les cases et les cadres se suivent : modifier l'un met l'autre à jour.
- **Taille finale** = photo d'origine + agrandissement. Le bord abîmé ne réduit pas l'image : il est remplacé.
- **Image entourée de vide** (ex. une photo carrée collée dans une image plus large, avec du transparent à gauche et
  à droite, ou en haut et en bas) : le cadre part de **la photo elle-même** (le pointillé montre le bord de
  l'image). **Tu choisis la taille** : tire le cadre dans le vide, juste un peu ou jusqu'au bord de l'image (il s'y
  arrête tout seul, comme un aimant), ou au-delà pour agrandir l'image. L'IA prolonge la photo dans le cadre ; le
  reste du vide reste transparent. Le cadre part de la photo **du calque choisi** : ce qu'il y a dans les autres
  calques ne compte pas (choisis donc le calque de la photo collée). Les traits fins isolés ne comptent pas non plus. Les **ronds rouges** (bord abîmé) marchent aussi : tire-les vers l'intérieur pour faire redessiner un bord douteux de la photo. Le bord à demi transparent d'une photo collée puis réduite est toujours redessiné (pas de liseré clair à la jonction). Les trous transparents à l'intérieur
  de la photo restent transparents.
- Le raccord entre la photo et l'ajout est fait par Pixane Photo : la photo d'origine est gardée **au pixel près**, avec un
  fondu progressif et un accord des couleurs, pour qu'aucune ligne ne soit visible. Dans les **fonds unis** (ciel,
  mur, fond sombre), l'ajout est remis au niveau de la photo jusqu'au bord : pas de partie plus claire ni de bandes
  (« effet fantôme »), et les légers **tourbillons** que l'IA laisse parfois dans ces fonds sont lissés (le grain
  fin et ce qui est vraiment dessiné, comme une étoile, sont gardés). Ce raccord est refait après *Pleine définition*.
- 3 propositions, environ 1 minute chacune.
- **Fond prolongé** : quand les bords à agrandir sont **unis** (fond de pochette, ciel lisse, dégradé), une
  proposition de plus, faite **sans IA**, s'ajoute aux autres : Pixane Photo continue lui-même le fond de la photo,
  ligne par ligne, avec le même grain. Aucun raccord ni tourbillon visible, et c'est instantané. Elle n'apparaît pas
  si un objet touche le bord (il serait étiré). *Partir de celle-ci* et *Pleine définition* ne la concernent pas
  (elle est déjà à la vraie taille).
- **Pleine définition** (case dans la barre, cochée par défaut) : l'IA invente l'ajout sur une image réduite à
  environ 1 million de pixels, puis l'ajout est agrandi à la taille de la photo ; sur une grande photo, il serait
  donc plus flou que le reste. Avec la case cochée, une fois la proposition choisie, l'ajout est **redessiné à la
  vraie taille**, par morceaux de 1024 px, en gardant sa forme : il devient aussi net et détaillé que la photo, et
  reçoit le **même grain**. Plus long : environ 30 s à 1 min par morceau (la fenêtre d'attente montre « Morceau 2
  sur 6 » et le temps restant). **Annuler** pendant ce travail garde la proposition telle quelle. Sans effet sur une
  petite photo (déjà travaillée à sa vraie taille).
- **Conseils** pour un ajout réaliste : agrandir par petites étapes (20 à 30 % à la fois) plutôt que 100 % d'un
  coup ; comparer les propositions (« Autres propositions ») ; marquer en bord abîmé un liseré ou un cadre.
- **Calques** : tous les calques sont décalés sur la nouvelle toile ; l'ajout et le bord refait vont dans le
  calque choisi (en général la photo), ou dans un calque « Agrandir 1 » avec l'option *nouveau calque*.
- Si la photo contient du texte, l'IA invente parfois des lettres sans sens dans l'ajout : utilisez
  « Autres propositions ».

### Upscale (Maj+U)
Augmente la définition (nombre de pixels) de la photo.

| Réglage | Valeurs | Effet |
|---|---|---|
| **Net** | par défaut | RealESRGAN agrandit, puis **Flux redessine les détails** morceau par morceau. Plus lent (environ 20 à 30 s par morceau de 1024 px) mais net |
| **Rapide** | | RealESRGAN seul : quelques secondes, mais peut donner un aspect lissé (« plastique ») |
| **Facteur** | ×1,5 à ×4 (×2 par défaut) | Combien de fois plus grand |
| **Force** (mode Net) | 0,10 à 0,60 (0,35 par défaut) | Liberté laissée à Flux : bas = fidèle à l'original, haut = plus de détails inventés |

**Comment régler la force** (mode Net) : RealESRGAN agrandit d'abord (fidèle mais un peu lisse), puis Flux repasse
dessus pour redessiner les détails ; la force règle l'importance de ce 2e passage.
- **0,10 à 0,25** (léger) : très fidèle, peu de détails ajoutés. Pour les **visages, textes, logos**, qui doivent
  rester exacts.
- **0,35** (par défaut) : bon équilibre, conseillé dans la plupart des cas.
- **0,45 à 0,60** (fort) : beaucoup de détails, mais l'IA en **invente** (un visage ou un texte peut changer un
  peu). Pour les **paysages, la végétation, les tissus**, qui manquent de matière.

La fenêtre le rappelle sous la case Force (bulle d'aide plus complète au survol).

**Rien d'inventé dans les aplats** (mode Net) : sans consigne, Flux a tendance à « voir » des choses dans une zone
unie (fond de pochette, ciel lisse) et y ajoute taches, textes fantômes ou dessins. Pixane Photo ne garde donc son travail
que là où l'image d'origine a vraiment du détail (traits, texte, matière d'une photo) ; les aplats sont repris de
l'image d'origine simplement agrandie, et les couleurs restent celles de l'origine. Rien à régler : c'est automatique.

**Image graphique** (pochette, logo, affiche : surtout des aplats) : Pixane Photo le reconnaît et propose d'office la force
**0,25**, car sur du texte Flux peut changer une lettre (vu en essai : « fig. 5 » devenu « ftp. 5 »). Pour un graphisme
très simple, le mode **Rapide** suffit souvent.

La fenêtre indique la taille finale avant de lancer ; pendant le calcul, la progression compte les morceaux.

**Que faut-il traiter ?** (en haut de la fenêtre ; le dernier choix est retenu)
- **Toute l'image** : l'image entière et tous ses calques grandissent (ex. 1000 × 1000 -> 2000 × 2000). Une photo
  d'un seul calque est simplement remplacée par le résultat. Avec plusieurs calques (ou l'option *nouveau calque*),
  tous les calques sont agrandis (lissage simple) et le résultat de l'IA arrive, complet, sur un calque « Upscale 1 »
  au-dessus.
- **Le calque choisi, plus net** : il garde sa taille et sa place, l'IA le redessine plus net (ex. une petite photo
  collée puis agrandie avec Ctrl+T, devenue floue). L'image entière ne change pas.
- **Le calque choisi, agrandi** : seul ce calque grandit (ex. photo collée de 400 × 400 -> 800 × 800, au même
  endroit) ; **l'image entière garde sa taille** (ex. 1000 × 1000) et les autres calques ne bougent pas. Ce qui
  dépasse de l'image est caché mais gardé (on le ramène en déplaçant le calque).

Pour le calque choisi : seul son contenu est envoyé à l'IA, et autour, le calque reste transparent. Avec l'option
*nouveau calque*, le résultat arrive dans un calque au-dessus et l'original reste. Un calque verrouillé est refusé.

### Sujet et arrière-plan
Modèle **BiRefNet** (MIT, 444 Mo, installé avec le moteur IA ; s'il manque, menu **IA > Installer le moteur IA…**
l'ajoute). Quelques secondes.
- **Supprimer l'arrière-plan** (Maj+B, panneau IA ou menu IA) : le fond du **calque choisi** devient transparent,
  le sujet reste. Enregistrez en PNG, PSD ou .piximg pour garder la transparence. Ctrl+Z annule.
- **Sélectionner le sujet** (Ctrl+Alt+S, menu Sélection) : sélectionne le sujet sans rien effacer, par exemple
  pour le régler (Ctrl+U), ou *Inverser* (Ctrl+Maj+I) pour travailler le fond.

### Créer une image d'après un texte (menu IA)
Décrivez l'image (sujet, couleurs, lumière, style) : **Flux Schnell** la crée, environ **30 secondes** par
proposition. Exemples de consignes dans la liste (fond abstrait, paysage, texture, illustration, portrait) ; comme
pour *Modifier avec une consigne*, une consigne en français peut être traduite en anglais sur votre PC.
- **Résultat** : *Nouvelle image* (formats carré pour une pochette ou les réseaux sociaux, 4:3, 3:4, 16:9, 9:16) ou
  *Nouveau calque dans l'image ouverte*, à sa taille (par exemple un fond derrière un détourage).
- Marche aussi **sans image ouverte** : une nouvelle image est créée.
- Dans la fenêtre de choix, **Partir de celle-ci** donne des variantes de la proposition choisie.
- L'IA écrit mal les textes : ajoutez-les ensuite avec l'outil Texte.
- Modèle Flux Schnell (Apache-2.0), installé avec le moteur IA (case *Flux Schnell*).

### Remplacer un texte (menu IA)
Pour changer un mot d'une pochette en gardant le même style.
1. Entourez le texte avec l'outil **Sélection de texte** (Y).
2. **IA > Remplacer un texte…** : Windows lit les lettres, et Pixane Photo cherche aussitôt la police la plus
   proche (vérifiez les lettres lues, corrigez-les si besoin).
3. Tapez le **nouveau texte** (« / » pour passer à la ligne), choisissez la police dans la liste si la première ne
   convient pas, puis **Effacer et remplacer**.
4. L'IA efface l'ancien texte (zone un peu élargie pour que le bord des lettres parte aussi ; fenêtre habituelle
   des propositions), puis le nouveau texte est posé **à la même place et à la même hauteur**, dans sa couleur, en
   **calque Texte modifiable**.

### Supprimer les personnes (menu IA)
L'IA (**SAM 3.1**) trouve **chaque personne** de la photo. Une fenêtre les montre : les personnes **cochées** (en
rouge) seront effacées ; **cliquez sur une personne** dans l'image (ou sur sa case) pour la cocher ou la décocher.
Au départ, tout est coché sauf le **sujet principal** (la personne nettement plus grande que les autres).
- **Effacer les personnes cochées** : elles sont sélectionnées (avec une petite marge pour les ombres et les
  cheveux), puis **Effacer** reconstruit le fond derrière elles (fenêtre de choix du résultat habituelle).
- **Seulement sélectionner** : pour compléter la sélection, par exemple une personne oubliée par l'IA (outil
  **Sélection d'objet**, Maj + clic), avant de lancer **IA > Effacer**.

### Retouche portrait (menu IA)
L'IA (**SAM 3.1**) trouve le visage, le cou, les yeux, les sourcils, les lèvres et les dents (quelques secondes),
puis une fenêtre de réglage s'ouvre, avec **aperçu en direct** sur la photo :
- **Lisser la peau** : atténue boutons, rougeurs et petites rides ; les contours (nez, yeux), les cils et les mèches
  de cheveux restent nets.
- **Garder le grain de la peau** : remet le grain fin, pour éviter l'effet « plastique ».
- **Éclaircir les yeux** : plus d'éclat et de netteté dans les yeux.
- **Blanchir les dents** : moins jaunes, un peu plus claires.
S'applique au calque choisi (dans la sélection s'il y en a une) ; tous les visages trouvés sont retouchés.

### Réduire le bruit, Netteté, Restaurer une vieille photo (menu IA)
Ces trois actions travaillent sur l'image visible ; s'il y a une **sélection**, le résultat ne change que
l'intérieur. Comme les autres actions IA, le résultat va dans le calque choisi (Ctrl+Z annule).
- **Réduire le bruit (IA)** : enlève le grain (photo de nuit, téléphone) et les défauts de compression JPEG en
  gardant les détails. Modèle **SCUNet** (Apache-2.0, 72 Mo). Quelques secondes.
- **Netteté (IA)** : rend un flou léger plus net (contours, textes, détails) : la photo est agrandie ×4 par
  RealESRGAN puis ramenée à sa taille. Elle lisse aussi le grain : sur une photo très texturée, le filtre
  *Netteté* (menu Filtres) peut être préférable. 15 à 20 secondes.
- **Restaurer une vieille photo…** : l'IA **redessine** toute la photo en enlevant rayures, taches, poussières,
  plis et grain, et en rendant le contraste et les visages plus nets. La photo garde **exactement sa taille et ses
  proportions**.
  - **Restaurer** garde les **couleurs d'origine** : une photo noir et blanc ou sépia le reste, une photo en couleur
    garde ses couleurs. L'IA ne fournit que la lumière et les détails ; Pixane Photo remet ensuite la teinte de
    l'original.
  - **Restaurer et coloriser** met en plus des couleurs naturelles à une photo en noir et blanc ou sépia.
  - Le résultat arrive dans un calque **« Restaurée »** (ou **« Restaurée et colorisée »**), et *Enregistrer sous*
    comme *Exporter pour le web* proposent un nom qui le dit : `photo_restauree.jpg`, `photo_restauree_colorisee.jpg`
    (sans accents, pour que le nom passe partout : sites web, autres logiciels, pièces jointes).
   Deux propositions, environ **2 minutes chacune** ;
  *Autres propositions* en redemande. L'IA peut changer de petits détails (traits d'un visage, lettres) :
  comparez bien avec l'original (œil du calque). Modèle **Flux Kontext dev** (11,9 Go, licence FLUX.1 [dev], usage
  **non commercial**), facultatif : case *Flux Kontext* dans **IA > Installer le moteur IA…**.

### Ciel, couleurs, lumière, profondeur (IA)
- **Sélection > Sélectionner le ciel (IA)** : l'IA (SAM 3.1) trouve le ciel et le sélectionne, bord un peu élargi et
  adouci pour que la ligne d'horizon se raccorde. Pixane Photo affine ensuite le bord d'après les couleurs : le ciel vu
  entre les branches d'un arbre nu est sélectionné aussi (et, avec *Remplacer le ciel*, les branches gardent leur
  couleur). Ensuite, tous les outils marchent sur cette sélection (réglages,
  Remplir…). Quelques secondes.
- **IA > Remplacer le ciel…** : choisissez le nouveau ciel sur des **vignettes d'exemple** (ciel bleu avec quelques nuages, grands nuages, coucher
  de soleil, ciel d'orage, nuit étoilée, aube). Pixane Photo sélectionne le ciel (nuages compris), Flux Kontext redessine
  la photo avec ce ciel, et **seul le ciel** en est gardé : le reste garde ses pixels d'origine. Deux propositions,
  environ 2 minutes chacune. Au bord d'un toit ou d'un arbre, l'IA peut laisser un petit reste décalé : choisissez la
  meilleure proposition, ou retouchez (tampon, Effacer). Le ciel reste sélectionné : pour l'harmoniser, un réglage de
  couleur sur le reste de la photo (Sélection > Inverser) aide souvent.
- **IA > Coloriser** : met des couleurs naturelles à une photo en noir et blanc (sans la restaurer) ; avec une
  sélection, seulement dedans. Flux Kontext, deux propositions, environ 2 minutes chacune.
- **IA > Changer la lumière…** : lumière dorée de fin de journée, lumière douce de studio, lumière marquée venant
  de la gauche ou de la droite, contre-jour, nuit éclairée par des lampadaires, néons colorés, temps couvert ; une
  vignette d'exemple pour chacune (double-clic : choisir et lancer). Avec une sélection, seulement dedans. Flux
  Kontext redessine la photo avec cette lumière, en gardant les personnes et les objets. Comparez bien : l'IA peut
  changer de petits détails.
- **Filtres > Flou selon la profondeur (IA)…** : comme le flou d'arrière-plan d'un appareil photo. L'IA calcule la
  distance de chaque point (quelques secondes) ; une fenêtre montre cette carte (clair = proche, foncé = loin) :
  **cliquez sur ce qui doit rester net** (au départ : ce qui est le plus proche). **Flou** règle la force, **Zone
  nette** la profondeur gardée nette autour du point. **Garder net tout le sujet** (cochée au départ) : le
  détourage rattrape ce que la carte met à tort au loin, par exemple une veste grise devant un mur gris. **Ne pas
  flouter ce qui est plus proche que le point net** : utile seulement quand vous cliquez sur quelque chose au loin
  (sinon rien n'est devant, la case ne change rien). **Si l'IA se trompe** : choisissez *Pinceau : garder net* ou *Pinceau : rendre flou* et peignez sur la carte
  (vert = net, rouge = flou ; *Taille du pinceau* ; *Effacer les coups de pinceau*). Aperçu en direct sur la photo ; s'applique au calque choisi (dans la sélection s'il y en a une). Modèle
  **Depth Anything 3 Small** (137 Mo, Apache-2.0), facultatif : case *Flou selon la profondeur* à l'installation de
  Pixane Photo, ou dans **IA > Installer le moteur IA…**.

---

## 6. Les calques

Une image peut avoir plusieurs **calques**, empilés comme des feuilles transparentes : celui du haut passe
devant. Une photo ouverte a un seul calque, « Arrière-plan ».

### Pixels hors de la feuille

Comme dans Photoshop, un calque peut être **plus grand que la feuille** : une image collée en taille réelle, un
élément poussé au bord avec Déplacer ou agrandi avec Ctrl+T. Ce qui dépasse **ne se voit pas, mais n'est jamais
coupé** : on peut le ramener, le réduire, le réafficher.
- **Déplacer**, **Transformer (Ctrl+T)**, le cadre à poignées, **Taille de la zone de travail**, **Taille de
  l'image**, les **rotations** et **miroirs** travaillent sur le calque entier. Le cadre à poignées montre aussi
  ce qui dépasse.
- Le **pinceau**, la **gomme**, les **filtres** et l'IA ne changent que ce qui est dans la feuille ; la partie
  dehors reste telle quelle.
- **Image > Tout faire apparaître** : la feuille s'agrandit juste assez pour montrer tout ce qui dépasse
  (Ctrl+Z pour revenir).
- Enregistré en **.piximg**, **PSD** et **ORA** (Photoshop, Krita et GIMP le relisent). JPEG, PNG… n'enregistrent
  que la feuille. **Recadrer** et **Aplatir** suppriment ce qui dépasse.

### Le panneau Calques
| Élément | Rôle |
|---|---|
| **Liste** | Le calque du haut est en haut. Cliquez sur un calque pour le choisir (il est surligné) |
| **Œil** | Afficher / masquer le calque (pratique pour comparer avant / après une retouche IA) |
| **Vignette** | Aperçu du calque, à la forme de l'image ; le damier gris montre les parties transparentes |
| **Nom** | Double-clic sur le nom pour renommer ; double-clic ailleurs sur la ligne : style du calque |
| **Opacité** | Transparence du calque choisi, de 0 % (invisible) à 100 % ; affichée sous le nom quand < 100 % |
| **Cadenas** (à droite du nom) | Verrouille le calque pour le protéger : il ne peut plus être gommé, supprimé ni fusionné, et son opacité est bloquée ; Aplatir est désactivé tant qu'un calque est verrouillé. Les actions IA sont refusées avec un message : Effacer et Remplir si le calque choisi est verrouillé, Agrandir et Upscale de toute l'image si un calque quelconque est verrouillé (ils changent la taille de tous les calques), Upscale du calque si ce calque est verrouillé. On peut toujours le masquer, le renommer et le monter / descendre. Le cadenas ouvert est discret, le cadenas fermé bien visible. Le verrou est gardé dans les fichiers .piximg et .ora |
| **Glisser un calque** | Changer sa place dans la pile à la souris : prenez la ligne (sur le nom) et glissez-la vers le haut ou le bas ; un **trait orange** montre où il ira. Lâché juste sous un calque d'un groupe ouvert, il entre dans le groupe ; un groupe bouge avec ses calques. Une seule étape dans Annuler |
| **Mode de fusion** (liste en haut du panneau) | Comment le calque se mélange à ce qui est dessous (voir plus bas) |
| **Vignette du masque** (à droite de la vignette) | Le masque du calque, s'il en a un. Clic : on peint le masque (cadre orange) ; clic sur la vignette du calque : on repeint les pixels. Maj+clic : désactiver / réactiver le masque (barré en rouge) |
| **Ctrl+clic** sur un calque | L'ajoute aux calques choisis (ou l'en retire) : on peut en choisir plusieurs, ils sont surlignés en bleu |
| **Maj+clic** sur un calque | Choisit tous les calques entre le calque actif et celui-ci |
| **Clic droit** | Menu du calque : renommer, dupliquer, supprimer, fusionner, aplatir, grouper, style, masque, afficher / masquer, verrouiller, nouveau calque. Avec plusieurs calques choisis : **Fusionner les calques choisis**, les supprimer, les afficher ou les masquer |

### Les boutons (de gauche à droite)
| Bouton | Action |
|---|---|
| **Nouveau calque** | Ajoute un calque vide au-dessus du calque choisi (Ctrl+Maj+N) |
| **Nouveau groupe** | Crée un dossier de calques (Ctrl+G met les calques choisis dans un groupe) |
| **Masque** | Ajoute un masque au calque choisi (d'après la sélection s'il y en a une) |
| **Réglage** | Menu : nouveau calque de réglage (Niveaux, Courbes, Balance, Noir et blanc, Vibrance, Réglages de l'image) |
| **Dupliquer** | Copie le calque choisi (Ctrl+J) ; un groupe est copié avec ses calques |
| **fx** | Style du calque (voir plus bas) |
| **Monter / Descendre** | Change la place du calque dans la pile ; entre dans un groupe ouvert, en sort au bord ; un groupe bouge avec ses calques |
| **Fusionner** (Ctrl+E) | Plusieurs calques choisis : les réunit en un seul (à la place du plus haut, avec son nom). Un seul : le réunit avec celui du dessous (opacité, masque et mode appliqués). Refusé pour un calque verrouillé, un groupe ou un calque de réglage |
| **Aplatir** | Réunit tous les calques visibles en un seul « Arrière-plan » |
| **Supprimer** | Supprime le calque choisi, ou tous les calques choisis (un groupe : avec ses calques) |

### Modes de fusion
Les mêmes que Photoshop, rangés par familles : **Normal** ; **Obscurcir**, **Produit**, **Densité couleur +** (ce qui
assombrit) ; **Éclaircir**, **Superposition**, **Densité couleur −**, **Densité linéaire − (Ajout)** (ce qui éclaircit) ;
**Incrustation**, **Lumière tamisée**, **Lumière crue** (contraste) ; **Différence**, **Exclusion** ; **Teinte**,
**Saturation**, **Couleur**, **Luminosité**. Exemples : *Produit* pour une ombre ou une texture sombre, *Superposition*
pour une lueur, *Incrustation* pour une texture de papier, *Couleur* pour teinter. Gardés dans les fichiers .piximg,
.ora et .psd.

### Masques de calque
Un masque **cache une partie du calque sans l'effacer** : noir = caché, blanc = visible, gris = à moitié. On peut
toujours revenir en arrière en repeignant en blanc.
- **Calque > Masque de calque** : *Ajouter : tout visible*, *Ajouter : montrer la sélection*, *Ajouter : cacher la
  sélection* ; *Peindre le masque / les pixels* (Ctrl+\) ; *Désactiver le masque* ; *Inverser le masque* ; *Masque
  vers sélection* ; *Appliquer le masque* (mis dans les pixels) ; *Supprimer le masque*.
- **Peindre le masque** : choisissez-le (clic sur sa vignette), puis le **pinceau de couleur** (en noir, il cache ;
  en blanc, il montre ; en gris, à moitié), la **gomme de calque** (cache), le **dégradé** (fondu progressif, par
  exemple pour fondre deux photos) ou le pot de peinture. Les réglages et filtres s'appliquent aussi au masque.
- Exemple : *Supprimer l'arrière-plan* puis un masque plutôt qu'une gomme : un bout de sujet coupé par erreur se
  récupère en peignant en blanc.
- Les masques suivent le calque (Ctrl+T, recadrer, taille de l'image, Upscale) et sont gardés en .piximg, .ora et .psd.

### Groupes
Un **groupe** range plusieurs calques dans un dossier : on peut les masquer, les déplacer, les dupliquer ou les
supprimer d'un coup, et donner au groupe une opacité, un mode de fusion et un masque qui valent pour tout son contenu.
- **Ctrl+G** (Calque > Grouper les calques) : met les calques choisis (Ctrl+clic ou Maj+clic dans le panneau) dans
  un même nouveau groupe, placé à l'endroit du plus haut ; ils gardent leur ordre. Un groupe choisi y entre avec tout
  son contenu. Avec un seul calque choisi : ce calque seul. **Ctrl+Maj+G** : défait le groupe (les calques restent).
- **Déplacer un groupe** : choisissez le groupe, puis l'outil Déplacer (V), à la souris ou aux flèches : tous ses
  calques bougent ensemble (une seule étape d'Annuler). De même pour plusieurs calques choisis (Ctrl+clic).
- **Calque qui dépasse de l'image** (texte, image, forme…) : quand il est choisi, un **cadre en pointillés** montre
  où il est, avec n'importe quel outil.
- **Calque > Pixelliser** (aussi au clic droit) : *Texte*, *Forme, pinceau, remplissage*, *Style du calque* (les
  effets deviennent des pixels), *Objet dynamique* (sa meilleure version est oubliée) ou *Calque entier* (tout à la
  fois). Le calque devient une image ordinaire ; Annuler revient en arrière.
- La flèche à gauche du groupe le **replie** ou le **déplie**. Les calques d'un groupe sont décalés vers la droite.
- Monter / Descendre fait entrer un calque dans un groupe ouvert, ou l'en fait sortir.

### Barre d'accès rapide
Une 2e ligne de boutons sous la barre du haut, toujours là quel que soit l'outil : Transformer (Ctrl+T), pivoter
l'image de 90° à gauche / à droite, retourner l'image entière, Grouper / Dégrouper, retourner le calque (symétries),
Aligner (6) et Répartir (2). La bulle de chaque bouton dit ce qu'il fait. **Affichage > Barre d'accès rapide** la
masque ou la remet (masquée : Aligner et Répartir reviennent dans la barre de l'outil Déplacer).

### Aligner, répartir, retourner les calques
Dans le menu **Calque** et dans la **barre d'accès rapide**. Pixane Photo prend ce que les calques contiennent vraiment (sans le vide transparent autour). Un groupe choisi
bouge comme un seul bloc ; les calques verrouillés ne bougent pas ; un seul Ctrl+Z annule.
- **Aligner** : bords gauches, centres horizontaux, bords droits, bords hauts, centres verticaux, bords bas.
  **Plusieurs calques choisis** : ils s'alignent entre eux (ex. « bords gauches » : sur celui qui est le plus à
  gauche). **Un seul calque** : il s'aligne sur la **sélection** s'il y en a une, sinon sur **l'image** (ex. centres
  horizontaux + centres verticaux = centré dans l'image).
- **Répartir** (3 calques choisis ou plus) : horizontalement ou verticalement, le premier et le dernier restent en
  place ; les autres sont placés pour que l'espace entre deux voisins soit le même partout.
- **Retourner le calque** : symétrie horizontale (gauche ↔ droite) ou verticale (haut ↔ bas). Un seul calque : il se
  retourne sur place (s'il y a une sélection : seulement la partie sélectionnée). Plusieurs calques ou un groupe : ils
  se retournent ensemble, comme un seul dessin. Un texte retourné devient une image. (Image > Retourner retourne
  toute l'image, tous les calques.)

### Calques de réglage
Un **calque de réglage** applique un réglage (Niveaux, Courbes, Balance des couleurs, Noir et blanc, Vibrance,
Réglages de l'image) à **tout ce qui est dessous**, sans toucher aux pixels : on peut le modifier (double-clic
dessus, ou **Calque > Modifier le réglage…**), le masquer (œil), baisser son opacité ou le supprimer à tout moment.
- **Calque > Nouveau calque de réglage**, ou le bouton **Réglage** du panneau. S'il y a une sélection, elle devient
  le masque du calque de réglage (le réglage ne s'applique que là).
- Dans un groupe, il ne règle que les calques du groupe placés dessous.
- Gardé tel quel en .piximg ; en .ora et .psd, il devient un calque d'image (le résultat).

### Calques de remplissage
**Calque > Nouveau calque de remplissage** (ou le bouton **Réglage** du panneau Calques, en haut de la liste) : un
calque qui couvre toute la feuille d'une **couleur unie**, d'un **dégradé** ou d'un **motif**, et qui reste
**modifiable** (double-clic dessus).
- **Dégradé** : style linéaire, radial, angulaire, réfléchi ou losange ; **Angle**, **Échelle**, **Inverser**. Au
  départ : de la couleur de peinture au blanc.
- **Motif** : un motif de la bibliothèque, à l'échelle voulue.
- S'il y a une sélection, elle devient le **masque** du calque (le remplissage ne se voit que là).
- Il est redessiné quand la feuille change de taille (taille de l'image, zone de travail, recadrer…) ; gardé en
  .piximg ; en .ora et .psd, il devient un calque d'image. *Convertir en image* (clic droit) le fige.

### Harmoniser un collage (Calque > Harmoniser avec l'arrière-plan…)
Un objet collé d'une autre photo jure souvent : lumière plus froide, noirs moins profonds… Choisissez son calque
(l'objet détouré, avec de la transparence autour, posé au-dessus de la photo) : il prend la lumière de la photo
qui l'entoure.
- **Lumière (noirs et blancs)** : mêmes noirs et mêmes blancs que la photo autour.
- **Couleur de la lumière** : même teinte de lumière (mesurée sur les parties claires : une chemise rouge posée
  sur de l'herbe ne devient pas verte).
- **Adoucir le bord** : bord plus doux, vers l'intérieur de l'objet.
Aperçu en direct, une étape dans Annuler.

### Style du calque : ombres, contour, lueur, relief… (Ctrl+Alt+F)
Des **effets ajoutés au calque**, toujours modifiables : les pixels du calque ne sont pas touchés. Pour l'ouvrir :
**double-clic** sur un calque (ailleurs que sur son nom), bouton **fx** du panneau, ou menu **Calque > Style du
calque…**. La photo montre le résultat en direct ; **OK** garde le style (une seule étape dans Annuler),
**Annuler** remet tout comme avant.

| Effet | Ce qu'il fait |
|---|---|
| **Ombre portée** | Ombre décalée sous le calque. Case **Ombre réaliste** : nette près de l'objet, de plus en plus floue en s'éloignant, comme une vraie ombre |
| **Ombre interne** | Ombre à l'intérieur des bords (effet creusé) |
| **Lueur externe / interne** | Halo de couleur autour du calque, ou depuis ses bords (ou son centre) vers l'intérieur |
| **Contour** | Trait autour du calque : à l'extérieur, au centre ou à l'intérieur, épaisseur au choix |
| **Biseau et relief** | Donne du volume : biseau interne, externe ou estampage ; vers le haut ou le bas ; hauteur de la lumière |
| **Incrustation couleur** | Recouvre le calque d'une couleur (modes Normal, Produit, Écran, Incrustation) |
| **Incrustation dégradé** | Recouvre le calque d'un dégradé linéaire ou radial, angle et échelle au choix ; un clic sur le dégradé ouvre l'éditeur de dégradé (plusieurs couleurs, opacité) |
| **Incrustation de motif** | Recouvre le calque d'un motif de la bibliothèque, répété (mode, opacité, échelle de 10 à 1000 %) |
| **Ombre au sol** | Pour un objet détouré : ombre couchée sur le sol, en perspective, nette au pied et floue au bout. **Tirez le point rond sur la photo** pour choisir sa direction et sa longueur |

- **Styles tout prêts** (en haut) : Ombre douce, Ombre réaliste, Ombre au sol, Autocollant, Contour noir, Contour
  seul, Néon, Or, Chrome, Relief, Gravé, Feu, Bonbon, Verre. Les vignettes sont calculées **sur votre calque**. Un
  clic l'essaie, puis chaque effet reste réglable.
- **Plusieurs fois le même effet** (deux contours, trois ombres…) : bouton ⧉. Le premier de la liste passe devant.
  ▲ / ▼ changent l'ordre, ✕ supprime, la case à cocher éteint un effet sans le perdre.
- **Remplissage** : opacité du contenu seul, les effets restent. À 0 % : il ne reste que le contour ou l'ombre
  (texte en contour, verre…).
- **Lumière commune** (cochée par défaut) : tous les calques ont la même lumière ; changer son angle sur un calque
  le change partout.
- **Enregistrer ce style…** : il rejoint les styles tout prêts (clic droit dessus pour le supprimer).
- Les effets **suivent le calque** : Ctrl+T, Taille de l'image et Upscale les agrandissent ou les réduisent avec lui.
  Ils suivent aussi un texte modifié ou un calque déplacé.
- Menu **Calque** : **Copier le style** / **Coller le style** (sur un autre calque), **Enlever le style**, **Mettre
  le style dans les pixels** (pour gommer ou peindre le calque avec ses effets).
- Enregistrement : en **.piximg**, les styles restent modifiables. En **.psd** et **.ora**, ils sont mis dans les pixels
  (visibles dans Photoshop, Krita, GIMP, mais plus modifiables). Les styles d'un PSD ouvert sont repris et restent modifiables (voir chapitre 2).
- Fusionner ou aplatir met aussi les effets dans les pixels.

### Gomme de calque (G)
Efface les pixels du **calque choisi** avec le pinceau rond (taille : curseur « Taille » ou `[` `]`).
Exemple : une retouche IA réussie sauf sur un bord → choisissez son calque et gommez ce bord ; la photo
d'origine réapparaît dessous. Les zones effacées d'un calque seul apparaissent en damier.
À ne pas confondre avec la **Gomme de sélection** (E), qui ne touche qu'au rouge de la sélection.
Sur un calque verrouillé, la gomme ne fait rien et un message en bas de la fenêtre l'indique.

Toutes les actions sur les calques s'annulent avec Ctrl+Z (changer de calque choisi ne compte pas).

---

## 7. Le texte

Outil **Texte** (touche **T**, icône « T » dans la barre d'outils). Le panneau **Texte** s'ouvre à gauche.

### Écrire, déplacer, tourner
- **Largeur du panneau Texte** : tirez son bord droit à la souris pour l'élargir ; la largeur est retenue.
- **Cliquer sur la photo** : un nouveau texte « Texte » apparaît à cet endroit, sur **son propre calque**.
  Tapez directement : le mot proposé est remplacé. La case du panneau accepte plusieurs lignes (Entrée).
- **Cliquer sur un texte existant** : il est choisi et ses réglages s'affichent ; on peut le modifier à tout
  moment, même après avoir enregistré en **.piximg** et rouvert.
- **Double-clic** sur un texte de la photo (avec n'importe quel outil) ou sur un **calque de texte** (hors de son
  nom) : l'outil Texte s'ouvre sur ce texte, prêt à être tapé. Le style (fx) d'un calque de texte reste au bouton
  **fx** du panneau Calques.
- **Clic posé par erreur** : **Ctrl+Z** retire le nouveau texte (tant qu'on n'a rien tapé ; sinon il annule d'abord
  la frappe).
- Le texte s'applique **au fur et à mesure** : rien à valider.
- **Choisir des lettres sur la photo** : glissez sur les lettres du texte (comme dans la case du panneau) ;
  **double-clic** sur un mot : le mot entier. Les lettres choisies sont surlignées et se règlent comme dans la case.
- **Déplacer le texte** : glissez son **bord en pointillés**, ou **Ctrl + glisser** n'importe où sur le texte (aussi
  avec l'outil Déplacer, V).
- **Poignée ronde** au-dessus du cadre : tourner le texte (**Maj** : par pas de 15°), ou case *Rotation*.
- Le nom du calque suit la première ligne du texte (tant qu'on ne l'a pas renommé à la main).
- Sans texte choisi, les réglages du panneau servent pour le **prochain** texte ; Pixane Photo retient aussi le
  dernier style utilisé (police, couleur, effets…). La taille du nouveau texte est calculée d'après la photo.

### Réglages du panneau
| Réglage | Effet |
|---|---|
| **Police** | Toutes les polices installées dans Windows. La liste montre chaque police **avec le début de votre texte** (ou de la partie sélectionnée dans la case), sinon « Aa Bb Cc 123 ». En passant la souris sur une police, **le texte de la photo la prend tout de suite** pour voir le résultat ; liste fermée sans choisir : il revient comme avant. Au-dessus : **Style** (Toutes, Avec empattements, Sans empattements, Manuscrites, Fantaisie, Chasse fixe : seulement les polices de ce style, lu dans chaque police ; quelques polices de fantaisie peuvent être mal rangées) et **Liste** (Petite, Moyenne, Grande : taille de la liste et de l'aperçu), retenus |
| **Taille** | Hauteur des lettres, en pixels de la photo |
| **Couleur** (pastille) | Couleur des lettres, avec la transparence (canal alpha). Pendant le choix, **le texte de la photo montre la couleur** ; Annuler la remet comme avant (de même pour le contour, l'ombre et le fond) |
| **G / I / S / B** | Gras, italique, souligné, barré |
| **Alignement** | À gauche, centré, à droite (pour plusieurs lignes), **justifié** (texte en cadre : lignes étirées jusqu'aux deux bords) |
| **Lettres** | Espace ajouté entre les lettres, en % de la taille (négatif = lettres serrées) |
| **Lignes** | Écart entre les lignes, × la taille des lettres |
| **Rotation** | Angle en degrés |
| **Courbe** | Texte en arc : positif = en voûte, négatif = en creux, 360° = cercle complet |
| **Largeur / Hauteur** | Étirer ou tasser les lettres (100 % = normal) |
| **Casse** | Comme tapé, TOUT EN MAJUSCULES, tout en minuscules, Petites capitales, Première Lettre En Majuscule (le texte tapé ne change pas : on peut revenir) |
| **Position** | Normale, **exposant** (m², 1er) ou **indice** (H₂O) : lettres plus petites, montées ou descendues |
| **Ligne de base** | Monter (positif) ou descendre (négatif) des lettres, en % de la taille |
| **Crénage** | *De la police* : espaces corrigés entre certaines paires (AV, To…) ; *Aucun* : espaces bruts |
| **Ici** | Crénage à la main entre les deux lettres autour du curseur, en millièmes de la taille (aussi **Alt+flèches** dans la case, **Ctrl+Alt+flèches** : 5 fois plus) |
| **Ligatures, Fractions, Chiffres anciens** | Options de la police (OpenType) : fi/fl liés, 1/2 → ½, chiffres de hauteurs variées. Sans effet si la police ne les a pas |
| **Bords lissés** | Décoché : bords nets pixel par pixel (pour le pixel art ou les petits textes) |
| **Texte vertical** | Lettres les unes sous les autres ; chaque ligne devient une colonne (de droite à gauche) |
| **Texte en cadre** | Les lignes se coupent toutes seules à la **largeur du cadre** ; **hauteur du cadre** : ce qui dépasse est caché (0 = auto : selon le texte) |
| **Retrait / Entre paragraphes** | Alinéa de la première ligne de chaque paragraphe ; espace ajouté entre les paragraphes (% de la taille) |
| **Déformation** | Comme « Déformer le texte » de Photoshop : Arc, Arc inférieur / supérieur, Arche, Renflement, Drapeau, Vague, Poisson, Montée, Œil de poisson, Gonflement, Compression, Torsion. **Force** : -100 à 100 % ; **Distorsion horiz. / vert.** : effet de perspective |
| **Contour** | Trait autour des lettres : couleur et épaisseur |
| **Ombre portée** | Couleur, distance, direction (0° = vers la droite, 90° = vers le bas) et flou |
| **Fond** | Rectangle coloré derrière le texte : couleur, marge et arrondi des coins |

Les tailles des effets (épaisseur, distance, flou, marge, arrondi) sont en **% de la taille des lettres** :
ils restent proportionnés quand on change la taille du texte.
**Transparence** du texte entier : curseur **Opacité** du panneau Calques.

### Changer seulement certaines lettres
**Sélectionnez des lettres dans la case du panneau** (à la souris ou Maj+flèches) : elles sont **surlignées sur
la photo**, et police, taille, couleur, gras,
italique, souligné, barré, lettres, largeur, hauteur, casse, position et ligne de base ne changent **que pour elles**
(une phrase sous la case le rappelle). Exemple : un mot en rouge, un « 2 » en indice.
Sans sélection, un réglage change **tout le texte**, lettres à style propre comprises. Les lettres tapées ensuite
prennent le style de celle qui les précède.

### Texte sur un tracé, glyphes, styles
- **Texte sur un tracé** : bouton **Dessiner un tracé** (partie Disposition), puis glissez sur la photo : le texte
  suit la ligne dessinée (elle est lissée). **Départ** : où le texte commence le long du tracé ; **Retirer** : le
  texte redevient droit. Le tracé suit le texte quand on le déplace ou le tourne ; il se voit en pointillés.
- **Glyphes** (bouton **Ω** à côté de la taille) : tous les caractères de la police (symboles, flèches, lettres
  accentuées, ½, ©, émojis…). Un clic insère le caractère à la place du curseur ; les derniers utilisés restent en
  haut. Recherche par nom anglais (*arrow*, *heart*, *euro*) ou par code (*U+2192*).
- **Styles de texte** (en bas du panneau) : **Copier** retient la police, la couleur, les effets et les réglages du
  texte ; **Coller** les donne à un autre texte (son texte et sa place ne changent pas). **+** enregistre le style
  sous un nom ; il reste dans la liste pour les prochaines fois (en choisir un l'applique) ; **−** en supprime un.

### Orthographe, césure, rechercher et remplacer
- **Orthographe** : dans la case du panneau Texte, les mots mal écrits sont **soulignés en rouge**. **Clic droit**
  sur un mot souligné : les suggestions (accents oubliés, lettres inversées, en trop, oubliées, mots collés),
  *Ignorer* (jusqu'à la fermeture de Pixane Photo) ou *Ajouter au dictionnaire* (gardé pour toujours).
- **Langue** (partie Paragraphe) : la langue du texte, pour l'orthographe et la césure ; *Langue de Pixane Photo* par
  défaut. Français et anglais.
- **Césure** (texte en cadre) : les mots longs sont coupés en fin de ligne, avec un tiret, selon les règles de la
  langue. En justifié, une ligne d'un seul mot reste à gauche (ses lettres ne sont pas écartées).
- **Option** (case à l'installation, avec le choix des langues, ou **Affichage > Orthographe et césure**) :
  décochée, rien n'est souligné ni coupé. **Affichage > Langues de l'orthographe…** : cocher ou décocher une
  langue ; une langue non installée est téléchargée après accord (dictionnaire de LibreOffice : français 1,4 Mo,
  anglais 0,6 Mo), dans %LOCALAPPDATA%\Pixane\dictionnaires.
- **Rechercher et remplacer** (**Ctrl+H**, menu Édition) : dans tous les textes de l'image. *Suivant* choisit le
  texte et sélectionne le mot dans le panneau ; *Remplacer*, *Tout remplacer* (une seule étape d'Annuler) ;
  *Respecter les majuscules*, *Mot entier*. Les lettres à style propre gardent leur style. Les textes verrouillés
  ne sont pas modifiés.

### Une photo dans les lettres (masque d'écrêtage)
Comme dans Photoshop : posez la photo (ou une texture, un dégradé…) **sur un calque juste au-dessus du texte**, puis
**Ctrl+Alt+G** (menu Calque > *Masque d'écrêtage*, ou clic droit sur le calque). La photo ne se voit plus que
**dans les lettres** ; le texte reste modifiable (texte, police, taille…) et la photo peut être déplacée. Dans le
panneau Calques, le calque écrêté est décalé avec une flèche ↳. Ctrl+Alt+G encore une fois : retiré. Marche aussi
avec n'importe quel calque (pas seulement un texte). Gardé en .piximg et .psd ; en .ora, il est mis dans les pixels.

### Bon à savoir
- Toutes les modifications s'annulent avec Ctrl+Z ; une saisie de plusieurs lettres s'annule d'un seul coup.
- **Agrandir** et **Upscale** gardent les textes modifiables : ils sont décalés ou redessinés nets à la nouvelle taille.
- La **Gomme de calque** sur un texte le transforme en image (un message le signale ; Ctrl+Z pour revenir).
  **Fusionner** ou **Aplatir** aussi.
- Un texte sur un calque **verrouillé** ne peut être ni déplacé ni modifié.
- Pour garder les textes modifiables, enregistrez en **.piximg** (dans un .ora, ils deviennent des images).

---

## 8. Recadrer, peindre, retoucher

Les outils de retouche à la main, comme dans Photoshop. Tout s'annule par **Ctrl+Z** ; un calque **verrouillé**
est protégé. Les outils d'un même bouton (petit triangle) se choisissent par **clic droit** sur le bouton.

### Recadrer (C)
1. Tirez un cadre sur la photo : la partie gardée reste claire, le reste est assombri, une grille des tiers aide à
   placer le sujet. La taille du résultat s'affiche sous le cadre.
2. Ajustez-le : les **poignées** (coins et milieux des côtés) changent sa taille, glisser **dans** le cadre le
   déplace. Le cadre ne sort jamais de la photo (pour l'agrandir, voir *Agrandir l'image*).
3. **Proportions** (barre du haut) : *Libre*, *Comme la photo*, 1:1, 4:3, 3:2, 16:9, et les mêmes en hauteur.
4. **Entrée**, double-clic dans le cadre ou bouton **Recadrer** : c'est fait. **Échap** ou **Annuler** : le cadre
   disparaît sans rien changer. Ce qui est hors du cadre est supprimé, même ce qui dépassait déjà de la feuille
   (comme dans Photoshop).

Tous les calques sont recadrés ensemble ; les textes restent modifiables. Menu **Sélection > Recadrer à la
sélection** : garde le plus petit rectangle qui contient la sélection.

### Pinceau de couleur (P)
Peint sur le **calque choisi** dans le panneau Calques (astuce : un calque vide au-dessus de la photo permet de
corriger sans toucher à la photo).
- **Couleur** : pastille de la barre du haut. **Alt+clic** sur la photo prend la couleur à cet endroit (pipette).
- **Taille** (ou `[` et `]`), **Opacité** (100 % couvre tout, moins laisse voir dessous) et **Dureté** (100 % bord
  net, 0 % bord très doux).
- Repasser au même endroit pendant un même coup ne fonce pas la couleur ; un nouveau coup, si.

#### Nuancier
Le panneau **NUANCIER** (onglet à côté de l'Historique) garde vos couleurs : **un clic** sur une couleur en fait la
couleur de peinture.
- **+** ajoute la couleur de peinture ; **−** retire la couleur choisie ; clic droit : *Renommer*, *Retirer*.
- **…** : **Importer** un nuancier Photoshop (.aco) ou GIMP (.gpl), **Exporter** en .aco (pour Photoshop),
  **Remettre les couleurs de départ**.
- Les couleurs du nuancier se retrouvent aussi dans « Couleurs personnalisées » des fenêtres de choix de couleur.

#### Calque de pinceau modifiable
Case **Calque modifiable** dans la barre du haut (décochée au départ). Cochée, le premier coup de pinceau crée un
**calque de pinceau** au-dessus du calque choisi (la photo n'est pas touchée), et les coups suivants y vont aussi.
Ce calque garde le **tracé** de chaque coup, pas seulement ses pixels :
- **même plus tard**, choisissez-le dans le panneau Calques avec le pinceau de couleur : la barre du haut montre ses
  réglages ; changer la **couleur**, la **taille**, l'**opacité**, la **dureté**, la **rotation** (↻) ou la
  **forme du pinceau** (et ses Réglages…) **redessine tous ses traits**. Chaque changement s'annule avec Ctrl+Z ;
- le **déplacer**, le transformer (Ctrl+T, sans sélection), pivoter ou retourner l'image, changer sa taille,
  recadrer, Agrandir, Upscale : il **reste modifiable** (les traits sont redessinés nets) ;
- un calque de pinceau a **un seul réglage pour tous ses traits** : pour une autre couleur à garder à part, choisissez
  un autre calque (ou la photo) avant de peindre, un nouveau calque de pinceau sera créé ;
- la **gomme**, un filtre, l'IA, le pot de peinture… en font un calque d'image ordinaire (un message le dit ; Ctrl+Z
  pour revenir). Clic droit sur le calque > **Convertir en image** le fait aussi ;
- il est gardé dans les fichiers **.piximg** ; dans un PSD, PNG, JPG… il est enregistré comme une image. Dans le
  panneau Calques, il est marqué « pinceau modifiable ».
Case décochée : on peint directement sur le calque choisi, comme avant.

### Pinceaux à forme : la bibliothèque (comme Photoshop, Krita)
Le pinceau de couleur (et les masques), la **gomme de calque** et le **pinceau de sélection** peuvent prendre une
**forme** : craie, crayon, herbe, feuilles, aquarelle, éclaboussures… Chaque outil garde son propre choix.
- **Pour peindre normalement** : le **Pinceau de couleur** (touche **P** ; il partage son bouton avec la gomme de
  calque, le dégradé et le pot de peinture : clic droit sur le bouton pour le choisir). La touche B est le pinceau
  *de sélection*, qui ne peint pas.
- **Pinceau** (barre du haut) : ouvre la bibliothèque. À gauche les groupes, à droite les vignettes ; double-clic pour
  choisir. **Rond simple** revient au pinceau rond habituel (sa dureté se règle dans la barre du haut).
- **Taille** : jusqu'à **5000 px** (glissière progressive, ou tape la valeur ; touches [ et ]). **Rotation** : la case
  **↻** à côté de Pinceau (flèches : 15° par cran, ou tape l'angle).
- Dans la bibliothèque, la glissière **Vignettes** agrandit les vignettes ; à droite, un **grand aperçu** de l'élément
  choisi (les motifs à leur taille réelle, pour voir leur grain).
- Les groupes, dans l'ordre :
  - **Styles prêts** : un clic choisit la forme **et** ses réglages : Crayon, Fusain, Craie, Encre (plume), Feutre,
    Calligraphie, Aquarelle, Peinture à l'huile, Couteau à peindre, Pinceau sec, Aérographe, Bombe, Feuillage,
    Herbe, Étoiles et paillettes, Nuages et fumée, Éclaboussures. On peut ensuite les ajuster avec **Réglages…** ;
    choisir un autre pinceau après un style remet les réglages de départ ;
  - **Simples** : les pinceaux de tous les jours : rond dur, rond doux, aérographe, carré, plat, biseau ;
  - puis les pinceaux de Krita **par familles** : Crayon et fusain, Peinture, Nature, Effets, Textures, Formes ;
  - enfin les fichiers que tu as ajoutés.
- **Livrés avec Pixane Photo** : 235 pinceaux et 87 motifs (ressources de Krita, licence CC-0), plus les pinceaux simples
  et les styles prêts.
- **Ajouter des fichiers…** : pinceaux de Photoshop (**.abr**), de GIMP et Krita (**.gbr**, **.gih**), paquets
  Krita (**.bundle**), ou une simple image (le noir peint ; une image en couleur garde ses couleurs). Chaque fichier
  devient un groupe ; **Retirer ce groupe** l'enlève. Les pinceaux sont rangés dans Pixane Photo : l'original peut être
  déplacé ou supprimé.
- **Rangement** : chaque pinceau et chaque motif ajouté est rangé à part, **à sa taille d'origine et sans perte de
  qualité** (PNG), avec sa vignette. Pixane Photo n'ouvre que le pinceau dont on se sert : même un .abr de plus d'un Go
  s'ouvre **sans attente** (bibliothèque, réglages du pinceau, démarrage), et prend moins de place (1,7 Go → 0,86
  Go pour un gros .abr). L'ajout d'un très gros fichier prend le temps de le ranger (environ 3 minutes pour 1,7 Go).
- Les pinceaux ajoutés **avec une version précédente** sont rangés ainsi **une seule fois**, en arrière-plan, au
  premier démarrage (message dans la barre d'état) ; Pixane Photo reste utilisable pendant ce temps.
- Un pinceau « animé » (.gih : herbe, feuilles…) a plusieurs formes qui alternent pendant le trait.
- **Réglages…** (un point « • » s'affiche quand un réglage est changé), avec un aperçu du trait :
  - **Forme** : espacement entre les touches, angle (ou « l'angle suit le trait », comme une plume), rondeur ;
  - **Dispersion** : les touches s'écartent du trait, plusieurs à la fois, taille, angle et rondeur au hasard ;
  - **Texture** : un motif creuse le trait (craie sur papier à grain) ; échelle, force, inverser ;
  - **Double pinceau** : une deuxième forme découpe la première ;
  - **Couleur** : teinte, saturation, luminosité qui varient à chaque touche, mélange avec le blanc ;
  - **Transfert** : flux (à moins de 100 %, les touches s'ajoutent, comme un aérographe), variations ;
  - **Tablette** : avec un stylet, la pression change la taille (et, au choix, l'opacité ou le flux).
- Avec un stylet de tablette graphique, même le pinceau rond suit la pression.

### Tampon (S)
Recopie une partie de la photo sur une autre : pour effacer un petit défaut à la main, dupliquer une texture…
1. **Alt+clic** sur l'endroit à copier (une croix le marque).
2. Peignez là où il doit être recopié : la croix suit, à la même distance.
3. Les coups suivants gardent ce même décalage (comme l'option « Aligné » de Photoshop). Un nouvel Alt+clic choisit
   un autre endroit.

Le tampon copie la photo **telle qu'on la voit** (tous les calques visibles) et peint sur le calque choisi. Taille,
opacité et dureté comme le pinceau.

### Motifs : pot de peinture, Remplir, Tampon de motif, Incrustation de motif
Les **87 motifs** livrés (papier, toile, bois, pierre…) et ceux que tu ajoutes dans la bibliothèque (Photoshop
**.pat**, GIMP, Krita, ou une simple image) servent à quatre endroits. Le motif est **répété** à partir du coin haut
gauche de l'image : deux remplissages avec le même motif se raccordent sans couture. **Échelle** : 100 % = taille
réelle (de 10 à 1000 %).
- **Pot de peinture** : dans la barre du haut, la liste à côté de *Tous les calques* passe de **Couleur** à
  **Motif** ; la vignette du motif apparaît (clic : choisir un autre motif) avec son échelle.
- **Édition > Remplir avec un motif…** : couvre le calque choisi d'un motif (seulement dans la **sélection** s'il y
  en a une) ; motif, échelle et opacité au choix. Ctrl+Z pour revenir.
- **Tampon de motif** (dans le groupe du Tampon : clic droit sur son bouton) : on **peint** avec le motif, à la
  taille, l'opacité et la dureté du pinceau. Pas besoin d'Alt+clic.
- **Style du calque > Incrustation de motif** : le calque (un texte par exemple) prend le motif, sans toucher à ses
  pixels ; modifiable à tout moment.

### Supprimer (J, IA)
Peignez sur un petit défaut (fil électrique, tache, bouton, poussière) : **au lâcher**, il disparaît (LaMa). Comme
pour *Effacer*, le résultat va **directement dans le calque choisi**. Avec l'option du menu IA « Mettre les
résultats dans un nouveau calque », il va dans un calque « Suppressions », réutilisé pour les coups suivants. Pour un gros objet, préférez
*Effacer* (Maj+E), qui propose plusieurs résultats.

> **Astuce** : utilisez une image de **très bonne qualité** et travaillez par **petites zones**, l'une après
> l'autre. Plus l'image est de bonne qualité, plus la suppression respecte l'image d'origine.

### Effacer d'un clic (IA)
Dans le même groupe que *Supprimer*. **Cliquez sur l'objet** à enlever (ou tirez un cadre autour) : l'IA
(**SAM 3.1**) le détoure, la zone est un peu élargie (bord flou, cheveux), puis **Effacer** se lance, avec
l'analyse de l'ombre et la fenêtre des propositions. Ctrl+Z revient en arrière étape par étape.

### Yeux rouges
Dans le même groupe que *Supprimer*. **Cliquez au milieu de l'œil rouge** (ou tirez un cadre autour) : la pupille
rougie par le flash redevient sombre ; le reflet blanc, l'iris et la peau ne changent pas. Sans IA, immédiat, dans
le calque choisi.

### Pinceau correcteur (R)
Comme le tampon, mais la copie **prend la lumière et la couleur d'autour** : idéal pour une ride, une tache sur la
peau, une rayure sur un ciel dégradé.
1. **Alt+clic** sur une zone saine.
2. Peignez sur le défaut : pendant le geste, la copie brute s'affiche ; **au lâcher**, elle est raccordée aux
   alentours.

### Dégradé (D)
Glissez du début à la fin du dégradé (**Maj** : horizontal, vertical ou à 45°). Barre du haut : **Linéaire** ou
**Radial**, puis l'**aperçu du dégradé** : un clic dessus ouvre l'**éditeur de dégradé** (comme dans Photoshop).
Dans la sélection s'il y en a une. Pendant que vous tirez, le résultat se voit **en direct** sur le calque ;
il est posé quand vous lâchez la souris (Ctrl+Z pour revenir).
- Sur un **calque de texte**, le dégradé se pose **sur les lettres seules**, comme style « Incrustation dégradé » :
  le texte reste modifiable, et un nouveau dégradé remplace le précédent. Le sens et la longueur du glissé
  donnent l'angle et l'échelle ; pour les retoucher : **Calque > Style du calque**.
- **Garder la transparence** (case de la barre du haut) : sur un calque image, le dégradé ne se pose que sur ce
  qui est déjà peint (un objet détouré, un dessin) ; le vide autour reste vide.
- Sur un **masque** (vignette du masque choisie dans le panneau Calques ; la barre du haut affiche alors
  **« → dans le masque »**), le dégradé ne colore pas : il rend le calque plus ou moins transparent, pour un fondu
  progressif (par exemple pour mélanger deux photos). Les couleurs y deviennent des gris, et la partie
  transparente du dégradé devient le gris opposé à la couleur de peinture (blanc pour une couleur foncée). Pour
  colorer, cliquez d'abord sur la vignette du calque.
- L'éditeur règle le **prochain** dégradé : ouvrez-le avant de tirer. Dans la fenêtre Style du calque, au
  contraire, chaque réglage de l'éditeur se voit tout de suite sur le calque (Annuler remet l'ancien).

**Éditeur de dégradé** :
- En haut, les **dégradés tout prêts** (couleur de peinture vers transparent, noir vers blanc, arc-en-ciel, or,
  chrome, cuivre, feu, ciel…) et ceux que vous avez enregistrés : un clic en charge un.
- La **barre** montre le dégradé (le damier = transparent). **Sous la barre**, les points de **couleur** ; **au-dessus**,
  les points d'**opacité** (noir = opaque, blanc = transparent).
- **Ajouter une couleur** : clic sous la barre, à l'endroit voulu ; le nouveau point prend la couleur qui s'y trouve.
  **Double-clic** sur le point (ou clic sur la case « Couleur ») pour choisir sa couleur. La case **Couleur de
  peinture** fait suivre au point la couleur de peinture du moment (petit « P » dans le point).
- **Ajouter un point d'opacité** : clic au-dessus de la barre, puis réglez son **Opacité** en bas.
- **Déplacer** un point : glissez-le, ou tapez sa **Position** en %. **Retirer** : tirez-le loin de la barre, touche
  **Suppr** ou bouton **Supprimer** (il reste toujours au moins deux points de chaque sorte).
- Les petits **losanges** à côté du point choisi règlent le **milieu** du passage entre deux points : plus près d'un
  point, le passage se fait plus vite de son côté.
- **Inverser** met le dégradé à l'envers. **Enregistrer dans la liste…** garde votre dégradé (avec un nom) ;
  **Retirer de la liste** l'enlève.
- Le dégradé choisi est gardé d'une séance à l'autre.

### Pot de peinture (K)
**À quoi il sert** : remplir d'un seul clic une zone de couleur unie, sans la peindre à la main. Par exemple :
changer la couleur d'un fond uni ou d'un bandeau, remplir l'intérieur d'une lettre ou d'une forme, colorer une zone
d'un dessin au trait, ou remplir une sélection.

**Comment** : choisissez la couleur (pastille de la barre du haut, ou **Alt+clic** sur la photo pour la prendre),
puis cliquez dans la zone : elle se remplit jusqu'à ce que la couleur change.
- **Tous les calques** (case de la barre du haut) : où le pot cherche la zone à remplir.
  - **Décochée** (par défaut, comme dans Photoshop) : dans le **calque choisi** seulement. Sur un calque vide, un
    clic remplit **tout le calque**, quoi qu'il y ait sur les autres calques.
  - **Cochée** : dans l'**image visible** (tous les calques ensemble). Utile pour colorier un dessin dont les traits
    sont sur un autre calque : le remplissage s'arrête aux traits. Attention : il s'arrête aussi aux bords de tout ce
    qu'on voit, même venant d'un autre calque ; si l'on supprime ou déplace ensuite ce calque, un « trou » apparaît
    dans le remplissage.
- **Tolérance** (barre du haut) : à 0, seule la couleur exacte est remplie ; plus haut, le remplissage déborde sur
  des teintes voisines (utile pour un fond légèrement dégradé ou une photo JPEG).
- S'il y a une **sélection**, il reste dedans. Il peint sur le calque choisi (astuce : un calque vide au-dessus
  permet de revenir en arrière facilement).

### Pinceaux de retouche : Densité, Éponge, Goutte d'eau, Netteté, Doigt, Historique
Deux familles dans la barre d'outils (clic droit ou clic maintenu pour choisir), comme Photoshop. Ils changent les
pixels du **calque choisi**, sous le pinceau ; **Force** (barre du haut) dit combien, la taille et la dureté se
règlent comme pour le pinceau. Repasser au même endroit pendant un même coup ne renforce pas l'effet ; un nouveau
coup, si. Chaque coup est une étape d'Annuler.

| Outil | Ce qu'il fait |
|---|---|
| **Densité −** | Éclaircit. **Tons** : *Ombres*, *Tons moyens* ou *Hautes lumières* (seuls ces tons bougent : éclaircir les ombres d'un visage sans brûler le front) |
| **Densité +** | Assombrit, avec le même choix de tons (foncer un ciel, un bord) |
| **Éponge** | **Désaturer** : ternit les couleurs (jusqu'au gris) ; **Saturer** : les ravive |
| **Goutte d'eau** | Floute (un fond, un grain de peau, une imperfection). Sur un **masque**, adoucit son bord |
| **Netteté** | Rend plus nets les détails (yeux, lettres) ; à petite force, sinon du grain apparaît |
| **Doigt** | Étale la couleur dans le sens du geste, comme de la peinture fraîche ; la force dit jusqu'où elle s'étale |
| **Pinceau d'historique** | Repeint l'**instantané** : au départ, la photo telle qu'à l'ouverture. Pour annuler un effet seulement à certains endroits. **Prendre un instantané** (barre du haut) garde l'état actuel. Il est rangé sous le Tampon, et aussi en bas du panneau **Historique** (bouton *Pinceau d'historique*) |

### Fluidité (Filtres > Fluidité…, Ctrl+Maj+X)
Pour modeler l'image au pinceau, comme la Fluidité de Photoshop : affiner une silhouette, allonger une lettre, gonfler
un détail. Une fenêtre s'ouvre avec le calque choisi ; on peint dessus avec un des outils :

| Outil | Ce qu'il fait |
|---|---|
| **Pousser** | L'image suit le geste (déplacer un contour, allonger) |
| **Gonfler** | Agrandit ce qui est sous le pinceau ; garder le bouton appuyé ou repasser pour renforcer |
| **Contracter** | Rétrécit ce qui est sous le pinceau |
| **Tourbillon** | Fait tourner ce qui est sous le pinceau |
| **Reconstruire** | Revient peu à peu à l'image d'origine là où l'on peint |

**Taille** (en pixels de la photo) et **Pression** se règlent à gauche. **Défaire le dernier geste** et **Tout
reconstruire** permettent de revenir en arrière avant d'appliquer. L'aperçu est réduit pour rester rapide, mais le
résultat est calculé en pleine définition à la fin, sans flou. Avec une sélection, seule la zone sélectionnée change.
Toute la Fluidité est une seule étape d'Annuler.

### Formes (U)
Glissez pour dessiner un **rectangle**, un **rectangle arrondi**, une **ellipse**, une **étoile**, un **polygone**,
une **ligne** ou une **flèche** (**Maj** : carré, cercle, ligne droite). **Côtés** : nombre de branches de l'étoile ou
de côtés du polygone. Barre du haut : **Remplissage** et **Contour** (cases, chacun avec sa couleur : clic sur la
couleur pour la changer) et l'**épaisseur** du contour.

Chaque forme va dans un **calque de forme** (« forme modifiable » dans Calques), comme dans Photoshop : choisissez ce
calque avec l'outil Formes ou la Plume, et la barre du haut montre ses réglages ; les changer redessine la forme (une
étape d'Annuler). Déplacée, redimensionnée, tournée (Ctrl+T), ou l'image agrandie : la forme est redessinée nette et
reste modifiable ; elle est gardée dans le fichier .piximg. La gomme, un filtre ou l'IA en font une image ordinaire
(un message le dit ; Ctrl+Z pour revenir) ; Calque > clic droit > **Convertir en image** aussi.

### Plume (A)
Pour dessiner des formes libres, en lignes droites et en courbes, point par point (comme la Plume de Photoshop) :
- **clic** : un point d'angle ; **cliquer-glisser** : un point en courbe (on tire ses poignées) ; **Maj** : à 45° ;
- **clic sur le premier point** : le tracé se ferme ; **Entrée** ou **double-clic** : il reste ouvert (un trait) ;
- **Retour arrière** retire le dernier point, **Échap** abandonne le tracé.

**Mode** (barre du haut) : **Forme** (le tracé devient un calque de forme, avec le remplissage et le contour de la
barre) ou **Sélection** (le tracé fermé devient la sélection ; Maj en finissant : ajoutée, Alt : retirée).

Avec un calque de forme choisi, la Plume montre ses points : tirez un **point** pour le déplacer, ou une **poignée**
pour changer la courbe (l'autre poignée suit ; **Alt** : la poignée bouge seule et fait un angle).

Un **texte** retouché au pinceau ou au tampon devient une image (un message le rappelle ; Ctrl+Z pour revenir).
Les groupes et calques de réglage n'ont pas de pixels : un message invite à choisir un calque d'image ou un masque.

---

## 9. Réglages de l'image

Menu **Image > Réglages de l'image…** (Ctrl+U) : corriger la lumière, les couleurs et la netteté.

| Réglage | De … à | Effet |
|---|---|---|
| **Luminosité** | -100 à +100 | Éclaircit ou assombrit, en gardant le noir et le blanc |
| **Contraste** | -100 à +100 | Écarte ou rapproche les clairs et les sombres |
| **Saturation** | -100 à +100 | Couleurs plus vives ou plus ternes ; -100 = noir et blanc |
| **Teinte** | -180° à +180° | Fait tourner toutes les couleurs (le rouge devient orange, vert…) |
| **Température** | -100 à +100 | Plus chaud (orangé) ou plus froid (bleuté) |
| **Netteté** | 0 à 200 % | Renforce les détails |

- Le réglage s'applique au **calque choisi** dans le panneau Calques ; s'il y a une **sélection**, seulement à
  l'intérieur (avec ses bords doux). La fenêtre le rappelle en haut.
- **Aperçu sur la photo** : on voit le résultat en direct en bougeant les curseurs (sur une grande photo, il
  arrive après une fraction de seconde). Décochez pour comparer avec l'original.
- **Réinitialiser** remet tout à zéro, **Appliquer** garde le résultat, **Annuler** (ou Échap) laisse la photo
  comme avant. Après Appliquer, Ctrl+Z annule le réglage.
- **Auto** : propose d'office une luminosité, un contraste et une température (d'après la photo, ou la sélection) ;
  les curseurs restent ajustables ensuite.
- Un calque **verrouillé** est protégé ; un **texte** réglé devient une image.

### Niveaux, Courbes, Balance, Noir et blanc, Vibrance… (menu Image > Réglages)
Comme dans Photoshop, avec aperçu en direct et histogramme. Ils changent les pixels du **calque choisi** (dans la
sélection s'il y en a une). Pour pouvoir y revenir plus tard, utilisez plutôt un **calque de réglage** (chapitre 6).

| Réglage | Raccourci | Ce qu'il fait |
|---|---|---|
| **Niveaux** | Ctrl+L | Point noir, gris (gamma) et blanc d'entrée, noir et blanc de sortie ; par canal (RVB, rouge, vert, bleu). **Auto** cale le noir et le blanc sur la photo |
| **Courbes** | Ctrl+M | Courbe de tons : clic pour ajouter un point, glisser pour le bouger, clic droit pour l'enlever ; par canal. Une courbe en S donne du contraste |
| **Balance des couleurs** | Ctrl+B | Pousse les **Ombres**, **Tons moyens** ou **Hautes lumières** vers Cyan–Rouge, Magenta–Vert, Jaune–Bleu ; *Préserver la luminosité* |
| **Noir et blanc** | Ctrl+Alt+Maj+B | Passe en noir et blanc en choisissant la clarté de chaque couleur (rouges, jaunes, verts, cyans, bleus, magentas) ; **Virage** : teinte le gris (sépia…) |
| **Vibrance** | — | Ravive surtout les couleurs ternes en ménageant celles déjà vives (la peau) ; **Saturation** : toutes les couleurs autant |
| **Remplacer la couleur** | — | Cliquez la couleur à changer dans l'aperçu (Maj+clic : en ajouter une, Alt+clic : en retirer une), réglez la **Tolérance**, puis la **Teinte**, la **Saturation** et la **Clarté** : seuls ces points changent, plis et ombres gardés (un pull rouge devient bleu) |
| **Filtre photo** | — | Comme un filtre de couleur devant l'objectif : réchauffant, refroidissant, sépia… ou une couleur au choix ; **Densité** ; *Garder la luminosité* |
| **Mélangeur de couches** | — | Chaque couleur de sortie (rouge, vert, bleu) est faite d'une part de rouge, de vert, de bleu et d'une constante ; **Monochrome** : noir et blanc sur mesure |
| **Courbe de transfert de dégradé** | — | Les tons sombres prennent la couleur de gauche d'un dégradé, les clairs celle de droite (« duotone », effets d'affiche) ; *Inverser* |
| **Négatif** | Ctrl+I | Inverse les couleurs |
| **Seuil** | — | Noir ou blanc selon la clarté (effet tampon, pochoir) |
| **Postérisation** | — | Garde peu de nuances par couleur : aplats comme une affiche |

Tous existent aussi en **calque de réglage** (Calque > Nouveau calque de réglage), modifiables à tout moment.

### Filtres (menu Filtres)
**Flou gaussien**, **Flou de mouvement** (angle, distance), **Flou radial** (*Rotation* : les points tournent autour
du centre ; *Zoom* : ils filent vers le centre ; quantité, centre en %), **Flou de l'objectif** (comme un vrai objectif :
chaque point devient un petit disque ; les points très clairs deviennent des **reflets ronds** : réglez leur force et
leur seuil), **Flou de surface** (lisse la peau ou un ciel en gardant les bords nets ; *Seuil* : à partir de quel écart
de couleur un bord est gardé), **Réduction du bruit** (force, garder les détails, bruit
de couleur), **Netteté** (quantité, rayon, seuil : le masque flou de Photoshop), **Vignette** (assombrir ou
éclaircir les bords : force, taille du centre, douceur, rond), **Correction de l'objectif** (*Déformation* :
redresse les lignes courbées en tonneau ou en coussin, l'image est agrandie juste assez pour ne laisser aucun coin
vide ; *Vignetage* : éclaircit les coins sombres ; *Franges de couleur* : enlève les liserés rouges ou cyan sur les
bords ; réglage à la main, sans profil d'appareil). Même fonctionnement que les réglages : aperçu en
direct, calque choisi, dans la sélection s'il y en a une, une étape dans Annuler. Ils marchent aussi sur un masque.

### Actions (panneau ACTIONS)
Comme dans Photoshop : **enregistrer** une suite d'opérations, puis la **rejouer** d'un clic sur d'autres photos.
- **● Enregistrer** : donnez un nom, puis faites votre travail : les **réglages** (Image > Réglages), les
  **filtres**, la **taille de l'image** (gardée en pourcentage si les proportions ne changent pas : elle marche sur
  des photos de toutes tailles), les **rotations** et les **retournements** s'ajoutent à l'action. **■ Arrêter**
  termine.
- **▶ Jouer** (ou double-clic) : l'action se rejoue sur la photo ouverte, sans fenêtre, avec les mêmes réglages ;
  **une seule étape** dans Annuler.
- **…** : *Renommer*, *Supprimer l'action ou l'étape*, *Exporter* / *Importer* les actions (.json, pour les
  garder ou les partager).
- **Fichier > Traitement par lot** : choisissez une action pour la jouer sur **tout un dossier**.

---

## 10. Menu Image : taille, rotation, transformer

- **Mode** : **Couleurs RVB** ou **Niveaux de gris**. En niveaux de gris, l'image est montrée et enregistrée en gris
  (JPEG, PNG, TIFF en vrai gris) ; les calques gardent leurs couleurs, pour revenir en RVB sans rien perdre.
- **8, 16 ou 32 bits par couche** (*Image > Mode*, comme Photoshop) : en 8 bits, chaque couleur a 256 nuances ; en
  **16 bits**, 65 536 ; en **32 bits (HDR)**, des nombres à virgule (voir plus bas). Utile pour les retouches fortes (niveaux, courbes, éclaircir une photo sombre), les
  **dégradés** et les ciels : pas de **cassures** (marches visibles) même après plusieurs réglages. Le titre de la
  fenêtre indique **(16 bits)**. Ctrl+Z annule le changement.
  - **Ouvert en 16 bits d'office** : les PNG, TIFF et PSD 16 bits, et les **photos RAW** (développées en 16 bits).
  - **Enregistré en 16 bits** : .piximg, PSD, TIFF, PNG. Le JPEG, le WebP et le BMP n'ont que 8 bits : l'image y est
    enregistrée en 8 bits, avec le **tramage** (voir plus bas).
  - **Calculé en 16 bits** : la fusion des calques (modes de fusion, calques de réglage, masques), tous les
    **réglages** (Réglages de l'image, Niveaux, Courbes, Balance…), les **filtres** (flous, netteté, bruit,
    vignette), le **Dégradé** et les calques de remplissage, la taille de l'image, pivoter, miroir, redresser,
    transformer, recadrer, Agrandir.
  - **Les pinceaux travaillent dans la profondeur de l'image** : pinceau, gomme, tampon de duplication, pinceau
    d'historique, Densité − / +, Éponge, Goutte d'eau, Netteté et Doigt (en 16 bits, sans arrondi à 256 nuances).
  - Les autres outils (pot de peinture, texte, IA…) travaillent en 8 bits, **seulement là où ils changent
    l'image** : le reste du calque garde ses 16 bits. L'IA rend toujours un résultat en 8 bits, posé seulement dans
    la zone traitée. La *mise à l'échelle d'après le contenu* repasse tout le calque en 8 bits de précision.
  - Une image 16 bits prend **deux fois plus de mémoire**, et les filtres sont un peu plus lents.
- **32 bits par couche (HDR)** (*Image > Mode > 32 bits par couche (HDR)*) : pour les photos **HDR** (plusieurs
  expositions réunies, rendus 3D). Une couleur peut être **plus claire que le blanc** : le soleil, une lampe ou un
  ciel très lumineux gardent leur détail, et on peut baisser l'exposition après coup sans rien perdre. Le titre de
  la fenêtre indique **(32 bits)**.
  - **Ouvert en 32 bits d'office** : les **.exr** (OpenEXR), **.hdr** (Radiance) et **TIFF 32 bits**.
  - **Enregistré en 32 bits** : .piximg, EXR, HDR, TIFF. Le PSD et le PNG sont enregistrés en 16 bits, le JPEG en
    8 bits : ce qui est plus clair que le blanc y devient blanc (passez d'abord en 16 ou 8 bits avec le *Virage
    HDR* pour choisir comment le ramener).
  - **Calculé en 32 bits**, sans couper au blanc : la fusion des calques, les calques de réglage, les réglages, les
    filtres, le Dégradé, les calques de remplissage, la taille, la géométrie, et les pinceaux (le **tampon** recopie
    aussi les zones plus claires que le blanc). Un réglage traite une couleur trop claire en gardant son éclat.
  - **Affichage > Exposition 32 bits…** : rend l'aperçu à l'écran plus clair ou plus sombre (en diaphs) pour
    regarder les zones plus claires que le blanc. L'image et ses exports ne changent pas.
  - **Virage HDR** : en passant une image 32 bits en 16 ou 8 bits, une fenêtre s'ouvre si l'image a des couleurs
    plus claires que le blanc : **Exposition** (baisser pour retrouver le ciel), **Gamma** (tons moyens), et
    **Compresser les hautes lumières** (tout est ramené en douceur sous le blanc, rien n'est coupé). Un aperçu montre
    le résultat.
  - Une image 32 bits prend **quatre fois plus de mémoire** qu'en 8 bits.
- **Tramage vers 8 bits** (*Image > Mode*, coché par défaut) : quand une image 16 ou 32 bits est montrée à l'écran,
  exportée en JPEG / WebP, ou repassée en 8 bits, un très léger grain invisible est ajouté pour que les dégradés ne
  montrent pas de marches (comme le « tramage » de Photoshop). Décochez-le pour un passage en 8 bits sans grain.
- **Taille de la zone de travail…** (Ctrl+Alt+C) : agrandit la feuille **sans étirer l'image** (par exemple pour
  ajouter un fond perdu ou une bande pour un titre), ou la rogne.
  - Nouvelle **largeur** et **hauteur** en pixels, pouces, cm, mm, points, picas ou **pourcentage** ; **Relative**
    : on tape ce qu'on ajoute (ex. +200 px).
  - **Ancrage** : où reste l'image (au centre, en haut à gauche…) ; les flèches montrent où la feuille s'agrandit.
  - **Aperçu** : la nouvelle feuille, la couleur ajoutée et l'image à sa place ; ce qui sera rogné est montré pâle,
    entouré d'un pointillé rouge.
  - **Couleur ajoutée** sur le calque du bas : blanc, transparent, noir ou une couleur au choix.
  - Les textes restent modifiables, les repères suivent ; Ctrl+Z annule. Ce qui dépassait de la feuille
    réapparaît s'il entre dans la nouvelle feuille.
- **Tout faire apparaître** : la feuille s'agrandit pour montrer tous les pixels qui dépassent des calques.
- **Taille de l'image…** (Ctrl+Alt+I) : en pixels ou en %, proportions gardées (case à décocher), boutons rapides
  (par exemple 1920 px pour l'écran et Internet). Sans IA : pour agrandir avec plus de détails, préférez Upscale.
  **Aperçu** : le centre de l'image à 100 %, avant (à gauche) et après (à droite), pour juger la netteté.
- **Mise à l'échelle d'après le contenu…** : changer les **proportions** (un carré en 16:9, un paysage en 4:5…)
  **sans écraser le sujet** : ce sont surtout les zones sans détails (ciel, mur, fond uni) qui s'étirent ou se
  tassent.
  - **Largeur**, **Hauteur**, ou un **format** rapide (1:1, 4:3, 3:2, 16:9, 3:4, 4:5, 9:16 : le plus grand côté
    est gardé).
  - **Protéger la sélection** : sélectionnez d'abord le sujet (Sélection > Sélectionner le sujet) : il n'est pas
    déformé du tout.
  - **Protection du contenu** : 0 % = étirement ordinaire, 100 % = seules les zones sans détails changent.
  - **Aperçu** du résultat. Tous les calques suivent, masques et sélection aussi ; les textes, formes et traits de
    pinceau deviennent des images (Ctrl+Z pour revenir).
- **Pivoter** de 90° à droite, à gauche ou de 180°, **Retourner** horizontalement ou verticalement : toute l'image,
  tous les calques, sans perte. Les textes retournés deviennent des images ; pivotés, ils restent modifiables.
- **Pivoter selon un angle…** : toute l'image tourne de l'angle tapé, **au degré près** (ou au dixième),
  de -359,9° à +359,9° (positif : sens des aiguilles d'une montre). La feuille s'agrandit pour tout garder, les coins
  sont transparents.
- **Redresser…** : tourner d'un petit angle (-45° à +45°) avec une grille pour aligner l'horizon ou un mur.
  *Recadrer pour enlever les coins vides* (coché par défaut) ; décoché, l'image s'agrandit et les coins sont
  transparents.
- **Recadrage en perspective** : pour une **façade, un tableau, un document, un écran photographié de biais**.
  Tirez les **4 coins** sur les bords de l'objet (une grille en perspective aide à suivre ses lignes ; dedans : tout
  déplacer), puis **Entrée**, double-clic ou **Recadrer** : l'objet devient un **rectangle droit** qui remplit
  l'image (largeur et hauteur de ses plus longs bords). Les textes deviennent des images. Échap : annuler ; Ctrl+Z
  pendant le réglage remet le coin d'avant.
- **Édition > Transformer le calque** (Ctrl+T) : un cadre entoure le **calque choisi**. Pour agrandir, réduire ou
  tourner **un seul élément** du calque, **sélectionnez-le d'abord** (rectangle, lasso, baguette…) : le cadre
  n'entoure que lui, le reste du calque ne bouge pas, sa place d'origine devient transparente.
  - **coin** : taille, proportions gardées (Maj : libre) ; **bord** : largeur ou hauteur seule ;
  - **dedans** : déplacer ; **dehors** (le curseur devient une flèche ronde) : tourner, **degré par degré**
    (Maj : par 15°) ;
  - la barre du haut montre **Largeur**, **Hauteur** (en %) et **Angle** (en degrés) dans des cases où l'on peut
    **taper la valeur exacte** (flèches : 1° ; Maj+flèches : 10°) ; **Entrée**, double-clic ou **Valider** pour garder,
    **Échap** ou **Annuler** pour revenir. Changer d'outil valide aussi.
  - **Mode** (barre du haut, ou **Édition > Transformation**) :
    - **Libre** : ci-dessus. **Ctrl+coin** : ce coin bouge seul (on passe en *Distordre*).
    - **Perspective** : un coin tiré entraîne le coin voisin **en miroir** (tiré vers le bas, le bord rétrécit ;
      tiré de côté, il s'élargit) : comme une façade vue de biais.
    - **Distordre** : chaque coin bouge seul, pour **poser une image sur un écran, une boîte, un mur, une
      pochette en 3D** ; un milieu de bord déplace tout ce bord.
    - **Déformation** : une **grille de 16 points** (des cercles pour les poignées, des carrés aux coins) : tirez-les
      pour courber, gonfler, plier l'image (drapeau, tasse, page qui ondule). Un coin emmène ses deux poignées.
    - Dans ces trois modes, **dedans** = déplacer, **dehors** = tourner toute la forme ; Ctrl+Z défait le dernier
      geste. Les cases Largeur / Hauteur / Angle sont grisées.
  Un texte transformé devient une image (pour garder un texte modifiable, utilisez l'outil Texte).

Tout s'annule par Ctrl+Z.

---

## 11. Astuces

Des conseils pour obtenir de meilleurs résultats. Ce chapitre s'ouvre aussi par **Aide > Astuces**.

### Intelligence artificielle
- **Outil Supprimer (IA)** : utilisez une image de **très bonne qualité** et travaillez par **petites zones**, l'une
  après l'autre. Plus l'image est de bonne qualité, plus la suppression respecte l'image d'origine.
- **Effacer** : peignez **un peu plus large** que l'objet, ombre comprise. L'analyse avant d'effacer propose de
  l'ajouter quand elle la trouve.
- **Gros objet** : préférez *Effacer* (Maj+E), qui propose plusieurs résultats ; *Supprimer* (J) est fait pour les
  petits défauts (fil, tache, poussière).
- **Résultat décevant** : relancez, ou choisissez une autre proposition dans la fenêtre des résultats ; l'IA ne
  donne jamais deux fois la même chose.
- **L'IA écrit mal les textes** : ajoutez-les ensuite avec l'outil Texte.

### Sélection
- **Baguette magique** : après le clic, glissez la souris à droite ou à gauche pour régler la tolérance en direct.
- **Lasso par points** (barre du Lasso) : pratique pour les objets aux bords droits (fenêtre, panneau, écran).
- **Maj** ajoute à la sélection, **Alt** en retire, pendant le tracé.

### Texte
- **Double-clic** sur un texte de la photo ou sur son calque : il s'ouvre pour être modifié.
- **Glisser sur les lettres** de la photo les choisit ; **Ctrl + glisser** (ou le bord du cadre) déplace le texte.
- **Trouver une police semblable** : entourez le texte de la photo bien serré ; cochez *Polices gratuites Google
  Fonts* pour chercher aussi parmi près de 2 000 polices gratuites.

### Calques et retouche
- **Peindre ou retoucher sans abîmer la photo** : ajoutez un calque vide au-dessus et travaillez dessus ; vous
  pourrez le gommer ou le supprimer à tout moment.
- **Déplacer plusieurs calques ensemble** : groupez-les (Ctrl+G), choisissez le groupe, puis l'outil Déplacer (V).
- **Ombre portée** (style de calque) : tirez le point rond sur la photo pour placer le bout de l'ombre.
- **Travail fin** (dégradés, réglages poussés) : passez l'image en **16 bits** (Image > Mode) ou créez-la
  directement en 16 bits.

## 12. Raccourcis

| Touche | Action |
|---|---|
| H, V, M, L, B, E, G, T | Main, Déplacer, Rectangle, Lasso, Pinceau, Gomme de sélection, Gomme de calque, Texte |
| C, P, S | Recadrer, Pinceau de couleur, Tampon |
| J, R, D, K, U | Supprimer (IA), Pinceau correcteur, Dégradé, Pot de peinture, Formes |
| Alt+clic | (Pinceau de couleur, Pot de peinture) prendre une couleur ; (Tampon, Pinceau correcteur) endroit à copier |
| `[` / `]` | Pinceau plus petit / plus grand |
| Espace (maintenu) | Déplacer la vue |
| Maj / Alt (en commençant un rectangle ou un lasso) | Ajouter / Retirer |
| Alt (maintenu, pinceau de sélection) | Retirer le temps d'un geste |
| Maj+E, Maj+R, Maj+A, Maj+U | Effacer, Remplir, Agrandir, Upscale |
| Ctrl+Z, Ctrl+Y | Annuler, Rétablir |
| Ctrl+A, Ctrl+D, Ctrl+Maj+I | Tout sélectionner, Désélectionner, Inverser |
| Ctrl+X, Ctrl+C, Ctrl+V, Suppr | Couper, Copier, Coller (nouveau calque), Supprimer la sélection |
| Ctrl+U | Réglages de l'image |
| Ctrl+L, Ctrl+M, Ctrl+B, Ctrl+Alt+Maj+B | Niveaux, Courbes, Balance des couleurs, Noir et blanc |
| Ctrl+I | Négatif |
| Ctrl+G, Ctrl+Maj+G | Grouper, Dégrouper |
| Ctrl+Alt+G | Masque d'écrêtage (le calque ne se voit que dans celui du dessous) |
| Ctrl+H | Rechercher et remplacer dans les textes |
| Ctrl+\ | Peindre le masque / les pixels du calque |
| Ctrl+Alt+R | Améliorer le contour |
| Ctrl+R, Ctrl+', Ctrl+;, Ctrl+Maj+; | Règles, Grille, Repères, Magnétisme |
| Ctrl+W, Ctrl+Tab, Ctrl+Maj+Tab | Fermer la photo, Photo suivante, Photo précédente |
| Ctrl+Alt+Maj+S, Ctrl+Alt+Maj+W | Exporter pour le web, Exporter sous |
| Ctrl+P | Imprimer |
| Flèches (Maj : x10) | Bouger la sélection (outils de sélection) |
| Ctrl+N, Ctrl+Alt+V | Nouvelle image, Nouvelle image depuis le presse-papiers |
| Ctrl+Alt+I, Ctrl+Alt+C | Taille de l'image, Taille de la zone de travail |
| Ctrl+Alt+Y | Aperçu de l'impression (CMJN) |
| Ctrl+Alt+B | Comparer avant / après |
| Ctrl+T | Transformer le calque (Entrée valider, Échap annuler) |
| Ctrl+Alt+F | Style du calque |
| Ctrl+Maj+N, Ctrl+J | Nouveau calque, Dupliquer le calque |
| Ctrl+Alt+S, Maj+B | Sélectionner le sujet, Supprimer l'arrière-plan (IA) |
| O, Q, W, Y | Sélection d'objet (IA), Sélection rapide (IA), Baguette magique, Sélection de texte |
| Glisser après un clic de baguette | Régler la tolérance en direct |
| Clic droit sur un outil à petit triangle | Choisir un autre outil du groupe |
| Ctrl+0, Ctrl+1 | Ajuster, 100 % |
| Entrée / Échap | (Agrandir) Lancer / Annuler ; (Recadrer) Valider / Annuler |
| Maj (en tournant un texte) | Rotation par pas de 15° |
| F1 | Guide, ouvert sur les raccourcis (menu Aide > Guide de Pixane Photo : tout le guide, avec une recherche) |

---

## 13. Matériel et licences

**Installation** : lancer `Pixane-Photo-Setup-<version>-64bits.exe`.
1. Langue de l'installation (ce sera aussi la langue de Pixane Photo, modifiable ensuite dans Affichage > Langue).
2. Pour moi seulement (par défaut, sans droits administrateur) ou pour tous les utilisateurs.
3. Dossier d'installation : par défaut `…\Pixane\Pixane Photo` (le dossier `Pixane` réunit les logiciels de la
   Suite Pixane). Une installation plus ancienne (`…\Pixane`) y est déplacée d'elle-même : réglages, projets,
   moteur IA et raccourcis sont gardés.
4. **Vérification du PC** : carte graphique NVIDIA et sa mémoire (8 Go conseillés), place libre, moteur IA
   (ComfyUI) trouvé ou non. Si ComfyUI est installé ailleurs, bouton **Parcourir…** pour indiquer son dossier.
   Sans ComfyUI, Pixane Photo ouvre, retouche (calques, texte) et enregistre, mais les actions IA ne marchent pas.
5. **Moteur IA** (seulement si ComfyUI n'est pas trouvé) : liste de ce qui sera téléchargé, avec taille, site et
   licence (21,5 Go à télécharger, environ 31 Go sur le disque) ; dossier du moteur (par défaut
   `%LOCALAPPDATA%\Pixane\moteur`) ; case facultative **Flux Schnell** pour « Upscale net » (11,8 Go de plus) ;
   case **J'accepte la licence FLUX.1 [dev]** (usage non commercial) obligatoire pour installer le moteur.
   On peut aussi décocher : Pixane Photo s'installe sans moteur.
6. Options : icône sur le Bureau ; ouvrir les fichiers .piximg avec Pixane Photo ; **taille de l'interface**
   (normale, compacte 85 %, grande 125 %, très grande 150 % ; ne remplace pas un choix déjà fait dans Pixane Photo).
7. À la fin, la fenêtre **Installer le moteur IA** télécharge et installe tout (ComfyUI portable, ses extensions,
   les modèles). Elle montre l'avancement, la vitesse et le temps restant. **Arrêter** est possible à tout moment :
   le téléchargement reprendra plus tard là où il s'était arrêté (même après une coupure). Chaque fichier est
   vérifié (empreinte SHA-256).

La même fenêtre s'ouvre par le menu **IA > Installer le moteur IA…** (par exemple pour ajouter Flux Schnell plus
tard, ou **Flux Kontext** — 11,9 Go, facultatif — pour *Restaurer une vieille photo*), et Pixane Photo la propose au démarrage s'il ne trouve pas de moteur. Si un ComfyUI installé autrement est déjà
là (ComfyUI Desktop, ComfyUI portable…), Pixane Photo l'utilise tel quel : au démarrage, il demande à ComfyUI ce qu'il a
déjà et, s'il manque des extensions ou des modèles, propose la fenêtre **Compléter le moteur IA** (aussi par
**IA > Installer le moteur IA…**). Elle liste **seulement ce qui manque** (taille, licence, source, dossier) et le
range dans les dossiers de ce ComfyUI, même un dossier de modèles partagé, sans rien remplacer ni effacer. Flux
Schnell et Flux Kontext s'y ajoutent en option. Si de nouvelles extensions sont ajoutées à ComfyUI Desktop ouvert,
fermez-le puis rouvrez-le pour qu'il les charge. Un ComfyUI trop ancien pour une fonction (par exemple la
sélection d'objet) est signalé : Pixane Photo ne le met pas à jour lui-même.

**Mises à jour du moteur IA** : les versions de ComfyUI, des extensions et des modèles sont choisies et essayées
avec chaque version de Pixane Photo ; rien ne change tout seul. Quand une nouvelle version de Pixane Photo demande d'autres
versions, Pixane Photo le propose une fois au démarrage (liste et taille à télécharger), et la fenêtre **Installer le
moteur IA** montre l'état de chaque élément (*à jour*, *nouvelle version*) avec le bouton **Mettre à jour**.
Seul ce qui a changé est téléchargé. ComfyUI est remplacé en gardant ses modèles, ses extensions et ses réglages ;
un ancien modèle remplacé est effacé. Le moteur est arrêté pendant la mise à jour et relancé après. Un ComfyUI
installé autrement (par exemple ComfyUI Desktop) se met à jour de son côté : Pixane Photo n'y touche pas.

**Aide > Rechercher une mise à jour…** (ou au démarrage, si *Vérifier les mises à jour au démarrage* est coché) : quand une nouvelle version existe, une fenêtre montre **ce qui change** (nouveautés, corrections) dans toutes les versions que vous n'avez pas encore ; **Télécharger** ouvre la page de téléchargement. Une nouvelle version s'installe par-dessus l'ancienne (réglages gardés). Désinstaller : Paramètres de Windows >
Applications. Le désinstalleur pose deux questions (réponse « Non » par défaut) :
- supprimer aussi le **moteur IA installé par Pixane Photo** (ComfyUI, extensions, modèles) ? Un ComfyUI installé
  autrement, par exemple ComfyUI Desktop, n'est jamais touché ;
- supprimer aussi les **réglages** (langue, thème, dernier dossier, style de texte, dossier du moteur) et les
  journaux ?

**Licences et matériel d'essai** :
- Pixane Photo : Licence Pixane 1.3, © 2026 Georges Christophe (chrypox) : gratuit, modifiable et partageable,
  nom de l'auteur obligatoire, aucune vente (ni de Pixane Photo ni d'une version modifiée) ; fichier `LICENSE`.
  Éléments tiers : `docs\LICENCES_TIERS.md`.
- Testé sur une carte graphique NVIDIA de 8 Go (RTX 3060 Ti). Les durées indiquées viennent de ce PC.
- Modèles utilisés : Flux.1 Fill dev (**usage non commercial** ; version GGUF Q8 si installé par Pixane Photo, même
  qualité), Flux.1 Kontext dev (**usage non commercial**, facultatif), Flux.1 Schnell (Apache-2.0), LaMa
  (Apache-2.0), RealESRGAN x4plus (BSD-3), SCUNet (Apache-2.0), BiRefNet (MIT), SAM 3.1 (SAM License de Meta).
- Moteur : ComfyUI (GPL-3.0) et ses extensions Inpaint nodes, Inpaint Crop and Stitch, Ultimate SD Upscale
  (GPL-3.0), ComfyUI-GGUF (Apache-2.0).
