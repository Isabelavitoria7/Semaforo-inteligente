"""
traffic_state.py
----------------
Máquina de estados do semáforo inteligente para cruzamento de 2 vias de mão única.

Estados
-------
RUA1_OPEN       — Rua 1 aberta para carros (1 min).
RUA1_EXTENDED   — Rua 1 com extensão (rua 2 vazia → +1 min).
RUA2_OPEN       — Rua 2 aberta para carros (1 min).
RUA2_EXTENDED   — Rua 2 com extensão (rua 1 vazia → +1 min).
PEDESTRIAN      — Todos carros fechados, pedestres abertos.

Comandos seriais gerados
------------------------
'A' → Rua1 verde, Rua2 vermelho, PedRua1 vermelho, PedRua2 verde
'B' → Rua2 verde, Rua1 vermelho, PedRua2 vermelho, PedRua1 verde
'P' → Todos carros vermelho, todos pedestres verde
"""

import time
from enum import Enum, auto


class State(Enum):
    RUA1_OPEN      = auto()
    RUA1_EXTENDED  = auto()
    RUA1_YELLOW    = auto()   # amarelo — transição saindo da Rua 1
    RUA2_OPEN      = auto()
    RUA2_EXTENDED  = auto()
    RUA2_YELLOW    = auto()   # amarelo — transição saindo da Rua 2
    PEDESTRIAN     = auto()


# Mapeamento estado → comando serial de ativação
_STATE_CMD = {
    State.RUA1_OPEN:      'A',
    State.RUA1_EXTENDED:  'A',
    State.RUA1_YELLOW:    'C',
    State.RUA2_OPEN:      'B',
    State.RUA2_EXTENDED:  'B',
    State.RUA2_YELLOW:    'D',
    State.PEDESTRIAN:     'P',
}

# Descrição legível de cada estado
_STATE_LABEL = {
    State.RUA1_OPEN:      "Rua 1: VERDE     | Rua 2: VERMELHO",
    State.RUA1_EXTENDED:  "Rua 1: VERDE (extensão) | Rua 2: VERMELHO",
    State.RUA1_YELLOW:    "Rua 1: AMARELO   | Rua 2: VERMELHO",
    State.RUA2_OPEN:      "Rua 2: VERDE     | Rua 1: VERMELHO",
    State.RUA2_EXTENDED:  "Rua 2: VERDE (extensão) | Rua 1: VERMELHO",
    State.RUA2_YELLOW:    "Rua 2: AMARELO   | Rua 1: VERMELHO",
    State.PEDESTRIAN:     "PEDESTRES: VERDE | Carros: VERMELHO",
}


class TrafficController:
    """
    Controla a lógica de semáforo para um cruzamento de 2 vias.

    Uso típico por ciclo de frame
    ------------------------------
        cmd = controller.update(count_rua1, count_rua2)
        if cmd:
            send_to_arduino(cmd)
    """

    GREEN_DURATION      = 60   # segundos — sinal verde base (máximo)
    MIN_GREEN_DURATION  = 20   # segundos — mínimo garantido por rua
    EXTENSION_DURATION  = 60   # segundos — extensão quando via oposta vazia
    YELLOW_DURATION     = 3    # segundos — sinal amarelo (transição segura)
    PEDESTRIAN_DURATION = 30   # segundos — tempo de travessia
    MIN_SAFE_TIME       = 10   # segundos — espera mínima antes de fechar com carros

    def __init__(self) -> None:
        self._state: State = State.RUA1_OPEN
        self._state_start: float = time.time()
        self._pedestrian_requested: bool = False
        self._pedestrian_request_time: float | None = None
        self._return_state: State | None = None       # estado ao sair de PEDESTRIAN
        self._next_after_yellow: State = State.RUA2_OPEN  # estado após amarelo
        self._green_rua1: float = self.GREEN_DURATION  # duração dinâmica Rua 1
        self._green_rua2: float = self.GREEN_DURATION  # duração dinâmica Rua 2
        self._last_count_rua1: int = 0
        self._last_count_rua2: int = 0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def state(self) -> State:
        return self._state

    @property
    def car_rua1(self) -> str:
        """'VERDE', 'AMARELO' ou 'VERMELHO' para o semáforo de carros da Rua 1."""
        if self._state in (State.RUA1_OPEN, State.RUA1_EXTENDED):
            return "VERDE"
        if self._state == State.RUA1_YELLOW:
            return "AMARELO"
        return "VERMELHO"

    @property
    def car_rua2(self) -> str:
        """'VERDE', 'AMARELO' ou 'VERMELHO' para o semáforo de carros da Rua 2."""
        if self._state in (State.RUA2_OPEN, State.RUA2_EXTENDED):
            return "VERDE"
        if self._state == State.RUA2_YELLOW:
            return "AMARELO"
        return "VERMELHO"

    @property
    def ped_rua1(self) -> str:
        """'VERDE' ou 'VERMELHO' para o semáforo de pedestre da Rua 1."""
        # Pedestre Rua1 verde quando carros da Rua1 estão fechados
        if self._state in (State.RUA1_OPEN, State.RUA1_EXTENDED, State.RUA1_YELLOW):
            return "VERMELHO"
        return "VERDE"

    @property
    def ped_rua2(self) -> str:
        """'VERDE' ou 'VERMELHO' para o semáforo de pedestre da Rua 2."""
        if self._state in (State.RUA2_OPEN, State.RUA2_EXTENDED, State.RUA2_YELLOW):
            return "VERMELHO"
        return "VERDE"

    @property
    def status_text(self) -> str:
        """Texto legível do estado global (para logs)."""
        base = _STATE_LABEL.get(self._state, str(self._state))
        if self._pedestrian_requested and self._state != State.PEDESTRIAN:
            base += " | [Pedestre aguardando]"
        return base

    @property
    def green_rua1(self) -> float:
        """Duração dinâmica atual do verde da Rua 1 em segundos."""
        return self._green_rua1

    @property
    def green_rua2(self) -> float:
        """Duração dinâmica atual do verde da Rua 2 em segundos."""
        return self._green_rua2

    def button_pressed(self, road: int = 0) -> None:
        """Chamar quando o botão de travessia de uma rua for pressionado.

        Parâmetros
        ----------
        road : int
            1 = botão da Rua 1, 2 = botão da Rua 2, 0 = qualquer (legado).

        Só age se a rua solicitada estiver atualmente ABERTA para veículos.
        Se já estiver fechada, o pedestre daquela rua já tem sinal verde —
        nenhuma ação necessária.
        """
        if self._state in (State.PEDESTRIAN,):
            return  # já em modo pedestre

        if self._pedestrian_requested:
            return  # já há uma solicitação pendente

        _rua1_states = (State.RUA1_OPEN, State.RUA1_EXTENDED, State.RUA1_YELLOW)
        _rua2_states = (State.RUA2_OPEN, State.RUA2_EXTENDED, State.RUA2_YELLOW)

        if road == 1 and self._state not in _rua1_states:
            # Rua 1 já está fechada para carros → pedestre já tem verde → ignora
            print("[CTRL] Botão Rua 1: pedestre já possui sinal verde, ignorado.")
            return
        if road == 2 and self._state not in _rua2_states:
            # Rua 2 já está fechada para carros → pedestre já tem verde → ignora
            print("[CTRL] Botão Rua 2: pedestre já possui sinal verde, ignorado.")
            return

        self._pedestrian_requested = True
        self._pedestrian_request_time = time.time()
        label = f"Rua {road}" if road else "rua desconhecida"
        print(f"[CTRL] Pedestre ({label}) solicitou travessia.")

    def update(self, count_rua1: int, count_rua2: int) -> str | None:
        """
        Atualiza a máquina de estados com as contagens atuais de veículos.

        Parâmetros
        ----------
        count_rua1 : int  — veículos detectados na câmera da Rua 1.
        count_rua2 : int  — veículos detectados na câmera da Rua 2.

        Retorna
        -------
        str | None — comando serial ('A', 'B' ou 'P') se houve transição, senão None.
        """
        self._last_count_rua1 = count_rua1
        self._last_count_rua2 = count_rua2
        self._update_green_durations(count_rua1, count_rua2)

        now = time.time()
        elapsed = now - self._state_start

        if self._state == State.RUA1_OPEN:
            return self._handle_rua1_open(now, elapsed, count_rua1, count_rua2)

        if self._state == State.RUA1_EXTENDED:
            return self._handle_rua1_extended(now, elapsed, count_rua1, count_rua2)

        if self._state == State.RUA1_YELLOW:
            return self._handle_yellow(now, elapsed, self._next_after_yellow)

        if self._state == State.RUA2_OPEN:
            return self._handle_rua2_open(now, elapsed, count_rua1, count_rua2)

        if self._state == State.RUA2_EXTENDED:
            return self._handle_rua2_extended(now, elapsed, count_rua1, count_rua2)

        if self._state == State.RUA2_YELLOW:
            return self._handle_yellow(now, elapsed, self._next_after_yellow)

        if self._state == State.PEDESTRIAN:
            return self._handle_pedestrian(now, elapsed, count_rua1, count_rua2)

        return None

    # ------------------------------------------------------------------
    # Handlers de estado
    # ------------------------------------------------------------------

    def _handle_rua1_open(self, now, elapsed, c1, c2) -> str | None:
        # Pedestre solicitou travessia
        if self._pedestrian_requested:
            if c1 == 0 or elapsed >= self.MIN_SAFE_TIME:
                return self._goto_yellow(now, State.RUA1_YELLOW, next_after=State.PEDESTRIAN,
                                         pedestrian_return=State.RUA2_OPEN)

        # Tempo dinâmico esgotado
        if elapsed >= self._green_rua1:
            if c2 == 0:
                return self._transition(State.RUA1_EXTENDED, now)
            return self._goto_yellow(now, State.RUA1_YELLOW, next_after=State.RUA2_OPEN)

        return None

    def _handle_rua1_extended(self, now, elapsed, c1, c2) -> str | None:
        # Pedestre solicitou travessia
        if self._pedestrian_requested:
            if c1 == 0 or elapsed >= self.MIN_SAFE_TIME:
                return self._goto_yellow(now, State.RUA1_YELLOW, next_after=State.PEDESTRIAN,
                                         pedestrian_return=State.RUA2_OPEN)

        # Veículo surgiu na via oposta → iniciar troca com amarelo
        if c2 > 0:
            return self._goto_yellow(now, State.RUA1_YELLOW, next_after=State.RUA2_OPEN)

        # Extensão esgotada
        if elapsed >= self.EXTENSION_DURATION:
            return self._goto_yellow(now, State.RUA1_YELLOW, next_after=State.RUA2_OPEN)

        return None

    def _handle_rua2_open(self, now, elapsed, c1, c2) -> str | None:
        if self._pedestrian_requested:
            if c2 == 0 or elapsed >= self.MIN_SAFE_TIME:
                return self._goto_yellow(now, State.RUA2_YELLOW, next_after=State.PEDESTRIAN,
                                         pedestrian_return=State.RUA1_OPEN)

        if elapsed >= self._green_rua2:
            if c1 == 0:
                return self._goto_yellow(now, State.RUA2_YELLOW, next_after=State.RUA2_EXTENDED)
            return self._goto_yellow(now, State.RUA2_YELLOW, next_after=State.RUA1_OPEN)

        return None

    def _handle_rua2_extended(self, now, elapsed, c1, c2) -> str | None:
        if self._pedestrian_requested:
            if c2 == 0 or elapsed >= self.MIN_SAFE_TIME:
                return self._goto_yellow(now, State.RUA2_YELLOW, next_after=State.PEDESTRIAN,
                                         pedestrian_return=State.RUA1_OPEN)

        if c1 > 0:
            return self._goto_yellow(now, State.RUA2_YELLOW, next_after=State.RUA1_OPEN)

        if elapsed >= self.EXTENSION_DURATION:
            return self._goto_yellow(now, State.RUA2_YELLOW, next_after=State.RUA1_OPEN)

        return None

    def _handle_yellow(self, now, elapsed, next_state: State) -> str | None:
        """Aguarda YELLOW_DURATION e então transita para next_state."""
        if elapsed >= self.YELLOW_DURATION:
            if next_state == State.PEDESTRIAN:
                return self._goto_pedestrian(now, return_to=self._return_state or State.RUA1_OPEN)
            return self._transition(next_state, now)
        return None

    def _handle_pedestrian(self, now, elapsed, c1, c2) -> str | None:
        if elapsed >= self.PEDESTRIAN_DURATION:
            next_state = self._return_state or State.RUA1_OPEN
            self._return_state = None
            return self._transition(next_state, now)
        return None

    # ------------------------------------------------------------------
    # Utilitários de transição
    # ------------------------------------------------------------------

    def _update_green_durations(self, c1: int, c2: int) -> None:
        """Recalcula o tempo de verde de cada rua proporcionalmente ao fluxo.

        Regra: a rua com menos veículos recebe metade do tempo da rua com
        mais veículos, respeitando o mínimo de MIN_GREEN_DURATION.
        Quando as contagens são iguais (ou ambas zero), ambas recebem
        GREEN_DURATION completo.
        """
        if c1 == c2:
            self._green_rua1 = self.GREEN_DURATION
            self._green_rua2 = self.GREEN_DURATION
            return

        if c1 > c2:
            self._green_rua1 = float(self.GREEN_DURATION)
            self._green_rua2 = max(self.GREEN_DURATION / 2.0, self.MIN_GREEN_DURATION)
        else:
            self._green_rua2 = float(self.GREEN_DURATION)
            self._green_rua1 = max(self.GREEN_DURATION / 2.0, self.MIN_GREEN_DURATION)

    def _transition(self, new_state: State, now: float) -> str:
        self._state = new_state
        self._state_start = now
        yellow_states = (State.RUA1_YELLOW, State.RUA2_YELLOW, State.PEDESTRIAN)
        if new_state not in yellow_states:
            self._pedestrian_requested = False
            self._pedestrian_request_time = None
        cmd = _STATE_CMD[new_state]
        print(f"[CTRL] Transição → {new_state.name}  |  Comando: '{cmd}'")
        return cmd

    def _goto_yellow(
        self,
        now: float,
        yellow_state: State,
        next_after: State,
        pedestrian_return: State | None = None,
    ) -> str:
        """Entra no estado de amarelo e registra o próximo estado após ele."""
        self._next_after_yellow = next_after
        if pedestrian_return is not None:
            self._return_state = pedestrian_return
        return self._transition(yellow_state, now)

    def _goto_pedestrian(self, now: float, return_to: State) -> str:
        self._return_state = return_to
        return self._transition(State.PEDESTRIAN, now)
