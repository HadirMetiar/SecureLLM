import os
import sys
import requests
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# ══════════════════════════════════════════════════════════
# CONFIGURATION DE LA PAGE
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title            = "🔐 SecureLLM Dashboard",
    page_icon             = "🔐",
    layout                = "wide",
    initial_sidebar_state = "expanded"
)

API_URL = "http://localhost:8000"

# ══════════════════════════════════════════════════════════
# SESSION STATE — historique des requêtes
# ══════════════════════════════════════════════════════════
if "historique" not in st.session_state:
    st.session_state.historique = []

# ══════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════
def appeler_api(question: str, role: str) -> dict:
    try:
        response = requests.post(
            f"{API_URL}/ask",
            json    = {"question": question, "role": role},
            timeout = 60
        )
        return response.json()
    except Exception as e:
        return {"erreur": str(e)}

def get_stats() -> dict:
    try:
        response = requests.get(f"{API_URL}/stats", timeout=5)
        return response.json()
    except Exception:
        return None

def check_api() -> bool:
    try:
        response = requests.get(f"{API_URL}/health", timeout=3)
        return response.status_code == 200
    except Exception:
        return False

# ══════════════════════════════════════════════════════════
# TITRE PRINCIPAL
# ══════════════════════════════════════════════════════════
st.title("🔐 SecureLLM — Tableau de bord de supervision")
st.markdown("**Plateforme de détection et prévention des menaces LLM**")
st.divider()

# ══════════════════════════════════════════════════════════
# STATUT API
# ══════════════════════════════════════════════════════════
api_ok = check_api()
if api_ok:
    st.success("✅ API SecureLLM connectée et opérationnelle")
else:
    st.error("❌ API non disponible — Lance d'abord : uvicorn api:app --reload")
    st.stop()

# ══════════════════════════════════════════════════════════
# SECTION 1 — MÉTRIQUES STATISTIQUES
# ══════════════════════════════════════════════════════════
st.subheader("📊 Statistiques en temps réel")

stats = get_stats()
if stats:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📨 Total requêtes",     stats["total_requetes"])
    col2.metric("🚫 Injections bloquées", stats["injections_bloquees"])
    col3.metric("🔒 PII détectées",       stats["pii_detectees"])
    col4.metric("📚 Réponses RAG",        stats["reponses_rag"])
    col5.metric("🌐 Réponses LLM",        stats["reponses_llm_general"])

st.divider()

# ══════════════════════════════════════════════════════════
# SECTION 2 — GRAPHIQUES
# ══════════════════════════════════════════════════════════
st.subheader("📈 Visualisation")

if stats and stats["total_requetes"] > 0:
    col_g1, col_g2 = st.columns(2)

    # Graphique 1 — Camembert répartition des modes
    with col_g1:
        labels = ["RAG local", "LLM général", "Bloquées"]
        values = [
            stats["reponses_rag"],
            stats["reponses_llm_general"],
            stats["injections_bloquees"]
        ]
        colors = ["#2ecc71", "#3498db", "#e74c3c"]
        fig1 = go.Figure(data=[go.Pie(
            labels = labels,
            values = values,
            hole   = 0.4,
            marker = dict(colors=colors)
        )])
        fig1.update_layout(title="Répartition des réponses")
        st.plotly_chart(fig1, use_container_width=True)

    # Graphique 2 — Barres comparaison
    with col_g2:
        fig2 = go.Figure(data=[go.Bar(
            x      = ["RAG local", "LLM général", "Bloquées", "PII détectées"],
            y      = [
                stats["reponses_rag"],
                stats["reponses_llm_general"],
                stats["injections_bloquees"],
                stats["pii_detectees"]
            ],
            marker_color = ["#2ecc71", "#3498db", "#e74c3c", "#f39c12"]
        )])
        fig2.update_layout(title="Statistiques par catégorie")
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Les graphiques apparaîtront après les premières requêtes.")

st.divider()

# ══════════════════════════════════════════════════════════
# SECTION 3 — INTERFACE DE CHAT
# ══════════════════════════════════════════════════════════
st.subheader("💬 Interface de chat sécurisée")

col_input, col_role = st.columns([4, 1])

with col_input:
    question = st.text_input(
        "Votre question :",
        placeholder = "Ex: Comment sécuriser un LLM ?"
    )

with col_role:
    role = st.selectbox("Rôle", ["user", "moderator", "admin"])

col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    envoyer = st.button("🚀 Envoyer", type="primary", use_container_width=True)
with col_btn2:
    st.empty()

if envoyer and question.strip():
    with st.spinner("Traitement en cours..."):
        resultat = appeler_api(question, role)

    if "erreur" in resultat:
        st.error(f"Erreur API : {resultat['erreur']}")
    else:
        # Ajout à l'historique
        st.session_state.historique.insert(0, {
            "timestamp" : datetime.now().strftime("%H:%M:%S"),
            "question"  : question,
            "role"      : role,
            "mode"      : resultat.get("mode", "?"),
            "bloque"    : resultat.get("bloque", False),
            "pii"       : resultat.get("pii_detectees", False),
            "sources"   : resultat.get("sources", []),
            "reponse"   : resultat.get("reponse", "")
        })

        # Affichage du résultat
        if resultat.get("bloque"):
            st.error(f"🚫 **Requête bloquée**")
            st.warning(f"Raison : {resultat.get('raison_blocage', 'Injection détectée')}")
        else:
            st.success("✅ Réponse reçue")

            col_r1, col_r2 = st.columns([3, 1])
            with col_r1:
                st.markdown("**Réponse :**")
                st.write(resultat.get("reponse", ""))
            with col_r2:
                st.markdown("**Détails :**")
                st.write(f"Mode : `{resultat.get('mode')}`")
                st.write(f"PII : {'⚠️ Oui' if resultat.get('pii_detectees') else '✅ Non'}")
                if resultat.get("sources"):
                    st.write("Sources :")
                    for s in resultat.get("sources", []):
                        st.write(f"  📄 {s}")

elif envoyer and not question.strip():
    st.warning("Écris une question avant d'envoyer.")

st.divider()

# ══════════════════════════════════════════════════════════
# SECTION 4 — HISTORIQUE DES REQUÊTES
# ══════════════════════════════════════════════════════════
st.subheader("📋 Historique des requêtes")

if st.session_state.historique:
    for i, req in enumerate(st.session_state.historique[:10]):
        if req["bloque"]:
            icone = "🚫"
            couleur = "red"
        elif req["pii"]:
            icone = "⚠️"
            couleur = "orange"
        else:
            icone = "✅"
            couleur = "green"

        with st.expander(f"{icone} [{req['timestamp']}] {req['question'][:60]}..."):
            col_h1, col_h2, col_h3 = st.columns(3)
            col_h1.write(f"**Mode :** {req['mode']}")
            col_h2.write(f"**Rôle :** {req['role']}")
            col_h3.write(f"**PII :** {'Oui' if req['pii'] else 'Non'}")
            if req["sources"]:
                st.write(f"**Sources :** {', '.join(req['sources'])}")
            st.write(f"**Réponse :** {req['reponse'][:200]}...")
else:
    st.info("Aucune requête pour le moment — pose une question ci-dessus.")

# ══════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.header("🔐 SecureLLM")
    st.markdown("---")
    st.markdown("**Modules actifs :**")
    st.success("✅ Module 1 — Filtrage injection")
    st.success("✅ Module 2 — Masquage PII")
    st.success("✅ Module 3 — RAG sécurisé")
    st.success("✅ API FastAPI")
    st.markdown("---")
    st.markdown("**Architecture :**")
    st.code("Requête\n→ Filtrage\n→ Masquage PII\n→ RAG + LLM\n→ JSON")    
    st.markdown("---")
    if st.button("🔄 Actualiser les stats"):
        st.rerun()
    st.markdown("---")
    st.caption("PFE Cycle Ingénieur — ENET'COM")
    st.caption("Encadrante : Emna KALLEL")