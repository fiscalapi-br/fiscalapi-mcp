"""Sobe o servidor: `python -m fiscalapi_mcp`. Um processo, porta em PORT."""

import logging
import os

import uvicorn


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    from fiscalapi_mcp.servidor import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        # TLS termina na borda do Railway, a única que alcança o contêiner.
        proxy_headers=True,
        forwarded_allow_ips="*",
        # Log de acesso traria IP de cliente sem ajudar em nada aqui.
        access_log=False,
        server_header=False,
    )


if __name__ == "__main__":
    main()
