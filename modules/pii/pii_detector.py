import re
import spacy
from gliner import GLiNER
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from deep_translator import GoogleTranslator

# ── CHARGEMENT DES MODÈLES ────────────────────────────────

nlp = spacy.load("en_core_web_lg")
gliner_model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()


# ── TRADUCTION ────────────────────────────────────────────

def traduire_en_anglais(texte: str) -> str:
    try:
        traduit = GoogleTranslator(source='auto', target='en').translate(texte)
        return traduit if traduit else texte
    except Exception:
        return texte


# ── COMPTEUR D'ALPHABET AVEC MÉMOIRE ─────────────────────

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

class CompteurAlphabet:
    def __init__(self):
        self.index = 0
        self.memoire = {}

    def normaliser(self, valeur: str) -> str:
        valeur_lower = valeur.lower().strip()
        for titre in TITRES_A_PRESERVER:
            if valeur_lower.startswith(titre + " "):
                valeur_lower = valeur_lower[len(titre) + 1:].strip()
                break
        return valeur_lower.replace(" ", "").replace("-", "").replace(".", "")

    def obtenir_lettre(self, valeur: str) -> str:
        cle = self.normaliser(valeur)
        if cle in self.memoire:
            return self.memoire[cle]
        lettre = ALPHABET[self.index % len(ALPHABET)]
        self.index += 1
        self.memoire[cle] = lettre
        return lettre

    def reset(self):
        self.index = 0
        self.memoire = {}


# ── FONCTION MASQUAGE PAR LETTRE ─────────────────────────

def masquer_par_lettre(valeur: str, lettre: str) -> str:
    valeur_nette = valeur.replace(" ", "").replace("-", "").replace(".", "")
    return lettre * len(valeur_nette)


# ── MASQUAGE EMAIL INTELLIGENT ────────────────────────────

def masquer_email_intelligent(email: str, lettre: str) -> str:
    if "@" not in email:
        return masquer_par_lettre(email, lettre)
    partie_locale, partie_domaine = email.split("@", 1)
    locale_masquee = lettre * len(partie_locale.replace(".", "").replace("-", ""))
    if "." in partie_domaine:
        nom_domaine, extension = partie_domaine.rsplit(".", 1)
        domaine_masque    = lettre * len(nom_domaine.replace(".", "").replace("-", ""))
        extension_masquee = lettre * len(extension)
        return f"{locale_masquee}@{domaine_masque}.{extension_masquee}"
    else:
        domaine_masque = lettre * len(partie_domaine)
        return f"{locale_masquee}@{domaine_masque}"


# ── MASQUAGE PASSWORD INTELLIGENT ────────────────────────

def masquer_password_intelligent(match, compteur: CompteurAlphabet) -> str:
    """
    Préserve le mot clé (password/mot de passe/etc.)
    et masque uniquement la valeur du mot de passe.
    password is Azerty@1234 → password is AAAAAAAAAAAA
    """
    texte_complet = match.group(0)
    valeur_mdp    = match.group(1)
    lettre        = compteur.obtenir_lettre(valeur_mdp)
    mdp_masque    = lettre * len(valeur_mdp)
    return texte_complet.replace(valeur_mdp, mdp_masque)


# ── MASQUAGE CVV INTELLIGENT ──────────────────────────────

def masquer_cvv_intelligent(match, compteur: CompteurAlphabet) -> str:
    """
    Préserve le mot clé CVV/CVC et masque uniquement le code.
    CVV 523 → CVV AAA
    """
    texte_complet = match.group(0)
    valeur_cvv    = match.group(1)
    lettre        = compteur.obtenir_lettre(valeur_cvv)
    cvv_masque    = lettre * len(valeur_cvv)
    return texte_complet.replace(valeur_cvv, cvv_masque)


# ── MASQUAGE PIN INTELLIGENT ──────────────────────────────

def masquer_pin_intelligent(match, compteur: CompteurAlphabet) -> str:
    """
    Préserve le mot clé PIN et masque uniquement le code.
    PIN 4521 → PIN AAAA
    """
    texte_complet = match.group(0)
    valeur_pin    = match.group(1)
    lettre        = compteur.obtenir_lettre(valeur_pin)
    pin_masque    = lettre * len(valeur_pin)
    return texte_complet.replace(valeur_pin, pin_masque)


# ── MASQUAGE AUTH CODE INTELLIGENT ───────────────────────

def masquer_auth_intelligent(match, compteur: CompteurAlphabet) -> str:
    """
    Préserve le mot clé authorization code et masque le code.
    authorization code is 774521 → authorization code is AAAAAA
    """
    texte_complet = match.group(0)
    valeur_auth   = match.group(1)
    lettre        = compteur.obtenir_lettre(valeur_auth)
    auth_masque   = lettre * len(valeur_auth)
    return texte_complet.replace(valeur_auth, auth_masque)


# ── PERSONNAGES PUBLICS ───────────────────────────────────

PERSONNAGES_PUBLICS = {
    "elon musk", "bill gates", "mark zuckerberg", "sam altman",
    "jeff bezos", "steve jobs", "linus torvalds", "tim cook",
    "sundar pichai", "satya nadella", "jensen huang",
    "barack obama", "donald trump", "joe biden", "emmanuel macron",
    "angela merkel", "vladimir putin", "xi jinping",
    "giorgia meloni", "pedro sanchez", "olaf scholz",
    "kais saied", "habib bourguiba", "zine el abidine ben ali",
    "rached ghannouchi",
    "albert einstein", "alan turing", "marie curie",
    "stephen hawking", "isaac newton",
    "lionel messi", "cristiano ronaldo", "roger federer",
    "novak djokovic", "lebron james", "michael jordan",
    "mohamed ali", "muhammad ali",
}

def est_personnage_public(nom: str) -> bool:
    if nom.lower().strip() in PERSONNAGES_PUBLICS:
        return True
    nom_lower = nom.lower().strip()
    for pub in PERSONNAGES_PUBLICS:
        if pub in nom_lower:
            return True
    return False


# ── TITRES À PRÉSERVER ────────────────────────────────────

TITRES_A_PRESERVER = [
    "the patient", "the employee", "the client", "the student",
    "our employee", "our patient", "our client",
    "patient", "employee", "client", "student",
    "dr.", "dr", "mr.", "mr", "mrs.", "mrs", "ms.", "ms",
    "prof.", "prof", "doctor", "nurse",
    "le patient", "la patiente", "l'employé", "l'employée",
    "notre employé", "notre employée", "notre patient",
    "m.", "mme.", "mme",
    "der patient", "die patientin", "der mitarbeiter",
    "herr", "frau",
    "il paziente", "la paziente", "il dipendente",
    "sig.", "sig",
    "el paciente", "la paciente", "el empleado", "el cliente",
    "sr.", "sra.",
    "o paciente", "a paciente", "o funcionário",
]

TITRES_MEDICAUX = {"dr.", "dr", "prof.", "prof", "doctor", "nurse"}

def separer_titre_nom(texte_ent: str) -> tuple:
    texte_lower = texte_ent.lower().strip()
    for titre in TITRES_A_PRESERVER:
        if texte_lower.startswith(titre + " "):
            offset = len(titre) + 1
            return texte_ent[:offset], texte_ent[offset:]
    return "", texte_ent

def chercher_titre_avant(texte: str, debut: int) -> str:
    fenetre = texte[max(0, debut - 30):debut]
    fenetre_lower = fenetre.lower()
    for titre in TITRES_A_PRESERVER:
        if fenetre_lower.rstrip().endswith(titre):
            return titre
    return ""

def contient_titre_medical(texte_ent: str) -> bool:
    texte_lower = texte_ent.lower().strip()
    for titre in TITRES_MEDICAUX:
        if texte_lower.startswith(titre + " "):
            return True
    return False


# ── COUCHE 1 — REGEX ──────────────────────────────────────

PATTERNS = {
    # Données structurées classiques
    "EMAIL":       r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    "CREDIT_CARD": r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    "PHONE":       r'\b(\+?[\d][\d\s\-\.]{6,}[\d])\b',
    "IBAN":        r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b',

    # Nouveaux patterns bancaires critiques
    # Mot de passe — multilingue
    "PASSWORD": (
        r'(?i)(?:password|mot\s+de\s+passe|passwort|contraseña|senha|'
        r'mdp|pass|code\s+d\'accès|access\s+code)\s*(?:is|est|ist|es|é|:)?\s*(\S+)'
    ),

    # CVV / CVC — code de sécurité carte
    "CVV": (
        r'(?i)\b(?:cvv|cvc|cvv2|cvc2|security\s+code|code\s+de\s+sécurité|'
        r'código\s+de\s+seguridad|sicherheitscode)\s*(?:is|est|ist|es|:)?\s*(\d{3,4})\b'
    ),

    # PIN — code secret
    "PIN": (
        r'(?i)\b(?:pin|code\s+secret|código\s+pin|geheimzahl|'
        r'code\s+confidentiel|secret\s+code)\s*(?:is|est|ist|es|:)?\s*(\d{4,6})\b'
    ),

    # Code d'autorisation
    "AUTH_CODE": (
        r'(?i)(?:authorization\s+code|auth\s+code|code\s+d\'autorisation|'
        r'código\s+de\s+autorización|autorisierungscode)\s*(?:is|est|ist|es|:)?\s*(\d{4,8})'
    ),
}

# Patterns avec groupe capturant la valeur à masquer
PATTERNS_AVEC_GROUPE = {"PASSWORD", "CVV", "PIN", "AUTH_CODE"}

def masquer_regex(texte: str, compteur: CompteurAlphabet) -> str:
    for label, pattern in PATTERNS.items():
        if label == "EMAIL":
            def remplacer_email(match, c=compteur):
                valeur = match.group(0)
                lettre = c.obtenir_lettre(valeur)
                return masquer_email_intelligent(valeur, lettre)
            texte = re.sub(pattern, remplacer_email, texte)

        elif label == "PASSWORD":
            def remplacer_pwd(match, c=compteur):
                return masquer_password_intelligent(match, c)
            texte = re.sub(pattern, remplacer_pwd, texte)

        elif label == "CVV":
            def remplacer_cvv(match, c=compteur):
                return masquer_cvv_intelligent(match, c)
            texte = re.sub(pattern, remplacer_cvv, texte)

        elif label == "PIN":
            def remplacer_pin(match, c=compteur):
                return masquer_pin_intelligent(match, c)
            texte = re.sub(pattern, remplacer_pin, texte)

        elif label == "AUTH_CODE":
            def remplacer_auth(match, c=compteur):
                return masquer_auth_intelligent(match, c)
            texte = re.sub(pattern, remplacer_auth, texte)

        else:
            def remplacer(match, c=compteur):
                valeur = match.group(0)
                lettre = c.obtenir_lettre(valeur)
                return masquer_par_lettre(valeur, lettre)
            texte = re.sub(pattern, remplacer, texte)

    return texte


# ── COUCHE 2 — GLINER ─────────────────────────────────────

GLINER_LABELS = [
    "private person name",
    "public figure name",
    "private street address",
    "public location",
    "organization name",
]

SEUIL_GLINER = 0.4

def masquer_gliner(texte: str, compteur: CompteurAlphabet) -> str:
    try:
        entites = gliner_model.predict_entities(
            texte,
            labels=GLINER_LABELS,
            threshold=SEUIL_GLINER
        )
    except Exception:
        return texte

    print("\n[GLiNER DEBUG] Entités détectées :")
    for ent in entites:
        print(f"  → texte='{ent['text']}' | label='{ent['label']}' | score={ent['score']:.2f} | pos=[{ent['start']}:{ent['end']}]")
    print()

    entites = sorted(entites, key=lambda e: e["start"], reverse=True)

    for ent in entites:
        label     = ent["label"]
        texte_ent = ent["text"]
        debut     = ent["start"]
        fin       = ent["end"]
        score     = ent["score"]

        if score < SEUIL_GLINER:
            continue

        if est_personnage_public(texte_ent):
            if label == "private person name":
                titre_avant = chercher_titre_avant(texte, debut)
                if titre_avant:
                    lettre = compteur.obtenir_lettre(texte_ent)
                    x = masquer_par_lettre(texte_ent, lettre)
                    texte = texte[:debut] + x + texte[fin:]
                    print(f"  [PUBLIC+PRIVE] '{texte_ent}' masqué avec '{lettre}'")
                else:
                    print(f"  [SKIP] '{texte_ent}' = personnage public → ignoré")
            else:
                print(f"  [SKIP] '{texte_ent}' = personnage public → ignoré")
            continue

        if label in {"private person name", "private street address"}:
            titre_avant = chercher_titre_avant(texte, debut)
            if titre_avant:
                lettre = compteur.obtenir_lettre(texte_ent)
                x = masquer_par_lettre(texte_ent, lettre)
                texte = texte[:debut] + x + texte[fin:]
                print(f"  [OK] Titre AVANT '{titre_avant}' → masqué avec '{lettre}' → '{x}'")
            else:
                partie_titre, partie_nom = separer_titre_nom(texte_ent)
                if partie_titre:
                    lettre = compteur.obtenir_lettre(partie_nom)
                    x = masquer_par_lettre(partie_nom, lettre)
                    offset = len(partie_titre)
                    texte = texte[:debut + offset] + x + texte[fin:]
                    print(f"  [OK] Titre DANS '{partie_titre}' → masqué avec '{lettre}' → '{x}'")
                else:
                    lettre = compteur.obtenir_lettre(texte_ent)
                    x = masquer_par_lettre(texte_ent, lettre)
                    texte = texte[:debut] + x + texte[fin:]
                    print(f"  [OK] Pas de titre → masqué avec '{lettre}' → '{x}'")
            print()

        elif label == "public figure name":
            titre_avant = chercher_titre_avant(texte, debut)
            partie_titre, partie_nom = separer_titre_nom(texte_ent)
            if titre_avant or contient_titre_medical(texte_ent):
                if partie_titre:
                    lettre = compteur.obtenir_lettre(partie_nom)
                    x = masquer_par_lettre(partie_nom, lettre)
                    offset = len(partie_titre)
                    texte = texte[:debut + offset] + x + texte[fin:]
                    print(f"  [CORR] titre médical '{partie_titre}' → masqué avec '{lettre}'")
                else:
                    lettre = compteur.obtenir_lettre(texte_ent)
                    x = masquer_par_lettre(texte_ent, lettre)
                    texte = texte[:debut] + x + texte[fin:]
                    print(f"  [CORR] contexte privé '{titre_avant}' → masqué avec '{lettre}'")
            else:
                print(f"  [SKIP] '{texte_ent}' label='public figure' sans contexte → ignoré")
            print()

        elif label == "organization name":
            titre_avant = chercher_titre_avant(texte, debut)
            partie_titre, partie_nom = separer_titre_nom(texte_ent)
            if titre_avant or contient_titre_medical(texte_ent):
                if partie_titre:
                    lettre = compteur.obtenir_lettre(partie_nom)
                    x = masquer_par_lettre(partie_nom, lettre)
                    offset = len(partie_titre)
                    texte = texte[:debut + offset] + x + texte[fin:]
                    print(f"  [CORR] ORG→médecin titre DANS → masqué avec '{lettre}'")
                else:
                    lettre = compteur.obtenir_lettre(texte_ent)
                    x = masquer_par_lettre(texte_ent, lettre)
                    texte = texte[:debut] + x + texte[fin:]
                    print(f"  [CORR] ORG→médecin titre AVANT → masqué avec '{lettre}'")
                print()

    return texte


# ── COUCHE 3 — PRESIDIO ───────────────────────────────────

def masquer_presidio(texte: str, compteur: CompteurAlphabet) -> str:
    resultats = analyzer.analyze(
        text=texte,
        language="en",
        entities=[
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
            "CREDIT_CARD", "IBAN_CODE", "LOCATION"
        ]
    )
    if not resultats:
        return texte

    resultats_filtres = []
    for res in resultats:
        valeur = texte[res.start:res.end]

        valeur_nette = valeur.replace(" ", "")
        if len(set(valeur_nette)) == 1 and valeur_nette[0].isalpha():
            continue

        if res.entity_type == "PERSON":
            if est_personnage_public(valeur):
                continue

        if res.entity_type == "LOCATION":
            continue

        resultats_filtres.append(res)

    if not resultats_filtres:
        return texte

    resultats_filtres.sort(key=lambda r: r.start, reverse=True)

    for res in resultats_filtres:
        valeur = texte[res.start:res.end]
        lettre = compteur.obtenir_lettre(valeur)
        if res.entity_type == "EMAIL_ADDRESS":
            x = masquer_email_intelligent(valeur, lettre)
        else:
            x = masquer_par_lettre(valeur, lettre)
        texte = texte[:res.start] + x + texte[res.end:]

    return texte


# ── PIPELINE COMPLET ──────────────────────────────────────

def masquer_pii(texte: str) -> dict:
    original = texte
    texte_en = traduire_en_anglais(texte)
    texte_traduit = texte_en

    compteur = CompteurAlphabet()

    texte_en = masquer_regex(texte_en, compteur)
    texte_en = masquer_gliner(texte_en, compteur)
    texte_en = masquer_presidio(texte_en, compteur)

    return {
        "texte_original": original,
        "texte_traduit":  texte_traduit,
        "texte_masque":   texte_en,
        "modifie":        texte_en != texte_traduit
    }
def masquer_pii_pour_rag(texte: str) -> str:
    """
    Masquage PII sur le texte ORIGINAL sans traduction.
    Utilisé pour envoyer au RAG dans la langue originale.
    Applique : regex + GLiNER + Presidio directement sur l'original.
    """
    compteur = CompteurAlphabet()

    # Étape 1 : Regex sur l'original
    texte = masquer_regex(texte, compteur)

    # Étape 2 : GLiNER sur l'original (sans traduction)
    texte = masquer_gliner(texte, compteur)

    # Étape 3 : Presidio sur l'original
    texte = masquer_presidio(texte, compteur)

    return texte