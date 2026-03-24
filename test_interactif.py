# test_interactif.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.filter.filter import filtrer_prompt, traduire_en_anglais, normaliser_texte
from backend.llm import ask_llm

print("=" * 60)
print("🛡️  SecureLLM — Test interactif du filtre")
print("Tapez 'exit' pour quitter")
print("=" * 60)

while True:
    print()
    prompt = input("✏️  Entrez votre prompt : ").strip()

    if prompt.lower() == "exit":
        print("Au revoir !")
        break

    if not prompt:
        continue

    # Étape 1 — Traduction
    traduit = traduire_en_anglais(prompt)
    print(f"🌍 Traduction     : {traduit}")

    # Étape 2 — Normalisation
    normalise = normaliser_texte(traduit)
    print(f"🔧 Normalisation  : {normalise}")

    # Étape 3 — Décision du filtre
    result = filtrer_prompt(prompt)

    if result["blocked"]:
        score = f" | score ML: {result['ml_score']}" if result["ml_score"] else ""
        print(f"🔍 Décision       : 🚫 BLOQUÉ | méthode: {result['method']} | {result['reason']}{score}")
        print("⛔ Message non envoyé au LLM.")
    else:
        score = f" | score ML: {result['ml_score']}" if result["ml_score"] else ""
        print(f"🔍 Décision       : ✅ AUTORISÉ | méthode: {result['method']} | {result['reason']}{score}")
        print("📤 Envoi au LLM...")
        print("-" * 60)
        reponse = ask_llm(prompt)
        print(f"🤖 Réponse LLM    : {reponse}")
        print("-" * 60)