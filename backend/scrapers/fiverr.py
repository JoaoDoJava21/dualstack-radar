"""
scrapers/fiverr.py
Busca CLIENTES no Fiverr Community via DuckDuckGo HTML.
DuckDuckGo é muito menos agressivo com rate-limit que o Google.
"""

import time
import random
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FIVERR_QUERIES = [
    'site:community.fiverr.com "need a developer"',
    'site:community.fiverr.com "looking for" developer',
    'site:community.fiverr.com "need" landing page',
    'site:community.fiverr.com "need" python bot',
    'site:community.fiverr.com "need" whatsapp bot',
    'site:community.fiverr.com "need" dashboard',
    'site:community.fiverr.com "busco" desenvolvedor',
    'site:community.fiverr.com "preciso" site',
]


def scrape_fiverr() -> list[dict]:
    leads = []
    vistos = set()

    for query in FIVERR_QUERIES:
        try:
            r = requests.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "kl": "br-pt"},
                headers=HEADERS,
                timeout=15,
            )

            if r.status_code != 200:
                print(f"[Fiverr] Status {r.status_code} para: {query[:50]}")
                continue

            soup = BeautifulSoup(r.text, "html.parser")

            for result in soup.select(".result"):
                link_el  = result.select_one("a.result__a")
                snip_el  = result.select_one(".result__snippet")

                if not link_el:
                    continue

                href = link_el.get("href", "")
                if not href.startswith("http"):
                    continue
                if "community.fiverr.com" not in href:
                    continue
                if href in vistos:
                    continue
                vistos.add(href)

                titulo = link_el.get_text(strip=True)
                desc   = snip_el.get_text(strip=True) if snip_el else ""

                leads.append({
                    "plataforma": "Fiverr",
                    "empresa":    "Cliente Fiverr",
                    "pedido":     f"{titulo} — {desc}".strip(" —"),
                    "link":       href,
                })

        except Exception as e:
            print(f"[Fiverr] Erro: {e}")

        time.sleep(random.uniform(2, 4))

    print(f"[Fiverr] {len(leads)} leads coletados")
    return leads


if __name__ == "__main__":
    dados = scrape_fiverr()
    for d in dados:
        print(d)
