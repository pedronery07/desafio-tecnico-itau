# Decisões

> - **Trade-offs**: o que foi escolhido, contra o que, e por quê.
> - **Limitações**: o que a solução não resolve e onde quebraria com dados reais.
> - **O que faria com mais tempo**: para cada item não implementado, como
>   atacaria — arquitetura, ferramenta, e como validaria que funcionou.

## Trade-offs

### Nível 1

- **Operação com data ausente (`OP-0017`).** Em vez de descartar a linha,
  mantive-a nas agregações que não dependem de data (volume total, contagem
  por canal, Regra 2) e a excluí só do agrupamento por data da Regra 1. Contra:
  descartar a linha inteira, que perderia volume real do cliente sem
  necessidade.
- **Duplicata exata (`OP-0007`).** Removida por `drop_duplicates(subset=["id"])`,
  uma checagem simples porque a duplicata era exata (todos os campos iguais).
- **Escolha e troca de modelo de LLM.** O `gemini-2.0-flash` sugerido
  inicialmente não estava mais disponível para a chave gerada; testei e troquei
  para `gemini-3.5-flash-lite`, migrando  também do SDK `google-generativeai` (deprecado) para `google-genai`.
- **Duas versões de prompt (v1 enxuto vs. v2 com contrato de saída rígido).**
  Trade-off entre custo fixo de prompt (maior em v2, que carrega mais
  instrução) contra risco de resposta malformada/verbosa fora do contrato
  (maior em v1). O padrão v2 seria mais interessante como base mais, por ser mais previsível e barato por resposta.
- **Regra 1 exige soma numérica, não só contagem de operações no dia.** Dois
  clientes (`CLI-A-1` e `CLI-A-3`) têm o mesmo padrão de 3 operações no mesmo
  dia, mas só um ultrapassa o limite de soma (R\$ 50.000). Contagem sozinha
  teria gerado falso positivo para `CLI-A-3`.

### Nível 2

- **Extrair a limpeza/regras do Nível 1 para `nivel_2/regras.py`.** No
  Nível 1 essa lógica ficou inline no notebook, presa a nomes de variável
  fixos e ao arquivo `dados_nivel_1.json`. Refatorei
  em funções (`carregar_dados`, `limpar_e_normalizar`,
  `aplicar_regra_fracionamento`, `aplicar_regra_valor_atipico`, `processar`). 
  Contra: manter a lógica duplicada em cada arquivo.
- **`n_sinalizacoes` conta por operação flagada, não por regra binária.** Um
  cliente com 4 operações flagadas pela Regra 1 conta 4, não 1.
- **Gráfico de distribuição condicional a existir USD na base.** `parte_a.py`
  só desenha o histograma comparativo (com/sem USD) se houver ao menos uma
  operação em USD; caso contrário, plota um único histograma. Decisão para o
  script continuar funcionando corretamente mesmo numa base sem moeda mista.
- **Cache em disco do resultado completo por cliente, não cache de contexto
  do provedor.** `agente.py` salva o parecer + tokens + latência +
  ferramentas chamadas em `outputs/nivel_2/cache/`, chaveado por
  `cliente_id + regras_disparadas + modelo + versão do prompt`. Se o mesmo
  cenário já foi processado, reaproveita em vez de chamar a LLM de novo.
- **Retry com backoff para o erro 429 (rate limit) em vez de deixar o lote
  quebrar.** Na primeira execução da Parte C em lote, o 4º cliente estourou o
  limite de 15 req/min do `gemini-3.5-flash-lite` e o script parou no meio. Adicionei retry em `agente.py` que lê o `retryDelay` sugerido pelo próprio erro da API e tenta de novo, em vez de simplesmente espaçar as chamadas com um `sleep` fixo — mais preciso e não desperdiça
  tempo esperando mais do que o necessário. Mais tarde também apareceu erro
  503 (servidor sobrecarregado) e o retry foi ampliado.
- **`historico_cliente` expõe a evidência exata de cada regra, não só o
  booleano.**: o agente não tinha como
  saber *qual* data investigar em `operacoes_do_dia` para fracionamento, nem
  *quanto* uma operação atípica destoava da mediana — só via
  `sinalizado_regra_*: true/false`. Adicionei `dias_fracionamento` (data,
  quantidade, soma) e `operacoes_atipicas` (id, valor, múltiplo da mediana) a
  `historico_cliente`, calculados por uma nova função `regras.detalhe_regras`.
  Contra: manter o agente "cego" e aceitar que ele investigasse às cegas.

### Nível 3

- **Trilha A (multiagente), escolhida por interesse pessoal.** Tive contato
  mais recente com esse tipo de arquitetura e queria praticar.
- **Amostra de 4 clientes em vez de rodar nos 10 da Parte A.** Nível 3 é
  bônus/opcional no enunciado — não exige lote completo. Foram escolhidos 4 casos
  para cobrir os dois caminhos do fluxo: fracionamento borderline (`CLI-003`), valor atípico forte (`CLI-023`), valor atípico moderado com agravante de mesmo dia (`CLI-028`) e valor atípico isolado e fraco (`CLI-008`, fora do top10 — o candidato mais forte a ser arquivado
  pelo Triador). Contra: rodar nos 10 clientes originais, que gastaria mais
  tempo/tokens sem agregar muito à demonstração da arquitetura em si.

## Limitações

### Nível 1

- **Amostra pequena (20 operações, 6 clientes).** Não dá para validar
  estatisticamente os limiares das regras (R\$ 50.000, R\$ 20.000, 5x mediana)
  nem a robustez delas fora dos poucos casos observados.
- **Regra 1 só detecta fracionamento no mesmo dia.** Um padrão de estruturação
  distribuído em vários dias (comum em cenários reais) não é capturado.
- **Regra 2 depende da mediana do próprio histórico do cliente.** Com o
  mínimo de 4 operações exigido, um cliente com poucas operações e perfil de
  valores muito variável pode ter uma mediana pouco representativa,
  distorcendo o que conta como "atípico" para ele.
- **Parecer do LLM testado numa única chamada por prompt.** A variância de
  tokens e latência observada entre execuções (ex.: uma chamada levou
  ~38s contra ~2s de outras) mostra que uma amostra única não é suficiente
  para afirmar com confiança qual prompt é mais rápido ou mais barato.
- **Taxa de câmbio fixa do arquivo.** Não reflete variação cambial ao longo do
  tempo.

### Nível 2

- **`n_sinalizacoes` pode contar a mesma operação duas vezes.** Uma operação
  flagada simultaneamente pela Regra 1 e pela Regra 2 soma 2 no contador do
  cliente — não ocorreu na base atual, mas é um caso possível que pesaria
  mais que dois clientes com uma operação cada flagada por uma regra
  diferente. O critério é discutível e está documentado aqui por transparência.
- **Ranking não normaliza por quantidade de operações do cliente.** Um
  cliente com mais operações tem naturalmente mais chances de ter alguma
  flagada.
- **O agente consome bem mais token que a chamada única do Nível 1** No Nível 1, uma única chamada com contexto pré-empacotado ficou em ~950–1050 tokens. No agente, cada rodada do loop de function calling reenvia a conversa inteira acumulada (prompt inicial + declaração das 3 ferramentas + toda chamada/resposta anterior). No teste com `CLI-029` (2 rodadas: `historico_cliente` → `operacoes_do_dia` → resposta final), o total chegou a 3629 tokens; com `CLI-014` (1 rodada só), 2053. Quanto mais ferramentas o agente decide chamar, mais caro fica. O cache em disco (ver Trade-offs) evita pagar esse custo de novo ao reprocessar o mesmo cliente, mas não reduz o custo de uma chamada nova.
- **Ferramentas subinformadas geram divergência artificial, não julgamento
  melhor.** Na primeira rodada da Parte C, `historico_cliente` só expunha um
  booleano (`sinalizado_regra_*`) — sem a data exata do fracionamento nem o
  quanto uma operação atípica destoava da mediana. Resultado: taxa de
  concordância de só 30% com o critério da Parte D, e investigação incorreta
  do `CLI-003` (o agente chamou `operacoes_do_dia` na *primeira* data do
  histórico do cliente, não na data que de fato disparou a regra — porque
  não tinha essa informação). Corrigido expondo a evidência exata (ver
  Trade-offs); depois da correção, a concordância subiu para 80% e as
  divergências restantes passaram a ser bem fundamentadas, não sintomas de
  falta de dado. Moral: um agente só é tão bom quanto a informação que as
  ferramentas dão a ele — "o agente discordou" não significa "o agente tem
  razão" se ele estava trabalhando com informação incompleta ou errada.

#### Dicussão sobre a Parte D

- Critério de correspondência usado (`nivel_2/confronto.py`): 2 regras
disparadas → `alto`, 1 regra → `médio`, 0 regras → `baixo` (justificado no
próprio arquivo — tratar qualquer sinalização isolada como "alto" ignoraria
que cada regra, sozinha, é propositalmente simples).

- Depois de corrigir a evidência exposta ao agente (ver Trade-offs/Limitações
acima), a taxa de concordância ficou em **80% (8/10)**. As 2 divergências que
sobraram são bem fundamentadas:

- **`CLI-023` (regra: médio, agente: alto) — acho que o agente está certo.**
  A regra só enxerga "tem valor atípico: sim/não" — mas as duas operações
  atípicas desse cliente estão a 12,9x e 20,2x da mediana, muito além do
  limiar mínimo de 5x. Nosso critério de correspondência trata qualquer
  cliente com 1 regra disparada como "médio", sem distinguir um caso
  borderline (5,1x a mediana) de um caso extremo (20x). Isso é uma
  limitação do *critério de correspondência* que escolhi para a Parte D —
  ele não captura magnitude, só a contagem de regras disparadas.
- **`CLI-003` (regra: médio, agente: baixo) — acho que a regra está mais
  perto de certa aqui, discordo parcialmente do agente.** A Regra 1
  literalmente define estruturação/fracionamento: várias operações no mesmo
  dia, somando acima de um limite, nenhuma isolada grande o bastante para
  disparar reporte individual — e é exatamente esse padrão que existe no
  histórico do `CLI-003` (4 operações em 02/05/2026, R\$ 50.846,72, nenhuma
  ≥ R\$ 20.000). A justificativa do agente para rebaixar ("canais e
  contrapartes distintos, sem evidência de evasão de limites") é uma
  interpretação razoável, mas dispersão de canal/contraparte não é
  necessariamente exculpatória em lavagem de dinheiro — pode ser tanto atividade legítima
  quanto uma forma de dificultar a detecção. Faria sentido manter esse cliente pelo
  menos em "médio" para revisão humana, em vez de baixar para "baixo".

**Conclusão prática:** Em nenhum dos dois casos o agente estava simplesmente "errado"
— mas também não é verdade que o agente sempre acerta mais que a regra. O
valor real do agente aqui foi trazer a magnitude e o contexto (canais,
contrapartes) que a regra binária não expõe — mesmo quando a conclusão final
dele não prevalece.

### Nível 3

- **Triador decide com base num resumo, não nos dados brutos.** Ele vê
  `contexto_regras`, mas não tem ferramentas — se o resumo omitir algo
  relevante (ex.: um padrão que só aparece olhando outras datas do cliente),
  o Triador pode arquivar um caso que merecia investigação.
- **Sem cache nem re-execução idempotente como no Nível 2.** `multiagente.py`
  não tem o cache em disco que `nivel_2/agente.py` tem — cada execução chama
  a LLM de novo para todos os clientes da lista, mesmo que já tenham sido
  processados.

## O que faria com mais tempo

### Nível 1

- Rodar cada prompt do LLM várias vezes (5–10 execuções) para medir média e
  variância reais de tokens/latência, em vez de uma amostra única. Validaria
  comparando o desvio-padrão entre execuções antes de declarar um prompt mais
  barato ou mais rápido que o outro.
- Estender a Regra 1 para detectar fracionamento numa janela de N dias, não
  só no mesmo dia. Validaria checando que ela não passa a gerar falso
  positivo para clientes com atividade normal espalhada no tempo.
- Escrever testes automatizados (pytest) para as regras determinísticas, em
  vez de só a validação manual no notebook. Poderia ser interessante rodar 
  em CI (com GitHub Actions) a cada mudança no código das regras.

### Nível 2

- Normalizar `n_sinalizacoes` pela quantidade de operações do cliente (uma
  "taxa de sinalização") para o ranking não favorecer só quem tem mais
  volume de operações. Validaria comparando o ranking normalizado com o
  atual e checando se a ordem dos primeiros colocados muda de forma
  defensável.

### Nível 3

- Rodar o fluxo multiagente nos 10 clientes da Parte A (não só na amostra de 4) 
  e comparar o parecer da Trilha A com o parecer do agente simples do
  Nível 2 lado a lado — validaria se o Triador realmente filtra casos que o
  agente de uma etapa só investigaria à toa, e se o resultado final diverge
  em algum caso.
- Portar o cache em disco do Nível 2 para `multiagente.py` — validaria
  rodando duas vezes e conferindo que a segunda não faz nenhuma chamada nova
  à API para os mesmos clientes.
