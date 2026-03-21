# modules/filter/filter.py
import re
import joblib
import os

# ── RÈGLES HEURISTIQUES ──────────────────────────────────────────────────────

MOTS_SUSPECTS = [
    # Classiques
    "ignore previous", "ignore all", "ignore your",
    "oublie tes instructions", "oublie tout",
    "agis comme", "tu es maintenant",
    "bypass", "jailbreak", "DAN mode",
    "pretend you are", "act as if",
    "you are no longer", "forget you are",
    # Injection via balises
    "system:", "[system]", "<instructions>",
    "new instructions:", "###override",
    # Exfiltration
    "repeat your instructions", "tell me your prompt",
    "what is your system prompt", "reveal your instructions",
    "show hidden instructions",
    # Manipulation de rôle
    "developer mode", "god mode", "unrestricted mode",
    "simulate a chatbot that", "roleplay as",
    "you have no restrictions", "no restrictions apply",
]

PATTERNS_REGEX = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"(you\s+are|act\s+as|pretend\s+to\s+be).{0,30}(without\s+restrictions|unrestricted)",
    r"system\s*:\s*new\s+instructions",
    r"<\s*/?system\s*>",
    r"\[?\s*override\s*\]?",
    r"forget\s+(everything|all|your)\s+(you\s+know|instructions|rules)",
    r"(repeat|print|show|reveal).{0,20}(system prompt|instructions|context)",
]

def detecter_heuristique(prompt: str):
    prompt_lower = prompt.lower()
    for mot in MOTS_SUSPECTS:
        if mot.lower() in prompt_lower:
            return True, f"Mot suspect : '{mot}'"
    for pattern in PATTERNS_REGEX:
        if re.search(pattern, prompt_lower):
            return True, f"Pattern suspect détecté"
    return False, "OK"


# ── CLASSIFICATEUR ML ─────────────────────────────────────────────────────────

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../models/classifier.pkl"
)

def detecter_ml(prompt: str):
    if not os.path.exists(MODEL_PATH):
        return False, 0.0
    pipeline = joblib.load(MODEL_PATH)
    proba = pipeline.predict_proba([prompt])[0]
    score = round(proba[1], 3)
    return score >= 0.70, score


# ── FILTRE COMBINÉ ────────────────────────────────────────────────────────────

def filtrer_prompt(prompt: str) -> dict:
    # 1. Heuristique (rapide)
    suspect, raison = detecter_heuristique(prompt)
    if suspect:
        return {
            "blocked": True,
            "reason": raison,
            "ml_score": None,
            "method": "heuristique"
        }

    # 2. ML (plus profond)
    malveillant, score = detecter_ml(prompt)
    if malveillant:
        return {
            "blocked": True,
            "reason": f"Score ML élevé : {score}",
            "ml_score": score,
            "method": "ml"
        }

    return {
        "blocked": False,
        "reason": "Prompt sûr",
        "ml_score": score,
        "method": "aucun"
    }