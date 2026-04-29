from gliner import GLiNER

print("Téléchargement en cours... (2.3 GB, patience)")
model = GLiNER.from_pretrained("urchade/gliner_multi-v2.1")
print("Modèle téléchargé avec succès !")