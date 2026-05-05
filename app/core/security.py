import re
from typing import Tuple
from app.core.config import settings


# ──────────────────────────────────────────
# Patterns de code dangereux bloqués
# ──────────────────────────────────────────

# Ces patterns sont bloqués dans TOUS les langages
DANGEROUS_PATTERNS = {

    # Suppression de fichiers système
    "system_delete": [
        r"rm\s+-rf\s+/",
        r"rmdir\s+/",
        r"format\s+[cC]:",
    ],

    # Fork bomb
    "fork_bomb": [
        r":\(\)\{.*:\|:&\}",          # Bash fork bomb
        r"while\s*True.*os\.fork",    # Python fork bomb
    ],

    # Accès réseau (redondant avec Docker mais défense en profondeur)
    "network_access": [
        r"import\s+socket",
        r"import\s+requests",
        r"import\s+urllib",
        r"require\s*\(\s*['\"]http",
        r"require\s*\(\s*['\"]net",
        r"#include\s*<\s*sys/socket",
    ],

    # Accès au système de fichiers sensibles
    "filesystem_sensitive": [
        r"/etc/passwd",
        r"/etc/shadow",
        r"/proc/self",
        r"C:\\Windows\\System32",
    ],
}

# Patterns spécifiques par langage
LANGUAGE_DANGEROUS_PATTERNS = {
    "python": [
        r"__import__\s*\(\s*['\"]os['\"]",
        r"os\.system\s*\(",
        r"subprocess\.",
        r"open\s*\(['\"]\/",           # Ouvrir fichiers racine
        r"eval\s*\(",                  # eval dynamique
        r"exec\s*\(",                  # exec dynamique
    ],
    "javascript": [
        r"require\s*\(\s*['\"]child_process",
        r"require\s*\(\s*['\"]fs",
        r"process\.exit",
        r"eval\s*\(",
    ],
    "c": [
        r"system\s*\(",
        r"popen\s*\(",
        r"exec[lv][pe]?\s*\(",
    ],
}


# ──────────────────────────────────────────
# Validation du code
# ──────────────────────────────────────────

def validate_code(code: str, language: str) -> Tuple[bool, str]:
    """
    Vérifie si le code contient des patterns dangereux.
    Retourne (is_safe, reason).
    """

    # 1. Vérifier la taille
    if len(code) > settings.MAX_CODE_LENGTH:
        return False, f"Code trop long ({len(code)} > {settings.MAX_CODE_LENGTH} caractères)"

    # 2. Vérifier les patterns globaux
    for category, patterns in DANGEROUS_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
                return False, f"Pattern dangereux détecté : {category}"

    # 3. Vérifier les patterns spécifiques au langage
    lang_patterns = LANGUAGE_DANGEROUS_PATTERNS.get(language, [])
    for pattern in lang_patterns:
        if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
            return False, f"Opération non autorisée en {language} : {pattern}"

    return True, "ok"


# ──────────────────────────────────────────
# Truncation de l'output
# ──────────────────────────────────────────

def truncate_output(output: str, max_length: int = None) -> str:
    """
    Tronque l'output si trop long pour éviter
    les sorties infinies (ex: boucle infinie qui print).
    """
    if output is None:
        return None

    limit = max_length or settings.MAX_OUTPUT_LENGTH

    if len(output) > limit:
        return output[:limit] + f"\n... [Output tronqué à {limit} caractères]"

    return output
