"""Textos fixos: custos, cobertura e mensagens.

Valores conferidos no backend da FiscalAPI em 07/11/2026 (tabela de preços por
plano e custo em consultas de cada tipo). Mudou o preço lá, muda aqui.
"""

CHAMADA_PARA_CHAVE = (
    "Para consultar dados reais: crie a chave em app.fiscalapi.com.br (10 consultas grátis de IE/CNPJ por mês)"
)

COMO_CONFIGURAR_CHAVE = (
    "Configure no cliente MCP o header X-API-Key: <sua chave> "
    "(ou Authorization: Bearer <sua chave>). A chave fica em app.fiscalapi.com.br, em Chave API."
)

# Preço de UMA consulta do saldo, por plano (franquia do plano; recarga entre parênteses).
_PRECO_1 = (
    "Lite R$ 0,67; Starter R$ 0,10 (recarga R$ 0,12); Pro R$ 0,065 (recarga R$ 0,07); "
    "Enterprise R$ 0,025 (recarga R$ 0,02)"
)
_PRECO_3 = (
    "Lite R$ 2,01; Starter R$ 0,30 (recarga R$ 0,36); Pro R$ 0,195 (recarga R$ 0,21); "
    "Enterprise R$ 0,075 (recarga R$ 0,06)"
)
_PRECO_NFE_SEM_CERT = (
    "Lite R$ 2,01; Starter R$ 0,30 (recarga R$ 0,36); Pro R$ 0,195 (recarga R$ 0,21); Enterprise R$ 0,05"
)

_COBRANCA = (
    "Erro não é cobrado. Resposta sem inscrição encontrada, sem_certidao ou nao_contribuinte conta como "
    "consulta. Conta sem plano paga o preço da recarga do último plano (R$ 0,12 se nunca assinou)."
)
_GRATIS_IE_CNPJ = (
    "Conta que nunca assinou, com e-mail confirmado e sem recarga, tem 10 consultas grátis por mês de IE "
    "em um estado e de CNPJ."
)

CUSTO_CONSULTA = f"Custo: 1 consulta do saldo ({_PRECO_1}). {_COBRANCA}"
CUSTO_CONSULTA_GRATIS = f"{CUSTO_CONSULTA} {_GRATIS_IE_CNPJ}"
CUSTO_IE_TODOS = f"{CUSTO_CONSULTA} Não entra nas consultas grátis: exige plano ou recarga."
CUSTO_CNPJ = (
    f"Custo: 1 consulta do saldo ({_PRECO_1}); com ao_vivo=true, 3 consultas ({_PRECO_3}). "
    f"{_COBRANCA} {_GRATIS_IE_CNPJ} A consulta ao vivo não entra nas grátis."
)
CUSTO_NFE_SEM_CERT = (
    f"Custo: 3 consultas do saldo (2 no Enterprise): {_PRECO_NFE_SEM_CERT} por chave. "
    "Cobra o XML entregue e também a chave cuja nota não foi encontrada (nao_encontrado); a mesma chave "
    "repetida logo depois de um nao_encontrado, chave inválida e erro não são cobrados. Não entra nas "
    "consultas grátis."
)

LIMITES_DA_API = (
    "Limite por minuto da conta: Lite 5, Starter 20, Pro 60, Enterprise 120 consultas "
    "(conta sem plano: 5). XML de NF-e sem certificado: até 2 consultas simultâneas por conta."
)

UFS = (
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
)

COBERTURA = {
    "inscricao_estadual": {
        "ferramentas": ["consultar_ie", "consultar_ie_todos_estados"],
        "ufs": list(UFS),
        "busca_por": ["CPF", "CNPJ", "IE"],
        "o_que_devolve": (
            "Dados cadastrais de cada inscrição: número, razão social, situação, tipo de IE, endereço, "
            "CNAE principal, regime de apuração e data de início; atividades secundárias sob pedido "
            "(secundarias=true)."
        ),
        "observacoes": [
            "Por CPF em todos os estados menos SP, que busca só por CNPJ ou IE.",
            "consultar_ie_todos_estados procura nos 27 estados numa chamada e conta como 1 consulta "
            "(não entra nas grátis).",
        ],
    },
    "cnpj": {
        "ferramentas": ["consultar_cnpj"],
        "o_que_devolve": (
            "Cadastro público do CNPJ na Receita Federal: razão social, nome fantasia, situação cadastral "
            "e motivo, abertura, matriz ou filial, CNAE principal e secundários, natureza jurídica, "
            "capital social, endereço, telefones, e-mail, quadro societário e opção pelo Simples Nacional "
            "e pelo MEI (da base mensal da Receita Federal). Com ao_vivo=true, consulta a Receita Federal "
            "na hora; nesse modo Simples e MEI voltam vazios."
        ),
    },
    "cnd_estadual": {
        "ferramentas": ["consultar_cnd_estadual"],
        "ufs": list(UFS),
        "busca_por": ["CPF", "CNPJ"],
        "o_que_devolve": (
            "Situação da Certidão Negativa de Débitos estadual (ICMS) na UF: negativa, positiva, "
            "positiva_com_efeitos_de_negativa, nao_contribuinte ou sem_certidao, com emissão, validade "
            "e protocolo."
        ),
        "observacoes": ["Alguns estados respondem nao_contribuinte quando o documento não tem inscrição lá."],
    },
    "certidoes_federais": {
        "ferramentas": ["consultar_cndt", "consultar_cnd_federal", "consultar_crf_fgts"],
        "busca_por": ["CPF", "CNPJ"],
        "o_que_devolve": {
            "cndt": "Certidão Negativa de Débitos Trabalhistas (TST).",
            "cnd_federal": "Certidão de débitos de tributos federais e Dívida Ativa da União (Receita Federal e PGFN).",
            "crf_fgts": "Certificado de Regularidade do FGTS (Caixa).",
        },
    },
    "xml_nfe_sem_certificado": {
        "ferramentas": ["baixar_xml_nfe_sem_certificado"],
        "o_que_devolve": (
            "Cópia para leitura do XML de uma NF-e (modelo 55) a partir da chave de acesso de 44 posições, "
            "sem a assinatura digital. Traz os dados da nota, mas não serve para validar schema nem "
            "assinatura. O XML assinado sai na consulta com certificado, no painel ou na API REST."
        ),
    },
    "sem_chave": {
        "ferramentas": ["validar_inscricao_estadual", "cobertura"],
        "o_que_devolve": "Conferência do formato e do dígito verificador da IE nas 27 UFs, e este resumo.",
    },
    "fora_deste_servidor": (
        "As demais consultas da API (CND de todos os estados de uma vez, XML de NF-e com certificado, "
        "consulta em massa e outras) estão na API REST: https://docs.fiscalapi.com.br"
    ),
    "limites": LIMITES_DA_API,
}

MSG_402 = (
    "O saldo não cobre esta consulta: acabaram as consultas do mês (as 10 grátis de IE/CNPJ ou a franquia do "
    "plano) e não há recarga que pague. Assine ou recarregue em app.fiscalapi.com.br para continuar."
)
MSG_CHAVE_RECUSADA = "A FiscalAPI recusou a chave: ausente, inválida ou revogada. " + COMO_CONFIGURAR_CHAVE
MSG_5XX = (
    "A FiscalAPI não conseguiu concluir a consulta agora (HTTP {status}). "
    "Erro não é cobrado; tente de novo em alguns minutos."
)
MSG_TIMEOUT = (
    "A consulta passou de 80 segundos sem resposta. Se a FiscalAPI concluir depois, ela pode ser cobrada: "
    "confira o saldo (ferramenta saldo) antes de repetir."
)
MSG_REDE = "Não foi possível falar com a FiscalAPI agora. Tente de novo em alguns minutos."
