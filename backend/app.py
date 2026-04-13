"""
app.py — DualStack Radar
Conecta dashboard.html com scrapers reais + Groq IA

Instalar:
  pip install flask

Rodar (a partir da raiz do projeto):
  python backend/app.py
  Abre: http://localhost:5000
"""

from flask import Flask, jsonify, render_template, Response, request
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
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
] if k]
from concurrent.futures import ThreadPoolExecutor, as_completed
_leads_lock = threading.Lock()   # protege state["leads"] em acesso paralelo

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

def gerar_proposta(empresa, pedido, plataforma, key):
    """Chama a API Groq com a chave informada (sem rotação global)."""
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
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

WORKANA_MAX_PAGES = 1

# ── QUERIES POR CATEGORIA ─────────────────────────────────

FREELAS99_QUERIES_ADMIN = [
    "gestao+empresarial","gestao+projetos","gestao+equipe","administracao+empresa",
    "assistente+administrativo","secretaria+virtual","assistente+virtual",
    "suporte+administrativo","organizacao+empresa","gestao+documentos",
    "financeiro+empresa","gestao+financeira","controle+financeiro","fluxo+caixa",
    "contabilidade+freelancer","auxiliar+contabil","lancamentos+contabeis",
    "declaracao+irpf","imposto+renda","contabilidade+online",
    "recursos+humanos","recrutamento+selecao","gestao+pessoas","folha+pagamento",
    "rh+freelancer","consultoria+rh","treinamento+equipe",
    "marketing+digital","gestao+redes+sociais","social+media","copywriting",
    "redacao+publicitaria","producao+conteudo","marketing+conteudo",
    "gestao+trafego","google+ads","facebook+ads","instagram+ads",
    "atendimento+cliente","suporte+cliente","customer+success",
    "gestao+crm","crm+empresa","relacionamento+cliente",
    "consultoria+empresarial","consultoria+negocios","plano+negocios",
    "business+plan","consultoria+startup","mentoria+negocios",
]

FREELAS99_QUERIES_DESIGN = [
    "design+grafico","identidade+visual","criacao+logo","logo+marca",
    "logotipo","branding","manual+marca","rebrand",
    "ui+ux","design+ui","design+ux","interface+usuario","wireframe",
    "prototipo+figma","design+figma","design+web","layout+site",
    "design+landing+page","mockup+site",
    "design+redes+sociais","posts+instagram","arte+instagram",
    "design+banner","banner+digital","flyer+digital","artes+graficas",
    "design+cartao+visita","cartao+visita+design","design+folder",
    "design+catalogo","design+panfleto","embalagem+produto",
    "motion+graphics","edicao+video","vinheta+animada","animacao+logo",
    "edicao+reels","producao+video",
    "ilustracao+digital","ilustracao+personagem","criacao+mascote",
    "design+icone","icon+design",
]

def scrape_workana(page_start=1, page_end=WORKANA_MAX_PAGES, workana_cat="it-programming"):
    leads = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            vistos = set()

            for p in range(page_start, page_end + 1):
                url = f"https://www.workana.com/jobs?category={workana_cat}&language=pt&page={p}"
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

CATEGORIAS = {
    "ti": {
        "workana_cat": "it-programming",
        "freelas":     FREELAS99_QUERIES,
        "reddit":      ["brdev", "forhire", "slavelabour", "brasil"],
        "github":      ["python freelance", "developer wanted", "landing page developer"],
    },
    "admin": {
        "workana_cat": "administration",
        "freelas":     FREELAS99_QUERIES_ADMIN,
        "reddit":      ["forhire", "slavelabour", "brasil", "smallbusiness", "entrepreneur"],
        "github":      [],
    },
    "design": {
        "workana_cat": "design-multimedia",
        "freelas":     FREELAS99_QUERIES_DESIGN,
        "reddit":      ["forhire", "slavelabour", "graphic_design", "web_design", "brasil"],
        "github":      ["designer wanted", "ui ux freelance", "design freelancer"],
    },
}


def scrape_99freelas(queries=None):
    leads = []
    vistos = set()

    for query in (queries or FREELAS99_QUERIES):
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

def scrape_reddit(subreddits=None):
    leads = []
    for sub in (subreddits or REDDIT_SUBS):
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

def scrape_github(search_queries=None):
    leads = []
    for q in (search_queries or GITHUB_QUERIES):
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
_vistos_lock = threading.Lock()   # protege _vistos em leituras/escritas paralelas

def ja_visto(link):
    h = hashlib.md5(link.encode()).hexdigest()
    with _vistos_lock:
        if h in _vistos:
            return True
        _vistos.add(h)
        return False


def _dividir_trabalho(n, cat_config):
    """
    Divide 99Freelas / Reddit / GitHub da categoria em n fatias (round-robin).
    Workana NÃO entra aqui — Playwright não é thread-safe e roda
    separadamente em fase única antes dos workers paralelos.
    """
    freelas = [cat_config["freelas"][i::n] for i in range(n)]
    reddit  = [cat_config["reddit"][i::n]  for i in range(n)]
    github  = [cat_config["github"][i::n]  for i in range(n)]

    return [
        {"freelas": freelas[i], "reddit": reddit[i], "github": github[i]}
        for i in range(n)
    ]

def _worker_paralelo(worker_id, key, pkg, workana_lote):
    """
    Worker paralelo (thread-safe): recebe sua fatia de leads Workana
    já raspados + raspa 99Freelas/Reddit/GitHub de forma independente.
    Gera propostas com sua chave dedicada e insere em state["leads"].
    NÃO usa Playwright — só requests/BeautifulSoup (thread-safe).
    """
    locais = list(workana_lote)  # leads Workana já coletados na fase 1

    # 99Freelas — fatia de queries exclusiva deste worker
    if pkg["freelas"]:
        state["log"].append(
            f"[W{worker_id}] 99Freelas ({len(pkg['freelas'])} queries)..."
        )
        leads = scrape_99freelas(queries=pkg["freelas"])
        state["log"].append(f"[W{worker_id}] 99Freelas: {len(leads)} leads")
        locais.extend(leads)

    # Reddit — subreddits exclusivos deste worker
    if pkg["reddit"]:
        state["log"].append(
            f"[W{worker_id}] Reddit ({', '.join(pkg['reddit'])})..."
        )
        leads = scrape_reddit(subreddits=pkg["reddit"])
        state["log"].append(f"[W{worker_id}] Reddit: {len(leads)} leads")
        locais.extend(leads)

    # GitHub — queries exclusivas deste worker
    if pkg["github"]:
        state["log"].append(f"[W{worker_id}] GitHub...")
        leads = scrape_github(search_queries=pkg["github"])
        state["log"].append(f"[W{worker_id}] GitHub: {len(leads)} leads")
        locais.extend(leads)

    # Filtra duplicatas globais (thread-safe via _vistos_lock)
    novos = [l for l in locais if not ja_visto(l["link"])]
    state["log"].append(
        f"[W{worker_id}] {len(novos)} leads novos → gerando propostas..."
    )

    # Gera propostas com a chave exclusiva deste worker
    for lead in novos:
        state["log"].append(
            f"[W{worker_id}] Gerando proposta: {lead['pedido'][:50]}..."
        )
        proposta = gerar_proposta(
            lead["empresa"], lead["pedido"], lead["plataforma"], key
        )
        lead["proposta"] = proposta
        lead["hora"]     = datetime.now().strftime("%H:%M")
        lead["id"]       = hashlib.md5(lead["link"].encode()).hexdigest()[:8]
        with _leads_lock:
            state["leads"].insert(0, lead)
        time.sleep(0.3)

    return len(novos)


def rodar_scan(categoria='ti'):
    state["rodando"] = True
    state["log"]     = []

    if not GROQ_API_KEYS:
        state["log"].append("ERRO: configure GROQ_API_KEY no .env")
        state["rodando"] = False
        return

    cat_config = CATEGORIAS.get(categoria, CATEGORIAS["ti"])
    n = len(GROQ_API_KEYS)

    # ── FASE 1: Workana — Playwright não é thread-safe, roda sequencial ──
    state["log"].append(f"Fase 1: Workana [{categoria}] (Playwright, sequencial)...")
    workana_leads = scrape_workana(workana_cat=cat_config["workana_cat"])
    state["log"].append(f"Fase 1 concluída — {len(workana_leads)} leads Workana")

    # Distribui leads Workana entre os workers (round-robin)
    workana_lotes = [workana_leads[i::n] for i in range(n)]

    # ── FASE 2: 99Freelas / Reddit / GitHub — paralelo, thread-safe ──
    pacotes = _dividir_trabalho(n, cat_config)
    state["log"].append(
        f"Fase 2: {n} worker(s) paralelo(s) — 99Freelas, Reddit, GitHub + propostas"
    )

    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = {
            ex.submit(
                _worker_paralelo, i + 1, GROQ_API_KEYS[i], pacotes[i], workana_lotes[i]
            ): i + 1
            for i in range(n)
        }
        for future in as_completed(futures):
            wid = futures[future]
            try:
                total = future.result()
                state["log"].append(f"[Worker {wid}] concluído — {total} leads")
            except Exception as e:
                state["log"].append(f"[Worker {wid}] ERRO: {e}")

    state["ultimo_scan"] = datetime.now().strftime("%H:%M")
    state["log"].append(
        f"Scan concluído — {len(state['leads'])} leads no total"
    )
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

@app.route("/plans")
def plans():
    return render_template("plans.html")

@app.route("/api/scan", methods=["POST"])
def api_scan():
    if state["rodando"]:
        return jsonify({"ok": False, "msg": "Scan já está rodando"})
    data      = request.get_json(silent=True) or {}
    categoria = data.get("categoria", "ti")
    if categoria not in CATEGORIAS:
        categoria = "ti"
    t = threading.Thread(target=rodar_scan, args=(categoria,), daemon=True)
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