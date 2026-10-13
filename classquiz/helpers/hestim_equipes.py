# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""HESTIM : mode équipe.

L'enseignant fixe le nombre d'équipes au lancement (2 à 8) ; chaque joueur choisit la sienne en
rejoignant la partie. Le score d'une équipe est la moyenne des scores de ses membres : une équipe
nombreuse n'écrase pas une petite. Les scores individuels ne changent pas (classement habituel,
scores envoyés à Planner).
"""

from classquiz.config import redis

EQUIPES_MIN = 2
EQUIPES_MAX = 8
# L'ordre compte : le site associe à chaque rang la couleur du même nom (lib/hestim/equipes.ts)
_NOMS = ["Rouge", "Bleu", "Vert", "Jaune", "Violet", "Orange", "Turquoise", "Rose"]
_DUREE_REDIS_S = 7200


def noms_des_equipes(nombre: int | None) -> list[str] | None:
    """Noms des équipes d'une partie ; None (ou 0) : partie sans équipes. ValueError hors de 2 à 8."""
    if not nombre:
        return None
    if not EQUIPES_MIN <= nombre <= EQUIPES_MAX:
        raise ValueError(f"nombre d'équipes entre {EQUIPES_MIN} et {EQUIPES_MAX}")
    return _NOMS[:nombre]


def equipe_valide(equipes: list[str], equipe: int | None) -> bool:
    return equipe is not None and 0 <= equipe < len(equipes)


def _cle(game_pin: str) -> str:
    return f"game:{game_pin}:hestim:equipes"


async def enregistrer_equipe(game_pin: str, username: str, equipe: int) -> None:
    await redis.hset(_cle(game_pin), username, str(equipe))
    await redis.expire(_cle(game_pin), _DUREE_REDIS_S)


async def retirer_de_son_equipe(game_pin: str, username: str) -> None:
    """Un joueur exclu de la partie ne compte plus dans la moyenne de son équipe."""
    await redis.hdel(_cle(game_pin), username)


async def equipes_des_joueurs(game_pin: str) -> dict[str, int]:
    """Rang de l'équipe de chaque joueur, par pseudo."""
    return {nom: int(equipe) for nom, equipe in (await redis.hgetall(_cle(game_pin))).items()}


def classement(equipes: list[str], equipe_de: dict[str, int], scores: dict[str, str]) -> list[dict]:
    """Équipes qui ont au moins un membre, de la meilleure moyenne à la moins bonne.

    Un membre qui n'a marqué aucun point compte pour 0 : l'équipe ne gagne rien à ce qu'il se taise.
    """
    membres: dict[int, list[str]] = {}
    for nom, equipe in equipe_de.items():
        if 0 <= equipe < len(equipes):
            membres.setdefault(equipe, []).append(nom)
    lignes = []
    for equipe, noms in membres.items():
        total = sum(int(float(scores.get(nom) or 0)) for nom in noms)
        lignes.append(
            {"equipe": equipe, "nom": equipes[equipe], "score": round(total / len(noms)), "membres": len(noms)}
        )
    return sorted(lignes, key=lambda ligne: (-ligne["score"], ligne["equipe"]))


async def classement_de_la_partie(equipes: list[str], game_pin: str) -> list[dict]:
    scores = await redis.hgetall(f"game_session:{game_pin}:player_scores")
    return classement(equipes, await equipes_des_joueurs(game_pin), scores)
