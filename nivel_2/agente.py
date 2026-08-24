"""
Agente que decide quais ferramentas de tools.py chamar, conforme o caso de
cada cliente, e produz um parecer estruturado (nivel_risco, tipologia_suspeita,
red_flags, justificativa).

Chamar todas as ferramentas sempre, para todo cliente, não é um agente — é um
script. O agente precisa decidir, com base no que já sabe, quais ferramentas
valem a pena chamar.

TODO:
- montar o loop de decisão do agente (framework livre: LangChain, LangGraph,
  PydanticAI, SDK nativo do provedor, ou na mão)
- rodar sobre os 10 clientes mais sinalizados (Parte A / Parte C)
- salvar resultados em outputs/ com custo e latência de cada chamada
"""

# from nivel_2 import tools


def rodar_agente(cliente_id):
    """Executa o agente para um cliente e retorna o parecer estruturado."""
    raise NotImplementedError


if __name__ == "__main__":
    # TODO: carregar os 10 clientes mais sinalizados (Nível 2 - Parte A)
    # e rodar o agente em lote, salvando em outputs/
    pass
