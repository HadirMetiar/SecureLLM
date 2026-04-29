import os
import sys
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_TOKEN"] = ""
import warnings
warnings.filterwarnings("ignore")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.filter.filter    import filtrer_prompt
from modules.pii.pii_detector import masquer_pii, masquer_pii_pour_rag
from modules.rag.rag_pipeline import rag_pipeline
from backend.llm              import ask_llm

VERT  = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
BLEU  = "\033[94m"
CYAN  = "\033[96m"
VIOLET= "\033[95m"
RESET = "\033[0m"
GRAS  = "\033[1m"

def afficher_banniere():
    print(f"\n{BLEU}{'='*65}{RESET}")
    print(f"{GRAS}   🔐 SecureLLM — Pipeline Hybride Sécurisé (Type 3){RESET}")
    print(f"{BLEU}{'='*65}{RESET}")
    print(f"  {JAUNE}➤  Module 1 : Filtrage injection      (traduction EN){RESET}")
    print(f"  {JAUNE}➤  Module 2 : Masquage PII            (traduction EN){RESET}")
    print(f"  {JAUNE}➤  Module 3 : RAG sécurisé            (langue originale){RESET}")
    print(f"  {VIOLET}➤  Fallback  : LLM général Groq       (si RAG échoue){RESET}")
    print(f"{BLEU}{'='*65}{RESET}")
    print(f"  {CYAN}Tape 'quit' pour quitter{RESET}")
    print(f"  {CYAN}Tape 'role' pour changer ton rôle{RESET}")
    print(f"{BLEU}{'='*65}{RESET}\n")

def afficher_etape(numero: int, titre: str):
    print(f"\n{CYAN}  ── Étape {numero} : {titre} ──{RESET}")

def pipeline_hybride(question: str, user_role: str = "user") -> dict:

    print(f"\n{BLEU}{'─'*65}{RESET}")
    print(f"  {GRAS}📝 REQUÊTE ORIGINALE :{RESET} {question}")
    print(f"  {GRAS}👤 RÔLE              :{RESET} {user_role}")
    print(f"{BLEU}{'─'*65}{RESET}")

    # ══════════════════════════════════════════
    # MODULE 1 — Filtrage injection
    # ══════════════════════════════════════════
    afficher_etape(1, "Filtrage injection (analyse en anglais)")

    resultat_filtre = filtrer_prompt(question)

    if resultat_filtre["blocked"]:
        score = f" (score ML: {resultat_filtre['ml_score']})" \
                if resultat_filtre["ml_score"] else ""
        print(f"  {ROUGE}🚫 BLOQUÉ — {resultat_filtre['reason']}{score}{RESET}")
        print(f"  {ROUGE}   Méthode : {resultat_filtre['method']}{RESET}")
        print(f"  {ROUGE}   La requête n'atteint pas les modules suivants.{RESET}")
        print(f"\n{BLEU}{'─'*65}{RESET}")
        return {
            "etape_bloquee" : "Module 1 — Filtrage",
            "raison"        : resultat_filtre["reason"],
            "reponse"       : "⛔ Requête bloquée — injection détectée.",
            "mode"          : "bloque",
        }

    print(f"  {VERT}✅ Requête propre — méthode : {resultat_filtre['method']}{RESET}")

    # ══════════════════════════════════════════
    # MODULE 2 — Masquage PII
    # Deux opérations séparées :
    #   A) masquer_pii()         → traduit EN → pour log/affichage
    #   B) masquer_pii_pour_rag() → langue originale → pour le RAG
    #      applique regex + GLiNER + Presidio sur l'original
    #      → noms propres, emails, téléphones, cartes masqués
    # ══════════════════════════════════════════
    afficher_etape(2, "Masquage PII")

    # A) Masquage complet traduit EN — pour log et affichage
    resultat_pii_complet = masquer_pii(question)

    # B) Masquage sur l'original sans traduction — pour le RAG
    question_pour_rag = masquer_pii_pour_rag(question)

    # Détecte si une PII a été trouvée dans l'une ou l'autre version
    pii_detectees = resultat_pii_complet["modifie"] or \
                    (question_pour_rag != question)

    if pii_detectees:
        print(f"  {JAUNE}⚠️  PII détectées et masquées :{RESET}")
        print(f"  {GRAS}   Original        :{RESET} {question}")
        print(f"  {GRAS}   Masqué (EN/log) :{RESET} {resultat_pii_complet['texte_masque']}")
        print(f"  {GRAS}   Pour le RAG     :{RESET} {question_pour_rag}")
    else:
        print(f"  {VERT}✅ Aucune PII détectée{RESET}")
        print(f"  {GRAS}   Texte pour RAG  :{RESET} {question_pour_rag}")

    # ══════════════════════════════════════════
    # MODULE 3 — RAG sécurisé
    # ══════════════════════════════════════════
    afficher_etape(3, "RAG sécurisé (recherche locale)")

    resultat_rag = rag_pipeline(
        question  = question_pour_rag,
        user_role = user_role
    )

    # ══════════════════════════════════════════
    # DÉCISION — RAG trouvé ou Fallback LLM
    # ══════════════════════════════════════════

    if not resultat_rag["bloque"]:
        print(f"\n{BLEU}{'═'*65}{RESET}")
        print(f"  {GRAS}🤖 RÉPONSE FINALE{RESET}")
        print(f"{BLEU}{'═'*65}{RESET}")
        print(f"  {GRAS}Mode               :{RESET} {VERT}RAG local ✅{RESET}")
        print(f"  {GRAS}Question originale :{RESET} {question}")
        if pii_detectees:
            print(f"  {GRAS}Question nettoyée  :{RESET} {question_pour_rag}")
        print(f"  {GRAS}Sources RAG        :{RESET} {resultat_rag['sources']}")
        print(f"\n  {GRAS}Réponse :{RESET}")
        for ligne in resultat_rag["reponse"].split('\n'):
            if ligne.strip():
                print(f"    {ligne}")
        print(f"{BLEU}{'═'*65}{RESET}")

        return {
            "etape_bloquee" : None,
            "question"      : question,
            "sources"       : resultat_rag["sources"],
            "reponse"       : resultat_rag["reponse"],
            "mode"          : "rag_local",
        }

    else:
        print(f"\n  {JAUNE}⚠️  Aucun document local pertinent trouvé.{RESET}")
        print(f"  {VIOLET}🌐 Recherche d'une réponse via le LLM général...{RESET}")

        afficher_etape(4, "Fallback — LLM général Groq")

        reponse_llm = ask_llm(question_pour_rag)

        print(f"\n{BLEU}{'═'*65}{RESET}")
        print(f"  {GRAS}🤖 RÉPONSE FINALE{RESET}")
        print(f"{BLEU}{'═'*65}{RESET}")
        print(f"  {GRAS}Mode               :{RESET} {VIOLET}LLM général (fallback) 🌐{RESET}")
        print(f"  {GRAS}Question originale :{RESET} {question}")
        if pii_detectees:
            print(f"  {GRAS}Question nettoyée  :{RESET} {question_pour_rag}")
        print(f"  {GRAS}Sources RAG        :{RESET} Aucune — réponse générale")
        print(f"\n  {GRAS}Réponse :{RESET}")
        for ligne in reponse_llm.split('\n'):
            if ligne.strip():
                print(f"    {ligne}")
        print(f"{BLEU}{'═'*65}{RESET}")

        return {
            "etape_bloquee" : None,
            "question"      : question,
            "sources"       : [],
            "reponse"       : reponse_llm,
            "mode"          : "llm_general",
        }


# ══════════════════════════════════════════════════════════
# BOUCLE INTERACTIVE
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":

    afficher_banniere()

    user_role = "user"
    compteur  = 0

    while True:
        try:
            print(f"\n  {GRAS}[{user_role.upper()}]{RESET} ", end="")
            question = input("Votre question : ").strip()

            if question.lower() == "quit":
                print(f"\n  {VERT}Au revoir ! {compteur} requête(s) traitée(s).{RESET}\n")
                break

            if question.lower() == "role":
                print(f"  Rôle actuel : {VERT}{user_role}{RESET}")
                nouveau = input("  Nouveau rôle (user / moderator / admin) : ").strip().lower()
                if nouveau in ["user", "moderator", "admin"]:
                    user_role = nouveau
                    print(f"  {VERT}✓ Rôle changé en : {user_role}{RESET}")
                else:
                    print(f"  {ROUGE}Rôle invalide. Conservé : {user_role}{RESET}")
                continue

            if not question:
                print(f"  {ROUGE}Question vide, réessaie.{RESET}")
                continue

            pipeline_hybride(question, user_role=user_role)
            compteur += 1
            print(f"\n  {JAUNE}[Requêtes traitées : {compteur}]{RESET}")

        except KeyboardInterrupt:
            print(f"\n\n  {VERT}Arrêté. {compteur} requête(s) traitée(s).{RESET}\n")
            break