# FiscalAPI MCP

Servidor MCP para consultar inscrição estadual (SINTEGRA) nos 27 estados, CNPJ na Receita Federal e certidões (CND estadual, CND Federal, CNDT, CRF/FGTS) dentro do Claude, do Cursor, do VS Code e do ChatGPT. É o servidor [MCP](https://modelcontextprotocol.io) oficial da [FiscalAPI](https://fiscalapi.com.br).

Também consulta Simples Nacional e NFS-e pela chave, baixa uma cópia para leitura do XML de NF-e pela chave de acesso (sem a assinatura digital) e coloca chaves de NF-e no Monitor de NF-e, usando a sua conta da FiscalAPI.

**Endereço:** `https://mcp.fiscalapi.com.br/mcp` (Streamable HTTP). No registro oficial de servidores MCP: `io.github.fiscalapi-br/fiscalapi-mcp`.

**Documentação:** [docs.fiscalapi.com.br/docs/getting-started/mcp](https://docs.fiscalapi.com.br/docs/getting-started/mcp)

Duas ferramentas funcionam sem chave e não cobram nada: `validar_inscricao_estadual` e `cobertura`. As outras usam a sua chave da FiscalAPI e cobram do saldo da conta, como a API REST.

Para consultar dados reais: crie a chave em [app.fiscalapi.com.br](https://app.fiscalapi.com.br) e tenha plano ou créditos extras (planos a partir de R$ 50 por mês).

## Configurar

A chave vai no header `X-API-Key` (também aceita `Authorization: Bearer <chave>`). Troque `fapi_sua_chave` pela sua.

### Claude Code

```bash
claude mcp add --transport http fiscalapi https://mcp.fiscalapi.com.br/mcp --header "X-API-Key: fapi_sua_chave"
```

Para não deixar a chave no histórico do terminal, guarde-a numa variável de ambiente e use `--header "X-API-Key: $FISCALAPI_API_KEY"`.

### Cursor

`.cursor/mcp.json` (no projeto) ou `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "fiscalapi": {
      "url": "https://mcp.fiscalapi.com.br/mcp",
      "headers": {
        "X-API-Key": "${env:FISCALAPI_API_KEY}"
      }
    }
  }
}
```

### VS Code

`.vscode/mcp.json`. O VS Code pede a chave na primeira vez e guarda de forma segura:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "fiscalapi-chave",
      "description": "Chave da FiscalAPI",
      "password": true
    }
  ],
  "servers": {
    "fiscalapi": {
      "type": "http",
      "url": "https://mcp.fiscalapi.com.br/mcp",
      "headers": {
        "X-API-Key": "${input:fiscalapi-chave}"
      }
    }
  }
}
```

### ChatGPT (modo desenvolvedor)

Crie um conector com a URL `https://mcp.fiscalapi.com.br/mcp`, sem autenticação. Os conectores do ChatGPT aceitam só OAuth ou nenhuma autenticação, não uma chave de API em header, então por lá funcionam só as ferramentas sem chave (`validar_inscricao_estadual` e `cobertura`). Para as consultas pagas, use um cliente que envia o header, como os de cima.

## Ferramentas

O saldo da conta é em créditos (1 crédito = R$ 1), e cada consulta desconta o preço dela. Preço de 1 consulta por plano, com os créditos do plano (com créditos extras entre parênteses): Starter R$ 0,10 (R$ 0,12); Pro R$ 0,065 (R$ 0,085); Enterprise R$ 0,025 (R$ 0,035). Como funcionam os créditos: https://fiscalapi.com.br/creditos/ . Consulta que termina em erro não é cobrada; resposta sem inscrição encontrada, `sem_certidao` ou `nao_contribuinte` conta como consulta.

| Ferramenta | O que faz | Custo |
|---|---|---|
| `validar_inscricao_estadual` | Confere formato e dígito verificador da IE na UF. Não diz se a IE existe ou está ativa. | Sem chave, sem custo |
| `cobertura` | O que a FiscalAPI consulta, por produto e UF, e os limites da API. | Sem chave, sem custo |
| `consultar_ie` | Inscrição Estadual numa UF, por CPF, CNPJ ou IE (por CPF, todos os estados menos SP). | 1 consulta |
| `consultar_ie_todos_estados` | Inscrições nos 27 estados numa chamada, por CPF, CNPJ ou IE. | 1 consulta |
| `consultar_cnpj` | Cadastro público do CNPJ na Receita Federal, com Simples e MEI. `ao_vivo=true` consulta na hora. | 1 consulta; ao vivo, R$ 0,30 (Starter), R$ 0,195 (Pro) ou R$ 0,075 (Enterprise) |
| `consultar_simples_nacional` | Situação do CNPJ no Simples Nacional, SIMEI e regimes IBS/CBS. | 1 consulta |
| `consultar_nfse` | NFS-e do padrão nacional pela chave de 50 dígitos, sem certificado. O PDF do DANFSe fica na API REST. | R$ 0,30 (Starter), R$ 0,195 (Pro) ou R$ 0,05 (Enterprise) por nota; só a nota entregue |
| `consultar_cnd_estadual` | CND estadual (ICMS) de CPF ou CNPJ na UF. | 1 consulta |
| `consultar_cndt` | Certidão Negativa de Débitos Trabalhistas. | 1 consulta |
| `consultar_cnd_federal` | Certidão de tributos federais e Dívida Ativa da União (CPF exige `data_nascimento`). | 1 consulta |
| `consultar_crf_fgts` | Certificado de Regularidade do FGTS. | 1 consulta |
| `baixar_xml_nfe_sem_certificado` | Cópia para leitura do XML de uma NF-e (modelo 55) pela chave de acesso, sem a assinatura digital. | R$ 0,30 (Starter), R$ 0,195 (Pro) ou R$ 0,05 (Enterprise) por chave |
| `monitorar_chaves_nfe` | Coloca até 1.000 chaves de NF-e no Monitor: a FiscalAPI acompanha cada nota na SEFAZ por até 180 dias e avisa no webhook da conta quando ela é cancelada, denegada ou recebe um evento. | R$ 0,03 (Starter), R$ 0,02 (Pro) ou R$ 0,015 (Enterprise) por chave aceita, uma vez; chave já monitorada ou inválida não cobra |
| `listar_chaves_monitoradas_nfe` | Chaves do monitor com situação, fim previsto, próxima verificação e avisos que falharam (paginada por cursor). | Não cobra |
| `consultar_chave_monitorada_nfe` | Situação, eventos registrados e próxima verificação de uma chave do monitor. | Não cobra |
| `remover_chaves_monitoradas_nfe` | Para de monitorar as chaves (sem estorno; monitorar de novo cobra outra vez). | Não cobra |
| `saldo` | Saldo em créditos (do plano, extras, guardados e disponível) e quanto ele ainda rende, em consultas e em notas. | Não consome consulta |

Pelo MCP toda consulta pede plano ou créditos extras, a partir de R$ 50 por mês. As 10 consultas grátis do mês são só no painel (app.fiscalapi.com.br). O XML de NF-e sem certificado cobra também a chave cuja nota não foi encontrada (menos a mesma chave repetida logo depois).

O XML de NF-e e de CT-e com certificado e o DIFAL de saída não existem no MCP: o certificado e a senha passariam pelo contexto do modelo. Use a [API REST](https://docs.fiscalapi.com.br) ou o painel.

A emissão de NFS-e Nacional também não existe no MCP, pelo mesmo motivo: a nota é assinada com o certificado A1 da empresa, que não pode passar pelo modelo. Emita pela [API REST](https://docs.fiscalapi.com.br/docs/emissao-nfse/visao-geral) ou pelos SDKs ([Python](https://github.com/fiscalapi-br/fiscalapi-python), [Node.js](https://github.com/fiscalapi-br/fiscalapi-node), [PHP](https://github.com/fiscalapi-br/fiscalapi-php)). A ferramenta `cobertura` explica isso ao agente.

O webhook do Monitor de NF-e (URL e segredo da assinatura) também fica fora do MCP: o segredo passaria pelo contexto do modelo. Cadastre pela API REST (`PUT /api/monitor-nfe/webhook`); sem webhook, o monitor funciona e o agente acompanha pela listagem.

O PDF das certidões não volta pelo MCP (é grande demais para o modelo). Na [API REST](https://docs.fiscalapi.com.br) ele vem no campo `pdf_base64`; repetir a consulta lá cobra de novo.

### Freios

- Toda ferramenta que cobra tem o parâmetro `confirmo_custo`. Sem `confirmo_custo=true`, ela só explica o custo e não consulta nada. O agente deve mostrar o custo e esperar o seu OK.
- Este servidor aceita até 30 consultas pagas por hora por chave (chave recusada pela API não conta). Para volume, use a API REST direto.
- Valem também os limites da sua conta: por minuto, Starter 20, Pro 60 e Enterprise 120 consultas (conta sem plano: 5); XML de NF-e sem certificado, 2 consultas simultâneas.

## Segurança

- A chave só é repassada à API da FiscalAPI (`https://api.fiscalapi.com.br`) no header `X-API-Key`, a cada chamada. O servidor não tem banco de dados, não registra headers e não guarda a chave: para contar o teto por hora, mantém em memória só um hash (SHA-256) dela, descartado depois que a janela de 1 hora passa (ou quando a chave é recusada pela API).
- O servidor só fala com `api.fiscalapi.com.br`; os caminhos são fixos no código e o que você informa vai como parâmetro.
- O código está aqui, com licença MIT.

## Desenvolvimento

Requer [uv](https://docs.astral.sh/uv/) e Python 3.12.

```bash
uv sync
uv run ruff check .
uv run pytest -q
uv run python -m fiscalapi_mcp   # sobe em http://localhost:8000/mcp (porta em PORT)
```

Os testes não chamam a API de verdade: as respostas são simuladas.

## Licença

MIT. Veja [LICENSE](LICENSE).
