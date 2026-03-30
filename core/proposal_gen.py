import os, requests, time, hashlib
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

load_dotenv()

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

SYSTEM_PROMPT = """Você é o assistente comercial da DualStack, equipe de TI
freelancer formada por João Victor e Carlos. Especialistas em:
automações Python, landing pages, bots WhatsApp/Telegram,
front-end, back-end, APIs e dashboards.
Gere propostas comerciais curtas (máx 120 palavras), diretas e personalizadas.
Tom: próximo e profissional, sem enrolação.
Sempre termine com WhatsApp e portfólio."""

USER_TEMPLATE = """Gere uma proposta comercial para:
Empresa/Usuário: {empresa}
Pedido: {pedido}
Plataforma: {plataforma}

- Mostre que leu o pedido deles
- Liste só os serviços relevantes
- Chame para conversa sem pressão
- Máximo 120 palavras
- Assine: João Victor & Carlos | DualStack
- WhatsApp: (71) 98183-3678
- Portfólio: dualstack.netlify.app"""


def gerar_proposta(empresa, pedido, plataforma):
    if not GROQ_API_KEYS:
        return "[ Configure GROQ_API_KEY no .env com sua chave real ]"
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {_next_key()}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_TEMPLATE.format(
                        empresa=empresa, pedido=pedido[:300], plataforma=plataforma)},
                ],
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[ERRO Groq] {e}"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

LINK_INVALIDO = {
    "https://www.workana.com/",
    "https://www.workana.com/jobs",
    "https://www.workana.com",
    "https://www.99freelas.com.br",
    "https://www.99freelas.com.br/",
    "https://www.99freelas.com.br/project/new",
}


def link_valido(href):
    """Retorna True só se for um link de projeto específico."""
    if not href or href in LINK_INVALIDO:
        return False
    if href.startswith("http") and len(href) > 40:
        return True
    return False


WORKANA_MAX_PAGES = 10

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

                for a in page.query_selector_all("a[href*='/job/']"):
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
        print(f"  [ERRO Workana] {e}")

    return leads


FREELAS99_QUERIES = [
    # 🌐 SITES (alta demanda)
    "landing+page",
    "landing+page+wordpress",
    "criacao+site",
    "criacao+site+wordpress",
    "site+institucional",
    "site+empresarial",
    "site+responsivo",
    "criar+site+do+zero",
    "refatoracao+site",
    "melhorar+site",

    # 🤖 AUTOMAÇÃO (alto valor)
    "automacao+python",
    "automacao+processos",
    "automacao+planilhas",
    "automacao+excel",
    "bot+whatsapp",
    "bot+whatsapp+api",
    "bot+telegram",
    "chatbot+atendimento",
    "automacao+atendimento",
    "robot+web+scraping",

    # 🧠 BACKEND / SISTEMAS (ticket médio alto)
    "sistema+web",
    "sistema+gestao",
    "sistema+interno",
    "erp+simples",
    "crm+simples",
    "api+rest",
    "api+node",
    "api+python",
    "backend+node",
    "backend+python",
    "desenvolvimento+backend",

    # 📊 DASHBOARDS / DADOS
    "dashboard+relatorio",
    "dashboard+power+bi",
    "dashboard+web",
    "painel+admin",
    "painel+controle",
    "analise+dados",
    "relatorio+automatizado",

    # 🛒 E-COMMERCE / INTEGRAÇÃO
    "loja+virtual",
    "ecommerce+wordpress",
    "loja+shopify",
    "woocommerce",
    "integracao+api",
    "integracao+pagamento",
    "mercado+pago+api",
    "pagseguro+integracao",

    # 🔌 INTEGRAÇÕES (muito dinheiro aqui)
    "integracao+sistema",
    "integracao+erp",
    "integracao+crm",
    "webhook+api",
    "consumir+api",
    "sincronizacao+dados",

    # 🕷️ SCRAPING / DADOS (nicho forte)
    "scraping+dados",
    "web+scraping",
    "extracao+dados",
    "coleta+dados",
    "raspagem+dados",
    "crawler+python",

    # 💻 DEV GERAL
    "desenvolvedor+freelancer",
    "programador+freelancer",
    "freelancer+python",
    "freelancer+node",
    "fullstack+freelancer",

    # ⚙️ CORREÇÕES / URGÊNCIA (ouro escondido)
    "corrigir+erro+site",
    "bug+site",
    "erro+api",
    "ajuste+codigo",
    "manutencao+site",
    "otimizacao+site",
    "site+lento",
    "problema+wordpress",


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
                href_base = href.split("?")[0]
                if href_base in vistos:
                    continue
                vistos.add(href_base)

                titulo = a.get_text(strip=True)
                if len(titulo) < 8:
                    titulo = a.parent.get_text(strip=True)[:120] if a.parent else titulo
                if len(titulo) < 5:
                    continue

                leads.append({
                    "plataforma": "99Freelas",
                    "empresa": "Cliente 99Freelas",
                    "pedido": titulo,
                    "link": href,
                })

            time.sleep(1)

        except Exception as e:
            print(f"  [ERRO 99Freelas query={query}] {e}")

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
                    "plataforma": f"Reddit r/{sub}",
                    "empresa": d["author"],
                    "pedido": f"{d['title']} {d.get('selftext','')[:100]}".strip(),
                    "link": f"https://reddit.com{d['permalink']}",
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [ERRO Reddit r/{sub}] {e}")
    return leads


_vistos: set[str] = set()

def ja_visto(link):
    h = hashlib.md5(link.encode()).hexdigest()
    if h in _vistos: return True
    _vistos.add(h); return False


def salvar(lead, proposta):
    with open("leads_encontrados.txt", "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Data:      {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
        f.write(f"Plataforma:{lead['plataforma']}\n")
        f.write(f"Empresa:   {lead['empresa']}\n")
        f.write(f"Pedido:    {lead['pedido'][:250]}\n")
        f.write(f"Link:      {lead['link']}\n")
        f.write(f"Proposta:\n{proposta}\n")


G = "\033[92m"; C = "\033[96m"; B = "\033[1m"; X = "\033[0m"


def rodar():
    print(f"\n{B}{'='*60}")
    print("   DUALSTACK RADAR — links reais dos projetos")
    print(f"   {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*60}{X}\n")

    todos = []
    for nome, fn in [
        ("Workana",   scrape_workana),
        ("99Freelas", scrape_99freelas),
        ("Reddit",    scrape_reddit),
    ]:
        print(f"  Rastreando {nome}...")
        leads = fn()
        print(f"  -> {len(leads)} leads encontrados")
        todos.extend(leads)
        time.sleep(2)

    print(f"\nTotal: {len(todos)} leads\n")

    if not todos:
        print("Nenhum lead coletado. Os sites podem estar com bloqueio temporário.")
        print("Tente novamente em alguns minutos.")
        return

    for lead in todos:
        if ja_visto(lead["link"]):
            continue

        print(f"\n{'='*60}")
        print(f"{B}[{lead['plataforma']}]{X}")
        print(f"{C}Pedido:{X} {lead['pedido'][:100]}")
        print(f"{C}Link:{X}   {lead['link']}")
        print(f"{B}Gerando proposta...{X}")
        proposta = gerar_proposta(lead["empresa"], lead["pedido"], lead["plataforma"])
        print(proposta)
        salvar(lead, proposta)
        time.sleep(1)

    print(f"\n{G}{B}Pronto! Salvo em leads_encontrados.txt{X}")


if __name__ == "__main__":
    rodar()