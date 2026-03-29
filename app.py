"""
app.py — DualStack Radar
Conecta dashboard.html com scrapers reais + Groq IA

Instalar:
  pip install flask

Rodar:
  python app.py
  Abre: http://localhost:5000
"""

from flask import Flask, jsonify, render_template, Response
import os, requests, time, hashlib, json, threading
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__, template_folder=".")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── estado global ─────────────────────────────────────────
state = {
    "rodando": False,
    "leads": [],
    "log": [],
    "ultimo_scan": None,
}

# ── IA ────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é o assistente comercial da DualStack, equipe de TI
freelancer formada por João Victor e Carlos. Especialistas em automações Python,
landing pages, bots WhatsApp/Telegram, front-end, back-end, APIs e dashboards.
Gere propostas comerciais curtas (máx 120 palavras), diretas e personalizadas.
Tom: próximo e profissional. Termine com WhatsApp e portfólio."""

def gerar_proposta(empresa, pedido, plataforma):
    if not GROQ_API_KEY:
        return "Configure GROQ_API_KEY no .env"
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": (
                        f"Empresa: {empresa}\n"
                        f"Pedido: {pedido[:300]}\n"
                        f"Plataforma: {plataforma}\n\n"
                        f"Assine: João Victor & Carlos | DualStack\n"
                        f"WhatsApp: (71) 98183-3678\n"
                        f"Portfólio: dualstack.netlify.app"
                    )},
                ],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Erro ao gerar proposta: {e}"


# ── SCRAPERS ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

def scrape_workana():
    leads = []
    try:
        r = requests.get(
            "https://www.workana.com/jobs?category=it-programming&language=pt",
            headers=HEADERS, timeout=15
        )
        soup = BeautifulSoup(r.text, "html.parser")
        vistos = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/job/" not in href and "/trabajo/" not in href:
                continue
            if not href.startswith("http"):
                href = "https://www.workana.com" + href
            base = href.split("?")[0]
            if base in vistos:
                continue
            vistos.add(base)
            titulo = a.get_text(strip=True)
            if len(titulo) < 8:
                titulo = (a.parent.get_text(strip=True)[:120] if a.parent else titulo)
            if len(titulo) < 5:
                continue
            leads.append({"plataforma": "Workana", "empresa": "Cliente Workana", "pedido": titulo, "link": href})
    except Exception as e:
        state["log"].append(f"[ERRO Workana] {e}")
    return leads

def scrape_99freelas():
    leads = []
    try:
        r = requests.get(
            "https://www.99freelas.com.br/projects?category=informatica-e-tecnologia",
            headers=HEADERS, timeout=15
        )
        soup = BeautifulSoup(r.text, "html.parser")
        vistos = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/project/" not in href or "/project/new" in href:
                continue
            if not href.startswith("http"):
                href = "https://www.99freelas.com.br" + href
            base = href.split("?")[0]
            if base in vistos:
                continue
            vistos.add(base)
            titulo = a.get_text(strip=True)
            if len(titulo) < 8:
                titulo = (a.parent.get_text(strip=True)[:120] if a.parent else titulo)
            if len(titulo) < 5:
                continue
            leads.append({"plataforma": "99Freelas", "empresa": "Cliente 99Freelas", "pedido": titulo, "link": href})
    except Exception as e:
        state["log"].append(f"[ERRO 99Freelas] {e}")
    return leads

def scrape_reddit():
    leads = []
    for sub in ["brdev", "forhire", "slavelabour", "brasil"]:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/new.json?limit=10",
                headers={**HEADERS, "User-Agent": "DualStack-Radar/1.0"},
                timeout=10
            )
            if r.status_code != 200:
                continue
            for post in r.json()["data"]["children"]:
                d = post["data"]
                leads.append({
                    "plataforma": f"Reddit",
                    "empresa": d["author"],
                    "pedido": f"{d['title']} {d.get('selftext','')[:100]}".strip(),
                    "link": f"https://reddit.com{d['permalink']}",
                })
            time.sleep(1)
        except Exception as e:
            state["log"].append(f"[ERRO Reddit r/{sub}] {e}")
    return leads

def scrape_github():
    leads = []
    for q in ["python freelance", "developer wanted", "landing page developer"]:
        try:
            r = requests.get(
                f"https://api.github.com/search/issues?q={q}+label:freelance+state:open&per_page=5",
                headers={"Accept": "application/vnd.github.v3+json"},
                timeout=10
            )
            if r.status_code != 200:
                continue
            for item in r.json().get("items", []):
                leads.append({
                    "plataforma": "GitHub",
                    "empresa": item["user"]["login"],
                    "pedido": f"{item['title']} {(item.get('body') or '')[:100]}".strip(),
                    "link": item["html_url"],
                })
            time.sleep(1)
        except Exception as e:
            state["log"].append(f"[ERRO GitHub] {e}")
    return leads


# ── LÓGICA DE SCAN ────────────────────────────────────────

_vistos: set[str] = set()

def ja_visto(link):
    h = hashlib.md5(link.encode()).hexdigest()
    if h in _vistos: return True
    _vistos.add(h); return False

def rodar_scan():
    state["rodando"] = True
    state["log"] = []
    novos = []

    scrapers = [
        ("Workana",   scrape_workana),
        ("99Freelas", scrape_99freelas),
        ("Reddit",    scrape_reddit),
        ("GitHub",    scrape_github),
    ]

    todos = []
    for nome, fn in scrapers:
        state["log"].append(f"Rastreando {nome}...")
        leads = fn()
        state["log"].append(f"{nome}: {len(leads)} leads encontrados")
        todos.extend(leads)
        time.sleep(1)

    state["log"].append(f"Total: {len(todos)} leads | Gerando propostas...")

    for lead in todos:
        if ja_visto(lead["link"]):
            continue
        state["log"].append(f"Gerando proposta para: {lead['pedido'][:60]}...")
        proposta = gerar_proposta(lead["empresa"], lead["pedido"], lead["plataforma"])
        lead["proposta"] = proposta
        lead["hora"] = datetime.now().strftime("%H:%M")
        lead["id"] = hashlib.md5(lead["link"].encode()).hexdigest()[:8]
        novos.append(lead)
        # prepend — mais recentes primeiro
        state["leads"].insert(0, lead)
        time.sleep(0.8)

    state["ultimo_scan"] = datetime.now().strftime("%H:%M")
    state["log"].append(f"Scan concluído — {len(novos)} novos leads")
    state["rodando"] = False


# ── ROTAS FLASK ───────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/api/scan", methods=["POST"])
def api_scan():
    if state["rodando"]:
        return jsonify({"ok": False, "msg": "Scan já está rodando"})
    t = threading.Thread(target=rodar_scan, daemon=True)
    t.start()
    return jsonify({"ok": True})

@app.route("/api/status")
def api_status():
    return jsonify({
        "rodando":     state["rodando"],
        "total_leads": len(state["leads"]),
        "ultimo_scan": state["ultimo_scan"],
        "log":         state["log"][-5:],  # últimas 5 mensagens
    })

@app.route("/api/leads")
def api_leads():
    return jsonify(state["leads"])

@app.route("/api/clear", methods=["POST"])
def api_clear():
    state["leads"] = []
    _vistos.clear()
    return jsonify({"ok": True})


# ── START ─────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser
    print("\n" + "="*50)
    print("  DualStack Radar — iniciando...")
    print("  Abrindo: http://localhost:5000")
    print("="*50 + "\n")
    webbrowser.open("http://localhost:5000")
    app.run(debug=False, port=5000)