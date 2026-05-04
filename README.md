# CodeRunner

CodeRunner est une API d'exécution de code à distance, conçue pour faire fonctionner et tester du code utilisateur au sein d'environnements (sandboxes) hautement sécurisés via Docker.

## Prérequis

1. **Python 3.11+**
2. **Docker** (Le service Docker doit être démarré car l'API lance des conteneurs pour exécuter le code).

---

## Installation

1. Cloner ou naviguer vers le projet :
   ```bash
   cd code-runner
   ```

2. Créer un environnement virtuel Python :
   ```bash
   python -m venv venv
   source venv/bin/activate
   # Sur Windows (PowerShell) : .\venv\Scripts\activate
   ```

3. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

---

## Exécution

### Étape 1 : Builder les Sandboxes (Environnements Docker)

L'API s'appuie sur des images Docker spécifiques pour isoler et exécuter chaque langage de programmation. Vous devez d'abord construire ces images. Nous utilisons Docker Compose pour cela.

Lancez la commande suivante à la racine du projet :
```bash
docker compose build
```

Vous pouvez vérifier que les images ont bien été créées en affichant l'inventaire Docker :
```bash
docker images | grep coderunner
```

### Étape 2 : Lancer l'API

Une fois les images prêtes et l'environnement virtuel activé, démarrez le serveur FastAPI.

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Vous pouvez ensuite retrouver la documentation Swagger à l'adresse suivante : http://localhost:8000/docs.

## Documentation de l'API

Consultez le fichier `ENDPOINT.md` inclus dans le répertoire pour la liste complète et le format des requêtes pour tous les points de terminaison de l'application.
