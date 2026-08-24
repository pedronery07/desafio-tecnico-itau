# Uso de IA

Quais ferramentas de IA foram usadas, para quê, e algum ponto em que a IA levou para o caminho errado e isso foi percebido.

Usei Claude Code (Sonnet - esforço médio) para montar a estrutura inicial de pastas/arquivos do repositório e como par de programação ao longo da implementação, incluindo a construção do `nivel_1/nivel_1.ipynb` (limpeza, regras determinísticas, análise exploratória e chamadas ao LLM). As decisões de modelagem das regras, os prompts do Nível 1/2 e o critério de confronto regra-vs-agente foram definidos e revisados por mim.

Pontos em que a IA errou e eu percebi:
- Ao montar os primeiros gráficos da análise exploratória, ela plotou o histograma de `valor` usando os dados brutos, misturando operações em BRL e USD sem converter — um gráfico com unidades incoerentes. Pedi a correção e ela normalizou os valores para BRL antes de plotar.
- Na mesma seção, a ordem original das células deixava a "análise exploratória" (com gráficos) antes da limpeza dos dados, mas depois de uma célula que já descrevia os problemas como resolvidos. Essa sequência confusa fazia os gráficos mostrarem dados ainda com duplicata e moeda mista. Pedi a reorganização: diagnóstico bruto → limpeza/normalização → análise exploratória (agora sobre dados coerentes).
