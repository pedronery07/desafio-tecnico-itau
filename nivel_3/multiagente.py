"""
Nível 3 — Trilha A: fluxo multiagente.

Três papéis encadeados, cada um lendo/escrevendo um estado compartilhado
(`EstadoCaso`):

  1. Triador      — decisão rápida, SEM ferramentas: o caso segue para
                     investigação completa ou é arquivado direto com um
                     risco preliminar? Esta é a CONDIÇÃO DE PARADA do fluxo
                     — se `segue=False`, o Investigador nunca roda, e o
                     Redator escreve o parecer só com o que o Triador viu.
  2. Investigador  — só roda se o Triador liberou o caso. Reaproveita as
                     ferramentas do Nível 2 (nivel_2/tools.py) via function
                     calling manual, decidindo sozinho quais chamar. Não
                     escreve parecer, só levanta achados.
  3. Redator       — recebe o estado acumulado (decisão do Triador + achados
                     do Investigador, se houver) e escreve o parecer final
                     estruturado.

Diagrama do fluxo: docs/ARQUITETURA.md
Rodar com: python nivel_3/multiagente.py
"""

import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Literal, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "nivel_2"))

import regras  # nivel_2/regras.py — mesmo pipeline de limpeza/regras
import tools  # nivel_2/tools.py — as 3 ferramentas do Investigador

load_dotenv(REPO_ROOT / ".env")

MODEL_NAME = os.environ.get("LLM_MODEL", "gemini-3.5-flash-lite")
client_llm = genai.Client(api_key=os.environ["LLM_API_KEY"])

OUTPUTS_DIR = REPO_ROOT / "outputs" / "nivel_3"

FERRAMENTAS_DISPONIVEIS = {
    "historico_cliente": tools.historico_cliente,
    "operacoes_do_dia": tools.operacoes_do_dia,
    "perfil_canal": tools.perfil_canal,
}


# ---------------------------------------------------------------------------
# Estado compartilhado
# ---------------------------------------------------------------------------
@dataclass
class EstadoCaso:
    cliente_id: str
    regras_disparadas: list
    contexto_regras: dict
    segue: Optional[bool] = None
    motivo_triagem: Optional[str] = None
    risco_preliminar: Optional[str] = None
    achados_investigacao: Optional[str] = None
    ferramentas_chamadas: list = field(default_factory=list)
    parecer_final: Optional[dict] = None
    tokens_total: int = 0
    etapas_executadas: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Schemas de saída (Triador e Redator)
# ---------------------------------------------------------------------------
class DecisaoTriagem(BaseModel):
    segue: bool
    motivo: str
    risco_preliminar: Literal["baixo", "médio", "alto"]


class ParecerFinal(BaseModel):
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


# ---------------------------------------------------------------------------
# Retry (mesmo padrão de nivel_2/agente.py: 429 com retryDelay, 503 com backoff)
# ---------------------------------------------------------------------------
def _extrair_retry_delay(erro, padrao=5.0):
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


def _generate_content_com_retry(contents, config, max_tentativas=5):
    for tentativa in range(1, max_tentativas + 1):
        try:
            return client_llm.models.generate_content(
                model=MODEL_NAME, contents=contents, config=config
            )
        except errors.ClientError as e:
            if e.code != 429 or tentativa == max_tentativas:
                raise
            espera = _extrair_retry_delay(e) + 1
            print(f"    [rate limit 429] tentativa {tentativa}/{max_tentativas}, "
                  f"aguardando {espera:.1f}s...")
            time.sleep(espera)
        except errors.ServerError as e:
            if e.code != 503 or tentativa == max_tentativas:
                raise
            espera = 5.0 * tentativa
            print(f"    [servidor sobrecarregado 503] tentativa {tentativa}/{max_tentativas}, "
                  f"aguardando {espera:.1f}s...")
            time.sleep(espera)


# ---------------------------------------------------------------------------
# Papel 1 — Triador
# ---------------------------------------------------------------------------
def papel_triador(estado: EstadoCaso) -> EstadoCaso:
    """Decide, sem chamar ferramentas, se o caso vale uma investigação
    completa (mais cara) ou se já dá para arquivar com um risco preliminar.
    Condição de parada do fluxo: `segue=False` pula o Investigador."""
    prompt = f"""Você é o TRIADOR de uma mesa de prevenção à lavagem de dinheiro.

Cliente: {estado.cliente_id}
Regras determinísticas disparadas: {', '.join(estado.regras_disparadas) or 'nenhuma'}
Evidência resumida (já calculada por regras determinísticas): \
{json.dumps(estado.contexto_regras, ensure_ascii=False)}

Sua função é uma triagem RÁPIDA — decidir se este caso merece investigação \
completa (mais cara e demorada, com ferramentas de consulta detalhada) ou se \
já dá para arquivar direto com um risco preliminar, sem investigar mais. \
Você não tem ferramentas aqui — julgue só pela evidência resumida acima. \
Casos com sinal muito próximo do limiar mínimo da regra (e nenhum outro \
agravante) são bons candidatos a arquivar direto; casos com sinal forte ou \
múltiplos agravantes merecem investigação completa.

Responda ESTRITAMENTE em JSON, sem markdown:
{{
  "segue": true | false,
  "motivo": "1-2 frases explicando a decisão",
  "risco_preliminar": "baixo" | "médio" | "alto"
}}
"""
    config = types.GenerateContentConfig()
    resposta = _generate_content_com_retry(
        [types.Content(role="user", parts=[types.Part(text=prompt)])], config
    )
    if resposta.usage_metadata:
        estado.tokens_total += resposta.usage_metadata.total_token_count or 0

    try:
        decisao = DecisaoTriagem.model_validate_json(extrair_json(resposta.text or ""))
        estado.segue = decisao.segue
        estado.motivo_triagem = decisao.motivo
        estado.risco_preliminar = decisao.risco_preliminar
    except (ValidationError, ValueError, TypeError) as e:
        # Triagem malformada: por segurança, o caso SEGUE para investigação
        # completa em vez de ser arquivado silenciosamente sem revisão.
        estado.segue = True
        estado.motivo_triagem = f"[triagem malformada, seguiu por padrão de segurança] {e}"
        estado.risco_preliminar = None

    estado.etapas_executadas.append("triador")
    return estado


# ---------------------------------------------------------------------------
# Papel 2 — Investigador
# ---------------------------------------------------------------------------
def papel_investigador(estado: EstadoCaso) -> EstadoCaso:
    """Só roda se o Triador liberou o caso (estado.segue). Usa as
    ferramentas do Nível 2 via function calling manual — decide sozinho
    quais chamar, não chama todas por padrão."""
    if not estado.segue:
        return estado

    prompt = f"""Você é o INVESTIGADOR de uma mesa de prevenção à lavagem de \
dinheiro. O TRIADOR já analisou o caso do cliente {estado.cliente_id} e \
decidiu que ele merece investigação completa: "{estado.motivo_triagem}" \
(risco preliminar: {estado.risco_preliminar}).

Regras disparadas: {', '.join(estado.regras_disparadas) or 'nenhuma'}

Use as ferramentas disponíveis para aprofundar a investigação — decida \
sozinho quais fazem sentido para este caso, não chame todas por padrão. \
`historico_cliente` já traz `dias_fracionamento` (data exata da concentração) \
e `operacoes_atipicas` (múltiplo da mediana) quando aplicável.

NÃO escreva o parecer final — isso é trabalho do Redator, não seu. Escreva \
um resumo objetivo dos achados, em texto corrido, citando fatos concretos \
(datas, valores, múltiplos, canais) — de 3 a 6 frases.
"""
    config = types.GenerateContentConfig(
        tools=list(FERRAMENTAS_DISPONIVEIS.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    texto_final = ""
    for _ in range(6):
        resposta = _generate_content_com_retry(contents, config)
        if resposta.usage_metadata:
            estado.tokens_total += resposta.usage_metadata.total_token_count or 0

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
            estado.ferramentas_chamadas.append({"ferramenta": nome, "args": args, "erro": erro})
            partes_resposta.append(
                types.Part.from_function_response(name=nome, response={"resultado": resultado})
            )
        contents.append(types.Content(role="user", parts=partes_resposta))
    else:
        texto_final = resposta.text or ""

    estado.achados_investigacao = texto_final
    estado.etapas_executadas.append("investigador")
    return estado


# ---------------------------------------------------------------------------
# Papel 3 — Redator
# ---------------------------------------------------------------------------
def papel_redator(estado: EstadoCaso) -> EstadoCaso:
    """Escreve o parecer final a partir do estado acumulado até aqui. Se o
    Triador parou o fluxo, escreve com base só na triagem; se o Investigador
    rodou, usa também os achados dele."""
    if estado.segue:
        contexto = f"""O TRIADOR decidiu investigar o caso: "{estado.motivo_triagem}" \
(risco preliminar: {estado.risco_preliminar}).

O INVESTIGADOR levantou os seguintes achados:
{estado.achados_investigacao}
"""
    else:
        contexto = f"""O TRIADOR decidiu ARQUIVAR o caso sem investigação completa: \
"{estado.motivo_triagem}" (risco preliminar: {estado.risco_preliminar}). Não há \
achados de investigação adicionais — escreva o parecer com base só nisso.
"""

    prompt = f"""Você é o REDATOR de uma mesa de prevenção à lavagem de dinheiro. \
Escreva o parecer final do cliente {estado.cliente_id}, sinalizado pelas \
regras determinísticas: {', '.join(estado.regras_disparadas) or 'nenhuma'}.

{contexto}
Os cálculos (soma, mediana, contagem, comparação com limite) já foram feitos \
por regras determinísticas antes deste fluxo — não recalcule nada, apenas \
interprete e redija.

Responda ESTRITAMENTE em JSON, sem nenhum texto fora do JSON e sem markdown:
{{
  "nivel_risco": "baixo" | "médio" | "alto",
  "tipologia_suspeita": "string curta",
  "red_flags": ["lista", "de", "strings"],
  "justificativa": "2 a 4 frases citando os fatos coletados"
}}
"""
    config = types.GenerateContentConfig()
    resposta = _generate_content_com_retry(
        [types.Content(role="user", parts=[types.Part(text=prompt)])], config
    )
    if resposta.usage_metadata:
        estado.tokens_total += resposta.usage_metadata.total_token_count or 0

    try:
        parecer = ParecerFinal.model_validate_json(extrair_json(resposta.text or ""))
        estado.parecer_final = parecer.model_dump()
    except (ValidationError, ValueError, TypeError) as e:
        estado.parecer_final = {"erro": str(e), "texto_bruto": resposta.text}

    estado.etapas_executadas.append("redator")
    return estado


# ---------------------------------------------------------------------------
# Orquestrador
# ---------------------------------------------------------------------------
def rodar_fluxo(cliente_id, df_clean) -> EstadoCaso:
    """Monta o estado inicial a partir das regras determinísticas e roda os
    três papéis em sequência. O Investigador é pulado automaticamente se o
    Triador decidir `segue=False` (condição de parada)."""
    estado = EstadoCaso(
        cliente_id=cliente_id,
        regras_disparadas=regras.regras_disparadas(df_clean, cliente_id),
        contexto_regras=regras.detalhe_regras(df_clean, cliente_id),
    )
    estado = papel_triador(estado)
    estado = papel_investigador(estado)  # no-op se estado.segue == False
    estado = papel_redator(estado)
    return estado


if __name__ == "__main__":
    df_clean = regras.processar("dados_nivel_2.json")

    # Amostra pequena e deliberada (ver docs/DECISOES.md): um caso de
    # fracionamento borderline, um valor atípico forte, um valor atípico
    # moderado com agravante (2 operações no mesmo dia) e um valor atípico
    # isolado e fraco — o candidato mais forte a ser arquivado pelo Triador
    # sem investigação completa (condição de parada).
    clientes_demo = ["CLI-003", "CLI-023", "CLI-028", "CLI-008"]

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    for cliente_id in clientes_demo:
        print(f"\n{'=' * 70}\nProcessando {cliente_id}...")
        estado = rodar_fluxo(cliente_id, df_clean)

        print(f"Regras disparadas: {estado.regras_disparadas}")
        print(f"Triador -> segue={estado.segue} | risco preliminar: {estado.risco_preliminar}")
        print(f"  motivo: {estado.motivo_triagem}")
        print(f"Etapas executadas: {' -> '.join(estado.etapas_executadas)}")
        print(f"Tokens totais: {estado.tokens_total}")
        print(f"Parecer final: {json.dumps(estado.parecer_final, ensure_ascii=False, indent=2)}")

        caminho = OUTPUTS_DIR / f"{cliente_id}.json"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(asdict(estado), f, ensure_ascii=False, indent=2)

    print(f"\nResultados salvos em {OUTPUTS_DIR}/")
