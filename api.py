import os
import sys
import json
import logging
from datetime import datetime
from typing import Optional

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_TOKEN"] = ""

import warnings
warnings.filterwarnings("ignore")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from pydantic import BaseModel

from modules.filter.filter        import filtrer_prompt
from modules.pii.pii_detector     import masquer_pii, masquer_pii_pour_rag
from modules.rag.rag_pipeline     import rag_pipeline
from backend.llm                  import ask_llm

# ══════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename  = "logs/securellm.log",
    level     = logging.INFO,
    format    = "%(asctime)s | %(levelname)s | %(message)s",
    datefmt   = "%Y-%m-%d %H:%M:%S",
    encoding  = "utf-8"
)
logger = logging.getLogger("securellm")

# ══════════════════════════════════════════════════════════
# INITIALISATION FASTAPI
# ══════════════════════════════════════════════════════════
app = FastAPI(
    title       = "🔐 SecureLLM API",
    description = "Plateforme de sécurisation des interactions avec les LLM",
    version     = "1.0.0"
)

# ══════════════════════════════════════════════════════════
# STATISTIQUES EN MÉMOIRE
# ══════════════════════════════════════════════════════════
stats = {
    "total_requetes"        : 0,
    "injections_bloquees"   : 0,
    "pii_detectees"         : 0,
    "reponses_rag"          : 0,
    "reponses_llm_general"  : 0,
    "demarrage"             : datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# ══════════════════════════════════════════════════════════
# MODÈLES PYDANTIC
# ══════════════════════════════════════════════════════════
class RequeteQuestion(BaseModel):
    question : str
    role     : str = "user"

class ReponseSecurisee(BaseModel):
    reponse        : str
    sources        : list
    mode           : str
    pii_detectees  : bool
    bloque         : bool
    raison_blocage : Optional[str] = None

# ══════════════════════════════════════════════════════════
# ENDPOINT 1 — GET /health
# ══════════════════════════════════════════════════════════
@app.get("/health")
def health():
    return {
        "status"   : "✅ SecureLLM API opérationnelle",
        "version"  : "1.0.0",
        "demarrage": stats["demarrage"]
    }

# ══════════════════════════════════════════════════════════
# ENDPOINT 2 — GET /stats
# ══════════════════════════════════════════════════════════
@app.get("/stats")
def get_stats():
    return {
        "total_requetes"       : stats["total_requetes"],
        "injections_bloquees"  : stats["injections_bloquees"],
        "pii_detectees"        : stats["pii_detectees"],
        "reponses_rag"         : stats["reponses_rag"],
        "reponses_llm_general" : stats["reponses_llm_general"],
        "taux_blocage"         : (
            round(stats["injections_bloquees"] / stats["total_requetes"] * 100, 1)
            if stats["total_requetes"] > 0 else 0
        ),
        "demarrage"            : stats["demarrage"]
    }

# ══════════════════════════════════════════════════════════
# ENDPOINT 3 — POST /ask
# ══════════════════════════════════════════════════════════
@app.post("/ask", response_model=ReponseSecurisee)
def ask(requete: RequeteQuestion):

    question  = requete.question
    user_role = requete.role
    stats["total_requetes"] += 1

    logger.info(f"REQUÊTE | role={user_role} | question={question[:80]}")

    # ── MODULE 1 : Filtrage injection ─────────────────────
    resultat_filtre = filtrer_prompt(question)

    if resultat_filtre["blocked"]:
        stats["injections_bloquees"] += 1
        raison = resultat_filtre["reason"]
        logger.warning(f"BLOQUÉ | méthode={resultat_filtre['method']} | raison={raison}")

        return ReponseSecurisee(
            reponse        = "⛔ Requête bloquée — injection détectée.",
            sources        = [],
            mode           = "bloque",
            pii_detectees  = False,
            bloque         = True,
            raison_blocage = raison
        )

    # ── MODULE 2 : Masquage PII de la question ────────────
    resultat_pii  = masquer_pii(question)
    question_rag  = masquer_pii_pour_rag(question)
    pii_trouvees  = resultat_pii["modifie"] or (question_rag != question)

    if pii_trouvees:
        stats["pii_detectees"] += 1
        logger.info(f"PII | masquée dans la question")

    # ── MODULE 3 : RAG sécurisé + LLM ────────────────────
    resultat_rag = rag_pipeline(
        question  = question_rag,
        user_role = user_role
    )

    # ── DÉCISION : RAG ou Fallback LLM ───────────────────
    if not resultat_rag["bloque"]:
        reponse_brute = resultat_rag["reponse"]
        sources       = resultat_rag["sources"]
        mode          = "rag_local"
        stats["reponses_rag"] += 1
    else:
        reponse_llm   = ask_llm(question_rag)
        reponse_brute = (
            "⚠️ Aucun document autorisé trouvé dans la base locale pour votre rôle.\n"
            "Voici une réponse générale du LLM :\n\n"
            + reponse_llm
        )
        sources       = []
        mode          = "llm_general"
        stats["reponses_llm_general"] += 1

    # ── Réponse finale ────────────────────────────────────
    reponse_finale = reponse_brute

    logger.info(f"RÉPONSE | mode={mode} | sources={sources} | pii={pii_trouvees}")

    return ReponseSecurisee(
        reponse        = reponse_finale,
        sources        = sources,
        mode           = mode,
        pii_detectees  = pii_trouvees,
        bloque         = False,
        raison_blocage = None
    )