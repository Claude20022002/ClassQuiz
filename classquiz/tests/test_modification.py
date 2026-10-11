# SPDX-FileCopyrightText: 2026 HESTIM
#
# SPDX-License-Identifier: MPL-2.0

"""Route HESTIM de mise à jour d'un quiz (lot IA-4) : signée, réservée aux quiz de l'enseignant."""

import json
import time
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import classquiz.routers.hestim as hestim

SECRET = "s" * 32
PROF = SimpleNamespace(id=uuid.uuid4(), email="prof@hestim.ma")
QUIZ_ID = uuid.uuid4()


class QuizFactice:
    """Un quiz en base : ce que la route lit, modifie et enregistre."""

    def __init__(self, proprietaire):
        self.id, self.user_id, self.public = QUIZ_ID, proprietaire, False
        self.title, self.description, self.questions = "Routage", "", []
        self.enregistre = False

    async def update(self):
        self.enregistre = True


@pytest.fixture
def quiz(monkeypatch):
    stocke = QuizFactice(PROF.id)

    async def utilisateur(email):
        return PROF if email == PROF.email else None

    async def quiz_de(id, user_id):
        return stocke if (id, user_id) == (stocke.id, stocke.user_id) else None

    monkeypatch.setattr(hestim, "User", SimpleNamespace(objects=SimpleNamespace(get_or_none=lambda email: utilisateur(email))))
    monkeypatch.setattr(hestim, "Quiz", SimpleNamespace(objects=SimpleNamespace(get_or_none=lambda id, user_id: quiz_de(id, user_id))))
    monkeypatch.setattr(hestim, "settings", lambda: SimpleNamespace(hestim_webhook_secret=SECRET, meilisearch_index="classquiz"))
    return stocke


def envoyer(corps: dict, quiz_id=QUIZ_ID, secret=SECRET):
    app = FastAPI()
    app.include_router(hestim.router, prefix="/api/v1/hestim")
    chemin = f"/api/v1/hestim/quiz/{quiz_id}"
    texte = json.dumps(corps).encode()
    horodatage = str(int(time.time()))
    entetes = {
        "x-hestim-timestamp": horodatage,
        "x-hestim-signature": hestim.signature_attendue(secret, horodatage, "POST", chemin, texte),
        "content-type": "application/json",
    }
    return TestClient(app).post(chemin, content=texte, headers=entetes)


def nouvelle_version(**champs) -> dict:
    question = {"question": "Quel protocole route entre systèmes autonomes ?", "time": 30, "type": "ABCD",
                "answers": [{"answer": "BGP", "right": True}, {"answer": "OSPF", "right": False}]}
    return {"email": PROF.email, "titre": "Routage, version 2", "questions": [question, {**question, "question": "Et à l'intérieur ?"}], **champs}


def test_le_quiz_est_remplace_et_enregistre(quiz):
    reponse = envoyer(nouvelle_version(titre="<b>Routage</b>, version 2<script>x</script>"))
    assert reponse.status_code == 200
    assert reponse.json() == {"id": str(QUIZ_ID), "titre": "<b>Routage</b>, version 2x", "nb_questions": 2}
    assert quiz.enregistre and [q["question"] for q in quiz.questions] == ["Quel protocole route entre systèmes autonomes ?", "Et à l'intérieur ?"]


def test_le_quiz_d_un_autre_enseignant_ne_se_modifie_pas(quiz):
    autre = envoyer(nouvelle_version(email="collegue@hestim.ma"))
    absent = envoyer(nouvelle_version(), quiz_id=uuid.uuid4())
    # 422 et non 404 : pour Planner, un 404 en écriture veut dire « route absente, fork à mettre à jour »
    assert (autre.status_code, absent.status_code) == (422, 422)
    assert not quiz.enregistre


def test_une_version_incoherente_ne_touche_pas_au_quiz(quiz):
    sans_bonne_reponse = nouvelle_version()
    sans_bonne_reponse["questions"][0]["answers"][0]["right"] = False
    assert envoyer(sans_bonne_reponse).status_code == 422
    assert envoyer(nouvelle_version(titre="  ")).status_code == 422
    assert envoyer(nouvelle_version(), quiz_id="pas-un-uuid").status_code == 422
    assert not quiz.enregistre


def test_une_requete_mal_signee_est_refusee(quiz):
    assert envoyer(nouvelle_version(), secret="x" * 32).status_code == 401
    assert not quiz.enregistre
