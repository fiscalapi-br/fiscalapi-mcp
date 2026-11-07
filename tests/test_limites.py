from fiscalapi_mcp.limites import JanelaDeslizante, hash_da_chave


def test_janela_bloqueia_acima_do_limite():
    janela = JanelaDeslizante(limite=2, janela_s=60)
    assert janela.tentar("a") == 0
    assert janela.tentar("a") == 0
    assert janela.tentar("a") > 0
    assert janela.tentar("b") == 0


def test_hash_nao_guarda_a_chave():
    assert hash_da_chave("fapi_x") != "fapi_x"
    assert len(hash_da_chave("fapi_x")) == 64
