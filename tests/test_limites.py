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


def test_desfazer_devolve_a_vaga_e_esquece_o_identificador():
    janela = JanelaDeslizante(limite=1, janela_s=60)
    assert janela.tentar("a") == 0
    janela.desfazer("a")
    assert janela.tentar("a") == 0


def test_teto_de_identificadores_descarta_o_mais_antigo():
    janela = JanelaDeslizante(limite=1, janela_s=60, max_identificadores=2)
    janela.tentar("a")
    janela.tentar("b")
    janela.tentar("c")
    assert janela.tentar("a") == 0
