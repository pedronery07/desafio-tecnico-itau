# Desafio Técnico — Estágio em Engenharia de Inteligência Artificial

Triagem de prevenção à lavagem de dinheiro combinando regras determinísticas.

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
│   ├── tools.py           # ferramentas que consultam a base
│   ├── agente.py          # agente que decide quais ferramentas chamar
│   └── confronto.py       # regra determinística x nivel_risco do agente
├── nivel_3/                # trilha opcional (A/B/C)
├── outputs/                # resultados salvos das execuções
└── docs/
    ├── DECISOES.md         # trade-offs, limitações, o que faria com mais tempo
    └── USO_DE_IA.md        # como IA foi usada na construção deste repositório
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

`git tag -n` lista as tags com descrição; `git log --oneline --decorate` mostra
onde cada uma cai no histórico.
