import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_TOKEN"] = ""
import hashlib
import re
import warnings
warnings.filterwarnings("ignore")

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# ─────────────────────────────────────────────
# RBAC — Rôle requis par document
# ─────────────────────────────────────────────
ROLES_DOCUMENTS = {
    # ── Accessibles par TOUS (user) ──────────────
    "securite_llm.txt"            : "user",
    "security_llm_en.txt"         : "user",
    "sicherheit_llm_de.txt"       : "user",
    "rag_securise.txt"            : "user",
    "medical_protocols.txt"       : "user",
    "medical_protocols_fr.txt"    : "user",
    "cybersecurity_policy_en.txt" : "user",
    "cybersecurity_complete.txt"  : "user",
    "securite_llm_complete.txt"   : "user",

    # ── Accessibles par MODERATOR et ADMIN ───────
    "rh_entreprise.txt"           : "moderator",
    "rh_entreprise_complete.txt"  : "moderator",
    "banque_politique.txt"        : "moderator",

    # ── Accessibles par ADMIN uniquement ─────────
    "contrats_juridiques.txt"     : "admin",
    "juridique_contrats.txt"      : "admin",
    "openstack_keystone.txt"      : "admin",
}

INJECTION_PATTERNS = [
    r"ignore (all |previous |above )?(instructions?|prompts?)",
    r"you are now",
    r"system:\s",
    r"act as",
    r"new persona",
    r"from this point forward",
    r"\[CRITICAL.*INSTRUCTION\]",
]

def valider_document(texte: str) -> tuple:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, texte, re.IGNORECASE):
            return False, f"Pattern suspect détecté : {pattern}"
    return True, "Document valide"

def hasher_document(texte: str) -> str:
    return hashlib.sha256(texte.encode()).hexdigest()

def ingerer_documents(dossier_documents: str):
    tous_les_chunks = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )

    for nom_fichier in os.listdir(dossier_documents):
        if not nom_fichier.endswith(".txt"):
            continue

        chemin = os.path.join(dossier_documents, nom_fichier)
        loader = TextLoader(chemin, encoding="utf-8")
        documents = loader.load()

        for doc in documents:
            valide, message = valider_document(doc.page_content)
            if not valide:
                print(f"  [REJETÉ]  {nom_fichier} — {message}")
                continue

            # ── Déterminer le rôle du document ────────
            role = ROLES_DOCUMENTS.get(nom_fichier, "user")
            print(f"  [VALIDÉ]  {nom_fichier} — rôle: {role}")

            chunks = splitter.split_documents([doc])

            for chunk in chunks:
                chunk.metadata["hash"]        = hasher_document(chunk.page_content)
                chunk.metadata["source"]      = nom_fichier
                chunk.metadata["role_requis"] = role

            print(f"            {len(chunks)} chunks créés — "
                  f"hash ex: {chunks[0].metadata['hash'][:20]}...")

            tous_les_chunks.extend(chunks)

    if not tous_les_chunks:
        print("\n  [ERREUR]  Aucun document valide trouvé.")
        return None

    print(f"\n  [INFO]    {len(tous_les_chunks)} chunks prêts pour l'indexation.")
    print("  [INFO]    Chargement du modèle multilingue...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    )

    print("  [INFO]    Création de la base vectorielle FAISS...")
    vectorstore = FAISS.from_documents(tous_les_chunks, embeddings)

    chemin_index = os.path.join(os.path.dirname(__file__), "faiss_index")
    vectorstore.save_local(chemin_index)
    print(f"  [OK]      Base vectorielle sauvegardée ✓")
    print(f"            Chemin : {chemin_index}")

    return vectorstore


if __name__ == "__main__":
    print("=" * 50)
    print("   INGESTION SÉCURISÉE DES DOCUMENTS")
    print("=" * 50)
    dossier = os.path.join(os.path.dirname(__file__), "documents")
    ingerer_documents(dossier)
    print("=" * 50)