"""
app.py — DualStack Radar
Conecta dashboard.html com scrapers reais + Groq IA

Instalar:
  pip install flask

Rodar (a partir da raiz do projeto):
  python backend/app.py
  Abre: http://localhost:5000
"""

from flask import Flask, jsonify, render_template, Response
import os, requests, time, hashlib, json, threading
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Carrega .env da raiz do projeto (um nível acima de backend/)
load_dotenv(Path(__file__).parent.parent / '.env')

# Templates e static ficam em frontend/, um nível acima
_root = Path(__file__).parent.parent
app = Flask(__name__,
            template_folder=str(_root / "frontend" / "templates"),
            static_folder=str(_root / "frontend" / "static"))
GROQ_API_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2"),
] if k]
_key_index = 0

def _next_key():
    global _key_index
    key = GROQ_API_KEYS[_key_index % len(GROQ_API_KEYS)]
    _key_index += 1
    return key

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
    if not GROQ_API_KEYS:
        return "Configure GROQ_API_KEY no .env"
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {_next_key()}", "Content-Type": "application/json"},
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

WORKANA_MAX_PAGES = 15

def scrape_workana():
    leads = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            vistos = set()

            for p in range(1, WORKANA_MAX_PAGES + 1):
                url = f"https://www.workana.com/jobs?category=it-programming&language=pt&page={p}"
                page.goto(url, wait_until="networkidle", timeout=30000)

                anchors = page.query_selector_all("a[href*='/job/']")
                for a in anchors:
                    href = a.get_attribute("href") or ""
                    if not href.startswith("http"):
                        href = "https://www.workana.com" + href
                    base = href.split("?")[0]
                    if base in vistos:
                        continue
                    vistos.add(base)
                    titulo = (a.inner_text() or "").strip()
                    if len(titulo) < 5:
                        continue
                    leads.append({
                        "plataforma": "Workana",
                        "empresa": "Cliente Workana",
                        "pedido": titulo,
                        "link": href,
                    })

                time.sleep(1)

            browser.close()

    except Exception as e:
        state["log"].append(f"[ERRO Workana] {e}")

    return leads


FREELAS99_QUERIES = [
    "landing+page","landing+page+wordpress","landing+page+html","criacao+site","criacao+site+wordpress",
    "site+institucional","site+empresarial","site+responsivo","site+simples","criar+site+do+zero",
    "refatoracao+site","melhorar+site","site+profissional","site+portfolio","site+negocio",
    "site+empresa","site+wordpress+ajuda","wordpress+site","elementor+site","site+rapido",
    "site+lento","otimizacao+site","seo+site","ajuste+site","manutencao+site",

    # 🤖 AUTOMAÇÃO
    "automacao+python","automacao+processos","automacao+tarefas","automacao+empresa","automacao+excel",
    "automacao+planilhas","automacao+dados","bot+whatsapp","bot+whatsapp+api","bot+telegram",
    "bot+discord","chatbot+atendimento","chatbot+empresa","automacao+atendimento","automacao+crm",
    "automacao+marketing","automacao+envio+mensagens","automacao+email","automacao+relatorios","rpa+python",
    "rpa+automacao","robot+web","script+automacao","automacao+web","automacao+sistema",

    # 🧠 BACKEND / SISTEMAS
    "sistema+web","sistema+gestao","sistema+interno","sistema+empresa","sistema+customizado",
    "erp+simples","crm+simples","crm+customizado","api+rest","api+node",
    "api+python","backend+node","backend+python","backend+developer","desenvolvimento+backend",
    "criar+api","api+do+zero","api+segura","api+autenticacao","api+login",
    "sistema+login","sistema+cadastro","painel+admin","admin+dashboard","crud+web",

    # 📊 DASHBOARD / DADOS
    "dashboard+relatorio","dashboard+web","dashboard+power+bi","dashboard+python","painel+controle",
    "painel+gestao","relatorio+automatizado","relatorio+dados","analise+dados","data+analysis",
    "business+intelligence","bi+dashboard","grafico+web","grafico+dashboard","dashboard+tempo+real",
    "monitoramento+dados","painel+kpi","dashboard+empresa","visualizacao+dados","report+automation",

    # 🛒 E-COMMERCE
    "loja+virtual","ecommerce+wordpress","loja+shopify","loja+woocommerce","woocommerce+ajuda",
    "shopify+ajuda","integracao+pagamento","mercado+pago+api","pagseguro+integracao","stripe+api",
    "checkout+customizado","carrinho+compras","pagamento+online","gateway+pagamento","integracao+loja",
    "api+ecommerce","sync+produtos","importar+produtos","automacao+loja","gestao+loja",

    # 🔌 INTEGRAÇÕES
    "integracao+api","integracao+sistema","integracao+erp","integracao+crm","webhook+api",
    "consumir+api","sincronizacao+dados","integracao+pagamentos","integracao+whatsapp","integracao+email",
    "integracao+planilha","integracao+google+sheets","integracao+zapier","integracao+make","automacao+integracao",
    "api+integration","system+integration","data+sync","automation+integration","backend+integration",

    # 🕷️ SCRAPING
    "scraping+dados","web+scraping","extracao+dados","coleta+dados","raspagem+dados",
    "crawler+python","bot+scraping","scraper+site","dados+web","data+scraping",
    "python+scraping","automation+scraping","scraping+ecommerce","scraping+precos","scraping+produtos",
    "scraping+imoveis","scraping+leads","extrair+dados+site","coletar+informacoes","web+crawler",

    # 💻 DEV GERAL
    "desenvolvedor+freelancer","programador+freelancer","freelancer+python","freelancer+node","fullstack+freelancer",
    "dev+freelancer","programador+web","dev+backend","dev+frontend","freelancer+fullstack",
    "contratar+programador","preciso+programador","dev+urgente","freelancer+urgente","programador+urgente",

    # ⚙️ BUG / URGÊNCIA (OURO)
    "corrigir+erro+site","bug+site","erro+api","erro+backend","erro+frontend",
    "ajuste+codigo","manutencao+codigo","codigo+bugado","resolver+bug","debug+codigo",
    "site+quebrado","site+fora+do+ar","api+erro","problema+wordpress","erro+login",
    "erro+servidor","bug+wordpress","falha+sistema","erro+deploy","fix+bug+website",

    # 🚀 INTENÇÃO
    "preciso+de+programador","contratar+dev","projeto+urgente","freelancer+urgente","preciso+site",
    "preciso+bot","preciso+automacao","preciso+api","preciso+sistema","preciso+integracao",
    "hire+developer","need+developer","urgent+project","looking+developer","backend+help",

    # 🌎 INGLÊS (DINHEIRO ESCONDIDO)
    "build+website","create+landing+page","wordpress+developer","fix+wordpress","website+bug",
    "api+development","rest+api+developer","python+developer","node+developer","backend+api",
    "automation+python","task+automation","bot+development","telegram+bot","whatsapp+bot",
    "web+automation","data+automation","scraping+python","web+scraper","extract+data",
    "dashboard+web","data+dashboard","build+dashboard","report+dashboard","analytics+dashboard"
]


def scrape_99freelas():
    leads = []
    vistos = set()

    for query in FREELAS99_QUERIES:
        try:
            url = f"https://www.99freelas.com.br/projects?q={query}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

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

            time.sleep(1)

        except Exception as e:
            state["log"].append(f"[ERRO 99Freelas query={query}] {e}")

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

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

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
        "groq_ok":     bool(GROQ_API_KEYS),
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