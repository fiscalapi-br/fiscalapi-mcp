"""Chamadas à API pública da FiscalAPI.

A URL base é fixa e os caminhos são constantes deste módulo: o que vem do
cliente MCP entra só como parâmetro de query ou campo do corpo JSON, nunca no
caminho nem no host. A chave vai SÓ no header X-API-Key e nunca é logada.
"""

import logging
import re
from typing import Any

import httpx

from fiscalapi_mcp import __version__, textos

logger = logging.getLogger(__name__)

URL_BASE = "https://api.fiscalapi.com.br"
USER_AGENT = f"fiscalapi-mcp/{__version__}"
TIMEOUT_S = 80.0
# Resposta maior que isso não cabe no contexto de um modelo de qualquer jeito.
MAX_BYTES_RESPOSTA = 5 * 1024 * 1024
_MAX_DETALHE = 300
# CPF, CNPJ, IE e chave de NF-e que a API ecoa no erro não vão para o log nem para o modelo.
_DOCUMENTO = re.compile(r"[0-9A-Za-z./-]*\d{4,}[0-9A-Za-z./-]*")

CAMINHOS = {
    "consultar_ie": ("GET", "/api/consultar"),
    "consultar_ie_todos_estados": ("GET", "/api/consultar-ie-todos"),
    "consultar_cnpj": ("GET", "/api/consultar-cnpj"),
    "consultar_cnd_estadual": ("GET", "/api/consultar-cnd"),
    "consultar_cndt": ("GET", "/api/consultar-cndt"),
    "consultar_cnd_federal": ("GET", "/api/consultar-cnd-federal"),
    "consultar_crf_fgts": ("GET", "/api/consultar-crf-fgts"),
    "baixar_xml_nfe_sem_certificado": ("POST", "/api/consultar-nfe-xml-sem-certificado"),
    "saldo": ("GET", "/api/saldo"),
}


class ErroDaAPI(Exception):
    """Falha já traduzida para uma mensagem em português, segura para o modelo ler."""

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.status = status


class ClienteFiscalAPI:
    """Um httpx.AsyncClient por chamada: sem estado entre requisições, sem retry."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def chamar(
        self,
        operacao: str,
        chave: str,
        params: dict[str, Any] | None = None,
        corpo: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metodo, caminho = CAMINHOS[operacao]
        headers = {"X-API-Key": chave, "User-Agent": USER_AGENT, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(
                base_url=URL_BASE,
                timeout=TIMEOUT_S,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as http:
                resposta = await http.request(metodo, caminho, params=params, json=corpo, headers=headers)
        except httpx.TimeoutException:
            logger.info("api operacao=%s resultado=timeout", operacao)
            raise ErroDaAPI(textos.MSG_TIMEOUT) from None
        except httpx.HTTPError:
            logger.info("api operacao=%s resultado=falha_de_rede", operacao)
            raise ErroDaAPI(textos.MSG_REDE) from None

        logger.info("api operacao=%s status=%s", operacao, resposta.status_code)
        if resposta.status_code >= 400:
            raise ErroDaAPI(_mensagem_de_erro(resposta), status=resposta.status_code)
        if len(resposta.content) > MAX_BYTES_RESPOSTA:
            raise ErroDaAPI("A resposta da FiscalAPI veio grande demais para devolver por aqui. Use a API REST.")
        try:
            dados = resposta.json()
        except ValueError:
            raise ErroDaAPI(textos.MSG_REDE) from None
        if not isinstance(dados, dict):
            raise ErroDaAPI(textos.MSG_REDE)
        return dados


def _corpo(resposta: httpx.Response) -> dict[str, Any]:
    try:
        dados = resposta.json()
    except ValueError:
        return {}
    return dados if isinstance(dados, dict) else {}


def _detalhe(corpo: dict[str, Any]) -> str:
    """Texto do erro como a API escreveu (`detail` do problem+json, `message` do
    portão de saldo, lista de validação do 422). Curto e sem eco de URL."""
    detalhe = corpo.get("detail") or corpo.get("message") or ""
    if isinstance(detalhe, list):
        partes = [str(item.get("msg", "")) for item in detalhe if isinstance(item, dict)]
        detalhe = "; ".join(p for p in partes if p)
    if not isinstance(detalhe, str):
        return ""
    return _DOCUMENTO.sub("[documento]", detalhe.strip())[:_MAX_DETALHE]


def _segundos(valor: Any) -> int | None:
    try:
        segundos = int(float(valor))
    except (TypeError, ValueError):
        return None
    return segundos if 0 < segundos <= 86_400 else None


def _mensagem_de_erro(resposta: httpx.Response) -> str:
    status = resposta.status_code
    corpo = _corpo(resposta)
    detalhe = _detalhe(corpo)
    if status == 402:
        return textos.MSG_402
    if status in (401, 403):
        if corpo.get("title") == "ACESSO_NEGADO" or corpo.get("error") == "ACESSO_NEGADO":
            return f"A chave não tem acesso a esta consulta ({detalhe or 'acesso negado'})."
        return textos.MSG_CHAVE_RECUSADA
    if status == 429:
        espera = _segundos(resposta.headers.get("retry-after") or corpo.get("retry_after"))
        quando = f" Espere {espera} s e tente de novo." if espera else " Espere um pouco e tente de novo."
        motivo = detalhe or "limite de consultas por minuto do plano"
        return f"A FiscalAPI limitou as chamadas desta conta ({motivo})." + quando
    if status in (400, 422):
        motivo = f": {detalhe}" if detalhe else "."
        return f"A FiscalAPI recusou os parâmetros{motivo} Corrija e tente de novo."
    if status >= 500:
        return textos.MSG_5XX.format(status=status)
    motivo = f": {detalhe}" if detalhe else "."
    return f"A FiscalAPI respondeu HTTP {status}{motivo}"
