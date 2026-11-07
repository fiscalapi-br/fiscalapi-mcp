"""Servidor MCP da FiscalAPI (Streamable HTTP em /mcp, sem estado, um processo).

Ferramentas pagas repassam a chave do cliente MCP à API da FiscalAPI; nada é
guardado. Ferramentas sem chave rodam aqui mesmo, sem chamar a API.
"""

import logging
import math
import os
import re
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from validador_ie import validar_ie

from fiscalapi_mcp import __version__, textos
from fiscalapi_mcp.api import ClienteFiscalAPI, ErroDaAPI
from fiscalapi_mcp.limites import JanelaDeslizante, hash_da_chave

# A chave viaja em header: nenhum logger de HTTP pode registrar requisição em detalhe.
for _nome in ("httpx", "httpcore", "httpx2", "httpcore2"):
    logging.getLogger(_nome).setLevel(logging.WARNING)
# O SDK loga cada ToolError em INFO com a mensagem; as nossas já vêm sem chave e
# com documentos mascarados, mas o log da ferramenta abaixo basta.
logging.getLogger("mcp.server.mcpserver.server").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

URL_PUBLICA = "https://mcp.fiscalapi.com.br/mcp"
URL_DOCUMENTACAO = "https://github.com/fiscalapi-br/fiscalapi-mcp#readme"

TETO_PAGAS_POR_HORA = 30
LIMITE_SEM_CHAVE_POR_MINUTO = 60
# Todas as chamadas com chave somadas: impede usar este servidor como repetidor.
LIMITE_COM_CHAVE_POR_MINUTO = 120

# Módulo-nível de propósito: os testes trocam por versões com transporte falso
# ou janelas novas.
cliente_api = ClienteFiscalAPI()
TETO_PAGO = JanelaDeslizante(TETO_PAGAS_POR_HORA, 3600)
LIMITE_SEM_CHAVE = JanelaDeslizante(LIMITE_SEM_CHAVE_POR_MINUTO, 60)
LIMITE_COM_CHAVE = JanelaDeslizante(LIMITE_COM_CHAVE_POR_MINUTO, 60)

# As chaves da FiscalAPI são `fapi_` + hexadecimal; aqui só se exige texto ASCII
# simples, sem espaço nem nada que possa virar outro header.
_FORMATO_CHAVE = re.compile(r"[A-Za-z0-9_-]{16,128}")
_NAO_ALFANUMERICO = re.compile(r"[^0-9A-Za-z]")

UF = Literal[
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
]

INSTRUCOES = (
    "Servidor MCP da FiscalAPI: Inscrição Estadual (27 UFs), CNPJ, CND estadual, CNDT, CND Federal, "
    "CRF/FGTS e XML de NF-e sem certificado (cópia para leitura, sem a assinatura digital). "
    "validar_inscricao_estadual e cobertura não precisam de chave nem cobram. As demais usam a chave da "
    "FiscalAPI do usuário (header X-API-Key ou Authorization: Bearer) e as de consulta cobram do saldo dele: "
    "antes de chamá-las, diga ao usuário o custo que está na descrição da ferramenta e só passe "
    "confirmo_custo=true depois que ele aceitar. " + textos.CHAMADA_PARA_CHAVE + "."
)

mcp = MCPServer(
    "fiscalapi",
    title="FiscalAPI",
    description="Inscrição Estadual, CNPJ, certidões e cópia para leitura do XML de NF-e, pela API da FiscalAPI.",
    instructions=INSTRUCOES,
    website_url="https://fiscalapi.com.br",
    version=__version__,
)

_SOMENTE_LEITURA = ToolAnnotations(read_only_hint=True, open_world_hint=False)

CampoCPF = Annotated[
    str | None, Field(description="CPF, com ou sem pontuação (informe só um documento).", max_length=20)
]
CampoCNPJ = Annotated[
    str | None, Field(description="CNPJ, com ou sem pontuação (informe só um documento).", max_length=24)
]
CampoIE = Annotated[
    str | None, Field(description="Número da Inscrição Estadual (informe só um documento).", max_length=24)
]
CampoSecundarias = Annotated[
    bool,
    Field(
        description=(
            "Busca também as atividades secundárias de cada inscrição. Pode somar de alguns a dezenas de "
            "segundos, conforme o estado."
        )
    ),
]
CampoConfirmo = Annotated[
    bool,
    Field(
        description=(
            "Obrigatório para executar: true só depois que o usuário aceitou o custo descrito na ferramenta. "
            "Sem isso a ferramenta só explica o custo e não consulta nada."
        )
    ),
]


# --- chave -----------------------------------------------------------------


def _headers_da_requisicao(ctx: Context) -> Mapping[str, str]:
    return ctx.headers or {}


def chave_dos_headers(headers: Mapping[str, str]) -> str | None:
    """A chave da FiscalAPI vinda do cliente MCP: X-API-Key ou Authorization: Bearer.

    Valor fora do formato (espaço, acento, caractere de controle, curto ou comprido
    demais) é descartado: nunca vai para outro header. Nada daqui é logado.
    """
    normalizados = {str(k).lower(): str(v) for k, v in headers.items()}
    valor = normalizados.get("x-api-key", "").strip()
    if not valor:
        esquema, _, token = normalizados.get("authorization", "").strip().partition(" ")
        if esquema.lower() == "bearer":
            valor = token.strip()
    if not _FORMATO_CHAVE.fullmatch(valor):
        return None
    return valor


def _chave_ou_erro(ctx: Context) -> str:
    chave = chave_dos_headers(_headers_da_requisicao(ctx))
    if chave is None:
        raise ToolError(
            "Esta ferramenta precisa da chave da FiscalAPI. "
            + textos.COMO_CONFIGURAR_CHAVE
            + " "
            + textos.CHAMADA_PARA_CHAVE
            + "."
        )
    return chave


# --- parâmetros ------------------------------------------------------------


def _limpo(valor: str | None) -> str | None:
    if valor is None:
        return None
    limpo = _NAO_ALFANUMERICO.sub("", valor).upper()
    return limpo or None


def _um_documento(**documentos: str | None) -> dict[str, str]:
    informados = {nome: _limpo(valor) for nome, valor in documentos.items()}
    informados = {nome: valor for nome, valor in informados.items() if valor}
    if len(informados) != 1:
        nomes = ", ".join(documentos)
        raise ToolError(f"Informe exatamente um documento: {nomes}.")
    return informados


def _sem_pdf(dados: Any) -> Any:
    """Tira o PDF em base64 (centenas de KB) que não serve ao modelo."""
    if isinstance(dados, list):
        return [_sem_pdf(item) for item in dados]
    if not isinstance(dados, dict):
        return dados
    saida: dict[str, Any] = {}
    for campo, valor in dados.items():
        if campo == "pdf_base64" and isinstance(valor, str) and valor:
            saida[campo] = ""
            saida["pdf_omitido"] = (
                "O PDF não vem pelo MCP (grande demais para o modelo). Na API REST ele vem no campo "
                "pdf_base64, mas repetir a consulta lá cobra de novo."
            )
        else:
            saida[campo] = _sem_pdf(valor)
    return saida


# --- execução --------------------------------------------------------------


async def _consulta_paga(
    ctx: Context,
    operacao: str,
    custo: str,
    confirmo_custo: bool,
    params: dict[str, Any] | None = None,
    corpo: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chave = _chave_ou_erro(ctx)
    if not confirmo_custo:
        raise ToolError(
            f"Consulta paga, nada foi consultado. {custo} Mostre o custo ao usuário e, só se ele aceitar, "
            "chame de novo com confirmo_custo=true."
        )
    identificador = hash_da_chave(chave)
    espera = TETO_PAGO.tentar(identificador)
    if espera:
        minutos = max(1, math.ceil(espera / 60))
        raise ToolError(
            f"Este servidor MCP aceita até {TETO_PAGAS_POR_HORA} consultas pagas por hora por chave. "
            f"Tente de novo em {minutos} min. Para volume, use a API REST direto."
        )
    try:
        return _sem_pdf(await _chamar_api(operacao, chave, params=params, corpo=corpo))
    except ToolError as erro:
        # Chave recusada não ocupa o teto de ninguém (e não deixa o hash guardado).
        if getattr(erro.__cause__, "status", None) in (401, 403):
            TETO_PAGO.desfazer(identificador)
        raise


async def _chamar_api(
    operacao: str, chave: str, params: dict[str, Any] | None = None, corpo: dict[str, Any] | None = None
) -> dict[str, Any]:
    if LIMITE_COM_CHAVE.tentar("global"):
        raise ToolError("Muitas chamadas neste servidor agora. Tente de novo em 1 minuto.")
    logger.info("ferramenta=%s", operacao)
    try:
        return await cliente_api.chamar(operacao, chave, params=params, corpo=corpo)
    except ErroDaAPI as erro:
        raise ToolError(str(erro)) from erro


def _limite_sem_chave() -> None:
    if LIMITE_SEM_CHAVE.tentar("global"):
        raise ToolError("Muitas chamadas neste servidor agora. Tente de novo em 1 minuto.")


# --- ferramentas sem chave -------------------------------------------------


@mcp.tool(
    title="Validar Inscrição Estadual (formato e dígito)",
    description=(
        "Confere o formato e o dígito verificador de uma Inscrição Estadual na UF informada. Não precisa de "
        "chave e não cobra. Não diz se a IE existe, está ativa ou a quem pertence: isso só a consulta real "
        "(consultar_ie) responde. Devolve valida, motivo da recusa, a IE formatada e quantos zeros à "
        "esquerda foram completados."
    ),
    annotations=_SOMENTE_LEITURA,
)
async def validar_inscricao_estadual(
    uf: Annotated[UF, Field(description="Sigla da UF da inscrição, ex.: MT.")],
    ie: Annotated[str, Field(description="Número da IE, com ou sem pontuação.", max_length=30)],
) -> dict[str, Any]:
    _limite_sem_chave()
    resultado = validar_ie(ie, uf)
    return {
        "uf": uf,
        "ie": ie,
        "valida": resultado.valida,
        "motivo": resultado.motivo,
        "formatada": resultado.formatada,
        "zeros_completados": resultado.zeros_completados,
        "aviso": "Confere só o formato e o dígito verificador, não a situação cadastral.",
        "proximo_passo": textos.CHAMADA_PARA_CHAVE,
    }


@mcp.tool(
    title="O que a FiscalAPI consulta",
    description=(
        "Resumo do que a FiscalAPI consulta por produto e UF, o que cada ferramenta devolve e os limites "
        "da API. Não precisa de chave e não cobra."
    ),
    annotations=_SOMENTE_LEITURA,
)
async def cobertura() -> dict[str, Any]:
    _limite_sem_chave()
    return {**textos.COBERTURA, "proximo_passo": textos.CHAMADA_PARA_CHAVE}


# --- ferramentas com chave -------------------------------------------------


@mcp.tool(
    title="Consultar Inscrição Estadual numa UF",
    description=(
        "Consulta a Inscrição Estadual na UF informada, por CPF, CNPJ ou IE (um só). Devolve os dados "
        "cadastrais de cada inscrição: número, razão social, situação, tipo, endereço, CNAE, regime e datas. "
        "Por CPF não funciona em SP (lá, use CNPJ ou IE). " + textos.CUSTO_CONSULTA_GRATIS
    ),
)
async def consultar_ie(
    ctx: Context,
    uf: Annotated[UF, Field(description="Sigla da UF, ex.: MT.")],
    cpf: CampoCPF = None,
    cnpj: CampoCNPJ = None,
    ie: CampoIE = None,
    secundarias: CampoSecundarias = False,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {"uf": uf, **_um_documento(cpf=cpf, cnpj=cnpj, ie=ie)}
    if secundarias:
        params["secundarias"] = "true"
    return await _consulta_paga(ctx, "consultar_ie", textos.CUSTO_CONSULTA_GRATIS, confirmo_custo, params=params)


@mcp.tool(
    title="Consultar Inscrição Estadual em todos os estados",
    description=(
        "Procura inscrições estaduais nos 27 estados numa chamada, por CPF, CNPJ ou IE (um só), sem informar "
        "a UF. Devolve, por UF, as inscrições encontradas e o campo complete (false = algum estado não "
        "respondeu, então ausência não prova que não existe inscrição). Conta como 1 consulta. " + textos.CUSTO_IE_TODOS
    ),
)
async def consultar_ie_todos_estados(
    ctx: Context,
    cpf: CampoCPF = None,
    cnpj: CampoCNPJ = None,
    ie: CampoIE = None,
    secundarias: CampoSecundarias = False,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params: dict[str, Any] = dict(_um_documento(cpf=cpf, cnpj=cnpj, ie=ie))
    if secundarias:
        params["secundarias"] = "true"
    return await _consulta_paga(ctx, "consultar_ie_todos_estados", textos.CUSTO_IE_TODOS, confirmo_custo, params=params)


@mcp.tool(
    title="Consultar CNPJ",
    description=(
        "Consulta o cadastro público de um CNPJ na Receita Federal: razão social, situação cadastral, abertura, "
        "CNAE, endereço, telefones, e-mail, quadro societário e opção pelo Simples e pelo MEI (base mensal da "
        "Receita Federal). Com ao_vivo=true consulta a Receita Federal na hora (mais lento; Simples e MEI "
        "voltam vazios). " + textos.CUSTO_CNPJ
    ),
)
async def consultar_cnpj(
    ctx: Context,
    cnpj: Annotated[str, Field(description="CNPJ, com ou sem pontuação.", max_length=24)],
    ao_vivo: Annotated[
        bool, Field(description="Consulta a Receita Federal na hora, ignorando o cache. Custa 3 consultas.")
    ] = False,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params: dict[str, Any] = dict(_um_documento(cnpj=cnpj))
    if ao_vivo:
        params["force_fresh"] = "true"
    return await _consulta_paga(ctx, "consultar_cnpj", textos.CUSTO_CNPJ, confirmo_custo, params=params)


@mcp.tool(
    title="Consultar CND estadual",
    description=(
        "Consulta a Certidão Negativa de Débitos estadual (ICMS) de um CPF ou CNPJ (um só) na UF informada. "
        "Devolve o status (negativa, positiva, positiva_com_efeitos_de_negativa, nao_contribuinte, "
        "sem_certidao ou erro), emissão, validade e protocolo. O PDF não vem pelo MCP. " + textos.CUSTO_CONSULTA
    ),
)
async def consultar_cnd_estadual(
    ctx: Context,
    uf: Annotated[UF, Field(description="Sigla da UF, ex.: MT.")],
    cpf: CampoCPF = None,
    cnpj: CampoCNPJ = None,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {"uf": uf, **_um_documento(cpf=cpf, cnpj=cnpj)}
    return await _consulta_paga(ctx, "consultar_cnd_estadual", textos.CUSTO_CONSULTA, confirmo_custo, params=params)


@mcp.tool(
    title="Consultar CNDT (débitos trabalhistas)",
    description=(
        "Consulta a Certidão Negativa de Débitos Trabalhistas (TST) de um CPF ou CNPJ (um só). Devolve status, "
        "emissão, validade e protocolo. O PDF não vem pelo MCP. " + textos.CUSTO_CONSULTA
    ),
)
async def consultar_cndt(
    ctx: Context,
    cpf: CampoCPF = None,
    cnpj: CampoCNPJ = None,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params = _um_documento(cpf=cpf, cnpj=cnpj)
    return await _consulta_paga(ctx, "consultar_cndt", textos.CUSTO_CONSULTA, confirmo_custo, params=params)


@mcp.tool(
    title="Consultar CND Federal",
    description=(
        "Consulta a certidão de débitos de tributos federais e Dívida Ativa da União (Receita Federal e PGFN) "
        "de um CPF ou CNPJ (um só). Se já existe certidão que vale por mais de 3 dias, devolve essa "
        "(modo=consulta); senão, emite uma nova (modo=emissao). Com emitir_nova=true, emite sempre. Devolve "
        "status, emissão, validade e protocolo. O PDF não vem pelo MCP. " + textos.CUSTO_CONSULTA
    ),
)
async def consultar_cnd_federal(
    ctx: Context,
    cpf: CampoCPF = None,
    cnpj: CampoCNPJ = None,
    emitir_nova: Annotated[bool, Field(description="Emite uma certidão nova mesmo que já exista uma válida.")] = False,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params: dict[str, Any] = dict(_um_documento(cpf=cpf, cnpj=cnpj))
    if emitir_nova:
        params["emitir_nova"] = "true"
    return await _consulta_paga(ctx, "consultar_cnd_federal", textos.CUSTO_CONSULTA, confirmo_custo, params=params)


@mcp.tool(
    title="Consultar CRF/FGTS",
    description=(
        "Consulta o Certificado de Regularidade do FGTS (Caixa) de um CPF ou CNPJ (um só). Devolve status, "
        "emissão, validade e protocolo. O PDF não vem pelo MCP. " + textos.CUSTO_CONSULTA
    ),
)
async def consultar_crf_fgts(
    ctx: Context,
    cpf: CampoCPF = None,
    cnpj: CampoCNPJ = None,
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    params = _um_documento(cpf=cpf, cnpj=cnpj)
    return await _consulta_paga(ctx, "consultar_crf_fgts", textos.CUSTO_CONSULTA, confirmo_custo, params=params)


@mcp.tool(
    title="Baixar XML de NF-e sem certificado (cópia para leitura)",
    description=(
        "Devolve uma cópia para leitura do XML de UMA NF-e (modelo 55) a partir da chave de acesso de 44 "
        "posições, sem certificado digital. A cópia vem sem a assinatura digital (assinado=false, "
        "tipo_xml=leitura): traz os dados da nota, mas não serve para validar schema nem assinatura. Status "
        "por chave: ok (com o XML), nao_encontrado ou erro. " + textos.CUSTO_NFE_SEM_CERT
    ),
)
async def baixar_xml_nfe_sem_certificado(
    ctx: Context,
    chave: Annotated[
        str, Field(description="Chave de acesso da NF-e (44 posições); separadores são ignorados.", max_length=60)
    ],
    confirmo_custo: CampoConfirmo = False,
) -> dict[str, Any]:
    chave_nfe = _limpo(chave)
    if not chave_nfe or len(chave_nfe) != 44:
        raise ToolError("A chave de acesso tem 44 posições. Confira e tente de novo.")
    return await _consulta_paga(
        ctx, "baixar_xml_nfe_sem_certificado", textos.CUSTO_NFE_SEM_CERT, confirmo_custo, corpo={"chave": chave_nfe}
    )


@mcp.tool(
    title="Saldo da conta",
    description=(
        "Quanto o saldo da conta ainda rende: consultas_restantes (IE, CNPJ, certidões) e notas_restantes "
        "(XML de NF-e). As duas formas dividem o mesmo saldo. notas_restantes conta o XML com certificado; "
        "no Enterprise o XML sem certificado gasta o dobro. Usa a chave da FiscalAPI e não consome consulta."
    ),
)
async def saldo(ctx: Context) -> dict[str, Any]:
    return await _chamar_api("saldo", _chave_ou_erro(ctx))


# --- rotas HTTP fora do MCP ------------------------------------------------


@mcp.custom_route("/", methods=["GET"])
async def raiz(request: Request) -> Response:
    return JSONResponse(
        {
            "nome": "fiscalapi-mcp",
            "versao": __version__,
            "mcp": URL_PUBLICA,
            "documentacao": URL_DOCUMENTACAO,
        }
    )


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


def hosts_permitidos() -> list[str]:
    """Host aceitos em /mcp (proteção contra DNS rebinding). O domínio público
    do Railway vem da variável que o próprio Railway injeta no serviço."""
    hosts = ["mcp.fiscalapi.com.br", "localhost", "127.0.0.1"]
    railway = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip().lower()
    if railway.endswith(".up.railway.app") and re.fullmatch(r"[a-z0-9.-]+", railway):
        hosts.append(railway)
    return [h for host in hosts for h in (host, f"{host}:*")]


seguranca = TransportSecuritySettings(
    allowed_hosts=hosts_permitidos(),
    allowed_origins=["https://mcp.fiscalapi.com.br", "http://localhost:*", "http://127.0.0.1:*"],
)

app = mcp.streamable_http_app(stateless_http=True, json_response=True, transport_security=seguranca)
