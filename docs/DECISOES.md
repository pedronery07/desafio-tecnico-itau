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
