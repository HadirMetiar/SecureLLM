from modules.pii.pii_detector import masquer_pii

print("=" * 60)
print("     TEST INTERACTIF — MODULE PII")
print("     Tape 'exit' pour quitter")
print("=" * 60)

while True:
    print()
    prompt = input("Entrez votre requête : ").strip()

    if prompt.lower() == "exit":
        print("Fin du test.")
        break

    if not prompt:
        print("Requête vide, réessayez.")
        continue

    res = masquer_pii(prompt)

    print()
    print(f"  ORIGINAL  : {res['texte_original']}")
    print(f"  TRADUIT   : {res['texte_traduit']}")
    print(f"  MASQUÉ    : {res['texte_masque']}")
    print(f"  MODIFIÉ   : {res['modifie']}")
    print("-" * 60)