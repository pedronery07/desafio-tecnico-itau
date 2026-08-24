"""
Nível 2 — Parte A: regras em escala.

Reaproveita o pipeline de limpeza/regras do Nível 1 (agora em regras.py) sobre
dados_nivel_2.json (~320 operações, 30 clientes), gera a mesma análise
exploratória do Nível 1 (salva em outputs/nivel_2/analise_exploratoria/) e
produz a lista dos 10 clientes mais sinalizados (outputs/nivel_2/top10_sinalizados.csv).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # script, sem display — só salvar em arquivo
import matplotlib.pyplot as plt

from regras import processar, ranking_clientes_sinalizados

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs" / "nivel_2"
EDA_DIR = OUTPUTS_DIR / "analise_exploratoria"

COR_PADRAO = "#2a78d6"
COR_DESTAQUE = "#eb6834"


def gerar_graficos(df_clean, top10):
    EDA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Distribuição de valor_brl — se houver operação em USD na base, plota
    #    dois histogramas lado a lado (com e sem USD) pra comparar visualmente
    #    o quanto a conversão de moeda puxa a cauda da distribuição. Sem
    #    USD, plota só um.
    tem_usd = (df_clean["moeda"] == "USD").any()

    if tem_usd:
        fig, (ax_com, ax_sem) = plt.subplots(1, 2, figsize=(14, 5))

        ax_com.hist(df_clean["valor_brl"], bins=20, color=COR_PADRAO, edgecolor="white")
        ax_com.set_title("Com operações em USD (convertidas)")
        ax_com.set_xlabel("Valor (R$)")
        ax_com.set_ylabel("Nº de operações")
        ax_com.spines[["top", "right"]].set_visible(False)

        valores_sem_usd = df_clean.loc[df_clean["moeda"] != "USD", "valor_brl"]
        ax_sem.hist(valores_sem_usd, bins=20, color=COR_PADRAO, edgecolor="white")
        ax_sem.set_title("Sem operações em USD")
        ax_sem.set_xlabel("Valor (R$)")
        ax_sem.set_ylabel("Nº de operações")
        ax_sem.spines[["top", "right"]].set_visible(False)

        fig.suptitle("Distribuição de 'valor_brl' (pós-limpeza) — Nível 2")
    else:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.hist(df_clean["valor_brl"], bins=20, color=COR_PADRAO, edgecolor="white")
        ax.set_title("Distribuição de 'valor_brl' (pós-limpeza) — Nível 2")
        ax.set_xlabel("Valor (R$)")
        ax.set_ylabel("Nº de operações")
        ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout()
    fig.savefig(EDA_DIR / "distribuicao_valor.png", dpi=120)
    plt.close(fig)

    # 2. Operações por canal
    fig, ax = plt.subplots(figsize=(8, 5))
    canal_counts = df_clean["canal"].value_counts().sort_values()
    ax.barh(canal_counts.index, canal_counts.values, color=COR_PADRAO)
    for i, v in enumerate(canal_counts.values):
        ax.text(v + 1, i, str(v), va="center", fontsize=9)
    ax.set_title("Operações por canal — Nível 2")
    ax.set_xlabel("Nº de operações")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(EDA_DIR / "operacoes_por_canal.png", dpi=120)
    plt.close(fig)

    # 3. Volume total por cliente (30 clientes — figura mais alta pra caber)
    volume_por_cliente = (
        df_clean.groupby("cliente_id")["valor_brl"].sum().sort_values()
    )
    clientes_top10 = set(top10["cliente_id"])
    cores = [
        COR_DESTAQUE if c in clientes_top10 else COR_PADRAO
        for c in volume_por_cliente.index
    ]
    fig, ax = plt.subplots(figsize=(9, 10))
    ax.barh(volume_por_cliente.index, volume_por_cliente.values, color=cores)
    ax.set_title(
        "Volume total por cliente — Nível 2\n(laranja = top 10 mais sinalizados)"
    )
    ax.set_xlabel("Volume (R$)")
    ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(EDA_DIR / "volume_por_cliente.png", dpi=120)
    plt.close(fig)

    # 4. Distribuição do nº de sinalizações por cliente
    n_sinalizacoes_por_cliente = (
        df_clean.assign(
            n_sinalizacoes=df_clean["flag_fracionamento"].astype(int)
            + df_clean["flag_valor_atipico"].astype(int)
        )
        .groupby("cliente_id")["n_sinalizacoes"]
        .sum()
    )
    contagem = n_sinalizacoes_por_cliente.value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    cores_sinalizacao = [COR_DESTAQUE if n > 0 else COR_PADRAO for n in contagem.index]
    ax.bar(contagem.index.astype(str), contagem.values, color=cores_sinalizacao)
    for i, v in enumerate(contagem.values):
        ax.text(i, v + 0.2, str(v), ha="center", fontsize=9)
    ax.set_title("Distribuição do nº de sinalizações por cliente — Nível 2")
    ax.set_xlabel("Nº de sinalizações (Regra 1 + Regra 2)")
    ax.set_ylabel("Nº de clientes")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(EDA_DIR / "sinalizacoes_por_cliente.png", dpi=120)
    plt.close(fig)

    print(f"Gráficos salvos em {EDA_DIR}/")


def main():
    df_clean = processar("dados_nivel_2.json")

    print(f"Linhas pós-limpeza: {len(df_clean)}")
    print(f"Clientes distintos: {df_clean['cliente_id'].nunique()}")
    print(f"Clientes sinalizados pela Regra 1: "
          f"{sorted(df_clean.loc[df_clean['flag_fracionamento'], 'cliente_id'].unique())}")
    print(f"Clientes sinalizados pela Regra 2: "
          f"{sorted(df_clean.loc[df_clean['flag_valor_atipico'], 'cliente_id'].unique())}")

    top10 = ranking_clientes_sinalizados(df_clean, top_n=10)
    print("\nTop 10 clientes mais sinalizados:")
    print(top10.to_string(index=False))

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    caminho_csv = OUTPUTS_DIR / "top10_sinalizados.csv"
    top10.to_csv(caminho_csv, index=False)
    print(f"\nTop 10 salvo em {caminho_csv}")

    gerar_graficos(df_clean, top10)


if __name__ == "__main__":
    main()
