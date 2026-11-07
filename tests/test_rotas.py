import httpx
import pytest

from fiscalapi_mcp import __version__, servidor


def _cliente_http() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=servidor.app), base_url="http://localhost")


@pytest.mark.anyio
async def test_raiz_devolve_nome_versao_e_documentacao():
    async with _cliente_http() as http:
        resposta = await http.get("/")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "fiscalapi-mcp"
    assert corpo["versao"] == __version__
    assert corpo["mcp"] == "https://mcp.fiscalapi.com.br/mcp"
    assert corpo["documentacao"].startswith("https://")


@pytest.mark.anyio
async def test_health():
    async with _cliente_http() as http:
        resposta = await http.get("/health")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_hosts_permitidos_inclui_dominio_do_railway(monkeypatch):
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "fiscalapi-mcp-production.up.railway.app")
    hosts = servidor.hosts_permitidos()
    assert "mcp.fiscalapi.com.br" in hosts
    assert "fiscalapi-mcp-production.up.railway.app" in hosts
    assert "localhost:*" in hosts


def test_hosts_permitidos_ignora_dominio_estranho(monkeypatch):
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "evil.example.com")
    assert "evil.example.com" not in servidor.hosts_permitidos()


def test_hosts_extra_mantem_o_dominio_do_railway_com_dominio_proprio(monkeypatch):
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "mcp.fiscalapi.com.br")
    monkeypatch.setenv("MCP_HOSTS_EXTRA", "mcp-production-e9f89.up.railway.app, evil.example.com")
    hosts = servidor.hosts_permitidos()
    assert "mcp-production-e9f89.up.railway.app" in hosts
    assert "evil.example.com" not in hosts
    assert hosts.count("mcp.fiscalapi.com.br") == 1
