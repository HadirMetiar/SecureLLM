import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

DOSSIER_DOCS = os.path.join("modules", "rag", "documents")

class HandlerDocument(FileSystemEventHandler):
    def __init__(self):
        self.derniere_ingestion = 0

    def on_modified(self, event):
        self.lancer_ingestion(event.src_path)

    def on_created(self, event):
        self.lancer_ingestion(event.src_path)

    def lancer_ingestion(self, chemin):
        if not chemin.endswith(".txt"):
            return
        # Évite de lancer 2 fois en moins de 3 secondes
        maintenant = time.time()
        if maintenant - self.derniere_ingestion < 3:
            return
        self.derniere_ingestion = maintenant

        print(f"\n[AUTO-INGEST] Fichier modifié : {chemin}")
        print("[AUTO-INGEST] Relance de l'ingestion...")
        subprocess.run(
            ["python", os.path.join("modules", "rag", "ingest.py")],
            cwd=os.getcwd()
        )
        print("[AUTO-INGEST] ✅ Ingestion terminée !")

if __name__ == "__main__":
    print(f"[AUTO-INGEST] Surveillance de : {DOSSIER_DOCS}")
    print("[AUTO-INGEST] Modifie un .txt pour déclencher l'ingestion automatiquement...")

    handler  = HandlerDocument()
    observer = Observer()
    observer.schedule(handler, DOSSIER_DOCS, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()