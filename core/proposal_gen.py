import os, requests, time, hashlib
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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
    if not GROQ_API_KEY or GROQ_API_KEY == "gsk_SUA_CHAVE_NOVA":
        return "[ Configure GROQ_API_KEY no .env com sua chave real ]"
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
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


def scrape_workana():
    leads = []
    try:
        r = requests.get(
            "https://www.workana.com/jobs?category=it-programming&language=pt",
            headers=HEADERS, timeout=15
        )
        soup = BeautifulSoup(r.text, "html.parser")

        # pega todos os links que apontam para projetos específicos
        todos_links = soup.find_all("a", href=True)
        vistos = set()

        for a in todos_links:
            href = a["href"]
            # links de projeto na Workana contêm /job/ ou /trabajo/
            if "/job/" not in href and "/trabajo/" not in href:
                continue
            if not href.startswith("http"):
                href = "https://www.workana.com" + href
            # remove query strings duplicadas
            href_base = href.split("?")[0]
            if href_base in vistos:
                continue
            vistos.add(href_base)

            titulo = a.get_text(strip=True)
            if len(titulo) < 8:
                # tenta pegar o texto do elemento pai
                titulo = a.parent.get_text(strip=True)[:120] if a.parent else titulo

            if len(titulo) < 5:
                continue

            leads.append({
                "plataforma": "Workana",
                "empresa": "Cliente Workana",
                "pedido": titulo,
                "link": href,
            })

    except Exception as e:
        print(f"  [ERRO Workana] {e}")
    return leads


def scrape_99freelas():
    leads = []
    try:
        r = requests.get(
            "https://www.99freelas.com.br/projects?category=informatica-e-tecnologia",
            headers=HEADERS, timeout=15
        )
        soup = BeautifulSoup(r.text, "html.parser")

        todos_links = soup.find_all("a", href=True)
        vistos = set()

        for a in todos_links:
            href = a["href"]
            # links de projeto no 99Freelas contêm /project/ mas NÃO /project/new
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

    except Exception as e:
        print(f"  [ERRO 99Freelas] {e}")
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