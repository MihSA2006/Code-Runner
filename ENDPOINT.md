# Documentation des Endpoints API CodeRunner

L'API de base est accessible sous le préfixe `/api/v1` sauf pour la racine de l'application.

## 1. Soumettre et attendre le résultat (Recommandé)
**URL** : `POST /api/v1/execute/wait`  
**Description** : Soumet un code et attend directement le résultat (synchrone).

### Body (JSON)
```json
{
  "language": "python", // Options: python, javascript, java, c, cpp
  "code": "print('Hello World!')"
}
```

### Réponse (JSON) - 200 OK
```json
{
  "token": "a1b2c3d4-e5f6...",
  "status": "completed",
  "language": "python",
  "output": "Hello World!\n",
  "error": null,
  "execution_time": 0.045
}
```

---

## 2. Soumettre un code (Asynchrone)
**URL** : `POST /api/v1/execute`  
**Description** : Soumet un code pour exécution asynchrone et retourne un `token`. À utiliser avec `GET /api/v1/result/{token}`.

### Body (JSON)
```json
{
  "language": "python",
  "code": "print('Hello World!')"
}
```

### Réponse (JSON) - 200 OK
```json
{
  "token": "a1b2c3d4-e5f6...",
  "status": "pending",
  "message": "Résultat disponible sur GET /result/a1b2c3d4-e5f6..."
}
```

---

## 3. Récupérer le résultat d'une exécution
**URL** : `GET /api/v1/result/{token}`  
**Description** : Récupère le résultat d'une exécution lancée via le point de terminaison asynchrone en utilisant le `token`.

### Paramètres URL
- `token` (str) : Le token retourné lors de l'exécution.

### Réponse (JSON) - 200 OK
```json
{
  "token": "a1b2c3d4-e5f6...",
  "status": "completed", // ou "pending", "failed"
  "language": "python",
  "output": "Hello World!\n",
  "error": null,
  "execution_time": 0.045
}
```

---

## 4. Supprimer un résultat d'exécution
**URL** : `DELETE /api/v1/result/{token}`  
**Description** : Supprime une exécution de la base de données SQLite manuellement.

### Paramètres URL
- `token` (str) : Le token de l'exécution à supprimer.

### Réponse (JSON) - 200 OK
```json
{
  "message": "Token 'a1b2c3d4-e5f6...' supprimé"
}
```

---

## 5. Lister les langages supportés
**URL** : `GET /api/v1/languages`  
**Description** : Retourne la liste des langages de programmation pris en charge ainsi que les images Docker correspondantes.

### Réponse (JSON) - 200 OK
```json
{
  "languages": [
    {
      "name": "python",
      "image": "coderunner-python"
    },
    {
      "name": "javascript",
      "image": "coderunner-javascript"
    }
  ]
}
```

---

## 6. Vérifier l'état de l'API (Healthcheck)
**URL** : `GET /api/v1/health`  
**Description** : Vérifie l'état de santé de l'API et l'accès au daemon Docker.

### Réponse (JSON) - 200 OK
```json
{
  "status": "ok",
  "app": "CodeRunner API",
  "version": "1.0.0",
  "docker": "ok",
  "docker_version": "24.0.5",
  "limits": {
    "max_execution_time": 5,
    "max_memory": "128m",
    "max_cpu": "0.5",
    "max_code_length": 50000,
    "rate_limit_execute": "10/minute"
  },
  "timestamp": 1700000000.123
}
```

---

## 7. Racine (Info API)
**URL** : `GET /`  
**Description** : Fournit les chemins vers la documentation Swagger.

### Réponse (JSON) - 200 OK
```json
{
  "app": "CodeRunner API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```
