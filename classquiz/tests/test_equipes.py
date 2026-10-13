# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""Mode équipe : choix de l'équipe en rejoignant, moyenne des membres, classement en fin de partie."""

import uuid

import pytest

import classquiz.db.models as modeles
import classquiz.helpers.hestim as hestim
import classquiz.helpers.hestim_equipes as equipes
import classquiz.socket_server as serveur
from classquiz.db.models import PlayGame, Quiz
from classquiz.routers.hestim import partie_nouvelle

PIN = "482913"


class RedisFactice:
    """Chaînes et tables de hachage en mémoire : ce que le mode équipe et join_game utilisent."""

    def __init__(self):
        self.valeurs: dict[str, str] = {}
        self.tables: dict[str, dict[str, str]] = {}
        self.ensembles: dict[str, set[str]] = {}

    async def get(self, cle):
        return self.valeurs.get(cle)

    async def set(self, cle, valeur, **kwargs):
        self.valeurs[cle] = valeur

    async def hset(self, cle, champ, valeur):
        self.tables.setdefault(cle, {})[champ] = valeur

    async def hget(self, cle, champ):
        return self.tables.get(cle, {}).get(champ)

    async def hgetall(self, cle):
        return dict(self.tables.get(cle, {}))

    async def hdel(self, cle, champ):
        self.tables.get(cle, {}).pop(champ, None)

    async def expire(self, *args):
        return None

    async def sadd(self, cle, valeur):
        self.ensembles.setdefault(cle, set()).add(valeur)

    async def srem(self, cle, valeur):
        self.ensembles.get(cle, set()).discard(valeur)


def partie(nb_equipes: int | None) -> PlayGame:
    return PlayGame(
        quiz_id=uuid.uuid4(),
        description="",
        user_id=uuid.uuid4(),
        title="Routage",
        questions=[],
        game_id=uuid.uuid4(),
        game_pin=PIN,
        equipes=equipes.noms_des_equipes(nb_equipes),
    )


@pytest.fixture
def redis(monkeypatch):
    factice = RedisFactice()
    for module in (equipes, serveur, modeles, hestim):
        monkeypatch.setattr(module, "redis", factice)
    return factice


@pytest.fixture
def emis(monkeypatch):
    evenements = []

    async def emettre(evenement, donnees=None, room=None, **kwargs):
        evenements.append((evenement, donnees, room))

    async def rien(*args, **kwargs):
        return None

    monkeypatch.setattr(serveur.sio, "emit", emettre)
    monkeypatch.setattr(serveur.sio, "enter_room", rien)
    monkeypatch.setattr(serveur, "save_session", rien)
    return evenements


def noms(evenements) -> list[str]:
    return [evenement for evenement, _, _ in evenements]


# ── Nombre d'équipes ───────────────────────────────────────────────────────


def test_sans_nombre_d_equipes_la_partie_se_joue_seul():
    assert equipes.noms_des_equipes(None) is None
    assert equipes.noms_des_equipes(0) is None


def test_de_deux_a_huit_equipes_aux_noms_distincts():
    assert equipes.noms_des_equipes(2) == ["Rouge", "Bleu"]
    assert len(set(equipes.noms_des_equipes(8))) == 8


@pytest.mark.parametrize("nombre", [1, 9, -2])
def test_un_nombre_d_equipes_hors_limites_est_refuse(nombre):
    with pytest.raises(ValueError):
        equipes.noms_des_equipes(nombre)


def test_une_partie_lancee_depuis_planner_garde_ses_equipes():
    quiz = Quiz(id=uuid.uuid4(), title="Routage", description="", questions=[], user_id=uuid.uuid4())
    game = partie_nouvelle(quiz, uuid.uuid4(), PIN, ["Rouge", "Bleu", "Vert"])
    assert game.equipes == ["Rouge", "Bleu", "Vert"]
    assert game.to_player_data()[0]["equipes"] == ["Rouge", "Bleu", "Vert"]


# ── Classement ─────────────────────────────────────────────────────────────


def test_le_score_d_une_equipe_est_la_moyenne_de_ses_membres():
    lignes = equipes.classement(
        ["Rouge", "Bleu"],
        {"amine": 0, "sara": 0, "yassine": 0, "nora": 1},
        {"amine": "900", "sara": "600", "yassine": "300", "nora": "700"},
    )
    # Trois membres à 600 de moyenne contre un seul à 700 : la petite équipe gagne
    assert lignes == [
        {"equipe": 1, "nom": "Bleu", "score": 700, "membres": 1},
        {"equipe": 0, "nom": "Rouge", "score": 600, "membres": 3},
    ]


def test_un_membre_sans_point_compte_pour_zero():
    lignes = equipes.classement(["Rouge", "Bleu"], {"amine": 0, "sara": 0}, {"amine": "800"})
    assert lignes[0]["score"] == 400


def test_une_equipe_vide_n_est_pas_classee_et_les_egalites_suivent_l_ordre_des_equipes():
    lignes = equipes.classement(["Rouge", "Bleu", "Vert"], {"amine": 2, "sara": 1}, {"amine": "500", "sara": "500"})
    assert [ligne["nom"] for ligne in lignes] == ["Bleu", "Vert"]


def test_une_equipe_inconnue_est_ignoree():
    assert equipes.classement(["Rouge", "Bleu"], {"amine": 5}, {"amine": "500"}) == []


# ── Serveur de jeu ─────────────────────────────────────────────────────────


async def rejoindre(redis, nb_equipes, **champs):
    await redis.set(f"game:{PIN}", partie(nb_equipes).model_dump_json())
    await serveur.join_game("sid-amine", {"username": "amine", "game_pin": PIN, **champs})


async def test_sans_equipe_choisie_on_ne_rejoint_pas_une_partie_par_equipes(redis, emis):
    await rejoindre(redis, 3)
    assert noms(emis) == ["equipe_requise"]
    assert await redis.get(f"game_session:{PIN}:players:amine") is None


async def test_une_equipe_hors_de_la_liste_est_refusee(redis, emis):
    await rejoindre(redis, 3, equipe=3)
    assert noms(emis) == ["equipe_requise"]


async def test_le_joueur_rejoint_son_equipe_et_l_enseignant_la_voit(redis, emis):
    await rejoindre(redis, 3, equipe=2)
    assert await equipes.equipes_des_joueurs(PIN) == {"amine": 2}
    arrivee = next(donnees for evenement, donnees, _ in emis if evenement == "player_joined")
    assert arrivee["equipe"] == 2


async def test_une_partie_sans_equipes_ignore_le_choix_d_equipe(redis, emis):
    await rejoindre(redis, None, equipe=1)
    assert await equipes.equipes_des_joueurs(PIN) == {}
    arrivee = next(donnees for evenement, donnees, _ in emis if evenement == "player_joined")
    assert arrivee["equipe"] is None


async def test_le_classement_des_equipes_precede_les_resultats_finaux(redis, emis, monkeypatch):
    game = partie(2)
    await redis.set(f"game:{PIN}", game.model_dump_json())
    await redis.hset(f"game_session:{PIN}:player_scores", "amine", "900")
    await equipes.enregistrer_equipe(PIN, "amine", 1)

    async def session(sid, sio):
        return {"game_pin": PIN, "admin": True}

    async def rien(*args):
        return None

    monkeypatch.setattr(serveur, "get_session", session)
    monkeypatch.setattr(serveur, "signaler_partie_terminee", rien)
    await serveur.get_final_results("sid-enseignant", {})

    assert noms(emis) == ["classement_equipes", "final_results"]
    assert emis[0][1] == [{"equipe": 1, "nom": "Bleu", "score": 900, "membres": 1}]
    assert emis[0][2] == PIN


async def test_sans_equipes_les_resultats_finaux_arrivent_seuls(redis, emis, monkeypatch):
    await redis.set(f"game:{PIN}", partie(None).model_dump_json())

    async def session(sid, sio):
        return {"game_pin": PIN, "admin": True}

    async def rien(*args):
        return None

    monkeypatch.setattr(serveur, "get_session", session)
    monkeypatch.setattr(serveur, "signaler_partie_terminee", rien)
    await serveur.get_final_results("sid-enseignant", {})
    assert noms(emis) == ["final_results"]


async def test_un_joueur_exclu_quitte_son_equipe(redis, emis, monkeypatch):
    await equipes.enregistrer_equipe(PIN, "amine", 0)
    await redis.set(f"game_session:{PIN}:players:amine", "sid-amine")

    async def session(sid, sio):
        return {"game_pin": PIN, "admin": True}

    async def rien(*args, **kwargs):
        return None

    monkeypatch.setattr(serveur, "get_session", session)
    monkeypatch.setattr(serveur.sio, "leave_room", rien)
    await serveur.kick_player("sid-enseignant", {"username": "amine"})
    assert await equipes.equipes_des_joueurs(PIN) == {}
