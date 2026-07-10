# 🚦 Semáforo Inteligente

> Cruzamento autônomo que enxerga o trânsito e decide sozinho quando abrir ou fechar o sinal.

Combina **visão computacional** (Python + OpenCV) com **firmware embarcado** (Arduino UNO) para controlar um cruzamento de duas vias de mão única de forma adaptativa — sem ciclos fixos, sem desperdício de verde.

---

## Como funciona
┌────────────┐ frame ┌──────────────────┐ serial ┌─────────────┐
│ Câmera 1 │ ────────► │ │ ──────────► │ │
│ (Rua 1) │ │ Python (main.py)│ │ Arduino UNO│
│ Câmera 2 │ ────────► │ MobileNet SSD │ ◄────────── │ (LEDs + │
│ (Rua 2) │ frame │ TrafficCtrl FSM │ '1' / '2' │ botões) │
└────────────┘ └──────────────────┘ └─────────────┘

1. Dois feeds de câmera capturam as vias em tempo real.
2. O modelo **MobileNet SSD** conta carros, ônibus e motos em cada frame.
3. A **máquina de estados** decide qual via deve ficar verde, por quanto tempo e quando ceder passagem a pedestres.
4. O Arduino executa os comandos e reporta acionamentos de botão.

---

## Máquina de Estados

| Estado | Descrição | Duração |
|---|---|---|
| `RUA1_OPEN` | Rua 1 verde | 20 – 60 s |
| `RUA1_EXTENDED` | Extensão automática (Rua 2 vazia) | +60 s |
| `RUA1_YELLOW` | Amarelo de transição | 3 s |
| `RUA2_OPEN` | Rua 2 verde | 20 – 60 s |
| `RUA2_EXTENDED` | Extensão automática (Rua 1 vazia) | +60 s |
| `RUA2_YELLOW` | Amarelo de transição | 3 s |
| `PEDESTRIAN` | Todos os carros fechados, pedestres abertos | 30 s |

---

## Protocolo Serial

| Direção | Byte | Significado |
|---|---|---|
| Python → Arduino | `A` | Rua 1 verde, Rua 2 vermelha, Ped Rua 2 verde |
| Python → Arduino | `B` | Rua 2 verde, Rua 1 vermelha, Ped Rua 1 verde |
| Python → Arduino | `C` | Rua 1 amarela (transição) |
| Python → Arduino | `D` | Rua 2 amarela (transição) |
| Python → Arduino | `P` | Todos carros vermelhos, todos pedestres verdes |
| Arduino → Python | `1` | Botão pedestre Rua 1 pressionado |
| Arduino → Python | `2` | Botão pedestre Rua 2 pressionado |

---

## Mapeamento de Pinos (Arduino UNO)

| Função | Pino |
|---|---|
| Rua 1 — Verde / Amarelo / Vermelho | 4 / 3 / 2 |
| Rua 2 — Verde / Amarelo / Vermelho | 7 / 6 / 5 |
| Pedestre Rua 1 — Verde / Vermelho | 9 / 8 |
| Pedestre Rua 2 — Verde / Vermelho | 11 / 10 |
| Botão Rua 1 / Rua 2 | A0 / A1 |

---

## Instalação

### Dependências Python
```bash
pip install opencv-python pyserial numpy
```

## Requer PlatformIO
```bash
pio run --target upload
```

## Uso
```bash
# Com Arduino conectado
python python_vision/main.py

# Sem hardware (modo simulador com teclado)
python python_vision/main.py --simulador
```

Teclas no modo simulador
Tecla	Ação
1	Simula botão de pedestre — Rua 1
2	Simula botão de pedestre — Rua 2
q	Encerra o programa

## Requisitos de Hardware
Arduino UNO e protoboard
Cerca de 120 jumpers F-f, M-f, m-m
2 câmeras USB (índices 0 e 1)
6 LEDs de sinalização (verde, amarelo, vermelho × 2 vias)
4 LEDs de pedestre (verde e vermelho × 2 cruzamentos)
2 botões de pedestre
Cabo USB para comunicação serial (/dev/ttyUSB0)

