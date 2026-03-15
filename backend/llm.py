from groq import Groq
from dotenv import load_dotenv
import os

# Charger la clé API depuis .env
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_llm(question: str) -> str:
    """Envoie une question au LLM et retourne la réponse."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Tu es un assistant utile et sécurisé."},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

# Test direct
if __name__ == "__main__":
    question = "Quelle est la capitale de la France ?"
    reponse = ask_llm(question)
    print(f"Question : {question}")
    print(f"Réponse  : {reponse}")