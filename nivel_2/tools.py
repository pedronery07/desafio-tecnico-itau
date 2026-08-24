"""
Ferramentas que consultam a base do Nível 2 (dados/dados_nivel_2.json).

Implementar ao menos:
- historico_cliente(cliente_id): resumo agregado das operações do cliente
- operacoes_do_dia(cliente_id, data): recorte de um dia específico
- perfil_canal(cliente_id): distribuição de uso por canal
"""

import json
from pathlib import Path

DADOS_PATH = Path(__file__).resolve().parent.parent / "dados" / "dados_nivel_2.json"


def _carregar_dados():
    with open(DADOS_PATH, encoding="utf-8") as f:
        return json.load(f)


def historico_cliente(cliente_id):
    """Resumo agregado das operações do cliente."""
    raise NotImplementedError


def operacoes_do_dia(cliente_id, data):
    """Recorte das operações de um cliente em uma data específica."""
    raise NotImplementedError


def perfil_canal(cliente_id):
    """Distribuição de uso por canal para o cliente."""
    raise NotImplementedError
