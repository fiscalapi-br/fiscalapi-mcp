---
name: fiscalapi
description: Use para consultar dados fiscais brasileiros pela API REST da FiscalAPI (api.fiscalapi.com.br) — Inscrição Estadual nos 27 estados por CPF, CNPJ ou IE, cadastro de CNPJ, Simples Nacional, NFS-e pela chave, CND estadual, CNDT, CND Federal, CRF/FGTS, XML de NF-e pela chave de acesso, Monitor de NF-e por chave (aviso por webhook) e saldo da conta. Cada consulta cobra do saldo do usuário; confirme o custo antes.
---

# FiscalAPI pela API REST

Base: `https://api.fiscalapi.com.br`. Autenticação: header `X-API-Key: <chave>` em toda chamada. Leia a chave de uma variável de ambiente (ex.: `FISCALAPI_API_KEY`); nunca a escreva em código, log ou resposta. A chave é criada em app.fiscalapi.com.br, em Chave API.

Documentação completa: https://docs.fiscalapi.com.br

## Antes de chamar

- Toda consulta abaixo, menos `/api/saldo`, cobra do saldo do usuário. Diga o custo e espere o OK dele antes da primeira chamada e antes de qualquer laço.
- O saldo é em créditos (1 crédito = R$ 1); cada consulta desconta o preço dela. Preço de 1 consulta por plano, com os créditos do plano (com créditos extras entre parênteses): Starter R$ 0,10 (R$ 0,12); Pro R$ 0,065 (R$ 0,085); Enterprise R$ 0,025 (R$ 0,035). Os créditos extras só são usados depois que os créditos do plano acabam.
- Pela API toda consulta pede plano ou créditos extras (planos a partir de R$ 50 por mês). As 10 consultas grátis do mês são só no painel (app.fiscalapi.com.br), não valem pela API.
- Consulta que termina em erro não é cobrada. Resposta sem inscrição encontrada, `sem_certidao` ou `nao_contribuinte` conta como consulta.
- Limite por minuto da conta: Starter 20, Pro 60, Enterprise 120 (sem plano: 5).
- Envie só um documento por chamada (`cpf`, `cnpj` ou `ie`), com ou sem pontuação.

## Endpoints

| Método e caminho | Parâmetros | Devolve | Custo |
|---|---|---|---|
| `GET /api/consultar` | `uf` + `cpf` ou `cnpj` ou `ie`; `secundarias=true` opcional | Inscrições estaduais na UF (por CPF, todas menos SP) | 1 consulta |
| `GET /api/consultar-ie-todos` | `cpf` ou `cnpj` ou `ie`; `secundarias=true` opcional | Inscrições nos 27 estados, por UF; `complete=false` se algum estado não respondeu | 1 consulta |
| `GET /api/consultar-cnpj` | `cnpj`; `force_fresh=true` opcional (ao vivo) | Cadastro público na Receita Federal, com Simples e MEI | 1 consulta; ao vivo, R$ 0,30 (Starter), R$ 0,195 (Pro) ou R$ 0,075 (Enterprise) |
| `GET /api/consultar-simples-nacional` | `cnpj` | Situação no Simples Nacional, SIMEI e regimes IBS/CBS | 1 consulta |
| `GET /api/consultar-nfse` | `chave` (50 dígitos); `danfse=true` opcional (PDF em `danfse_pdf_base64`) | NFS-e do padrão nacional, sem certificado; 30 a 60 s | R$ 0,30 (Starter), R$ 0,195 (Pro) ou R$ 0,05 (Enterprise) por nota; só a nota entregue |
| `GET /api/consultar-cnd` | `uf` + `cpf` ou `cnpj` | CND estadual: status, emissão, validade, PDF em `pdf_base64` | 1 consulta |
| `GET /api/consultar-cndt` | `cpf` ou `cnpj` | CNDT (débitos trabalhistas) | 1 consulta |
| `GET /api/consultar-cnd-federal` | `cnpj`, ou `cpf` com `data_nascimento`; `emitir_nova=true` opcional | Certidão de tributos federais e Dívida Ativa da União | 1 consulta |
| `GET /api/consultar-crf-fgts` | `cpf` ou `cnpj` | Certificado de Regularidade do FGTS | 1 consulta |
| `POST /api/consultar-nfe-xml-sem-certificado` | corpo JSON só com `{"chave": "<44 posições>"}` (campo a mais dá 422) | Cópia para leitura do XML de uma NF-e (modelo 55), sem a assinatura digital (`assinado=false`, `tipo_xml=leitura`) | R$ 0,30 (Starter), R$ 0,195 (Pro) ou R$ 0,05 (Enterprise) por chave; cobra também `nao_encontrado` |
| `POST /api/monitor-nfe/chaves` | corpo `{"chaves": [{"chave": "<44 dígitos>", "status_conhecido": "autorizada"}], "prazo_dias": 180}` (até 1.000 chaves; `status_conhecido` e `prazo_dias` opcionais) | Por chave: `aceita`, `ja_monitorada` ou `invalida` (com `motivo`); `aceitas` e `valor_cobrado`. Sem saldo para todas: 402 e nenhuma entra | R$ 0,03 (Starter), R$ 0,02 (Pro) ou R$ 0,015 (Enterprise) por chave aceita, uma vez |
| `GET /api/monitor-nfe/chaves` | `status`, `ativo`, `alterado_desde`, `cursor`, `limite` (≤ 1.000) opcionais | Chaves do monitor e `proximo_cursor` | Não cobra |
| `GET /api/monitor-nfe/chaves/{chave}` | — | Situação, eventos, próxima verificação e avisos que o webhook não recebeu | Não cobra |
| `POST /api/monitor-nfe/chaves/remover` | corpo `{"chaves": ["<44 dígitos>"]}` | `removidas` e `nao_encontradas` (sem estorno) | Não cobra |
| `PUT /api/monitor-nfe/webhook` | corpo `{"url": "https://..."}` (só https, porta 443, nome público) | `segredo` da assinatura, mostrado só aqui: o usuário guarda, nunca o repita na resposta | Não cobra |
| `GET /api/saldo` | — | `consultas_restantes`, `notas_restantes` e `creditos` (`plano`, `extras`, `guardados`, `disponivel`, em créditos) | Não consome |

Status da CND/certidão: `negativa`, `positiva`, `positiva_com_efeitos_de_negativa`, `nao_contribuinte`, `sem_certidao` (não há certidão emitida; não é erro) ou `erro`.

Monitor de NF-e: os avisos chegam por POST JSON no webhook da conta (tipos `nfe.status_alterado`, `nfe.evento_registrado`, `nfe.monitoramento_encerrado`, `teste`). Para conferir que veio da FiscalAPI: `X-FiscalAPI-Assinatura` = `v1=` + HMAC-SHA256 em hex, com o segredo inteiro `whsec_...` como chave, sobre `"{X-FiscalAPI-Timestamp}." + corpo_bruto`; aceite se alguma `v1=` bater (na troca de segredo vêm duas), compare em tempo constante, recuse timestamp com mais de 5 min de diferença e deduplique pelo `id`. Os SDKs oficiais (Python, Node.js, PHP) já trazem a verificação.

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

- `402`: o saldo em créditos não cobre a consulta: os créditos do plano acabaram e não há créditos extras, ou a conta não tem plano nem créditos extras. O motivo está em `detail`/`message`; o corpo traz também `creditos` (saldo por parte) e `preco` (R$ desta consulta, `plano` e `extras`). Não repita: repasse o motivo e avise o usuário para assinar um plano ou comprar créditos extras em app.fiscalapi.com.br.
- `403` com `API_KEY_ERROR`: chave ausente, inválida ou revogada. Não tente outra chave por conta própria.
- `429`: passou do limite por minuto do plano (ou de outro limite descrito em `detail`/`message`, como consultas simultâneas). Espere o tempo de `Retry-After` (ou `retry_after` no corpo) antes de repetir; em lote, espace as chamadas pelo limite do plano.
- `400`/`422`: parâmetro faltando ou inválido; corrija antes de repetir.
- `5xx`: falha momentânea, não cobrada. Uma nova tentativa depois de alguns segundos é razoável; não fique em laço.

## Também existe o servidor MCP

`https://mcp.fiscalapi.com.br/mcp` expõe as mesmas consultas como ferramentas MCP, com o header `X-API-Key`. Veja o README deste repositório.
