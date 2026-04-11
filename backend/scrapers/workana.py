import requests
import time
import random
from typing import List, Dict

BASE_API = "https://www.workana.com/api/projects"  # pode variar (veja DevTools)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.workana.com/",
}

PARAMS = {
    "language": "pt",
    "category": "it-programming",
    "page": 1,
}

MAX_PAGES = 3


def fetch_projects(page: int) -> dict | None:
    try:
        params = PARAMS.copy()
        params["page"] = page

        response = requests.get(
            BASE_API,
            headers=HEADERS,
            params=params,
            timeout=15
        )

        if response.status_code != 200:
            print(f"[ERRO] Status {response.status_code}")
            return None

        return response.json()

    except Exception as e:
        print(f"[ERRO] {e}")
        return None


def scrape_workana_api() -> List[Dict]:
    leads = []

    for page in range(1, MAX_PAGES + 1):
        print(f"[INFO] Página {page}")

        data = fetch_projects(page)

        if not data:
            continue

        projects = data.get("projects") or data.get("data") or []

        for proj in projects:
            try:
                titulo = proj.get("title", "").strip()
                desc = proj.get("description", "").strip()[:300]

                budget_data = proj.get("budget") or {}
                orcamento = budget_data.get("amount") or budget_data.get("min") or "Não informado"

                link = f"https://www.workana.com/job/{proj.get('slug', '')}"

                leads.append({
                    "plataforma": "Workana",
                    "empresa": "Cliente Workana",
                    "pedido": f"{titulo} — {desc}".strip(" —"),
                    "orcamento": str(orcamento),
                    "link": link,
                })

            except Exception as e:
                print(f"[ERRO PARSE] {e}")

        time.sleep(random.uniform(1, 3))

    print(f"[Workana API] {len(leads)} leads coletados")
    return leads


if __name__ == "__main__":
    leads = scrape_workana_api()

    for lead in leads:
        print("=" * 50)
        print(lead["pedido"])
        print(lead["orcamento"])
        print(lead["link"])