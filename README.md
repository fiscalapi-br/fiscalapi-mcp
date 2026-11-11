# FiscalAPI MCP

Servidor [MCP](https://modelcontextprotocol.io) da [FiscalAPI](https://fiscalapi.com.br). Deixa um agente de IA (Claude, Cursor, VS Code, ChatGPT) consultar Inscrição Estadual nos 27 estados, CNPJ, Simples Nacional, NFS-e por chave, CND estadual, CNDT, CND Federal, CRF/FGTS e baixar uma cópia para leitura do XML de NF-e pela chave de acesso (sem a assinatura digital), usando a sua conta da FiscalAPI.

**Endereço:** `https://mcp.fiscalapi.com.br/mcp` (Streamable HTTP)

Duas ferramentas funcionam sem chave e não cobram nada: `validar_inscricao_estadual` e `cobertura`. As outras usam a sua chave da FiscalAPI e cobram do saldo da conta, como a API REST.

Para consultar dados reais: crie a chave em [app.fiscalapi.com.br](https://app.fiscalapi.com.br) (10 consultas grátis por mês).

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

Preço de 1 consulta do saldo por plano (franquia do plano; recarga entre parênteses): Lite R$ 0,67; Starter R$ 0,10 (R$ 0,12); Pro R$ 0,065 (R$ 0,07); Enterprise R$ 0,025 (R$ 0,02). Consulta que termina em erro não é cobrada; resposta sem inscrição encontrada, `sem_certidao` ou `nao_contribuinte` conta como consulta.

| Ferramenta | O que faz | Custo |
|---|---|---|
| `validar_inscricao_estadual` | Confere formato e dígito verificador da IE na UF. Não diz se a IE existe ou está ativa. | Sem chave, sem custo |
| `cobertura` | O que a FiscalAPI consulta, por produto e UF, e os limites da API. | Sem chave, sem custo |
| `consultar_ie` | Inscrição Estadual numa UF, por CPF, CNPJ ou IE (por CPF, todos os estados menos SP). | 1 consulta |
| `consultar_ie_todos_estados` | Inscrições nos 27 estados numa chamada, por CPF, CNPJ ou IE. | 1 consulta (fora das grátis) |
| `consultar_cnpj` | Cadastro público do CNPJ na Receita Federal, com Simples e MEI. `ao_vivo=true` consulta na hora. | 1 consulta; ao vivo, 3 |
| `consultar_simples_nacional` | Situação do CNPJ no Simples Nacional, SIMEI e regimes IBS/CBS. | 1 consulta |
| `consultar_nfse` | NFS-e do padrão nacional pela chave de 50 dígitos, sem certificado. O PDF do DANFSe fica na API REST. | 3 consultas (2 no Enterprise); mínimo R$ 0,05; só a nota entregue |
| `consultar_cnd_estadual` | CND estadual (ICMS) de CPF ou CNPJ na UF. | 1 consulta |
| `consultar_cndt` | Certidão Negativa de Débitos Trabalhistas. | 1 consulta |
| `consultar_cnd_federal` | Certidão de tributos federais e Dívida Ativa da União. | 1 consulta |
| `consultar_crf_fgts` | Certificado de Regularidade do FGTS. | 1 consulta |
| `baixar_xml_nfe_sem_certificado` | Cópia para leitura do XML de uma NF-e (modelo 55) pela chave de acesso, sem a assinatura digital. | 3 consultas (2 no Enterprise); mínimo R$ 0,05 (fora das grátis) |
| `saldo` | Quanto o saldo ainda rende, em consultas e em notas. | Não consome consulta |

Conta que nunca assinou, com e-mail confirmado e sem recarga, tem 10 consultas grátis por mês em qualquer consulta avulsa (IE em um estado, CNPJ inclusive ao vivo, Simples Nacional, NFS-e, CND estadual, CNDT, CND Federal e CRF/FGTS), somadas com as do painel. Cada consulta entregue gasta 1 das 10, mesmo as que custam 3 num plano; erro não gasta. Ficam fora a IE em todos os estados e o XML de NF-e sem certificado. As grátis acabam na primeira assinatura e não voltam depois de cancelar. O XML de NF-e sem certificado cobra também a chave cuja nota não foi encontrada (menos a mesma chave repetida logo depois) e não entra nas grátis.

O PDF das certidões não volta pelo MCP (é grande demais para o modelo). Na [API REST](https://docs.fiscalapi.com.br) ele vem no campo `pdf_base64`; repetir a consulta lá cobra de novo.

### Freios

- Toda ferramenta que cobra tem o parâmetro `confirmo_custo`. Sem `confirmo_custo=true`, ela só explica o custo e não consulta nada. O agente deve mostrar o custo e esperar o seu OK.
- Este servidor aceita até 30 consultas pagas por hora por chave (chave recusada pela API não conta). Para volume, use a API REST direto.
- Valem também os limites da sua conta: por minuto, Lite 5, Starter 20, Pro 60 e Enterprise 120 consultas; XML de NF-e sem certificado, 2 consultas simultâneas.

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
