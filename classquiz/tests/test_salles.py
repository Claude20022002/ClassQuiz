# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""Serveur de jeu : les événements d'une réponse restent dans la partie qui les produit."""

from datetime import datetime
from types import SimpleNamespace

import pytest

import classquiz.socket_server as serveur

PIN = "482913"


class RedisFactice:
    """Juste ce que submit_answer lit et écrit dans Redis."""

    def __init__(self, joueurs: int):
        self.joueurs = joueurs

    async def get(self, cle):
        return datetime.now().isoformat() if cle.endswith(":current_time") else None

    async def set(self, *args, **kwargs):
        return None

    async def hincrby(self, *args):
        return None

    async def scard(self, cle):
        return self.joueurs


async def evenements_d_une_reponse(monkeypatch, joueurs: int) -> list:
    """Rend les (événement, salle) émis quand un joueur répond, sur une partie de `joueurs` joueurs."""
    emis = []

    async def emettre(evenement, donnees=None, room=None, **kwargs):
        emis.append((evenement, room))

    async def session(sid, sio):
        return {"game_pin": PIN, "username": "amine", "ping": "0"}

    async def deja_repondu(*args):
        return False

    async def enregistrer(*args):
        return None

    partie = SimpleNamespace(current_question=0, questions=[SimpleNamespace(time="30")], question_show=True, save=enregistrer)

    async def partie_en_cours(pin):
        return partie

    monkeypatch.setattr(serveur, "redis", RedisFactice(joueurs))
    monkeypatch.setattr(serveur.sio, "emit", emettre)
    monkeypatch.setattr(serveur, "get_session", session)
    monkeypatch.setattr(serveur, "has_already_answered", deja_repondu)
    monkeypatch.setattr(serveur, "check_answer", lambda partie, donnees: (True, "BGP"))
    monkeypatch.setattr(serveur.PlayGame, "get_from_redis", partie_en_cours)

    await serveur.submit_answer("sid-joueur", {"question_index": 0, "answer": "BGP"})
    return emis


@pytest.mark.asyncio
async def test_le_compteur_de_reponses_ne_va_qu_a_l_enseignant_de_la_partie(monkeypatch):
    emis = await evenements_d_une_reponse(monkeypatch, joueurs=2)
    assert emis == [("player_answer", f"admin:{PIN}")]


@pytest.mark.asyncio
async def test_la_fin_de_question_ne_va_qu_aux_joueurs_de_la_partie(monkeypatch):
    # Les joueurs l'écoutent aussi (play/question.svelte, application) : la salle de la partie, pas celle de l'enseignant
    emis = await evenements_d_une_reponse(monkeypatch, joueurs=1)
    assert emis == [("player_answer", f"admin:{PIN}"), ("everyone_answered", PIN)]
