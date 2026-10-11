# Le fork HESTIM de ClassQuiz

Ce dépôt est le moteur de quiz de HESTIM Planner, tiré de [ClassQuiz](https://github.com/mawoka-myblock/ClassQuiz) (lot R-2). Ce fichier dit d'où il part, ce qui a changé et ce que la licence impose.

## Point de départ

| | |
|---|---|
| Projet d'origine | `mawoka-myblock/ClassQuiz`, branche `master` |
| Commit d'origine | `711bdde7a7dcd2d217cfc75dbbbb2592a78582d3` (« Fix and add basic RTL support », 30 août 2026) |
| Branche du fork | `hestim` sur `Claude20022002/ClassQuiz` (dépôt public), suivie localement par `main` |
| Reprise de l'amont | **aucune avant la soutenance** |

Liste exacte des fichiers changés depuis l'origine, à jour à tout moment :

```bash
git diff --name-status 711bdde7 HEAD
```

## Ce qui a changé pour HESTIM

### Fichiers propres à HESTIM

Ils n'existent pas dans l'origine : une reprise de l'amont ne les touche pas.

| Fichier | Rôle |
|---|---|
| `classquiz/routers/hestim.py` | Routes signées par Planner : quiz lus et écrits, partie lancée depuis une séance |
| `classquiz/helpers/hestim.py` | Webhooks vers Planner (partie démarrée, scores), contrôle de l'identifiant de partie |
| `classquiz/tests/test_hestim.py`, `classquiz/tests/test_salles.py` | Tests de ce qui précède et des salles du serveur de jeu |
| `frontend/src/lib/hestim/` | Marque et thème HESTIM |
| `frontend/src/lib/play/hestim_anti_triche.ts` | Journal des sorties du joueur pendant une question |
| `frontend/src/lib/play/admin/nuage_mots.svelte` | Nuage de mots des réponses libres |
| `frontend/static/hestim-embleme.png` | Emblème |

### Fichiers de l'origine modifiés

Dans le code Python, chaque modification porte un commentaire qui commence par « HESTIM : ».

| Où | Quoi |
|---|---|
| `classquiz/__init__.py`, `config.py` | Branchement des routes HESTIM ; adresse et secret des webhooks |
| `classquiz/db/models.py` | L'identifiant de partie (`game_id`) ne part plus chez un joueur |
| `classquiz/routers/quiz.py` | Webhook « partie démarrée » ; la route publique ne rend plus l'identifiant d'une partie |
| `classquiz/socket_server/` | Prise de main réservée à qui a l'identifiant ; réponses mélangées par joueur ; journal des sorties ; compteur de réponses et fin de question limités à leur partie |
| `classquiz/tests/test_server.py` | Adapté à la route qui ne rend plus l'identifiant |
| `frontend/src/lib/play/`, `frontend/src/routes/play/` | Rejoindre une partie depuis Planner (pseudo et jeton dans le lien), anti-triche, nuage de mots |
| Le reste de `frontend/src/` (environ 60 fichiers) | Style HESTIM (couleurs, polices, textes) et nom affiché « PlannerQuiz » |
| `frontend/static/` | Icônes et manifeste |
| `frontend/Dockerfile`, `README.md` | Image du site ; titre du README |

`.expo/` est un dossier créé par erreur par `expo start` : il n'a rien à faire ici.

## Règles pour modifier le fork

1. **Une modification HESTIM vit dans un fichier HESTIM quand c'est possible** (`hestim.py`, `lib/hestim/`, un composant nouveau). Un fichier de l'origine ne reçoit que le branchement, avec un commentaire « HESTIM : ».
2. **Chaque fichier nouveau commence par l'en-tête SPDX** de l'école (`SPDX-FileCopyrightText: 2026 HESTIM`, `SPDX-License-Identifier: MPL-2.0`).
3. **Tenir ce fichier à jour** quand un fichier de l'origine est modifié pour la première fois.

## Travailler à deux groupes

Décision du chef de projet, 11 octobre 2026 : les mêmes règles que pour Planner.

- **Une branche par lot**, partie de `hestim` et préfixée par le groupe : `a/<lot>` (groupe A, le code Python de `classquiz/`), `b/<lot>` (groupe B, le site Svelte de `frontend/`). Une PR par branche vers `hestim` ; le chef de projet fusionne.
- **Un dossier de travail par groupe** : le groupe A garde `../ClassQuiz`, le groupe B travaille dans une copie (`git worktree add ../ClassQuiz-b -b b/<lot> origin/hestim`). Aucun groupe n'écrit dans le dossier de l'autre.
- **Pas de CI** dans ce dépôt : les tests Python se lancent sur le poste, dans l'image de l'API (commande dans le compte rendu de Planner, repères pratiques).

## Ce que la licence impose et permet

Le code de ClassQuiz est sous **Mozilla Public License 2.0** (`LICENSE`), avec quelques fichiers sous MIT (`LICENSES/`).

- **Usage commercial permis** : l'école peut faire payer Planner, quiz compris.
- **Les fichiers modifiés restent publiés** sous MPL 2.0, en code source : le site du quiz est envoyé aux navigateurs, donc distribué. Le dépôt public du fork y suffit, à condition d'y pousser ce qui tourne en production.
- **Les avis de licence et de droits d'auteur de l'origine restent en place**, dans chaque fichier.
- **La licence ne s'étend pas à Planner** : elle porte fichier par fichier. Le code de Planner, qui parle au quiz par des routes et des webhooks, n'est pas concerné.
- **Le nom et le logo de ClassQuiz** ne sont pas couverts par la licence : le fork affiche la marque HESTIM.
