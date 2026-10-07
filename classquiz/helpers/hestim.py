# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""HESTIM : signale à la plateforme (HESTIM Planner) le début et la fin des parties.

- game.started : Planner rattache la partie à la séance en cours de l'enseignant et prévient
  ses étudiants.
- game.finished : scores, bonnes réponses et réponses libres. Chaque étudiant arrivé depuis
  la plateforme porte un jeton signé par Planner (?hid=), gardé avec son pseudo : Planner le
  vérifie et rattache le score à l'étudiant, donc au module (classement par groupe de TP).
Le corps est signé : HMAC-SHA256 de « <horodatage>.<corps> » avec le secret partagé
HESTIM_WEBHOOK_SECRET, en hexadécimal (en-têtes X-Hestim-Timestamp et X-Hestim-Signature).
L'envoi part en tâche de fond : un Planner lent ou absent ne retarde jamais la partie.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timezone

import httpx

from classquiz.config import redis, settings

logger = logging.getLogger(__name__)
_taches: set[asyncio.Task] = set()


def _signer(secret: str, horodatage: str, corps: bytes) -> str:
    return hmac.new(secret.encode(), f"{horodatage}.".encode() + corps, hashlib.sha256).hexdigest()


async def _envoyer(url: str, secret: str, evenement: dict) -> None:
    corps = json.dumps(evenement, separators=(",", ":")).encode()
    for essai in range(3):
        horodatage = str(int(time.time()))
        entetes = {
            "Content-Type": "application/json",
            "X-Hestim-Timestamp": horodatage,
            "X-Hestim-Signature": _signer(secret, horodatage, corps),
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                reponse = await client.post(url, content=corps, headers=entetes)
            if reponse.status_code < 500:
                if reponse.status_code >= 400:
                    logger.warning("Webhook HESTIM refusé (%s)", reponse.status_code)
                return
        except httpx.HTTPError as erreur:
            logger.warning("Webhook HESTIM injoignable (%s)", erreur)
        await asyncio.sleep(2**essai)


def signaler_partie_demarree(*, game_id, game_pin: str, quiz_id, quiz_title: str, game_mode: str, user_email: str) -> None:
    """Planifie l'envoi ; sans configuration (URL ou secret), ne fait rien."""
    reglages = settings()
    if not reglages.hestim_webhook_url or not reglages.hestim_webhook_secret:
        return
    evenement = {
        "event": "game.started",
        "game_id": str(game_id),
        "game_pin": str(game_pin),
        "quiz_id": str(quiz_id),
        "quiz_title": quiz_title,
        "game_mode": game_mode,
        "user_email": user_email,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    tache = asyncio.create_task(_envoyer(reglages.hestim_webhook_url, reglages.hestim_webhook_secret, evenement))
    # Garder une référence : sinon la tâche peut être ramassée avant la fin
    _taches.add(tache)
    tache.add_done_callback(_taches.discard)

# ── Fin de partie ──────────────────────────────────────────────────────────

_JETON = re.compile(r"^[A-Za-z0-9._-]{1,200}$")
_BALISES = re.compile(r"<[^>]*>")
_DUREE_REDIS_S = 7200
_JOUEURS_MAX = 300
_REPONSES_LIBRES_MAX = 300


def _actif() -> bool:
    reglages = settings()
    return bool(reglages.hestim_webhook_url and reglages.hestim_webhook_secret)


async def enregistrer_joueur(game_pin: str, username: str, jeton: str | None) -> None:
    """Garde le jeton HESTIM du joueur avec son pseudo (le temps de la partie)."""
    if not jeton or not _actif() or not _JETON.match(jeton):
        return
    cle = f"game:{game_pin}:players:hestim"
    await redis.hset(cle, username, jeton)
    await redis.expire(cle, _DUREE_REDIS_S)


def _texte(valeur, longueur: int) -> str:
    return _BALISES.sub("", str(valeur or "")).strip()[:longueur]


async def signaler_partie_terminee(game, game_pin: str) -> None:
    """Envoie les scores à Planner, une seule fois par partie ; sans configuration, ne fait rien."""
    if not _actif() or game is None:
        return
    # Les résultats finaux peuvent être demandés puis enregistrés : un seul envoi
    if not await redis.set(f"game:{game_pin}:hestim:terminee", "1", nx=True, ex=_DUREE_REDIS_S):
        return
    from classquiz.db.models import User

    hote = await User.objects.get_or_none(id=game.user_id)
    scores = await redis.hgetall(f"game_session:{game_pin}:player_scores")
    jetons = await redis.hgetall(f"game:{game_pin}:players:hestim")
    bonnes: dict[str, int] = {}
    questions = []
    for i, question in enumerate(game.questions):
        try:
            reponses = json.loads(await redis.get(f"game_session:{game_pin}:{i}") or "[]")
        except (TypeError, ValueError):
            reponses = []
        for r in reponses:
            if r.get("right"):
                bonnes[r.get("username", "")] = bonnes.get(r.get("username", ""), 0) + 1
        type_question = str(question.type.value if hasattr(question.type, "value") else question.type or "ABCD")
        resume = {"index": i, "type": type_question, "question": _texte(question.question, 300), "reponses": len(reponses)}
        # Réponses libres : nuage de mots côté Planner
        if type_question == "TEXT":
            resume["reponses_libres"] = [_texte(r.get("answer"), 100) for r in reponses[:_REPONSES_LIBRES_MAX]]
        questions.append(resume)

    noms = list(scores.keys() | jetons.keys())[:_JOUEURS_MAX]
    evenement = {
        "event": "game.finished",
        "game_id": str(game.game_id),
        "game_pin": str(game_pin),
        "quiz_title": game.title,
        "user_email": hote.email if hote else None,
        "nb_questions": len(game.questions),
        "joueurs": [
            {"pseudo": nom[:60], "score": int(float(scores.get(nom) or 0)), "bonnes": bonnes.get(nom, 0), "hid": jetons.get(nom)}
            for nom in noms
        ],
        "questions": questions,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    reglages = settings()
    tache = asyncio.create_task(_envoyer(reglages.hestim_webhook_url, reglages.hestim_webhook_secret, evenement))
    _taches.add(tache)
    tache.add_done_callback(_taches.discard)
