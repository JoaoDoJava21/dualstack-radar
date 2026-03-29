"""
test_local.py
Roda o radar completo sem Telegram, WhatsApp ou OpenAI.
Resultados aparecem no terminal E salvam em leads_encontrados.txt
"""

import time, hashlib, json
from datetime import datetime

# ── Scrapers ──────────────────────────────────────────────
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

def scrape_workana():
    leads = []
    try:
        url = "https://www.workana.com/jobs?category=it-programming&language=pt"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".project-item, [data-project-id]"):
            titulo  = card.select_one("h2 a, .project-title a, h3 a")
            desc    = card.select_one(".project-short-description, p")
            orcam   = card.select_one(".budget, .project-budget")
            link_el = card.select_one("a[href*='/job/'], a[href*='/proyecto/']")
            if not titulo: continue
            href = link_el["href"] if link_el else url
            if href and not href.startswith("http"):
                href = "https://www.workana.com" + href
            leads.append({
                "plataforma": "Workana",
                "empresa": "Cliente Workana",
                "pedido": f"{titulo.get_text(strip=True)} — {desc.get_text(strip=True)[:200] if desc else ''}",
                "orcamento": orcam.get_text(strip=True) if orcam else "Não informado",
                "link": href,
            })
    except Exception as e:
        print(f"  [ERRO Workana] {e}")
    return leads

def scrape_99freelas():
    leads = []
    try:
        url = "https://www.99freelas.com.br/projects?category=informatica-e-tecnologia"
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".project-item, article, .resultado-item"):
            titulo  = card.select_one("h2, h3, .title")
            desc    = card.select_one("p, .description")
            link_el = card.select_one("a[href]")
            if not titulo: continue
            href = link_el["href"] if link_el else url
            if href and not href.startswith("http"):
                href = "https://www.99freelas.com.br" + href
            leads.append({
                "plataforma": "99Freelas",
                "empresa": "Cliente 99Freelas",
                "pedido": f"{titulo.get_text(strip=True)} — {desc.get_text(strip=True)[:200] if desc else ''}",
                "orcamento": "Ver no link",
                "link": href,
            })
    except Exception as e:
        print(f"  [ERRO 99Freelas] {e}")
    return leads

def scrape_reddit():
    leads = []
    headers = {**HEADERS, "User-Agent": "DualStack-Radar/1.0"}
    for sub in ["brdev", "forhire", "slavelabour"]:
        try:
            url = f"https://www.reddit.com/r/{sub}/new.json?limit=15"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200: continue
            for post in r.json()["data"]["children"]:
                d = post["data"]
                leads.append({
                    "plataforma": f"Reddit r/{sub}",
                    "empresa": d["author"],
                    "pedido": f"{d['title']} — {d.get('selftext','')[:150]}",
                    "orcamento": "Ver post",
                    "link": f"https://reddit.com{d['permalink']}",
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [ERRO Reddit r/{sub}] {e}")
    return leads

def scrape_github():
    leads = []
    for q in ["python freelance", "developer wanted", "landing page"]:
        try:
            url = f"https://api.github.com/search/issues?q={q}+label:freelance+state:open&per_page=5"
            r = requests.get(url, headers={"Accept": "application/vnd.github.v3+json"}, timeout=10)
            if r.status_code != 200: continue
            for item in r.json().get("items", []):
                leads.append({
                    "plataforma": "GitHub Issues",
                    "empresa": item["user"]["login"],
                    "pedido": f"{item['title']} — {(item.get('body') or '')[:150]}",
                    "orcamento": "Ver issue",
                    "link": item["html_url"],
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [ERRO GitHub] {e}")
    return leads

# ── Scorer ────────────────────────────────────────────────
SERVICOS = [
    "landing page","automação","python","bot whatsapp","bot telegram",
    "site","sistema web","front-end","back-end","api","integração",
    "dashboard","scraping","e-commerce","wordpress","react","dev","app",
]
KEYWORDS = [
    "preciso de desenvolvedor","busco freelancer","alguém faz site",
    "preciso de automação","quem faz","busco programador",
    "contratar freelancer","preciso de bot","fazer um app","criar um site",
]

def pontuar(texto):
    t = texto.lower()
    score = 0
    hits = []
    for s in SERVICOS:
        if s in t: score += 8; hits.append(s)
    for k in KEYWORDS:
        if k in t: score += 5
    if any(w in t for w in ["r$","reais","orçamento","pagar"]): score += 10
    if any(w in t for w in ["urgente","rápido","hoje","agora"]): score += 7
    return min(score, 100), hits

# ── Deduplicador ──────────────────────────────────────────
_vistos = set()
def ja_visto(link):
    h = hashlib.md5(link.encode()).hexdigest()
    if h in _vistos: return True
    _vistos.add(h); return False

# ── Proposta fake (sem OpenAI) ────────────────────────────
def proposta_placeholder(empresa, pedido):
    return (
        f"Olá {empresa}! Vimos que você precisa de ajuda com: "
        f'"{pedido[:80]}..."\n\n'
        f"Somos a DualStack — João Victor & Carlos.\n"
        f"Podemos resolver isso pra você.\n\n"
        f"📱 (71) 98183-3678 | dualstack.netlify.app\n"
        f"[PROPOSTA GERADA PELA IA QUANDO OpenAI ESTIVER CONFIGURADA]"
    )

# ── Saída colorida no terminal ────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def print_lead(lead, score, hits, proposta):
    cor = GREEN if score >= 80 else YELLOW
    print(f"\n{'='*60}")
    print(f"{cor}{BOLD}LEAD ENCONTRADO — Score {score}/100{RESET}")
    print(f"{'='*60}")
    print(f"{CYAN}Plataforma:{RESET} {lead['plataforma']}")
    print(f"{CYAN}Empresa:   {RESET} {lead['empresa']}")
    print(f"{CYAN}Pedido:    {RESET} {lead['pedido'][:120]}")
    print(f"{CYAN}Orçamento: {RESET} {lead['orcamento']}")
    print(f"{CYAN}Link:      {RESET} {lead['link']}")
    print(f"{CYAN}Matches:   {RESET} {', '.join(hits) if hits else '—'}")
    print(f"\n{BOLD}--- PROPOSTA GERADA ---{RESET}")
    print(proposta)
    print(f"{'='*60}")

# ── Salva em arquivo ──────────────────────────────────────
def salvar_txt(lead, score, proposta):
    with open("leads_encontrados.txt", "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        f.write(f"Score: {score}/100\n")
        f.write(f"Plataforma: {lead['plataforma']}\n")
        f.write(f"Empresa: {lead['empresa']}\n")
        f.write(f"Pedido: {lead['pedido'][:200]}\n")
        f.write(f"Link: {lead['link']}\n")
        f.write(f"Proposta:\n{proposta}\n")

# ── MAIN ──────────────────────────────────────────────────
def rodar():
    print(f"\n{BOLD}{'='*60}")
    print("   DUALSTACK RADAR — Modo local (sem bot)")
    print(f"   {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}{RESET}\n")

    print("Coletando leads...\n")

    plataformas = [
        ("Workana",       scrape_workana),
        ("99Freelas",     scrape_99freelas),
        ("Reddit",        scrape_reddit),
        ("GitHub Issues", scrape_github),
    ]

    todos = []
    for nome, fn in plataformas:
        print(f"  Rastreando {nome}...")
        leads = fn()
        print(f"  -> {len(leads)} leads coletados")
        todos.extend(leads)
        time.sleep(2)

    print(f"\nTotal bruto: {len(todos)} leads")
    print(f"Aplicando filtro (score >= 60)...\n")

    aprovados = 0
    for lead in todos:
        if ja_visto(lead["link"]): continue
        score, hits = pontuar(lead["pedido"])
        if score < 60: continue

        proposta = proposta_placeholder(lead["empresa"], lead["pedido"])
        print_lead(lead, score, hits, proposta)
        salvar_txt(lead, score, proposta)
        aprovados += 1
        time.sleep(0.3)

    print(f"\n{BOLD}Ciclo completo!{RESET}")
    print(f"  Leads aprovados (score >= 60): {GREEN}{aprovados}{RESET}")
    print(f"  Salvos em: {CYAN}leads_encontrados.txt{RESET}")
    if aprovados == 0:
        print(f"\n  {YELLOW}Nenhum lead passou o filtro agora.")
        print(f"  Isso é normal — tente em 30min ou abaixe o score mínimo para 40.{RESET}")

if __name__ == "__main__":
    rodar()