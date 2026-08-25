# Desafio Técnico — Estágio em Engenharia de Inteligência Artificial

Triagem de prevenção à lavagem de dinheiro combinando regras determinísticas
(pandas) com interpretação via LLM. De um notebook exploratório (Nível 1) a
um agente com ferramentas (Nível 2) e um fluxo multiagente com Triador,
Investigador e Redator (Nível 3, Trilha A).

## Estrutura

```
.
├── ENTREGA.yaml           # autodeclaração do que foi feito
├── requirements.txt
├── .env.example           # nomes das variáveis de ambiente (sem valores)
├── dados/
│   ├── dados_nivel_1.json
│   └── dados_nivel_2.json
├── nivel_1/
│   └── nivel_1.ipynb      # limpeza, regras, parecer com LLM
├── nivel_2/
│   ├── regras.py          # limpeza + Regras 1/2 do Nível 1, reaproveitável
│   ├── parte_a.py         # regras em escala: top 10 sinalizados + EDA
│   ├── tools.py           # ferramentas que consultam a base
│   ├── agente.py          # agente que decide quais ferramentas chamar
│   ├── parte_c.py         # execução em lote sobre os 10 mais sinalizados
│   └── confronto.py       # regra determinística x nivel_risco do agente
├── nivel_3/                # Trilha A: fluxo multiagente
│   └── multiagente.py      # Triador → Investigador → Redator
├── outputs/                # resultados salvos das execuções
└── docs/
    ├── DECISOES.md         # trade-offs, limitações, o que faria com mais tempo
    ├── USO_DE_IA.md        # como IA foi usada na construção deste repositório
    └── ARQUITETURA.md      # diagrama Mermaid do fluxo multiagente (Nível 3)
```

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # opcional
pip install -r requirements.txt
cp .env.example .env   # preencher com uma chave de camada gratuita
```

**Nível 1** — notebook com tudo já executado, mas dá pra rodar de novo:

```bash
jupyter notebook nivel_1/nivel_1.ipynb
```

**Nível 2** — cada parte é um script independente, na ordem:

```bash
python nivel_2/parte_a.py    # regras em escala: top 10 sinalizados + gráficos em outputs/nivel_2/
python nivel_2/parte_c.py    # roda o agente nos 10 clientes (usa cache; chama a LLM só p/ casos novos)
python nivel_2/confronto.py  # compara regra determinística x nivel_risco do agente
```

**Nível 3** (Trilha A — fluxo multiagente):

```bash
python nivel_3/multiagente.py
```

## Status

Ver [`ENTREGA.yaml`](ENTREGA.yaml) para o que está completo, parcial ou não feito, e [`docs/DECISOES.md`](docs/DECISOES.md) para o raciocínio por trás das escolhas.

## Versionamento

Os marcos do desenvolvimento estão marcados com tags `vX.Y-descricao`, uma por
etapa concluída:

| Tag | Marco |
|---|---|
| `v0.1-estrutura` | Estrutura de pastas/arquivos conforme a seção 3 do enunciado |
| `v0.2-nivel1-parte-a` | Nível 1 Parte A: limpeza, Regras 1/2, validação |
| `v0.3-nivel1-parte-b` | Nível 1 Parte B: parecer via LLM, saída validada, comparação de prompts |
| `v0.4-nivel1-parte-a-eda` | Nível 1 Parte A revisada: reordena limpeza → EDA(análise exploratória de dados), adiciona análise exploratória e gráficos |
| `v0.5-nivel1-revisao` | Nível 1 revisado: gráfico de volume por cliente, print formatado do parecer, análise de tokens (prompt vs. resposta) refinada |
| `v0.6-nivel1-completo` | Nível 1 completo: notebook, `ENTREGA.yaml`, `DECISOES.md` e `USO_DE_IA.md` preenchidos |
| `v0.7-nivel2-parte-a` | Nível 2 Parte A: `regras.py` reutilizável, `parte_a.py`, top 10 sinalizados e EDA em `outputs/nivel_2/` |
| `v0.8-nivel2-parte-b` | Nível 2 Parte B: `tools.py` (3 ferramentas), `agente.py` (function calling, decide quais ferramentas chamar) e cache em disco por cliente |
| `v0.9-nivel2-parte-c` | Nível 2 Parte C: execução em lote sobre os 10 clientes, retry com backoff para rate limit, resumo de custo/latência com pandas |
| `v0.10-nivel2-parte-c-fix` | Nível 2 Parte C corrigida: `historico_cliente` passa a expor a evidência exata das regras (data do fracionamento, múltiplo da mediana), retry ampliado para 429+503 |
| `v0.11-nivel2-parte-d` | Nível 2 Parte D: `confronto.py`, critério de correspondência regra→risco, 80% de concordância e análise das divergências em `docs/DECISOES.md` |
| `v0.12-nivel3-trilha-a` | Nível 3 Trilha A: fluxo multiagente (Triador/Investigador/Redator), estado compartilhado e condição de parada em `multiagente.py`, diagrama Mermaid em `docs/ARQUITETURA.md` |
| `v1.0-entrega-final` | Revisão final: README com seção "Como rodar" e estrutura atualizada, typos corrigidos em `DECISOES.md`, `horas_dedicadas` preenchida no `ENTREGA.yaml` |

`git tag -n` lista as tags com descrição; `git log --oneline --decorate` mostra
onde cada uma cai no histórico.
