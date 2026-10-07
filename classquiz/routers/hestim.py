# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""HESTIM : lecture des quiz par la plateforme (devoirs notés).

Planner donne un quiz en devoir : il liste les quiz d'un enseignant puis copie les questions du
quiz choisi, et corrige lui-même les réponses des étudiants. Ces routes ne servent qu'à Planner :
chaque requête est signée avec le secret partagé HESTIM_WEBHOOK_SECRET (HMAC-SHA256 de
« <horodatage>.<méthode>.<chemin et requête> », à 5 minutes près) ; sans configuration elles
répondent 404, comme si elles n'existaient pas.
"""

import hashlib
import hmac
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from classquiz.config import settings
from classquiz.db.models import Quiz, User

router = APIRouter()
_TOLERANCE_S = 300


def _verifier(requete: Request) -> None:
    secret = settings().hestim_webhook_secret
    if not secret or len(secret) < 32:
        raise HTTPException(status_code=404)
    horodatage = requete.headers.get("x-hestim-timestamp", "")
    signature = requete.headers.get("x-hestim-signature", "")
    if not horodatage.isdigit() or abs(time.time() - int(horodatage)) > _TOLERANCE_S:
        raise HTTPException(status_code=401, detail="signature expirée")
    cible = requete.url.path + (f"?{requete.url.query}" if requete.url.query else "")
    attendue = hmac.new(secret.encode(), f"{horodatage}.{requete.method}.{cible}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(attendue, signature):
        raise HTTPException(status_code=401, detail="signature invalide")


@router.get("/quizzes")
async def quiz_de_l_enseignant(requete: Request, email: str):
    """Quiz d'un enseignant (par son adresse) : identifiant, titre, nombre de questions."""
    _verifier(requete)
    user = await User.objects.get_or_none(email=email.lower())
    if user is None:
        return []
    quiz = await Quiz.objects.filter(user_id=user.id).order_by(Quiz.updated_at.desc()).all()
    return [{"id": str(q.id), "titre": q.title, "nb_questions": len(q.questions), "modifie_le": q.updated_at.isoformat()} for q in quiz]


@router.get("/quiz/{quiz_id}")
async def contenu_du_quiz(requete: Request, quiz_id: str, email: str):
    """Questions complètes (avec les réponses attendues) d'un quiz appartenant à cet enseignant."""
    _verifier(requete)
    try:
        identifiant = uuid.UUID(quiz_id)
    except ValueError:
        raise HTTPException(status_code=404)
    user = await User.objects.get_or_none(email=email.lower())
    quiz = await Quiz.objects.get_or_none(id=identifiant, user_id=user.id) if user else None
    if quiz is None:
        raise HTTPException(status_code=404)
    # Les questions reviennent de la base en dictionnaires (champ JSON), parfois en modèles
    questions = [q if isinstance(q, dict) else q.model_dump(mode="json") for q in quiz.questions]
    return {"id": str(quiz.id), "titre": quiz.title, "description": quiz.description, "questions": questions}
