"""
Ferramentas que consultam a base do Nível 2 (dados/dados_nivel_2.json).

Usa o pipeline de regras.py (limpeza + normalização + as duas regras
determinísticas) como fonte dos dados — os tipos e docstrings de cada função
seguem o padrão que o SDK do Gemini (google-genai) usa para gerar o schema de
function calling automaticamente (ver agente.py).
"""

from regras import detalhe_regras, processar

_df = processar("dados_nivel_2.json")


def historico_cliente(cliente_id: str) -> dict:
    """Resumo agregado de todas as operações de um cliente: quantidade de
    operações, volume total em BRL, período coberto, canais e tipos de
    operação usados, contrapartes distintas, e se/como o cliente foi
    sinalizado pelas regras determinísticas — incluindo, quando aplicável, a
    data exata do fracionamento (com soma e quantidade de operações daquele
    dia) e qual(is) operação(ões) é(são) o valor atípico, com o múltiplo da
    mediana do cliente que ela representa.

    Args:
        cliente_id: identificador do cliente, no formato "CLI-014".
    """
    ops = _df[_df["cliente_id"] == cliente_id]
    if ops.empty:
        return {"erro": f"cliente {cliente_id} nao encontrado na base"}

    ops_com_data = ops[~ops["data_ausente"]]
    detalhe = detalhe_regras(_df, cliente_id)
    return {
        "cliente_id": cliente_id,
        "quantidade_operacoes": int(len(ops)),
        "volume_total_brl": round(float(ops["valor_brl"].sum()), 2),
        "primeira_data": ops_com_data["data"].min() if not ops_com_data.empty else None,
        "ultima_data": ops_com_data["data"].max() if not ops_com_data.empty else None,
        "canais_utilizados": ops["canal"].value_counts().to_dict(),
        "tipos_operacao": ops["tipo"].value_counts().to_dict(),
        "contrapartes_distintas": sorted(ops["contraparte"].unique().tolist()),
        "sinalizado_regra_fracionamento": bool(ops["flag_fracionamento"].any()),
        "dias_fracionamento": detalhe["dias_fracionamento"],
        "sinalizado_regra_valor_atipico": bool(ops["flag_valor_atipico"].any()),
        "operacoes_atipicas": detalhe["operacoes_atipicas"],
    }


def operacoes_do_dia(cliente_id: str, data: str) -> dict:
    """Recorte detalhado das operações de um cliente em uma data específica
    — útil para investigar de perto um dia sinalizado pela regra de
    fracionamento (ver o valor e o canal de cada operação individual daquele
    dia).

    Args:
        cliente_id: identificador do cliente, no formato "CLI-014".
        data: data no formato "YYYY-MM-DD", ex. "2026-05-26".
    """
    ops = _df[(_df["cliente_id"] == cliente_id) & (_df["data"] == data)]
    if ops.empty:
        return {
            "cliente_id": cliente_id,
            "data": data,
            "quantidade": 0,
            "soma_valor_brl": 0.0,
            "operacoes": [],
        }

    return {
        "cliente_id": cliente_id,
        "data": data,
        "quantidade": int(len(ops)),
        "soma_valor_brl": round(float(ops["valor_brl"].sum()), 2),
        "operacoes": ops[["id", "valor_brl", "canal", "tipo", "contraparte"]].to_dict(
            orient="records"
        ),
    }


def perfil_canal(cliente_id: str) -> dict:
    """Distribuição de uso de canais de um cliente: quantidade e percentual
    de operações por canal (pix, ted, boleto, cartao, especie) — útil para
    avaliar se o cliente concentra operações em um canal específico ou
    pulveriza entre vários.

    Args:
        cliente_id: identificador do cliente, no formato "CLI-014".
    """
    ops = _df[_df["cliente_id"] == cliente_id]
    if ops.empty:
        return {"erro": f"cliente {cliente_id} nao encontrado na base"}

    contagem = ops["canal"].value_counts()
    total = int(contagem.sum())
    return {
        "cliente_id": cliente_id,
        "distribuicao": {
            canal: {"quantidade": int(qtd), "percentual": round(100 * qtd / total, 1)}
            for canal, qtd in contagem.items()
        },
    }
