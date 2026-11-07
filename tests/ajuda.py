from typing import Any


def texto(resultado: Any) -> str:
    return "\n".join(getattr(bloco, "text", "") for bloco in resultado.content)


def dados(resultado: Any) -> Any:
    estruturado = resultado.structured_content
    if isinstance(estruturado, dict) and set(estruturado) == {"result"}:
        return estruturado["result"]
    return estruturado
