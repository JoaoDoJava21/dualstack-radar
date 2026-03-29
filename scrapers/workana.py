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

WORKANA_URLS = [
    "https://www.workana.com/jobs?category=it-programming&language=pt",
    "https://www.workana.com/jobs?category=web-mobile&language=pt",
]

def scrape_workana() -> list[dict]:
    leads = []

    for url in WORKANA_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            cards = soup.select(".project-item, .js-project-item, article.project")

            for card in cards:
                titulo_el  = card.select_one("h2, h3, .project-title, [class*='title']")
                desc_el    = card.select_one(".project-description, .description, p")
                orcam_el   = card.select_one(".budget, .amount, [class*='budget']")
                link_el    = card.select_one("a[href*='/job/'], a[href*='/project/']")

                if not titulo_el:
                    continue

                titulo  = titulo_el.get_text(strip=True)
                desc    = desc_el.get_text(strip=True)[:300] if desc_el else ""
                orcam   = orcam_el.get_text(strip=True) if orcam_el else "Não informado"
                href    = link_el["href"] if link_el else ""
                link    = f"https://www.workana.com{href}" if href.startswith("/") else href or url

                leads.append({
                    "plataforma": "Workana",
                    "empresa":    "Cliente Workana",
                    "pedido":     f"{titulo} — {desc}".strip(" —"),
                    "orcamento":  orcam,
                    "link":       link,
                })

            time.sleep(2)

        except Exception as e:
            print(f"[Workana] Erro ao rastrear {url}: {e}")

    print(f"[Workana] {len(leads)} leads coletados")
    return leads