"""
main.py — DualStack Radar
Passo 1: rastre as 3 plataformas e exibe os leads no terminal
"""

from scrapers.workana   import scrape_workana
from scrapers.freelas99 import scrape_99freelas
from scrapers.getninjas import scrape_getninjas
from core.scorer        import pontuar_lead, lead_valido
from config.settings    import SCORE_MINIMO


def rodar_radar():
    print("🚀 DualStack Radar — Passo 1")
    print("=" * 50)

    # 1. Coleta todos os leads das 3 plataformas
    todos = []
    todos += scrape_workana()
    todos += scrape_99freelas()
    todos += scrape_getninjas()

    print(f"\n📦 Total coletado: {len(todos)} leads\n")

    # 2. Filtra e pontua cada lead
    aprovados = []
    for lead in todos:
        score, matches = pontuar_lead(lead["pedido"])
        if score >= SCORE_MINIMO:
            lead["score"]   = score
            lead["matches"] = matches
            aprovados.append(lead)

    print(f"✅ Leads aprovados (score >= {SCORE_MINIMO}): {len(aprovados)}")
    print("=" * 50)

    # 3. Exibe os leads aprovados no terminal
    for i, lead in enumerate(aprovados, 1):
        print(f"\n[Lead {i}] Score: {lead['score']}/100")
        print(f"  Plataforma : {lead['plataforma']}")
        print(f"  Pedido     : {lead['pedido'][:120]}...")
        print(f"  Orçamento  : {lead['orcamento']}")
        print(f"  Link       : {lead['link']}")
        print(f"  Matches    : {', '.join(lead['matches'])}")

    if not aprovados:
        print("\n⚠️  Nenhum lead aprovado nesse ciclo.")
        print("   Dica: reduza SCORE_MINIMO em config/settings.py para testar.")

    return aprovados


if __name__ == "__main__":
    rodar_radar()