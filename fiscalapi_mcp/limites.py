"""Limites em memória (um processo só, sem estado compartilhado).

São um freio contra laço de agente, não a proteção real: quem protege o saldo
é o limite do plano e o próprio saldo da conta, conferidos pela API.
"""

import hashlib
import threading
import time
from collections import OrderedDict, deque

# Teto de identificadores guardados: acima disso sai o usado há mais tempo.
_MAX_IDENTIFICADORES = 5_000
# A cada tantas chamadas, descarta as janelas vencidas (o hash some em até ~1 janela).
_LIMPAR_A_CADA = 200


def hash_da_chave(chave: str) -> str:
    """sha256 da chave da API: a chave em si nunca fica guardada aqui."""
    return hashlib.sha256(chave.encode("utf-8")).hexdigest()


class JanelaDeslizante:
    """No máximo `limite` eventos por `janela_s` segundos, por identificador."""

    def __init__(self, limite: int, janela_s: float, max_identificadores: int = _MAX_IDENTIFICADORES) -> None:
        self.limite = limite
        self.janela_s = janela_s
        self._max = max_identificadores
        self._eventos: OrderedDict[str, deque[float]] = OrderedDict()
        self._chamadas = 0
        self._trava = threading.Lock()

    def espera(self, identificador: str) -> float:
        """0 se há vaga agora; senão, quantos segundos faltam. Não registra nada."""
        with self._trava:
            return self._espera(identificador, time.monotonic())

    def registrar(self, identificador: str) -> None:
        with self._trava:
            agora = time.monotonic()
            self._manutencao(agora)
            fila = self._eventos.get(identificador)
            if fila is None:
                fila = deque()
                self._eventos[identificador] = fila
                while len(self._eventos) > self._max:
                    self._eventos.popitem(last=False)
            self._eventos.move_to_end(identificador)
            fila.append(agora)

    def tentar(self, identificador: str) -> float:
        """Registra o evento e devolve 0. Se o limite já foi atingido, não
        registra e devolve quantos segundos faltam para abrir uma vaga."""
        with self._trava:
            espera = self._espera(identificador, time.monotonic())
        if espera:
            return espera
        self.registrar(identificador)
        return 0.0

    def desfazer(self, identificador: str) -> None:
        """Devolve a vaga do último evento (ex.: a API recusou a chave)."""
        with self._trava:
            fila = self._eventos.get(identificador)
            if fila:
                fila.pop()
            if fila is not None and not fila:
                del self._eventos[identificador]

    def _espera(self, identificador: str, agora: float) -> float:
        fila = self._eventos.get(identificador)
        if not fila:
            return 0.0
        while fila and agora - fila[0] >= self.janela_s:
            fila.popleft()
        if len(fila) >= self.limite:
            return max(1.0, self.janela_s - (agora - fila[0]))
        return 0.0

    def _manutencao(self, agora: float) -> None:
        self._chamadas += 1
        if self._chamadas % _LIMPAR_A_CADA:
            return
        vencidas = [k for k, fila in self._eventos.items() if not fila or agora - fila[-1] >= self.janela_s]
        for k in vencidas:
            del self._eventos[k]
