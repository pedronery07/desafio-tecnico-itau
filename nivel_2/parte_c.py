"""
Nível 2 — Parte C: execução em lote do agente sobre os 10 clientes mais
sinalizados (Parte A). Salva um registro por cliente (parecer estruturado +
metadados) em outputs/nivel_2/lote/, e um resumo agregado de custo/latência
em outputs/nivel_2/lote_resumo.csv.

Reaproveita o cache em disco do agente (agente.py) — se um cliente já tiver
sido processado com o mesmo cenário, não chama a LLM de novo. Por isso o
resumo separa "tokens/tempo registrados" (inclui valores de chamadas antigas,
reaproveitadas do cache) de "tokens/tempo gastos nesta execução" (só as
chamadas novas, que de fato bateram na API agora).

Rodar com: python nivel_2/parte_c.py
"""

import json
from pathlib import Path

import pandas as pd

from agente import rodar_agente
from regras import processar, regras_disparadas

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs" / "nivel_2"
TOP10_CSV = OUTPUTS_DIR / "top10_sinalizados.csv"
LOTE_DIR = OUTPUTS_DIR / "lote"


def carregar_top10():
    if not TOP10_CSV.exists():
        raise FileNotFoundError(
            f"{TOP10_CSV} não existe — rode `python nivel_2/parte_a.py` primeiro."
        )
    return pd.read_csv(TOP10_CSV)["cliente_id"].tolist()


def main():
    df_clean = processar("dados_nivel_2.json")
    clientes = carregar_top10()

    LOTE_DIR.mkdir(parents=True, exist_ok=True)
    resultados = []

    for cliente_id in clientes:
        regras = regras_disparadas(df_clean, cliente_id)
        print(f"Processando {cliente_id} (regras disparadas: {regras or 'nenhuma'})...")
        resultado = rodar_agente(cliente_id, regras)
        resultados.append(resultado)

        caminho = LOTE_DIR / f"{cliente_id}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    resumo = pd.DataFrame(
        [
            {
                "cliente_id": r["cliente_id"],
                "regras_disparadas": ", ".join(r["regras_disparadas"]) or "nenhuma",
                "nivel_risco_agente": (r["parecer"] or {}).get("nivel_risco"),
                "valido": r["valido"],
                "cache_hit": r["cache_hit"],
                "n_ferramentas_chamadas": len(r["ferramentas_chamadas"]),
                "tempo_resposta_s": r["tempo_resposta_s"],
                "tokens_total": r["tokens_total"],
            }
            for r in resultados
        ]
    )

    print("\n=== Resumo do lote (10 clientes) ===")
    print(resumo.to_string(index=False))

    print(f"\nRespostas válidas: {resumo['valido'].sum()}/{len(resumo)}")
    print(f"Cache hits: {resumo['cache_hit'].sum()}/{len(resumo)}")

    print("\n=== Distribuição de nivel_risco atribuído pelo agente ===")
    print(resumo["nivel_risco_agente"].value_counts())

    # Custo/latência: separa o que foi de fato gasto NESTA execução (chamadas
    # novas) do que só reflete valores históricos reaproveitados do cache.
    novas = resumo[~resumo["cache_hit"]]
    print("\n=== Custo/latência das chamadas NOVAS nesta execução ===")
    if novas.empty:
        print("Nenhuma chamada nova — todos os 10 clientes vieram do cache.")
    else:
        print(f"Qtd. de chamadas novas: {len(novas)}")
        print(f"Tokens totais (novas): {novas['tokens_total'].sum()}")
        print(f"Tokens médios por chamada nova: {novas['tokens_total'].mean():.1f}")
        print(f"Tempo total (novas): {novas['tempo_resposta_s'].sum():.2f}s")
        print(f"Tempo médio por chamada nova: {novas['tempo_resposta_s'].mean():.2f}s")

    print("\n=== Tokens/tempo registrados no total (inclui valores do cache) ===")
    print(f"Tokens totais registrados: {resumo['tokens_total'].sum()}")
    print(f"Tempo total registrado: {resumo['tempo_resposta_s'].sum():.2f}s")

    caminho_resumo = OUTPUTS_DIR / "lote_resumo.csv"
    resumo.to_csv(caminho_resumo, index=False)
    print(f"\nRegistros individuais em {LOTE_DIR}/")
    print(f"Resumo salvo em {caminho_resumo}")


if __name__ == "__main__":
    main()
