# Uso de IA

Quais ferramentas de IA foram usadas, para quê, e algum ponto em que a IA levou para o caminho errado e isso foi percebido.

Usei Claude Code (Sonnet - esforço médio) para montar a estrutura inicial de pastas/arquivos do repositório e como par de programação ao longo da implementação.

Pontos em que a IA errou e eu percebi:

## Nível 1
- Ao montar os primeiros gráficos da análise exploratória, ela plotou o histograma de `valor` usando os dados brutos, misturando operações em BRL e USD sem converter — um gráfico com unidades incoerentes. Pedi a correção e ela normalizou os valores para BRL antes de plotar.
- Na comparação de custo entre os dois prompts do Nível 1, ela escreveu a análise olhando só `tokens_total`, o que sugeria que os dois prompts custavam praticamente o mesmo. Percebi que isso escondia o fato de `tokens_prompt` (o contrato de saída mais rígido do prompt v2) e `tokens_resposta` (a resposta mais livre e longa do prompt v1) puxarem em direções opostas e quase se cancelarem no total — pedi para decompor a análise nesses dois componentes em vez de comparar só o total.

## Nível 2
- Na Parte A, usei a IA para refatorar a lógica de limpeza/regras do notebook do Nível 1 em `nivel_2/regras.py` (funções reutilizáveis) e escrever `nivel_2/parte_a.py`, que roda o pipeline na base maior, gera os gráficos de análise exploratória e o ranking dos 10 clientes mais sinalizados.
