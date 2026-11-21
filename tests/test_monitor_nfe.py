import json

import pytest

from fiscalapi_mcp import servidor
from tests.ajuda import dados, texto

pytestmark = pytest.mark.anyio

CHAVE = "fapi_chave_de_teste_123"
CHAVE_NFE = "35261111222333000181550010000001231123456787"


async def test_monitorar_sem_confirmo_custo_nao_chama_a_api(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})

    resultado = await cliente.call_tool("monitorar_chaves_nfe", {"chaves": [CHAVE_NFE]})

    assert resultado.is_error
    assert "confirmo_custo" in texto(resultado)
    assert "R$ 0,015" in texto(resultado)
    assert api_falsa.requisicoes == []


async def test_monitorar_manda_chaves_limpas_prazo_e_status(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.corpo = {"resultados": [], "aceitas": 2, "valor_cobrado": "0,06"}

    resultado = await cliente.call_tool(
        "monitorar_chaves_nfe",
        {
            "chaves": [f"NFe {CHAVE_NFE[:4]}.{CHAVE_NFE[4:]}", CHAVE_NFE],
            "prazo_dias": 30,
            "status_conhecido": "cancelada",
            "confirmo_custo": True,
        },
    )

    assert not resultado.is_error
    assert dados(resultado)["valor_cobrado"] == "0,06"
    [requisicao] = api_falsa.requisicoes
    assert requisicao.method == "POST"
    assert requisicao.url.path == "/api/monitor-nfe/chaves"
    assert requisicao.headers["X-API-Key"] == CHAVE
    assert json.loads(requisicao.content) == {
        "chaves": [
            {"chave": CHAVE_NFE, "status_conhecido": "cancelada"},
            {"chave": CHAVE_NFE, "status_conhecido": "cancelada"},
        ],
        "prazo_dias": 30,
    }


async def test_monitorar_chave_com_tamanho_errado_nao_chama_a_api(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})

    resultado = await cliente.call_tool("monitorar_chaves_nfe", {"chaves": ["123"], "confirmo_custo": True})

    assert resultado.is_error
    assert "44 dígitos" in texto(resultado)
    assert api_falsa.requisicoes == []


async def test_listar_nao_pede_confirmo_custo_e_manda_filtros(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.corpo = {"itens": [], "proximo_cursor": None}

    resultado = await cliente.call_tool(
        "listar_chaves_monitoradas_nfe", {"status": "cancelada", "ativo": False, "cursor": "abc", "limite": 10}
    )

    assert not resultado.is_error
    [requisicao] = api_falsa.requisicoes
    assert requisicao.method == "GET"
    assert requisicao.url.path == "/api/monitor-nfe/chaves"
    assert dict(requisicao.url.params) == {"limite": "10", "status": "cancelada", "ativo": "false", "cursor": "abc"}


async def test_listar_sem_chave_explica_como_configurar(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({})

    resultado = await cliente.call_tool("listar_chaves_monitoradas_nfe", {})

    assert resultado.is_error
    assert "X-API-Key" in texto(resultado)
    assert api_falsa.requisicoes == []


async def test_consultar_chave_vai_no_caminho_so_com_digitos(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.corpo = {"chave": CHAVE_NFE, "status": "cancelada", "eventos": [], "entregas_que_falharam": []}

    resultado = await cliente.call_tool(
        "consultar_chave_monitorada_nfe", {"chave": CHAVE_NFE[:20] + " " + CHAVE_NFE[20:]}
    )

    assert not resultado.is_error
    [requisicao] = api_falsa.requisicoes
    assert requisicao.url.path == f"/api/monitor-nfe/chaves/{CHAVE_NFE}"
    assert requisicao.url.query == b""


async def test_consultar_chave_nao_aceita_caminho_estranho(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})

    resultado = await cliente.call_tool("consultar_chave_monitorada_nfe", {"chave": "../../api/saldo"})

    assert resultado.is_error
    assert api_falsa.requisicoes == []


async def test_cliente_da_api_recusa_chave_nfe_fora_do_formato():
    with pytest.raises(servidor.ErroDaAPI):
        await servidor.cliente_api.chamar("consultar_chave_monitorada_nfe", CHAVE, chave_nfe="1" * 43 + "/")


async def test_404_do_monitor_vira_mensagem(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.status = 404
    api_falsa.corpo = {"title": "MONITORAMENTO_NAO_ENCONTRADO", "detail": "Esta chave não está no monitor da conta."}

    resultado = await cliente.call_tool("consultar_chave_monitorada_nfe", {"chave": CHAVE_NFE})

    assert resultado.is_error
    assert "não está no monitor" in texto(resultado)


async def test_remover_manda_a_lista_no_corpo(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.corpo = {"removidas": 1, "nao_encontradas": []}

    resultado = await cliente.call_tool("remover_chaves_monitoradas_nfe", {"chaves": [CHAVE_NFE]})

    assert not resultado.is_error
    [requisicao] = api_falsa.requisicoes
    assert (requisicao.method, requisicao.url.path) == ("POST", "/api/monitor-nfe/chaves/remover")
    assert json.loads(requisicao.content) == {"chaves": [CHAVE_NFE]}


async def test_cobertura_lista_o_monitor(cliente, api_falsa):
    corpo = dados(await cliente.call_tool("cobertura", {}))

    assert "monitorar_chaves_nfe" in corpo["monitor_nfe"]["ferramentas"]
    assert len(corpo["monitor_nfe"]["ufs"]) == 27
    assert "webhook do monitor" in corpo["fora_deste_servidor"]
