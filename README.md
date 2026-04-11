# DualStack Radar

Ferramenta de captação automática de leads para a equipe DualStack. Varre plataformas de freelancer e redes sociais em busca de projetos de TI e gera propostas comerciais personalizadas via IA (Groq).

---

## Fontes rastreadas

| Plataforma | Método |
|---|---|
| **Workana** | Playwright (headless) — projetos de TI/programação |
| **99Freelas** | HTTP + BeautifulSoup — busca por dezenas de queries |
| **GitHub** | API pública — issues com label `freelance` |

---

## Pré-requisitos

```bash
pip install -r requirements.txt
playwright install chromium
```

---

## Configuração (.env)

Crie o arquivo `.env` na raiz do projeto:

```env
# Groq — geração de propostas (obrigatório)
GROQ_API_KEY=gsk_...
GROQ_API_KEY_2=gsk_...   # opcional, faz rodízio para evitar rate limit

```

---

## Como usar

### Modo terminal (CLI)

```bash
python core/proposal_gen.py
```

Varre todas as fontes, imprime os leads e propostas no terminal e salva em `leads_encontrados.txt`.

### Modo dashboard (web)

```bash
python app.py
```

Abre automaticamente `http://localhost:5000` com interface visual para disparar scans, ver leads e propostas em tempo real.

---

## Saída

- **Terminal:** leads formatados com proposta gerada por IA
- **`leads_encontrados.txt`:** histórico persistente de todos os leads e propostas
- **Dashboard web:** painel com botão de scan, log ao vivo e cards de leads

---

## Estrutura

```
dualstack-radar/
├── app.py                  # Servidor Flask (dashboard web)
├── core/
│   └── proposal_gen.py     # CLI + scrapers + geração de propostas
├── scrapers/               # Scrapers auxiliares (GetNinjas, etc.)
├── dashboard.html          # Frontend do dashboard
├── leads_encontrados.txt   # Histórico de leads
└── .env                    # Credenciais (não versionar)
```
