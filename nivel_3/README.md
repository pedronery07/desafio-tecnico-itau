# Nível 3 — Trilha A: fluxo multiagente

Justificativa da escolha em `docs/DECISOES.md`.

- **`multiagente.py`** — Triador → Investigador → Redator, com estado
  compartilhado (`EstadoCaso`) e condição de parada (o Triador pode arquivar
  o caso sem investigação completa). Reaproveita as ferramentas e as regras
  do Nível 2. Rodar com `python nivel_3/multiagente.py`.
- Diagrama Mermaid do fluxo: `docs/ARQUITETURA.md`.
- Resultados salvos em `outputs/nivel_3/{cliente_id}.json` (um por cliente,
  com o estado completo do fluxo, não só o parecer final).
