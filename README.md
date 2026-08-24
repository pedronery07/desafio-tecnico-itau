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
