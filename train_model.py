# train_model.py
import pandas as pd
import joblib
import os
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# Charger le dataset
df = pd.read_csv("data/filter_training/dataset.csv")
X = df["text"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Pipeline : TF-IDF + Logistic Regression
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 3), max_features=5000)),
    ("clf", LogisticRegression(max_iter=1000))
])

pipeline.fit(X_train, y_train)

# Évaluation
y_pred = pipeline.predict(X_test)
print(classification_report(y_test, y_pred,
      target_names=["Normal", "Malveillant"]))

# Sauvegarder le modèle
os.makedirs("models", exist_ok=True)
joblib.dump(pipeline, "models/classifier.pkl")
print("✅ Modèle sauvegardé dans models/classifier.pkl")