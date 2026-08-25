"""
Pipeline de limpeza e regras determinísticas — mesma lógica do Nível 1
(nivel_1/nivel_1.ipynb), extraída em funções reutilizáveis para rodar sobre
qualquer um dos arquivos de dados (nivel_1 ou nivel_2).

Fonte única de verdade da limpeza/regras: nivel_2/parte_a.py, agente.py e
confronto.py importam daqui em vez de duplicar a lógica.
"""

import json
from pathlib import Path

import pandas as pd

DADOS_DIR = Path(__file__).resolve().parent.parent / "dados"

# Limiares da Regra 1 — Fracionamento
LIMITE_SOMA_FRACIONAMENTO = 50_000
LIMITE_OPERACAO_ISOLADA = 20_000
MIN_OPERACOES_FRACIONAMENTO = 3

# Limiares da Regra 2 — Valor atípico
MULTIPLICADOR_ATIPICO = 5
MIN_OPERACOES_ATIPICO = 4


def carregar_dados(nome_arquivo):
    """Carrega um dos arquivos de dados/. Retorna (df, taxa_cambio_usd_brl)."""
    caminho = DADOS_DIR / nome_arquivo
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    df = pd.DataFrame(dados["operacoes"])
    return df, dados["taxa_cambio_usd_brl"]


def limpar_e_normalizar(df, taxa_cambio_usd_brl):
    """Remove duplicata exata por id, marca data ausente e normaliza para BRL.

    Mesmos três problemas de qualidade tratados no Nível 1:
    1. Registro duplicado -> drop_duplicates(subset=["id"])
    2. Data ausente -> mantida nas agregações, marcada em `data_ausente`
       (fica de fora do agrupamento por data da Regra 1)
    3. Moeda mista -> convertida para BRL em `valor_brl`, usada em tudo
       daqui pra frente em vez do `valor` bruto.
    """
    df_clean = df.drop_duplicates(subset=["id"]).copy()
    df_clean["data_ausente"] = df_clean["data"].isna()
    df_clean["valor_brl"] = df_clean.apply(
        lambda r: r["valor"] * taxa_cambio_usd_brl if r["moeda"] == "USD" else r["valor"],
        axis=1,
    )
    return df_clean


def aplicar_regra_fracionamento(df_clean):
    """Regra 1: cliente com 3+ operações na mesma data somando > R$ 50.000,
    sem nenhuma operação isolada >= R$ 20.000. Adiciona `flag_fracionamento`.
    """
    com_data = df_clean[~df_clean["data_ausente"]]

    por_dia = (
        com_data.groupby(["cliente_id", "data"])["valor_brl"]
        .agg(qtd_operacoes="count", soma_valor="sum", maior_operacao="max")
        .reset_index()
    )

    candidatos = por_dia[
        (por_dia["qtd_operacoes"] >= MIN_OPERACOES_FRACIONAMENTO)
        & (por_dia["soma_valor"] > LIMITE_SOMA_FRACIONAMENTO)
        & (por_dia["maior_operacao"] < LIMITE_OPERACAO_ISOLADA)
    ]

    chaves = set(zip(candidatos["cliente_id"], candidatos["data"]))
    df_clean = df_clean.copy()
    df_clean["flag_fracionamento"] = df_clean.apply(
        lambda r: (r["cliente_id"], r["data"]) in chaves, axis=1
    )
    return df_clean, candidatos


def aplicar_regra_valor_atipico(df_clean):
    """Regra 2: operação com valor_brl > 5x a mediana do cliente, aplicada só
    a clientes com 4+ operações. Adiciona `flag_valor_atipico`.
    """
    qtd_operacoes_cliente = df_clean.groupby("cliente_id")["valor_brl"].transform("count")
    mediana_cliente = df_clean.groupby("cliente_id")["valor_brl"].transform("median")

    df_clean = df_clean.copy()
    df_clean["flag_valor_atipico"] = (qtd_operacoes_cliente >= MIN_OPERACOES_ATIPICO) & (
        df_clean["valor_brl"] > MULTIPLICADOR_ATIPICO * mediana_cliente
    )
    return df_clean


def processar(nome_arquivo):
    """Pipeline completo: carrega, limpa/normaliza e aplica as duas regras.
    Retorna o df_clean com as colunas valor_brl, flag_fracionamento e
    flag_valor_atipico.
    """
    df, taxa_cambio_usd_brl = carregar_dados(nome_arquivo)
    df_clean = limpar_e_normalizar(df, taxa_cambio_usd_brl)
    df_clean, _ = aplicar_regra_fracionamento(df_clean)
    df_clean = aplicar_regra_valor_atipico(df_clean)
    return df_clean


def ranking_clientes_sinalizados(df_clean, top_n=10):
    """Lista os clientes mais sinalizados: nº de sinalizações (fracionamento +
    valor atípico, por operação flagada) ordenado desc, com o volume total
    como critério de desempate.
    """
    sinalizacoes = (
        df_clean.assign(
            n_sinalizacoes=df_clean["flag_fracionamento"].astype(int)
            + df_clean["flag_valor_atipico"].astype(int)
        )
        .groupby("cliente_id")
        .agg(
            n_sinalizacoes=("n_sinalizacoes", "sum"),
            volume_total_brl=("valor_brl", "sum"),
            qtd_operacoes=("id", "count"),
        )
        .reset_index()
        .sort_values(
            by=["n_sinalizacoes", "volume_total_brl"], ascending=[False, False]
        )
        .reset_index(drop=True)
    )
    sinalizacoes["volume_total_brl"] = sinalizacoes["volume_total_brl"].round(2)
    return sinalizacoes.head(top_n)


def detalhe_regras(df_clean, cliente_id):
    """Evidência específica por trás de cada regra disparada para um cliente
    — não só o booleano `flag_*`, mas a data/soma exata do fracionamento e
    qual(is) operação(ões) é(são) o valor atípico e por qual múltiplo da
    mediana. Usado por tools.py para dar ao agente (function calling) a
    mesma evidência que a regra determinística usou — sem isso, o agente não
    tem como saber qual data investigar em `operacoes_do_dia`, nem o quanto
    uma operação atípica realmente destoa do resto do histórico do cliente.
    """
    ops_cliente = df_clean[df_clean["cliente_id"] == cliente_id]

    dias_fracionamento = (
        ops_cliente[ops_cliente["flag_fracionamento"]]
        .groupby("data")["valor_brl"]
        .agg(qtd_operacoes="count", soma_valor_brl="sum")
        .reset_index()
    )

    mediana_cliente = ops_cliente["valor_brl"].median()
    operacoes_atipicas = ops_cliente[ops_cliente["flag_valor_atipico"]][
        ["id", "data", "valor_brl"]
    ].copy()
    if not operacoes_atipicas.empty:
        operacoes_atipicas["multiplo_da_mediana"] = (
            operacoes_atipicas["valor_brl"] / mediana_cliente
        ).round(1)

    return {
        "dias_fracionamento": [
            {
                "data": row["data"],
                "qtd_operacoes": int(row["qtd_operacoes"]),
                "soma_valor_brl": round(float(row["soma_valor_brl"]), 2),
            }
            for _, row in dias_fracionamento.iterrows()
        ],
        "operacoes_atipicas": [
            {
                "id": row["id"],
                "data": row["data"],
                "valor_brl": round(float(row["valor_brl"]), 2),
                "multiplo_da_mediana": float(row["multiplo_da_mediana"]),
            }
            for _, row in operacoes_atipicas.iterrows()
        ],
    }


def regras_disparadas(df_clean, cliente_id):
    """Lista os nomes das regras determinísticas que dispararam para um
    cliente (['fracionamento', 'valor_atipico'], subconjunto, ou vazia).
    Reaproveitado pelo agente (contexto inicial) e pelo confronto.py
    (Parte D).
    """
    ops = df_clean[df_clean["cliente_id"] == cliente_id]
    disparadas = []
    if ops["flag_fracionamento"].any():
        disparadas.append("fracionamento")
    if ops["flag_valor_atipico"].any():
        disparadas.append("valor_atipico")
    return disparadas
