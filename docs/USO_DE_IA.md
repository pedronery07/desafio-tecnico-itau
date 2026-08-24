# Uso de IA

Quais ferramentas de IA foram usadas, para quê, e algum ponto em que a IA levou para o caminho errado e isso foi percebido.

Usei Claude Code (Sonnet - esforço médio) para montar a estrutura inicial de pastas/arquivos do repositório e como par de programação ao longo da implementação.

Pontos em que a IA errou e eu percebi:
- Ao montar os primeiros gráficos da análise exploratória, ela plotou o histograma de `valor` usando os dados brutos, misturando operações em BRL e USD sem converter — um gráfico com unidades incoerentes. Pedi a correção e ela normalizou os valores para BRL antes de plotar.
- Na mesma seção, a ordem original das células deixava a "análise exploratória" (com gráficos) antes da limpeza dos dados, mas depois de uma célula que já descrevia os problemas como resolvidos. Essa sequência confusa fazia os gráficos mostrarem dados ainda com duplicata e moeda mista. Pedi a reorganização: diagnóstico bruto → limpeza/normalização → análise exploratória (agora sobre dados coerentes).
- Na comparação de custo entre os dois prompts do Nível 1, ela escreveu a análise olhando só `tokens_total`, o que sugeria que os dois prompts custavam praticamente o mesmo. Percebi que isso escondia o fato de `tokens_prompt` (o contrato de saída mais rígido do prompt v2) e `tokens_resposta` (a resposta mais livre e longa do prompt v1) puxarem em direções opostas e quase se cancelarem no total — pedi para decompor a análise nesses dois componentes em vez de comparar só o total.
