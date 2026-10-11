# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""Routes HESTIM : signature des écritures et nettoyage d'un quiz préparé dans Planner."""

import hashlib
import hmac
import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException

from classquiz.db.models import Quiz
from classquiz.helpers.hestim import identifiant_de_partie_valide
from classquiz.routers.hestim import QuestionAEcrire, partie_nouvelle, questions_nettoyees, signature_attendue

SECRET = "s" * 32


def question(**champs) -> QuestionAEcrire:
    base = {
        "question": "Quel protocole route entre systèmes autonomes ?",
        "time": 30,
        "type": "ABCD",
        "answers": [{"answer": "BGP", "right": True}, {"answer": "OSPF", "right": False}],
    }
    return QuestionAEcrire(**{**base, **champs})


def test_signature_d_une_lecture_inchangee():
    attendue = hmac.new(SECRET.encode(), b"1700000000.GET./api/v1/hestim/quizzes?email=a%40b.c", hashlib.sha256).hexdigest()
    assert signature_attendue(SECRET, "1700000000", "GET", "/api/v1/hestim/quizzes?email=a%40b.c") == attendue


def test_signature_d_une_ecriture_couvre_le_corps():
    corps = b'{"titre":"Routage"}'
    signee = signature_attendue(SECRET, "1700000000", "POST", "/api/v1/hestim/quiz", corps)
    assert signee != signature_attendue(SECRET, "1700000000", "POST", "/api/v1/hestim/quiz", corps + b" ")
    assert signee != signature_attendue(SECRET, "1700000000", "POST", "/api/v1/hestim/quiz")


def test_questions_au_format_classquiz_sans_balises_interdites():
    propres = questions_nettoyees([question(question="<script>alert(1)</script>Le <b>routage</b> ?")])
    assert propres[0]["question"] == "alert(1)Le <b>routage</b> ?"
    assert propres[0]["time"] == "30"
    assert propres[0]["type"] == "ABCD"
    assert [(r["answer"], r["right"]) for r in propres[0]["answers"]] == [("BGP", True), ("OSPF", False)]


@pytest.mark.parametrize(
    "champs",
    [
        {"type": "TEXT"},
        {"time": 2},
        {"question": "   "},
        {"answers": [{"answer": "BGP", "right": True}]},
        {"answers": [{"answer": "BGP", "right": False}, {"answer": "OSPF", "right": False}]},
        {"answers": [{"answer": "BGP", "right": True}, {"answer": "OSPF", "right": True}]},
    ],
)
def test_question_incoherente_refusee(champs):
    with pytest.raises(HTTPException) as erreur:
        questions_nettoyees([question(**champs)])
    assert erreur.value.status_code == 422


def test_plusieurs_bonnes_reponses_acceptees_en_check():
    propres = questions_nettoyees([question(type="CHECK", answers=[{"answer": "BGP", "right": True}, {"answer": "OSPF", "right": True}, {"answer": "FTP", "right": False}])])
    assert propres[0]["type"] == "CHECK"


def test_partie_demarree_depuis_planner_sans_captcha():
    proprietaire = uuid.uuid4()
    quiz = Quiz(
        id=uuid.uuid4(),
        public=False,
        title="Routage",
        description="",
        questions=questions_nettoyees([question()]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    partie = partie_nouvelle(quiz, proprietaire, "482913")
    assert (partie.game_pin, partie.title, partie.quiz_id, partie.user_id) == ("482913", "Routage", quiz.id, proprietaire)
    assert partie.captcha_enabled is False and partie.started is False and partie.game_mode == "kahoot"
    assert [q.question for q in partie.questions] == ["Quel protocole route entre systèmes autonomes ?"]
    # L'identifiant donne la main sur la partie : il est tiré au hasard à chaque partie
    assert partie.game_id != partie_nouvelle(quiz, proprietaire, "482913").game_id


def test_la_main_sur_une_partie_demande_son_identifiant():
    partie = partie_nouvelle(Quiz(id=uuid.uuid4(), title="Routage", questions=questions_nettoyees([question()])), uuid.uuid4(), "482913")
    garde = partie.model_dump_json()
    assert identifiant_de_partie_valide(garde, str(partie.game_id))
    assert identifiant_de_partie_valide(garde, str(partie.game_id).upper())
    # Le code seul ne suffit pas : identifiant inventé, vide, ou partie absente de Redis
    assert not identifiant_de_partie_valide(garde, str(uuid.uuid4()))
    assert not identifiant_de_partie_valide(garde, "")
    assert not identifiant_de_partie_valide(None, str(partie.game_id))
    assert not identifiant_de_partie_valide("pas du json", str(partie.game_id))


def test_l_identifiant_de_la_partie_ne_part_pas_chez_un_joueur():
    partie = partie_nouvelle(Quiz(id=uuid.uuid4(), title="Routage", questions=questions_nettoyees([question()])), uuid.uuid4(), "482913")
    (donnees,) = partie.to_player_data()
    # Ce qu'un joueur reçoit en rejoignant : de quoi afficher la partie, rien qui donne la main
    assert donnees["game_pin"] == "482913" and donnees["title"] == "Routage" and donnees["question_count"] == 1
    assert "game_id" not in donnees and str(partie.game_id) not in str(donnees)
    assert "questions" not in donnees and "user_id" not in donnees


def test_quiz_vide_ou_trop_long_refuse():
    for questions in ([], [question()] * 51):
        with pytest.raises(HTTPException):
            questions_nettoyees(questions)
