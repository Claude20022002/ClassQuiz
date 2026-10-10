# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""Routes HESTIM : signature des écritures et nettoyage d'un quiz préparé dans Planner."""

import hashlib
import hmac

import pytest
from fastapi import HTTPException

from classquiz.routers.hestim import QuestionAEcrire, questions_nettoyees, signature_attendue

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


def test_quiz_vide_ou_trop_long_refuse():
    for questions in ([], [question()] * 51):
        with pytest.raises(HTTPException):
            questions_nettoyees(questions)
