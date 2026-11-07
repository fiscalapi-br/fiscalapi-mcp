"""Limites em memória (um processo só, sem estado compartilhado).

São um freio contra laço de agente, não a proteção real: quem protege o saldo
é o limite do plano e o próprio saldo da conta, conferidos pela API.
"""

import hashlib
import threading
import time
from collections import deque

# Acima disso, cada passagem descarta as janelas já vazias.
_MAX_CHAVES_ANTES_DE_LIMPAR = 10_000


def hash_da_chave(chave: str) -> str:
    """sha256 da chave da API: a chave em si nunca fica guardada aqui."""
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


class JanelaDeslizante:
    """No máximo `limite` eventos por `janela_s` segundos, por identificador."""

    def __init__(self, limite: int, janela_s: float) -> None:
        self.limite = limite
        self.janela_s = janela_s
        self._eventos: dict[str, deque[float]] = {}
        self._trava = threading.Lock()

    def tentar(self, identificador: str) -> float:
        """Registra o evento e devolve 0. Se o limite já foi atingido, não
        registra e devolve quantos segundos faltam para abrir uma vaga."""
        agora = time.monotonic()
        with self._trava:
            if len(self._eventos) > _MAX_CHAVES_ANTES_DE_LIMPAR:
                self._limpar(agora)
            fila = self._eventos.setdefault(identificador, deque())
            while fila and agora - fila[0] >= self.janela_s:
                fila.popleft()
            if len(fila) >= self.limite:
                return max(1.0, self.janela_s - (agora - fila[0]))
            fila.append(agora)
            return 0.0

    def _limpar(self, agora: float) -> None:
        vencidas = [k for k, fila in self._eventos.items() if not fila or agora - fila[-1] >= self.janela_s]
        for k in vencidas:
            del self._eventos[k]
