"""
Nível 2 — Parte D: confronto entre o nivel_risco que o agente atribuiu
(Parte C, outputs/nivel_2/lote/) e o que as regras determinísticas apontam
para o mesmo cliente.

Critério de correspondência (regra -> nivel_risco esperado):
  - 2 regras disparadas (fracionamento + valor atípico) -> alto
  - 1 regra disparada                                    -> médio
  - 0 regras disparadas                                  -> baixo

Justificativa: tratar qualquer sinalização isolada como "alto" ignoraria que
cada regra, sozinha, é propositalmente simples e gera falso positivo.
Duas regras concordando é um sinal mais forte que uma só — daí a
escala de 3 níveis em vez de um corte binário sinalizado/não-sinalizado.

Rodar com: python nivel_2/confronto.py (depois de python nivel_2/parte_c.py)
"""

import json
import textwrap
from pathlib import Path

import pandas as pd

from regras import processar, regras_disparadas

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs" / "nivel_2"
LOTE_DIR = OUTPUTS_DIR / "lote"


def nivel_risco_regra(regras):
    """Mapeia a lista de regras disparadas para o nivel_risco esperado
    segundo o critério documentado no topo do arquivo."""
    if len(regras) >= 2:
        return "alto"
    if len(regras) == 1:
        return "médio"
    return "baixo"


def carregar_resultados_lote():
    if not LOTE_DIR.exists() or not any(LOTE_DIR.glob("*.json")):
        raise FileNotFoundError(
            f"{LOTE_DIR} vazio — rode `python nivel_2/parte_c.py` primeiro."
        )
    resultados = {}
    for caminho in sorted(LOTE_DIR.glob("*.json")):
        with open(caminho, encoding="utf-8") as f:
            r = json.load(f)
        resultados[r["cliente_id"]] = r
    return resultados


def main():
    df_clean = processar("dados_nivel_2.json")
    resultados_lote = carregar_resultados_lote()

    linhas = []
    for cliente_id, resultado in resultados_lote.items():
        regras = regras_disparadas(df_clean, cliente_id)
        risco_regra = nivel_risco_regra(regras)
        risco_agente = (resultado["parecer"] or {}).get("nivel_risco")
        justificativa = (resultado["parecer"] or {}).get("justificativa", "")

        linhas.append(
            {
                "cliente_id": cliente_id,
                "regras_disparadas": ", ".join(regras) or "nenhuma",
                "nivel_risco_regra": risco_regra,
                "nivel_risco_agente": risco_agente,
                "concorda": risco_regra == risco_agente,
                "justificativa_agente": justificativa,
            }
        )

    confronto = pd.DataFrame(linhas).sort_values("cliente_id").reset_index(drop=True)

    print("=== Confronto: regra determinística vs. agente ===")
    print(
        confronto[
            ["cliente_id", "regras_disparadas", "nivel_risco_regra", "nivel_risco_agente", "concorda"]
        ].to_string(index=False)
    )

    taxa_concordancia = confronto["concorda"].mean()
    print(f"\nTaxa de concordância: {taxa_concordancia:.0%} "
          f"({confronto['concorda'].sum()}/{len(confronto)})")

    print("\n=== Divergências (regra vs. agente) ===")
    divergentes = confronto[~confronto["concorda"]]
    if divergentes.empty:
        print("Nenhuma divergência.")
    else:
        for _, row in divergentes.iterrows():
            print(f"\n{row['cliente_id']} — regras: {row['regras_disparadas']}")
            print(f"  Regra aponta:  {row['nivel_risco_regra']}")
            print(f"  Agente aponta: {row['nivel_risco_agente']}")
            print("  Justificativa do agente:")
            for linha in textwrap.wrap(row["justificativa_agente"], width=76):
                print(f"    {linha}")

    caminho_csv = OUTPUTS_DIR / "confronto.csv"
    confronto.to_csv(caminho_csv, index=False)
    print(f"\nResultado salvo em {caminho_csv}")


if __name__ == "__main__":
    main()
