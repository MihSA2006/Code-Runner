import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:8000/api/v1"
WAIT_TIME = 15  # secondes max pour attendre un résultat


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

async def submit_code(session, language, code):
    """Soumet un code et retourne le token."""
    async with session.post(
        f"{BASE_URL}/execute",
        json={"language": language, "code": code}
    ) as resp:
        return await resp.json(), resp.status


async def wait_result(session, token, timeout=WAIT_TIME):
    """Attend et retourne le résultat final."""
    for _ in range(timeout):
        await asyncio.sleep(1)
        async with session.get(f"{BASE_URL}/result/{token}") as resp:
            data = await resp.json()
            if data.get("status") in ("done", "error"):
                return data
    return None


async def run_test(session, label, language, code,
                   expect_status="done",
                   expect_output=None,
                   expect_error_contains=None):
    """Lance un test et affiche le résultat."""

    print(f"\n{'─'*50}")
    print(f"  TEST : {label}")
    print(f"{'─'*50}")

    # Soumettre
    response, http_code = await submit_code(session, language, code)

    # Cas où la soumission est refusée (400)
    if http_code == 400:
        detail = response.get("detail", "")
        if expect_status == "rejected":
            print(f"  ✅ Refusé comme attendu : {detail}")
            return True
        else:
            print(f"  ❌ Refusé inattendu     : {detail}")
            return False

    token = response.get("token")
    print(f"  Token   : {token[:8]}...")

    # Attendre le résultat
    result = await wait_result(session, token)

    if result is None:
        print(f"  ❌ Timeout : pas de résultat après {WAIT_TIME}s")
        return False

    status = result.get("status")
    output = result.get("output")
    error  = result.get("error")
    exec_t = result.get("execution_time")

    print(f"  Status  : {status}")
    print(f"  Output  : {output}")
    print(f"  Error   : {error}")
    print(f"  Temps   : {exec_t}s")

    # Vérifications
    ok = True

    if status != expect_status:
        print(f"  ❌ Status attendu : {expect_status}, obtenu : {status}")
        ok = False

    if expect_output and output:
        if expect_output not in output:
            print(f"  ❌ Output attendu contient : '{expect_output}'")
            ok = False

    if expect_error_contains and error:
        if expect_error_contains.lower() not in error.lower():
            print(f"  ❌ Erreur attendue contient : '{expect_error_contains}'")
            ok = False

    if ok:
        print(f"  ✅ Test passé")

    return ok


# ──────────────────────────────────────────
# Suite de tests
# ──────────────────────────────────────────

async def main():
    results = []
    print("\n" + "═"*50)
    print("   CODERUNNER — TESTS COMPLETS")
    print("═"*50)

    async with aiohttp.ClientSession() as session:

        # ══════════════════════════════════════
        # SECTION 1 : Hello World par langage
        # ══════════════════════════════════════

        print("\n\n  ▶ SECTION 1 : Hello World\n")

        results.append(await run_test(
            session, "Python - Hello World", "python",
            'print("Hello World")',
            expect_output="Hello World"
        ))

        results.append(await run_test(
            session, "JavaScript - Hello World", "javascript",
            'console.log("Hello World")',
            expect_output="Hello World"
        ))

        results.append(await run_test(
            session, "C - Hello World", "c",
            '''#include <stdio.h>
int main() {
    printf("Hello World\\n");
    return 0;
}''',
            expect_output="Hello World"
        ))

        results.append(await run_test(
            session, "C++ - Hello World", "cpp",
            '''#include <iostream>
int main() {
    std::cout << "Hello World" << std::endl;
    return 0;
}''',
            expect_output="Hello World"
        ))

        results.append(await run_test(
            session, "Java - Hello World", "java",
            '''public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
    }
}''',
            expect_output="Hello World"
        ))


        # ══════════════════════════════════════
        # SECTION 2 : Algorithmes classiques
        # ══════════════════════════════════════

        print("\n\n  ▶ SECTION 2 : Algorithmes\n")

        results.append(await run_test(
            session, "Python - Fibonacci", "python",
            '''def fib(n):
    if n <= 1: return n
    return fib(n-1) + fib(n-2)
for i in range(8):
    print(fib(i), end=" ")
''',
            expect_output="0 1 1 2 3 5 8 13"
        ))

        results.append(await run_test(
            session, "Python - Tri à bulles", "python",
            '''arr = [64, 34, 25, 12, 22, 11, 90]
for i in range(len(arr)):
    for j in range(len(arr)-i-1):
        if arr[j] > arr[j+1]:
            arr[j], arr[j+1] = arr[j+1], arr[j]
print(arr)
''',
            expect_output="[11, 12, 22, 25, 34, 64, 90]"
        ))

        results.append(await run_test(
            session, "JavaScript - Factorielle", "javascript",
            '''function fact(n) {
    if (n <= 1) return 1;
    return n * fact(n-1);
}
console.log(fact(10));
''',
            expect_output="3628800"
        ))

        results.append(await run_test(
            session, "C++ - Somme tableau", "cpp",
            '''#include <iostream>
#include <vector>
#include <numeric>
int main() {
    std::vector<int> v = {1,2,3,4,5,6,7,8,9,10};
    int sum = std::accumulate(v.begin(), v.end(), 0);
    std::cout << sum << std::endl;
    return 0;
}''',
            expect_output="55"
        ))

        results.append(await run_test(
            session, "Java - Nombre premier", "java",
            '''public class Main {
    static boolean isPrime(int n) {
        if (n < 2) return false;
        for (int i = 2; i <= Math.sqrt(n); i++)
            if (n % i == 0) return false;
        return true;
    }
    public static void main(String[] args) {
        for (int i = 2; i <= 20; i++)
            if (isPrime(i)) System.out.print(i + " ");
        System.out.println();
    }
}''',
            expect_output="2 3 5 7 11 13 17 19"
        ))

        results.append(await run_test(
            session, "C - Recherche binaire", "c",
            '''#include <stdio.h>
int binary_search(int arr[], int n, int target) {
    int left = 0, right = n - 1;
    while (left <= right) {
        int mid = (left + right) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) left = mid + 1;
        else right = mid - 1;
    }
    return -1;
}
int main() {
    int arr[] = {1,3,5,7,9,11,13,15};
    printf("%d\\n", binary_search(arr, 8, 7));
    return 0;
}''',
            expect_output="3"
        ))


        # ══════════════════════════════════════
        # SECTION 3 : Gestion des erreurs
        # ══════════════════════════════════════

        print("\n\n  ▶ SECTION 3 : Gestion des erreurs\n")

        results.append(await run_test(
            session, "Python - SyntaxError", "python",
            'print("parenthese manquante"',
            expect_status="error",
            expect_error_contains="SyntaxError"
        ))

        results.append(await run_test(
            session, "Python - ZeroDivisionError", "python",
            'print(1/0)',
            expect_status="error",
            expect_error_contains="ZeroDivisionError"
        ))

        results.append(await run_test(
            session, "JavaScript - ReferenceError", "javascript",
            'console.log(variableInexistante)',
            expect_status="error",
            expect_error_contains="ReferenceError"
        ))

        results.append(await run_test(
            session, "C - Erreur compilation", "c",
            'int main() { return 0 }',
            expect_status="error"
        ))

        results.append(await run_test(
            session, "C++ - Erreur compilation", "cpp",
            'int main() { std::cout << "test" }',
            expect_status="error"
        ))

        results.append(await run_test(
            session, "Java - Erreur compilation", "java",
            '''public class Main {
    public static void main(String[] args) {
        System.out.println("manque point virgule")
    }
}''',
            expect_status="error"
        ))


        # ══════════════════════════════════════
        # SECTION 4 : Sécurité
        # ══════════════════════════════════════

        print("\n\n  ▶ SECTION 4 : Sécurité\n")

        results.append(await run_test(
            session, "Python - Blocage import socket", "python",
            'import socket\ns = socket.socket()',
            expect_status="rejected"
        ))

        results.append(await run_test(
            session, "Python - Blocage subprocess", "python",
            'import subprocess\nsubprocess.run(["ls"])',
            expect_status="rejected"
        ))

        results.append(await run_test(
            session, "JavaScript - Blocage child_process", "javascript",
            "const cp = require('child_process'); cp.exec('ls')",
            expect_status="rejected"
        ))

        results.append(await run_test(
            session, "C - Blocage system()", "c",
            '''#include <stdlib.h>
int main() { system("ls"); return 0; }''',
            expect_status="rejected"
        ))

        # results.append(await run_test(
        #     session, "Langage non supporté", "ruby",
        #     'puts "hello"',
        #     expect_status="rejected"
        # ))

        # Langage non supporté → FastAPI retourne 422
        print(f"\n{'─'*50}")
        print(f"  TEST : Langage non supporté (ruby)")
        print(f"{'─'*50}")
        async with session.post(
            f"{BASE_URL}/execute",
            json={"language": "ruby", "code": 'puts "hello"'}
        ) as resp:
            ok = resp.status == 422
            data = await resp.json()
            print(f"  HTTP    : {resp.status}")
            print(f"  Detail  : {data.get('detail', '')}")
            print(f"  {'✅ Test passé (422 attendu)' if ok else '❌ Test échoué'}")
            results.append(ok)


        # ══════════════════════════════════════
        # SECTION 5 : Timeout
        # ══════════════════════════════════════

        print("\n\n  ▶ SECTION 5 : Timeout\n")

        results.append(await run_test(
            session, "Python - Boucle infinie (timeout)", "python",
            'while True: pass',
            expect_status="error",
            expect_error_contains="Timeout"
        ))

        results.append(await run_test(
            session, "JavaScript - Boucle infinie (timeout)", "javascript",
            'while(true) {}',
            expect_status="error",
            expect_error_contains="Timeout"
        ))


        # ══════════════════════════════════════
        # SECTION 6 : Endpoints info
        # ══════════════════════════════════════

        print("\n\n  ▶ SECTION 6 : Endpoints\n")

        # Health
        print(f"\n{'─'*50}")
        print(f"  TEST : GET /health")
        print(f"{'─'*50}")
        async with session.get(f"{BASE_URL}/health") as resp:
            data = await resp.json()
            ok = data.get("status") == "ok" and data.get("docker") == "ok"
            print(f"  Docker  : {data.get('docker_version')}")
            print(f"  Status  : {data.get('status')}")
            print(f"  {'✅ Test passé' if ok else '❌ Test échoué'}")
            results.append(ok)

        # Languages
        print(f"\n{'─'*50}")
        print(f"  TEST : GET /languages")
        print(f"{'─'*50}")
        async with session.get(f"{BASE_URL}/languages") as resp:
            data = await resp.json()
            langs = [l["name"] for l in data.get("languages", [])]
            ok = len(langs) == 5
            print(f"  Langages : {langs}")
            print(f"  {'✅ Test passé' if ok else '❌ Test échoué'}")
            results.append(ok)

        # Token inexistant
        print(f"\n{'─'*50}")
        print(f"  TEST : GET /result/token-inexistant")
        print(f"{'─'*50}")
        async with session.get(
            f"{BASE_URL}/result/00000000-0000-0000-0000-000000000000"
        ) as resp:
            ok = resp.status == 404
            print(f"  HTTP    : {resp.status}")
            print(f"  {'✅ Test passé (404 attendu)' if ok else '❌ Test échoué'}")
            results.append(ok)


    # ══════════════════════════════════════
    # Résumé final
    # ══════════════════════════════════════

    total  = len(results)
    passed = sum(1 for r in results if r)
    failed = total - passed

    print("\n\n" + "═"*50)
    print("   RÉSUMÉ FINAL")
    print("═"*50)
    print(f"  Total   : {total}")
    print(f"  ✅ Passé : {passed}")
    print(f"  ❌ Échoué: {failed}")
    print(f"  Score   : {round(passed/total*100)}%")
    print("═"*50 + "\n")


asyncio.run(main())
