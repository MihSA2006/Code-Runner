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

## Quick Start (Docker Compose)

La méthode la plus simple pour lancer tout l'écosystème CodeRunner est d'utiliser Docker Compose.

```bash
# Build et lancement de tous les services
docker compose up --build -d

# Voir les logs de l'API
docker logs -f coderunner-api
```

L'API sera disponible sur : **http://localhost:8000**

---

## Installation Manuelle (Développement)

### Étape 1 : Builder les Sandboxes

L'API s'appuie sur des images Docker spécifiques. Buildez-les d'abord :
```bash
docker compose build
```

### Étape 2 : Lancer l'API localement

1. Créer un environnement virtuel :
   ```bash
   python -m venv venv
   # Windows : .\venv\Scripts\activate
   # Linux/Mac : source venv/bin/activate
   ```
2. Installer les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancer le serveur :
   ```bash
   uvicorn app.main:app --reload
   ```

---

## Documentation
- **Swagger UI** : http://localhost:8000/docs
- **Endpoints** : Consultez [ENDPOINT.md](ENDPOINT.md)
