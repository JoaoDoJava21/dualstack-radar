import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

FREELAS99_URLS = [
    "https://www.99freelas.com.br/projects?q=site+landing+page",
    "https://www.99freelas.com.br/projects?q=python+automacao+bot",
    "https://www.99freelas.com.br/projects?q=sistema+web+api",
]

def scrape_99freelas() -> list[dict]:
    leads = []

    for url in FREELAS99_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            cards = soup.select("li.item, article.project-item, .project-list-item")

            for card in cards:
                titulo_el = card.select_one("h2, h3, .title, a[href*='/project/']")
                desc_el   = card.select_one(".description, .text, p")
                orcam_el  = card.select_one(".budget, .value, [class*='price']")
                link_el   = card.select_one("a[href*='/project/']")

                if not titulo_el:
                    continue

                titulo = titulo_el.get_text(strip=True)
                desc   = desc_el.get_text(strip=True)[:300] if desc_el else ""
                orcam  = orcam_el.get_text(strip=True) if orcam_el else "Ver no link"
                href   = link_el["href"] if link_el else ""
                link   = f"https://www.99freelas.com.br{href}" if href.startswith("/") else href or url

                leads.append({
                    "plataforma": "99Freelas",
                    "empresa":    "Cliente 99Freelas",
                    "pedido":     f"{titulo} — {desc}".strip(" —"),
                    "orcamento":  orcam,
                    "link":       link,
                })

            time.sleep(2)

        except Exception as e:
            print(f"[99Freelas] Erro ao rastrear {url}: {e}")

    print(f"[99Freelas] {len(leads)} leads coletados")
    return leads