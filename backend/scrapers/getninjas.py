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

GETNINJAS_URLS = [
    "https://www.getninjas.com.br/desenvolvimento-de-software",
    "https://www.getninjas.com.br/criacao-de-sites",
    "https://www.getninjas.com.br/informatica",
]

def scrape_getninjas() -> list[dict]:
    leads = []

    for url in GETNINJAS_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            cards = soup.select(
                ".request-card, .service-card, article, "
                "[class*='request'], [class*='service-item']"
            )

            for card in cards:
                titulo_el = card.select_one("h2, h3, h4, .title, strong")
                desc_el   = card.select_one("p, .description, .text")
                link_el   = card.select_one("a[href]")

                if not titulo_el:
                    continue

                titulo = titulo_el.get_text(strip=True)
                desc   = desc_el.get_text(strip=True)[:300] if desc_el else ""
                href   = link_el["href"] if link_el else ""
                link   = f"https://www.getninjas.com.br{href}" if href.startswith("/") else href or url

                leads.append({
                    "plataforma": "GetNinjas",
                    "empresa":    "Cliente GetNinjas",
                    "pedido":     f"{titulo} — {desc}".strip(" —"),
                    "orcamento":  "Ver no link",
                    "link":       link,
                })

            time.sleep(2)

        except Exception as e:
            print(f"[GetNinjas] Erro ao rastrear {url}: {e}")

    print(f"[GetNinjas] {len(leads)} leads coletados")
    return leads