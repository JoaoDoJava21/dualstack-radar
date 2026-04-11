from config.settings import SERVICOS, KEYWORDS, SCORE_MINIMO


def pontuar_lead(texto: str) -> tuple[int, list[str]]:
    """
    Pontua um lead de 0 a 100 com base no texto do pedido.
    Retorna (score, lista de matches encontrados).
    """
    t = texto.lower()
    score = 0
    matches = []

    # Serviços que a DualStack oferece (+8 cada)
    for s in SERVICOS:
        if s in t:
            score += 8
            if s not in matches:
                matches.append(s)

    # Keywords de intenção de contratar (+5 cada)
    for k in KEYWORDS:
        if k in t:
            score += 5

    # Bônus: orçamento mencionado (+10)
    if any(w in t for w in ["r$", "reais", "orçamento", "orcamento", "pagar", "budget", "valor"]):
        score += 10

    # Bônus: urgência (+7)
    if any(w in t for w in ["urgente", "urgência", "rápido", "rapido", "hoje", "agora", "asap", "prazo"]):
        score += 7

    # Bônus: contato disponível (+5)
    if any(w in t for w in ["whatsapp", "zap", "email", "contato", "ligar"]):
        score += 5

    return min(score, 100), matches


def lead_valido(texto: str) -> bool:
    score, _ = pontuar_lead(texto)
    return score >= SCORE_MINIMO


def resumo_score(texto: str) -> str:
    score, matches = pontuar_lead(texto)
    status = "APROVADO" if score >= SCORE_MINIMO else "DESCARTADO"
    return f"[{status}] Score: {score}/100 | Matches: {', '.join(matches) or 'nenhum'}"