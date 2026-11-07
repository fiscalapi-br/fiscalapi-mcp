---
name: fiscalapi
description: Use para consultar dados fiscais brasileiros pela API REST da FiscalAPI (api.fiscalapi.com.br) — Inscrição Estadual nos 27 estados por CPF, CNPJ ou IE, cadastro de CNPJ, CND estadual, CNDT, CND Federal, CRF/FGTS, XML de NF-e pela chave de acesso e saldo da conta. Cada consulta cobra do saldo do usuário; confirme o custo antes.
---

# FiscalAPI pela API REST

Base: `https://api.fiscalapi.com.br`. Autenticação: header `X-API-Key: <chave>` em toda chamada. Leia a chave de uma variável de ambiente (ex.: `FISCALAPI_API_KEY`); nunca a escreva em código, log ou resposta. A chave é criada em app.fiscalapi.com.br, em Chave API.

Documentação completa: https://docs.fiscalapi.com.br

## Antes de chamar

- Toda consulta abaixo, menos `/api/saldo`, cobra do saldo do usuário. Diga o custo e espere o OK dele antes da primeira chamada e antes de qualquer laço.
- Preço de 1 consulta por plano (franquia; recarga entre parênteses): Lite R$ 0,67; Starter R$ 0,10 (R$ 0,12); Pro R$ 0,065 (R$ 0,07); Enterprise R$ 0,025 (R$ 0,02).
- Conta que nunca assinou, com e-mail confirmado e sem recarga: 10 consultas grátis por mês de IE em um estado e de CNPJ (não valem para a IE em todos os estados nem para o CNPJ ao vivo).
- Conta sem plano paga a recarga do último plano (R$ 0,12 se nunca assinou).
- Consulta que termina em erro não é cobrada. Resposta sem inscrição encontrada, `sem_certidao` ou `nao_contribuinte` conta como consulta.
- Limite por minuto da conta: Lite 5, Starter 20, Pro 60, Enterprise 120 (sem plano: 5).
- Envie só um documento por chamada (`cpf`, `cnpj` ou `ie`), com ou sem pontuação.

## Endpoints

| Método e caminho | Parâmetros | Devolve | Custo |
|---|---|---|---|
| `GET /api/consultar` | `uf` + `cpf` ou `cnpj` ou `ie`; `secundarias=true` opcional | Inscrições estaduais na UF (por CPF, todas menos SP) | 1 consulta |
| `GET /api/consultar-ie-todos` | `cpf` ou `cnpj` ou `ie`; `secundarias=true` opcional | Inscrições nos 27 estados, por UF; `complete=false` se algum estado não respondeu | 1 consulta |
| `GET /api/consultar-cnpj` | `cnpj`; `force_fresh=true` opcional (ao vivo) | Cadastro público na Receita Federal, com Simples e MEI | 1 consulta; ao vivo, 3 |
| `GET /api/consultar-cnd` | `uf` + `cpf` ou `cnpj` | CND estadual: status, emissão, validade, PDF em `pdf_base64` | 1 consulta |
| `GET /api/consultar-cndt` | `cpf` ou `cnpj` | CNDT (débitos trabalhistas) | 1 consulta |
| `GET /api/consultar-cnd-federal` | `cpf` ou `cnpj`; `emitir_nova=true` opcional | Certidão de tributos federais e Dívida Ativa da União | 1 consulta |
| `GET /api/consultar-crf-fgts` | `cpf` ou `cnpj` | Certificado de Regularidade do FGTS | 1 consulta |
| `POST /api/consultar-nfe-xml-sem-certificado` | corpo JSON só com `{"chave": "<44 posições>"}` (campo a mais dá 422) | Cópia para leitura do XML de uma NF-e (modelo 55), sem a assinatura digital (`assinado=false`, `tipo_xml=leitura`) | 3 consultas (2 no Enterprise); cobra também `nao_encontrado` |
| `GET /api/saldo` | — | `consultas_restantes` e `notas_restantes` | Não consome |

Status da CND/certidão: `negativa`, `positiva`, `positiva_com_efeitos_de_negativa`, `nao_contribuinte`, `sem_certidao` (não há certidão emitida; não é erro) ou `erro`.

## Exemplos (documentos fictícios)

```bash
curl -s "https://api.fiscalapi.com.br/api/consultar-cnpj?cnpj=12345678000195" \
  -H "X-API-Key: $FISCALAPI_API_KEY"

curl -s "https://api.fiscalapi.com.br/api/consultar?uf=MT&cnpj=12345678000195" \
  -H "X-API-Key: $FISCALAPI_API_KEY"

curl -s "https://api.fiscalapi.com.br/api/consultar-ie-todos?cpf=12345678909" \
  -H "X-API-Key: $FISCALAPI_API_KEY"

curl -s -X POST "https://api.fiscalapi.com.br/api/consultar-nfe-xml-sem-certificado" \
  -H "X-API-Key: $FISCALAPI_API_KEY" -H "Content-Type: application/json" \
  -d '{"chave": "<chave de acesso de 44 posições>"}'

curl -s "https://api.fiscalapi.com.br/api/saldo" -H "X-API-Key: $FISCALAPI_API_KEY"
```

```python
import os

import httpx

resposta = httpx.get(
    "https://api.fiscalapi.com.br/api/consultar-cnpj",
    params={"cnpj": "12345678000195"},
    headers={"X-API-Key": os.environ["FISCALAPI_API_KEY"]},
    timeout=95,
)
resposta.raise_for_status()
cadastro = resposta.json().get("result")  # None quando a consulta não trouxe dado
print(cadastro["razao_social"] if cadastro else "sem dado nesta consulta")
```

## Erros

Os erros vêm em JSON; o motivo está em `detail` (ou `message`).

- `402`: o saldo não cobre a consulta (acabaram as consultas do mês, as 10 grátis de IE/CNPJ ou a franquia do plano, e não há recarga). Não repita: avise o usuário para assinar ou recarregar em app.fiscalapi.com.br.
- `403` com `API_KEY_ERROR`: chave ausente, inválida ou revogada. Não tente outra chave por conta própria.
- `429`: passou do limite por minuto do plano (ou de outro limite descrito em `detail`/`message`, como consultas simultâneas). Espere o tempo de `Retry-After` (ou `retry_after` no corpo) antes de repetir; em lote, espace as chamadas pelo limite do plano.
- `400`/`422`: parâmetro faltando ou inválido; corrija antes de repetir.
- `5xx`: falha momentânea, não cobrada. Uma nova tentativa depois de alguns segundos é razoável; não fique em laço.

## Também existe o servidor MCP

`https://mcp.fiscalapi.com.br/mcp` expõe as mesmas consultas como ferramentas MCP, com o header `X-API-Key`. Veja o README deste repositório.
