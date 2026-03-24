# train_model.py
import pandas as pd
import joblib
import os
import numpy as np

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Seed pour reproductibilité
RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# Charger le dataset
df = pd.read_csv("data/filter_training/dataset.csv")

# 🔁 Shuffle du dataset
df = df.sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)

# Vérifier distribution
print("Distribution des classes :")
print(df["label"].value_counts())

print("\nRatio (%) :")
print(df["label"].value_counts(normalize=True) * 100)

X = df["text"]
y = df["label"]

# ⚖️ Split stratifié
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=RANDOM_STATE,
    stratify=y
)

# 🔥 Pipeline amélioré
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=7000,
        lowercase=True,
        stop_words=None
    )),
    ("clf", LogisticRegression(
        max_iter=1000,
        class_weight="balanced",   # ⚖️ important
        random_state=RANDOM_STATE
    ))
])

# Entraînement
pipeline.fit(X_train, y_train)

# Évaluation
y_pred = pipeline.predict(X_test)

print("\n=== Classification Report ===")
print(classification_report(
    y_test, y_pred,
    target_names=["Normal", "Malveillant"]
))

# Sauvegarde
os.makedirs("models", exist_ok=True)
joblib.dump(pipeline, "models/classifier.pkl")

print("\n✅ Modèle sauvegardé dans models/classifier.pkl")