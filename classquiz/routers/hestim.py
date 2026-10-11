# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""HESTIM : lecture et écriture des quiz par la plateforme.

Planner donne un quiz en devoir : il liste les quiz d'un enseignant puis copie les questions du
quiz choisi, et corrige lui-même les réponses des étudiants. Il crée aussi les quiz que
l'enseignant a préparés dans Planner (générés par l'IA puis relus), sans que l'enseignant ait à
ouvrir ClassQuiz : son compte est créé au besoin ; il les modifie ensuite depuis Planner. Il démarre enfin une partie en direct pour
l'enseignant, qui l'anime depuis Planner. Ces routes ne servent qu'à Planner :
chaque requête est signée avec le secret partagé HESTIM_WEBHOOK_SECRET (HMAC-SHA256 de
« <horodatage>.<méthode>.<chemin et requête> », à 5 minutes près ; pour une écriture, suivi de
« .<SHA-256 du corps> ») ; sans configuration elles répondent 404, comme si elles n'existaient pas.
"""

import hashlib
import hmac
import html
import secrets
import time
import uuid
from datetime import datetime

import asyncpg
import bleach
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from classquiz.config import ALLOWED_TAGS_FOR_QUIZ, meilisearch, redis, settings
from classquiz.db.models import ABCDQuizAnswer, GameInLobby, PlayGame, Quiz, QuizQuestion, QuizQuestionType, User, UserAuthTypes
from classquiz.helpers import get_meili_data
from classquiz.helpers.avatar import gzipped_user_avatar

router = APIRouter()
_TOLERANCE_S = 300
_QUESTIONS_MAX = 50
_CORPS_MAX = 512 * 1024
# Types qu'un quiz préparé dans Planner peut contenir (ceux que ses devoirs savent noter)
_TYPES_ECRITS = {QuizQuestionType.ABCD, QuizQuestionType.CHECK}
# Mode d'une partie lancée depuis Planner : questions et réponses sur l'écran projeté
_MODE_DE_JEU = "kahoot"


def signature_attendue(secret: str, horodatage: str, methode: str, cible: str, corps: bytes | None = None) -> str:
    """Signature d'une requête de Planner ; le corps d'une écriture est couvert par son empreinte."""
    message = f"{horodatage}.{methode}.{cible}"
    if corps is not None:
        message += f".{hashlib.sha256(corps).hexdigest()}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _verifier(requete: Request, corps: bytes | None = None) -> None:
    secret = settings().hestim_webhook_secret
    if not secret or len(secret) < 32:
        raise HTTPException(status_code=404)
    horodatage = requete.headers.get("x-hestim-timestamp", "")
    signature = requete.headers.get("x-hestim-signature", "")
    if not horodatage.isdigit() or abs(time.time() - int(horodatage)) > _TOLERANCE_S:
        raise HTTPException(status_code=401, detail="signature expirée")
    cible = requete.url.path + (f"?{requete.url.query}" if requete.url.query else "")
    attendue = signature_attendue(secret, horodatage, requete.method, cible, corps)
    if not hmac.compare_digest(attendue, signature):
        raise HTTPException(status_code=401, detail="signature invalide")


class ReponseAEcrire(BaseModel):
    answer: str
    right: bool


class QuestionAEcrire(BaseModel):
    question: str
    time: int
    type: QuizQuestionType
    answers: list[ReponseAEcrire]


class QuizAEcrire(BaseModel):
    """Quiz préparé dans Planner. `sub` et `username` sont ceux que Planner donne à la connexion
    OpenID : le compte créé ici est le même que celui d'une connexion ultérieure à ClassQuiz."""

    email: str
    sub: uuid.UUID
    username: str
    titre: str
    description: str = ""
    questions: list[QuestionAEcrire]


def _texte(valeur: str) -> str:
    return bleach.clean(valeur, tags=ALLOWED_TAGS_FOR_QUIZ, strip=True).strip()


def questions_nettoyees(questions: list[QuestionAEcrire]) -> list[dict]:
    """Questions au format de ClassQuiz, balises interdites retirées ; refuse un quiz incohérent."""
    if not 1 <= len(questions) <= _QUESTIONS_MAX:
        raise HTTPException(status_code=422, detail=f"1 à {_QUESTIONS_MAX} questions attendues")
    propres = []
    for numero, q in enumerate(questions, start=1):
        if q.type not in _TYPES_ECRITS:
            raise HTTPException(status_code=422, detail=f"question {numero} : type non accepté")
        enonce = _texte(q.question)
        reponses = [ABCDQuizAnswer(answer=html.unescape(_texte(r.answer)), right=r.right) for r in q.answers]
        justes = sum(1 for r in reponses if r.right)
        if not enonce or not 2 <= len(reponses) <= 6 or any(not r.answer for r in reponses):
            raise HTTPException(status_code=422, detail=f"question {numero} : énoncé et 2 à 6 réponses non vides attendus")
        if justes == 0 or (q.type == QuizQuestionType.ABCD and justes != 1):
            raise HTTPException(status_code=422, detail=f"question {numero} : bonnes réponses incohérentes")
        if not 5 <= q.time <= 600:
            raise HTTPException(status_code=422, detail=f"question {numero} : durée de 5 à 600 secondes")
        propres.append(QuizQuestion(question=enonce, time=str(q.time), type=q.type, answers=reponses).model_dump(mode="json"))
    return propres


async def _compte_de(donnees: QuizAEcrire) -> User:
    """Compte de l'enseignant, créé s'il n'a jamais ouvert ClassQuiz (même identité qu'en OpenID)."""
    # L'adresse est gardée telle que Planner la donne (la connexion OpenID la recherche à l'identique)
    email = donnees.email.strip()
    user = await User.objects.get_or_none(email=email) or await User.objects.get_or_none(email=email.lower())
    if user is not None:
        return user
    nom = donnees.username.strip()[:100] or email.split("@")[0][:100]
    # Nom d'utilisateur déjà pris par un autre compte : un suffixe tiré de l'identifiant Planner
    for candidat in (nom, f"{nom[:91]}-{donnees.sub.hex[-8:]}"):
        try:
            return await User.objects.create(
                id=uuid.uuid4(),
                email=email,
                username=candidat,
                verified=True,
                auth_type=UserAuthTypes.CUSTOM,
                google_uid=donnees.sub.hex,
                avatar=gzipped_user_avatar(),
            )
        except asyncpg.exceptions.UniqueViolationError:
            # Créé entre-temps par une connexion OpenID ? On le reprend ; sinon on essaie l'autre nom
            user = await User.objects.get_or_none(email=email)
            if user is not None:
                return user
    raise HTTPException(status_code=409, detail="compte impossible à créer")


@router.post("/quiz", status_code=201)
async def creer_le_quiz(requete: Request):
    """Crée un quiz privé pour l'enseignant désigné par son adresse : { id, titre, nb_questions }."""
    corps = await requete.body()
    _verifier(requete, corps)
    if len(corps) > _CORPS_MAX:
        raise HTTPException(status_code=413)
    try:
        donnees = QuizAEcrire.model_validate_json(corps)
    except ValidationError:
        raise HTTPException(status_code=422, detail="quiz illisible")
    titre = _texte(donnees.titre)[:300]
    if not titre:
        raise HTTPException(status_code=422, detail="titre requis")
    questions = questions_nettoyees(donnees.questions)
    user = await _compte_de(donnees)
    maintenant = datetime.now()
    quiz = Quiz(
        id=uuid.uuid4(),
        public=False,
        title=titre,
        description=_texte(donnees.description)[:2000],
        questions=questions,
        user_id=user.id,
        created_at=maintenant,
        updated_at=maintenant,
    )
    await quiz.save()
    await redis.delete("global_quiz_count")
    return {"id": str(quiz.id), "titre": quiz.title, "nb_questions": len(questions)}


class QuizAModifier(BaseModel):
    """Nouvelle version d'un quiz de l'enseignant désigné par son adresse : tout est remplacé."""

    email: str
    titre: str
    description: str = ""
    questions: list[QuestionAEcrire]


@router.post("/quiz/{quiz_id}")
async def modifier_le_quiz(requete: Request, quiz_id: str):
    """Remplace le titre, la description et les questions d'un quiz de l'enseignant : { id, titre, nb_questions }.

    Les parties déjà lancées et les devoirs déjà donnés gardent leur copie des questions.
    """
    corps = await requete.body()
    _verifier(requete, corps)
    if len(corps) > _CORPS_MAX:
        raise HTTPException(status_code=413)
    try:
        donnees = QuizAModifier.model_validate_json(corps)
        identifiant = uuid.UUID(quiz_id)
    except (ValidationError, ValueError):
        raise HTTPException(status_code=422, detail="quiz illisible")
    titre = _texte(donnees.titre)[:300]
    if not titre:
        raise HTTPException(status_code=422, detail="titre requis")
    questions = questions_nettoyees(donnees.questions)
    email = donnees.email.strip()
    user = await User.objects.get_or_none(email=email) or await User.objects.get_or_none(email=email.lower())
    # Seulement ses propres quiz. 422 et non 404 : Planner lit un 404 en écriture comme « route absente »
    quiz = await Quiz.objects.get_or_none(id=identifiant, user_id=user.id) if user else None
    if quiz is None:
        raise HTTPException(status_code=422, detail="quiz introuvable pour cet enseignant")
    quiz.title = titre
    quiz.description = _texte(donnees.description)[:2000]
    quiz.questions = questions
    quiz.updated_at = datetime.now()
    await quiz.update()
    if quiz.public:
        # Comme l'éditeur de ClassQuiz : la recherche suit le quiz public ; elle ne bloque pas l'enregistrement
        try:
            meilisearch.index(settings().meilisearch_index).update_documents([await get_meili_data(quiz)])
        except Exception:
            pass
    return {"id": str(quiz.id), "titre": quiz.title, "nb_questions": len(questions)}


class PartieADemarrer(BaseModel):
    """Partie en direct demandée par Planner pour un quiz de l'enseignant désigné par son adresse."""

    email: str
    quiz_id: uuid.UUID


def partie_nouvelle(quiz: Quiz, user_id: uuid.UUID, game_pin: str) -> PlayGame:
    """Partie prête à être rejointe, comme la crée /api/v1/quiz/start, sans captcha : les étudiants
    arrivent par l'application de la plateforme, qui remplit déjà le code."""
    return PlayGame(
        quiz_id=quiz.id,
        game_pin=game_pin,
        questions=quiz.questions,
        game_id=uuid.uuid4(),
        title=quiz.title,
        description=quiz.description or "",
        captcha_enabled=False,
        cover_image=quiz.cover_image,
        game_mode=_MODE_DE_JEU,
        user_id=user_id,
        background_color=quiz.background_color,
        background_image=quiz.background_image,
    )


@router.post("/parties", status_code=201)
async def demarrer_la_partie(requete: Request):
    """Démarre une partie d'un quiz de l'enseignant : { game_id, game_pin, quiz_id, titre, nb_questions, game_mode }.

    `game_id` donne la main sur la partie (register_as_admin) : Planner ne le remet qu'à l'enseignant.
    Pas de webhook « game.started » ici : Planner, qui demande la partie, l'enregistre lui-même.
    """
    corps = await requete.body()
    _verifier(requete, corps)
    if len(corps) > _CORPS_MAX:
        raise HTTPException(status_code=413)
    try:
        donnees = PartieADemarrer.model_validate_json(corps)
    except ValidationError:
        raise HTTPException(status_code=422, detail="demande illisible")
    email = donnees.email.strip()
    user = await User.objects.get_or_none(email=email) or await User.objects.get_or_none(email=email.lower())
    # Seulement ses propres quiz : un quiz public d'un autre compte ne se lance pas par cette route
    quiz = await Quiz.objects.get_or_none(id=donnees.quiz_id, user_id=user.id) if user else None
    if quiz is None:
        raise HTTPException(status_code=422, detail="quiz introuvable pour cet enseignant")
    quiz.plays += 1
    await quiz.update()
    game_pin = str(100000 + secrets.randbelow(900000))
    while await redis.get(f"game:{game_pin}") is not None:
        game_pin = str(100000 + secrets.randbelow(900000))
    game = partie_nouvelle(quiz, user.id, game_pin)
    await redis.set(f"game:{game_pin}", game.model_dump_json(), ex=18000)
    await redis.set(f"game_pin:{user.id}:{quiz.id}", game_pin, ex=18000)
    await redis.set(
        f"game_in_lobby:{user.id.hex}",
        GameInLobby(game_id=game.game_id, game_pin=game_pin, quiz_title=quiz.title).model_dump_json(),
        ex=900,
    )
    return {
        "game_id": str(game.game_id),
        "game_pin": game_pin,
        "quiz_id": str(quiz.id),
        "titre": quiz.title,
        "nb_questions": len(quiz.questions),
        "game_mode": _MODE_DE_JEU,
    }


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
