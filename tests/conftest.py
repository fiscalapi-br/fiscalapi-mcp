from collections.abc import Callable, Mapping
from typing import Any

import httpx
import pytest
from mcp import Client

from fiscalapi_mcp import servidor
from fiscalapi_mcp.api import ClienteFiscalAPI
from fiscalapi_mcp.limites import JanelaDeslizante


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class ApiFalsa:
    """Faz o papel de api.fiscalapi.com.br e guarda cada requisição recebida."""

    def __init__(self) -> None:
        self.requisicoes: list[httpx.Request] = []
        self.status = 200
        self.corpo: Any = {"request_id": "teste", "ok": True}
        self.headers: dict[str, str] = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requisicoes.append(request)
        return httpx.Response(self.status, json=self.corpo, headers=self.headers)


@pytest.fixture
def api_falsa(monkeypatch: pytest.MonkeyPatch) -> ApiFalsa:
    falsa = ApiFalsa()
    monkeypatch.setattr(servidor, "cliente_api", ClienteFiscalAPI(transport=httpx.MockTransport(falsa)))
    monkeypatch.setattr(servidor, "TETO_PAGO", JanelaDeslizante(servidor.TETO_PAGAS_POR_HORA, 3600))
    monkeypatch.setattr(servidor, "LIMITE_SEM_CHAVE", JanelaDeslizante(servidor.LIMITE_SEM_CHAVE_POR_MINUTO, 60))
    monkeypatch.setattr(servidor, "LIMITE_COM_CHAVE", JanelaDeslizante(servidor.LIMITE_COM_CHAVE_POR_MINUTO, 60))
    return falsa


@pytest.fixture
def headers_do_cliente(monkeypatch: pytest.MonkeyPatch) -> Callable[[Mapping[str, str]], None]:
    """Simula os headers HTTP que o cliente MCP mandou (o cliente em memória não tem HTTP)."""

    def definir(headers: Mapping[str, str]) -> None:
        monkeypatch.setattr(servidor, "_headers_da_requisicao", lambda ctx: headers)

    return definir


@pytest.fixture
async def cliente():
    async with Client(servidor.mcp, raise_exceptions=True) as conectado:
        yield conectado
