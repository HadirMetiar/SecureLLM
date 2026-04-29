import os
import hashlib
import re
import warnings
warnings.filterwarnings("ignore")
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# ─────────────────────────────────────────────
# Seuil de score maximum
# ─────────────────────────────────────────────
SCORE_MAX = 11

# ─────────────────────────────────────────────
# CHARGEMENT UNIQUE DU MODÈLE AU DÉMARRAGE
# Le modèle est chargé UNE SEULE FOIS et gardé
# en mémoire pour toutes les requêtes suivantes
# ─────────────────────────────────────────────
print("  [INFO]    Chargement du modèle multilingue en mémoire...")
_EMBEDDINGS = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
print("  [INFO]    Modèle chargé et mis en cache ✓")

# ─────────────────────────────────────────────
# CHARGEMENT UNIQUE DE LA BASE FAISS
# ─────────────────────────────────────────────
_VECTORSTORE = None

def charger_base_vectorielle():
    """
    Charge la base FAISS depuis le disque.
    Utilise le modèle déjà chargé en mémoire.
    """
    global _VECTORSTORE

    # Si déjà chargée, on la retourne directement
    if _VECTORSTORE is not None:
        return _VECTORSTORE

    chemin_index = os.path.join(os.path.dirname(__file__), "faiss_index")

    if not os.path.exists(chemin_index):
        print("  [ERREUR]  Base vectorielle introuvable.")
        print("            Lance d'abord : python ingest.py")
        return None

    # Utilise le modèle déjà chargé — pas de rechargement
    _VECTORSTORE = FAISS.load_local(
        chemin_index,
        _EMBEDDINGS,
        allow_dangerous_deserialization=True
    )

    print("  [OK]      Base vectorielle chargée ✓")
    return _VECTORSTORE

# ─────────────────────────────────────────────
# Patterns d'injection
# ─────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore.*(instructions?|prompts?|rules?|previous|above|all)",
    r"you are now",
    r"system:\s",
    r"act as",
    r"new persona",
    r"from this point forward",
    r"\[CRITICAL.*INSTRUCTION\]",
    r"disregard.*(instructions?|rules?)",
    r"forget.*(instructions?|rules?|previous)",
    r"override",
    r"jailbreak",
    r"without restrictions",
    r"unrestricted",
]

def scanner_injection(texte: str) -> bool:
    """Retourne True si le texte contient un pattern suspect."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, texte, re.IGNORECASE):
            return True
    return False

def verifier_integrite(texte: str, hash_stocke: str) -> bool:
    """Vérifie que le chunk n'a pas été modifié après indexation."""
    hash_actuel = hashlib.sha256(texte.encode()).hexdigest()
    return hash_actuel == hash_stocke

def retrieval_securise(query: str, user_role: str = "user", k: int = 3):
    """
    Recherche sécurisée dans la base FAISS.
    Utilise le modèle et la base déjà chargés en mémoire.
    """
    ROLES = {
        "admin"     : ["admin", "moderator", "user"],
        "moderator" : ["moderator", "user"],
        "user"      : ["user"],
    }
    roles_accessibles = ROLES.get(user_role, ["user"])

    vectorstore = charger_base_vectorielle()
    if vectorstore is None:
        return []

    resultats_bruts = vectorstore.similarity_search_with_score(query, k=k*3)

    print(f"\n  [INFO]    {len(resultats_bruts)} chunks trouvés avant filtrage.")

    docs_valides = []

    for doc, score in resultats_bruts:
        source      = doc.metadata.get("source", "inconnu")
        role_requis = doc.metadata.get("role_requis", "user")
        hash_stocke = doc.metadata.get("hash", "")

        # ── Étape 0 : Filtre score ─────────────────────
        if score > SCORE_MAX:
            print(f"  [SCORE]   IGNORÉ — {source} "
                  f"(score {score:.4f} > {SCORE_MAX} = hors contexte)")
            continue

        # ── Étape 1 : Filtre RBAC ──────────────────────
        if role_requis not in roles_accessibles:
            print(f"  [RBAC]    BLOQUÉ — {source} "
                  f"(requis: {role_requis}, utilisateur: {user_role})")
            continue

        # ── Étape 2 : Vérification d'intégrité ─────────
        if hash_stocke and not verifier_integrite(doc.page_content, hash_stocke):
            print(f"  [INTÉGRITÉ] BLOQUÉ — {source} modifié après indexation !")
            continue

        # ── Étape 3 : Validation anti-injection ────────
        if scanner_injection(doc.page_content):
            print(f"  [INJECTION] BLOQUÉ — {source} contient un pattern suspect !")
            continue

        # ── Chunk validé ───────────────────────────────
        print(f"  [VALIDÉ]  {source} — score : {score:.4f}")
        docs_valides.append(doc)

        if len(docs_valides) >= k:
            break

    print(f"\n  [RÉSULTAT] {len(docs_valides)} chunk(s) validé(s) retourné(s).")
    return docs_valides


# ─────────────────────────────────────────────
# Test direct
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("   RETRIEVAL SÉCURISÉ — TEST")
    print("=" * 55)

    tests = [
        ("Français pertinent",  "Comment sécuriser un LLM contre les attaques ?", 3),
        ("Anglais pertinent",   "How to secure an LLM ?",                         3),
        ("Anglais OpenStack",   "What is Keystone in OpenStack ?",                3),
        ("Français hors ctx",   "Quelle est la météo aujourd'hui ?",              0),
        ("Tarte aux pommes",    "Comment faire une tarte aux pommes ?",           0),
    ]

    for titre, query, attendu in tests:
        print(f"\n── {titre} ──")
        print(f"  Requête  : {query}")
        print(f"  Attendu  : {attendu} chunk(s)")
        docs = retrieval_securise(query, user_role="user")
        print(f"  Obtenu   : {len(docs)} chunk(s) — "
              f"{'✅' if len(docs) == attendu else '⚠️ à vérifier'}")
        print("=" * 55)