import os
from dotenv import load_dotenv

load_dotenv()

# ── IDENTIDADE DA EQUIPE ──────────────────────────────────────
EQUIPE = {
    "nome":      "DualStack",
    "membros":   "João Victor , Carlos , Bruno e Welson",
    "whatsapp":  "(71) 98183-3678",
    "portfolio": "dualstack.netlify.app",
}

# ── TELEGRAM ─────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── OPENAI ────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── GOOGLE SHEETS ─────────────────────────────────────────────
SHEET_NAME = "DualStack Leads"

# ── SERVIÇOS QUE A DUALSTACK OFERECE ─────────────────────────
# Quanto mais específico, melhor a filtragem
SERVICOS = [
    "landing page",
    "automação",
    "automacao",
    "python",
    "bot whatsapp",
    "bot telegram",
    "chatbot",
    "site",
    "website",
    "sistema web",
    "sistema",
    "front-end",
    "frontend",
    "back-end",
    "backend",
    "api",
    "integração",
    "integracao",
    "dashboard",
    "scraping",
    "e-commerce",
    "ecommerce",
    "loja virtual",
    "react",
    "node",
    "desenvolvimento",
    "programação",
    "programacao",
]

# ── KEYWORDS QUE INDICAM UM LEAD ─────────────────────────────
KEYWORDS = [
    "preciso de desenvolvedor",
    "preciso de dev",
    "busco freelancer",
    "busco freela",
    "procuro desenvolvedor",
    "procuro programador",
    "alguém faz site",
    "quem faz site",
    "preciso de automação",
    "preciso de sistema",
    "quem faz landing page",
    "busco programador",
    "contratar freelancer",
    "contratar dev",
    "preciso de bot",
    "quem programa",
    "freelance ti",
    "preciso criar",
    "quero criar um site",
    "quero criar um sistema",
    "indicação de dev",
    "indica desenvolvedor",
]

# ── FILTRO DE QUALIDADE ───────────────────────────────────────
SCORE_MINIMO = 55       # Só notifica leads com score >= 55
INTERVALO_MINUTOS = 30  # Roda a cada 30 minutos
MAX_LEADS_POR_CICLO = 10 # Máximo de notificações por ciclo

# ── LOGS ──────────────────────────────────────────────────────
LOG_FILE = "logs/radar.log"