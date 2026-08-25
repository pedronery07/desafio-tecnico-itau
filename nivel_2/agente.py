"""
Agente que decide quais ferramentas de tools.py chamar, conforme o caso de
cada cliente, e produz um parecer estruturado (nivel_risco, tipologia_suspeita,
red_flags, justificativa).

O agente recebe só o cliente_id e as regras que dispararam
para ele (o "gatilho" determinístico), não o histórico já pronto — ele decide
sozinho quais ferramentas consultar para investigar o caso.

Implementado com function calling nativo do SDK google-genai, em loop manual
(não o modo automático) para poder registrar tokens e latência de cada
chamada real à API.

Tem cache em disco por cliente (outputs/nivel_2/cache/): se o mesmo cliente
já foi processado com as mesmas regras disparadas, o mesmo modelo e a mesma
versão de prompt, reaproveita o resultado salvo em vez de chamar a LLM de
novo — reduz consumo de tokens em reprocessamentos.

Mesmo com cache, um lote de vários clientes novos pode estourar o limite de
requisições por minuto da camada gratuita (15 req/min no gemini-3.5-flash-lite)
— por isso as chamadas à API têm retry com backoff (respeitando o
`retryDelay` que o próprio erro 429 devolve) em vez de derrubar o lote inteiro.
"""

import hashlib
import json as _json
import os
import re
import time
from pathlib import Path
from typing import List, Literal

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

import tools

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

MODEL_NAME = os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite")
client_llm = genai.Client(api_key=os.environ["LLM_API_KEY"])

PROMPT_VERSION = "v2"  # muda se o texto de montar_prompt_inicial mudar, pra invalidar o cache
CACHE_DIR = Path(__file__).resolve().parent.parent / "outputs" / "nivel_2" / "cache"

FERRAMENTAS_DISPONIVEIS = {
    "historico_cliente": tools.historico_cliente,
    "operacoes_do_dia": tools.operacoes_do_dia,
    "perfil_canal": tools.perfil_canal,
}


class ParecerLLM(BaseModel):
    nivel_risco: Literal["baixo", "médio", "alto"]
    tipologia_suspeita: str
    red_flags: List[str]
    justificativa: str


def extrair_json(texto):
    """O LLM às vezes envolve o JSON em ```json ... ``` — remove o fence."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
    return texto.strip()


def montar_prompt_inicial(cliente_id, regras_disparadas):
    regras_texto = ", ".join(regras_disparadas) if regras_disparadas else "nenhuma"
    return f"""Você é um agente de investigação de prevenção à lavagem de \
dinheiro em um banco.

O cliente {cliente_id} foi sinalizado pelas seguintes regras determinísticas: \
{regras_texto}.

Você tem ferramentas para consultar a base de operações desse cliente. NÃO \
chame todas as ferramentas por padrão — decida quais são realmente \
necessárias para investigar ESTE caso específico. `historico_cliente` já \
traz a evidência exata por trás de cada regra disparada: se foi \
fracionamento, o campo `dias_fracionamento` diz a(s) data(s) exata(s) com a \
soma e a quantidade de operações daquele dia — use essa data (não adivinhe) \
se quiser aprofundar com `operacoes_do_dia`. Se foi valor atípico, o campo \
`operacoes_atipicas` já traz qual(is) operação(ões) é(são) o valor atípico e \
por qual múltiplo da mediana do cliente ela passa — um múltiplo de 5x é bem \
diferente de um múltiplo de 15x, considere isso na sua avaliação de risco. \
Perfil de canal é útil quando a concentração ou diversidade de canais \
parecer relevante para a tipologia.

Os cálculos (soma, mediana, contagem, comparação com limite) já foram feitos \
pelas regras determinísticas — não recalcule nada, use os números que as \
ferramentas devolverem apenas para interpretar e redigir o parecer.

Ao terminar a investigação, responda ESTRITAMENTE em JSON válido, sem \
nenhum texto fora do JSON e sem markdown, no formato:
{{
  "nivel_risco": "baixo" | "médio" | "alto",
  "tipologia_suspeita": "string curta",
  "red_flags": ["lista", "de", "strings"],
  "justificativa": "2 a 4 frases citando fatos coletados pelas ferramentas"
}}
"""


def _extrair_retry_delay(erro, padrao=5.0):
    """Lê o retryDelay sugerido pelo erro 429 (ex.: '3.85s') — se não achar,
    usa um valor padrão."""
    try:
        for violacao in erro.details.get("error", {}).get("details", []):
            delay = violacao.get("retryDelay")
            if delay:
                match = re.match(r"([\d.]+)s?", delay)
                if match:
                    return float(match.group(1))
    except (AttributeError, TypeError):
        pass
    return padrao


def _generate_content_com_retry(model_name, contents, config, max_tentativas=5):
    """Chama a API com retry/backoff para dois tipos de erro transitório:
    - 429 (ClientError): limite de requisições por minuto da camada
      gratuita — usa o retryDelay que o próprio erro sugere.
    - 503 (ServerError): modelo temporariamente sobrecarregado do lado do
      provedor — não vem com retryDelay, usa backoff exponencial simples.
    Sem isso, um lote de vários clientes novos derruba no meio."""
    for tentativa in range(1, max_tentativas + 1):
        try:
            return client_llm.models.generate_content(
                model=model_name, contents=contents, config=config
            )
        except errors.ClientError as e:
            if e.code != 429 or tentativa == max_tentativas:
                raise
            espera = _extrair_retry_delay(e) + 1  # +1s de margem
            print(f"  [rate limit 429] tentativa {tentativa}/{max_tentativas}, "
                  f"aguardando {espera:.1f}s...")
            time.sleep(espera)
        except errors.ServerError as e:
            if e.code != 503 or tentativa == max_tentativas:
                raise
            espera = 5.0 * tentativa  # backoff simples: 5s, 10s, 15s...
            print(f"  [servidor sobrecarregado 503] tentativa {tentativa}/{max_tentativas}, "
                  f"aguardando {espera:.1f}s...")
            time.sleep(espera)


def _cache_path(cliente_id, regras_disparadas, model_name):
    """Chave do cache = cliente + regras disparadas + modelo + versão do
    prompt. Muda qualquer um desses e o cache é invalidado naturalmente
    (não reaproveita resultado de um cenário diferente)."""
    chave_bruta = f"{cliente_id}|{','.join(sorted(regras_disparadas))}|{model_name}|{PROMPT_VERSION}"
    hash_curto = hashlib.sha256(chave_bruta.encode()).hexdigest()[:12]
    return CACHE_DIR / f"{cliente_id}_{hash_curto}.json"


def rodar_agente(
    cliente_id, regras_disparadas, model_name=MODEL_NAME, max_iteracoes=6, usar_cache=True
):
    """Executa o agente para um cliente: loop de decisão sobre quais
    ferramentas chamar, até produzir o parecer final em JSON.

    Se `usar_cache=True` (padrão) e já existir um resultado salvo em disco
    para o mesmo (cliente, regras, modelo, versão de prompt), reaproveita em
    vez de chamar a LLM de novo — ver docstring do módulo.

    Retorna um dict com o parecer validado, tokens/latência totais e a lista
    de ferramentas efetivamente chamadas (para auditoria/observabilidade).
    """
    cache_path = _cache_path(cliente_id, regras_disparadas, model_name)
    if usar_cache and cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            resultado = _json.load(f)
        resultado["cache_hit"] = True
        return resultado

    config = types.GenerateContentConfig(
        tools=list(FERRAMENTAS_DISPONIVEIS.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [
        types.Content(
            role="user",
            parts=[types.Part(text=montar_prompt_inicial(cliente_id, regras_disparadas))],
        )
    ]

    ferramentas_chamadas = []
    tokens_total = 0
    texto_final = ""
    inicio = time.time()

    for _ in range(max_iteracoes):
        resposta = _generate_content_com_retry(model_name, contents, config)
        if resposta.usage_metadata:
            tokens_total += resposta.usage_metadata.total_token_count or 0

        candidato = resposta.candidates[0]
        contents.append(candidato.content)

        function_calls = [p.function_call for p in candidato.content.parts if p.function_call]
        if not function_calls:
            texto_final = resposta.text or ""
            break

        partes_resposta = []
        for fc in function_calls:
            nome = fc.name
            args = dict(fc.args) if fc.args else {}
            try:
                resultado = FERRAMENTAS_DISPONIVEIS[nome](**args)
                erro = None
            except Exception as e:  # ferramenta chamada com args inválidos, etc.
                resultado = {"erro": str(e)}
                erro = str(e)
            ferramentas_chamadas.append({"ferramenta": nome, "args": args, "erro": erro})
            partes_resposta.append(
                types.Part.from_function_response(name=nome, response={"resultado": resultado})
            )
        contents.append(types.Content(role="user", parts=partes_resposta))
    else:
        texto_final = resposta.text or ""

    duracao = time.time() - inicio

    resultado = {
        "cliente_id": cliente_id,
        "regras_disparadas": regras_disparadas,
        "tempo_resposta_s": round(duracao, 2),
        "tokens_total": tokens_total,
        "ferramentas_chamadas": ferramentas_chamadas,
        "texto_bruto": texto_final,
        "parecer": None,
        "valido": False,
        "erro": None,
    }

    try:
        parsed = _json.loads(extrair_json(texto_final))
        parecer = ParecerLLM(**parsed)
        resultado["parecer"] = parecer.model_dump()
        resultado["valido"] = True
    except (_json.JSONDecodeError, ValidationError) as e:
        resultado["erro"] = str(e)

    resultado["cache_hit"] = False

    if usar_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            _json.dump(resultado, f, ensure_ascii=False, indent=2)

    return resultado


if __name__ == "__main__":
    # Teste rápido com um único cliente — a execução em lote sobre os 10
    # mais sinalizados (Parte C) usa esta mesma função a partir de outro
    # script/notebook.
    import regras as regras_module

    df_clean = regras_module.processar("dados_nivel_2.json")
    cliente_teste = "CLI-023"
    regras_teste = regras_module.regras_disparadas(df_clean, cliente_teste)

    resultado = rodar_agente(cliente_teste, regras_teste)
    print(_json.dumps(resultado, indent=2, ensure_ascii=False))
