import json

import pytest

from fiscalapi_mcp import servidor
from tests.ajuda import dados, texto

pytestmark = pytest.mark.anyio

PAGAS = {
    "consultar_ie",
    "consultar_ie_todos_estados",
    "consultar_cnpj",
    "consultar_cnd_estadual",
    "consultar_cndt",
    "consultar_cnd_federal",
    "consultar_crf_fgts",
    "baixar_xml_nfe_sem_certificado",
}
SEM_CHAVE = {"validar_inscricao_estadual", "cobertura"}
CHAVE = "fapi_chave_de_teste_123"


async def test_tools_list_tem_todas_as_ferramentas(cliente):
    resultado = await cliente.list_tools()
    por_nome = {ferramenta.name: ferramenta for ferramenta in resultado.tools}

    assert set(por_nome) == PAGAS | SEM_CHAVE | {"saldo"}
    for nome in SEM_CHAVE:
        assert por_nome[nome].annotations is not None
        assert por_nome[nome].annotations.read_only_hint is True
    for nome in PAGAS | {"saldo"}:
        anotacoes = por_nome[nome].annotations
        assert anotacoes is None or not anotacoes.read_only_hint
    for nome in PAGAS:
        assert "confirmo_custo" in por_nome[nome].input_schema["properties"]
        assert "R$" in (por_nome[nome].description or "")


async def test_validar_ie_valida(cliente, api_falsa):
    resultado = await cliente.call_tool("validar_inscricao_estadual", {"uf": "SP", "ie": "110.042.490.114"})

    assert not resultado.is_error
    corpo = dados(resultado)
    assert corpo["valida"] is True
    assert corpo["formatada"] == "110.042.490.114"
    assert "10 consultas grátis" in corpo["proximo_passo"]
    assert api_falsa.requisicoes == []


async def test_validar_ie_invalida(cliente, api_falsa):
    resultado = await cliente.call_tool("validar_inscricao_estadual", {"uf": "MG", "ie": "0623079040082"})

    assert not resultado.is_error
    corpo = dados(resultado)
    assert corpo["valida"] is False
    assert "dígito" in corpo["motivo"]
    assert api_falsa.requisicoes == []


async def test_cobertura_nao_chama_a_api(cliente, api_falsa):
    resultado = await cliente.call_tool("cobertura", {})

    assert not resultado.is_error
    corpo = dados(resultado)
    assert len(corpo["inscricao_estadual"]["ufs"]) == 27
    assert "app.fiscalapi.com.br" in corpo["proximo_passo"]
    assert api_falsa.requisicoes == []


async def test_paga_sem_confirmo_custo_nao_chama_a_api(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})

    resultado = await cliente.call_tool("consultar_ie", {"uf": "MT", "cnpj": "12.345.678/0001-95"})

    assert resultado.is_error
    assert "confirmo_custo" in texto(resultado)
    assert "R$" in texto(resultado)
    assert api_falsa.requisicoes == []


async def test_paga_com_confirmo_custo_false_nao_chama_a_api(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})

    resultado = await cliente.call_tool("baixar_xml_nfe_sem_certificado", {"chave": "1" * 44, "confirmo_custo": False})

    assert resultado.is_error
    assert api_falsa.requisicoes == []


async def test_paga_sem_chave_explica_como_configurar(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({})

    resultado = await cliente.call_tool("consultar_cnpj", {"cnpj": "12345678000195", "confirmo_custo": True})

    assert resultado.is_error
    assert "X-API-Key" in texto(resultado)
    assert api_falsa.requisicoes == []


async def test_bearer_vira_x_api_key(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"Authorization": f"Bearer {CHAVE}"})
    api_falsa.corpo = {"request_id": "r1", "cnpj": "12345678000195", "result": {"razao_social": "EXEMPLO LTDA"}}

    resultado = await cliente.call_tool("consultar_cnpj", {"cnpj": "12.345.678/0001-95", "confirmo_custo": True})

    assert not resultado.is_error
    assert dados(resultado)["result"]["razao_social"] == "EXEMPLO LTDA"
    [requisicao] = api_falsa.requisicoes
    assert requisicao.headers["x-api-key"] == CHAVE
    assert "authorization" not in requisicao.headers
    assert requisicao.headers["user-agent"].startswith("fiscalapi-mcp/")
    assert requisicao.url.host == "api.fiscalapi.com.br"
    assert requisicao.url.path == "/api/consultar-cnpj"
    assert dict(requisicao.url.params) == {"cnpj": "12345678000195"}


async def test_x_api_key_tem_precedencia_sobre_bearer():
    headers = {"X-API-Key": "fapi_da_x_api_key_01", "Authorization": "Bearer fapi_do_bearer_000001"}
    assert servidor.chave_dos_headers(headers) == "fapi_da_x_api_key_01"


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer "},
        {"X-API-Key": "tem espaco"},
        {"X-API-Key": "x" * 300},
        {"X-API-Key": "fapi_chave_com_acentuação"},
        {"X-API-Key": "curta"},
    ],
)
async def test_chave_ausente_ou_malformada_vira_none(headers):
    assert servidor.chave_dos_headers(headers) is None


async def test_402_vira_mensagem_clara(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.status = 402
    api_falsa.corpo = {"error": "LIMITE_ATINGIDO", "message": "Seu saldo não cobre esta consulta."}

    resultado = await cliente.call_tool("consultar_ie_todos_estados", {"cpf": "123.456.789-09", "confirmo_custo": True})

    assert resultado.is_error
    mensagem = texto(resultado)
    assert "acabaram as consultas do mês" in mensagem.lower()
    assert "10 grátis de IE/CNPJ" in mensagem
    assert "app.fiscalapi.com.br" in mensagem
    assert CHAVE not in mensagem


async def test_403_nao_ecoa_a_chave(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.status = 403
    api_falsa.corpo = {"title": "API_KEY_ERROR", "detail": "Invalid API key", "status": 403}

    resultado = await cliente.call_tool("consultar_cndt", {"cnpj": "12345678000195", "confirmo_custo": True})

    assert resultado.is_error
    assert "recusou a chave" in texto(resultado)
    assert CHAVE not in texto(resultado)


async def test_teto_de_consultas_pagas_por_hora(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    argumentos = {"uf": "MT", "cnpj": "12345678000195", "confirmo_custo": True}

    for _ in range(servidor.TETO_PAGAS_POR_HORA):
        resultado = await cliente.call_tool("consultar_cnd_estadual", argumentos)
        assert not resultado.is_error

    resultado = await cliente.call_tool("consultar_cnd_estadual", argumentos)

    assert resultado.is_error
    assert str(servidor.TETO_PAGAS_POR_HORA) in texto(resultado)
    assert len(api_falsa.requisicoes) == servidor.TETO_PAGAS_POR_HORA


async def test_teto_e_por_chave(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    for _ in range(servidor.TETO_PAGAS_POR_HORA):
        await cliente.call_tool("consultar_crf_fgts", {"cnpj": "12345678000195", "confirmo_custo": True})

    headers_do_cliente({"X-API-Key": "fapi_outra_chave"})
    resultado = await cliente.call_tool("consultar_crf_fgts", {"cnpj": "12345678000195", "confirmo_custo": True})

    assert not resultado.is_error


async def test_nfe_sem_certificado_manda_so_a_chave_no_corpo(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    chave_nfe = "35" + "1" * 42
    api_falsa.corpo = {
        "request_id": "r1",
        "total": 1,
        "com_dado": 1,
        "creditos_cobrados": 3,
        "resultados": [{"chave": chave_nfe, "status": "ok", "xml": "<nfeProc/>", "assinado": False}],
    }

    resultado = await cliente.call_tool(
        "baixar_xml_nfe_sem_certificado", {"chave": f"{chave_nfe[:4]} {chave_nfe[4:]}", "confirmo_custo": True}
    )

    assert not resultado.is_error
    [requisicao] = api_falsa.requisicoes
    assert requisicao.method == "POST"
    assert requisicao.url.path == "/api/consultar-nfe-xml-sem-certificado"
    assert json.loads(requisicao.content) == {"chave": chave_nfe}


async def test_um_documento_so(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})

    resultado = await cliente.call_tool(
        "consultar_ie", {"uf": "MT", "cpf": "12345678909", "cnpj": "12345678000195", "confirmo_custo": True}
    )

    assert resultado.is_error
    assert api_falsa.requisicoes == []


async def test_pdf_base64_nao_vai_para_o_modelo(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.corpo = {
        "request_id": "r1",
        "result": {"tipo": "cndt", "status": "negativa", "pdf_base64": "JVBERi0xLjQK" * 1000},
    }

    resultado = await cliente.call_tool("consultar_cndt", {"cpf": "12345678909", "confirmo_custo": True})

    assert not resultado.is_error
    certidao = dados(resultado)["result"]
    assert certidao["pdf_base64"] == ""
    assert "pdf_omitido" in certidao
    assert "JVBERi0" not in texto(resultado)


async def test_saldo_nao_pede_confirmo_custo(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"Authorization": f"bearer {CHAVE}"})
    api_falsa.corpo = {"consultas_restantes": 1500, "notas_restantes": 500}

    resultado = await cliente.call_tool("saldo", {})

    assert not resultado.is_error
    assert dados(resultado) == {"consultas_restantes": 1500, "notas_restantes": 500}
    [requisicao] = api_falsa.requisicoes
    assert requisicao.url.path == "/api/saldo"
    assert requisicao.headers["x-api-key"] == CHAVE


async def test_chave_recusada_nao_ocupa_o_teto(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.status = 403
    api_falsa.corpo = {"title": "API_KEY_ERROR", "detail": "Invalid API key", "status": 403}

    for _ in range(servidor.TETO_PAGAS_POR_HORA + 1):
        resultado = await cliente.call_tool("consultar_cndt", {"cnpj": "12345678000195", "confirmo_custo": True})
        assert "recusou a chave" in texto(resultado)

    assert len(api_falsa.requisicoes) == servidor.TETO_PAGAS_POR_HORA + 1


async def test_erro_da_api_nao_ecoa_documento(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.status = 400
    api_falsa.corpo = {"title": "DOCUMENTO_INVALIDO", "detail": "Documento inválido: 12345678909", "status": 400}

    resultado = await cliente.call_tool("consultar_cndt", {"cpf": "12345678909", "confirmo_custo": True})

    assert resultado.is_error
    assert "12345678909" not in texto(resultado)
    assert "Documento inválido" in texto(resultado)


async def test_429_traz_o_motivo_e_a_espera(cliente, api_falsa, headers_do_cliente):
    headers_do_cliente({"X-API-Key": CHAVE})
    api_falsa.status = 429
    api_falsa.corpo = {"error": "RATE_LIMIT_EXCEEDED", "message": "Limite de requisicoes do plano excedido."}
    api_falsa.headers = {"Retry-After": "12"}

    resultado = await cliente.call_tool("consultar_cnpj", {"cnpj": "12345678000195", "confirmo_custo": True})

    assert resultado.is_error
    assert "Limite de requisicoes do plano excedido." in texto(resultado)
    assert "12 s" in texto(resultado)
