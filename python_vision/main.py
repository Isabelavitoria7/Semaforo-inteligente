"""
main.py — Ponto de entrada do Semáforo Inteligente
===================================================
Executa o loop principal de detecção e controle:
  1. Captura frames das 2 câmeras (uma por rua).
  2. Detecta veículos em cada frame via MobileNet SSD.
  3. Atualiza a máquina de estados (TrafficController).
  4. Envia comandos seriais ao Arduino UNO conforme necessário.

Hardware:
  Os botões de pedestre estão conectados ao Arduino UNO (pinos 2 e 3).
  O Arduino envia '1' ou '2' via serial quando um botão é pressionado.

Requisitos:
    pip install opencv-python pyserial numpy

Uso:
    python main.py                  # Com Arduino conectado
    python main.py --simulador      # Sem Arduino (teclas de atalho)

Teclas (modo simulador):
    1 — simular botão de pedestre Rua 1
    2 — simular botão de pedestre Rua 2
    q — encerrar
"""

import os
import sys
import time
import argparse

import cv2

# Módulos internos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vehicle_detector import VehicleDetector
from traffic_state import TrafficController, State

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
CAMERA_INDEX = [0, 1]        # Câmera 0 → Rua 1 | Câmera 1 → Rua 2
SERIAL_PORT  = '/dev/ttyUSB0'
BAUD_RATE    = 9600

# Botões de pedestre gerenciados pelo Arduino UNO (pinos 2 e 3)
# O Arduino envia '1' ou '2' via serial quando um botão é pressionado.

# ---------------------------------------------------------------------------
# Argumentos de linha de comando
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(
    description="Semáforo Inteligente — controle de cruzamento com 2 vias."
)
parser.add_argument(
    '--simulador', action='store_true',
    help='Executa sem Arduino (modo simulação com teclado)',
)
args = parser.parse_args()

# ---------------------------------------------------------------------------
# Carregar detector de veículos
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
detector = VehicleDetector(
    prototxt=os.path.join(BASE_DIR, 'MobileNetSSD_deploy.prototxt'),
    model=os.path.join(BASE_DIR, 'MobileNetSSD_deploy.caffemodel'),
)

# ---------------------------------------------------------------------------
# Inicializar câmeras
# ---------------------------------------------------------------------------
cap1 = cv2.VideoCapture(CAMERA_INDEX[0])
cap2 = cv2.VideoCapture(CAMERA_INDEX[1])

if not cap1.isOpened():
    print(f"[AVISO] Câmera {CAMERA_INDEX[0]} (Rua 1) não encontrada.")
if not cap2.isOpened():
    print(f"[AVISO] Câmera {CAMERA_INDEX[1]} (Rua 2) não encontrada.")

# ---------------------------------------------------------------------------
# Inicializar Serial (Arduino)
# ---------------------------------------------------------------------------
arduino = None
if not args.simulador:
    try:
        import serial
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Aguarda reset do Arduino
        arduino.reset_input_buffer()  # Descarta lixo do bootloader
        print(f"[SERIAL] Arduino conectado em {SERIAL_PORT}")
    except Exception as exc:
        print(f"[SERIAL] Falha ao conectar: {exc}")


def send_command(cmd: str) -> None:
    """Envia um comando serial ao Arduino ou imprime no simulador."""
    if arduino:
        arduino.write(cmd.encode())
        arduino.flush()
        print(f"[ARDUINO] → '{cmd}'")
    elif args.simulador:
        print(f"[SIMULADOR] Comando: '{cmd}'")


# ---------------------------------------------------------------------------
# Controlador de estado
# ---------------------------------------------------------------------------
controller = TrafficController()
send_command('A')  # Estado inicial: Rua 1 aberta

# ---------------------------------------------------------------------------
# Helpers de exibição
# ---------------------------------------------------------------------------
_CAR_COLOR   = {"VERDE": (0, 255, 0), "AMARELO": (0, 255, 255), "VERMELHO": (0, 0, 255)}
_PED_COLOR   = {"VERDE": (0, 255, 0), "VERMELHO": (0, 0, 255)}


def overlay_info(frame, road_label: str, count: int,
                 car_status: str, ped_status: str,
                 green_duration: float | None = None) -> None:
    """Desenha informações de diagnóstico independentes sobre o frame."""
    car_color = _CAR_COLOR.get(car_status, (255, 255, 255))
    ped_color = _PED_COLOR.get(ped_status, (255, 255, 255))
    cv2.putText(frame, f"{road_label} — Veiculos: {count}",
                (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(frame, f"Carros:    {car_status}",
                (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.75, car_color, 2)
    cv2.putText(frame, f"Pedestre:  {ped_status}",
                (10, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.75, ped_color, 2)
    if green_duration is not None:
        cv2.putText(frame, f"Verde:     {int(green_duration)}s",
                    (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 140, 0), 2)


# ---------------------------------------------------------------------------
# Loop principal
# ---------------------------------------------------------------------------
print("[MAIN] Iniciando loop. Pressione 'q' para encerrar.")

while True:
    # --- Leitura de botões via teclado (apenas no modo simulador) ---
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('1'):
        controller.button_pressed(road=1)
        if args.simulador:
            print("[SIMULADOR] Botão pedestre Rua 1 pressionado (tecla '1')")
    elif key == ord('2'):
        controller.button_pressed(road=2)
        if args.simulador:
            print("[SIMULADOR] Botão pedestre Rua 2 pressionado (tecla '2')")

    # --- Leitura de eventos do Arduino (botões físicos) ---
    if arduino and arduino.in_waiting:
        msg = arduino.read().decode(errors='ignore').strip()
        if msg in ('1', '2'):
            print(f"[ARDUINO] ← Botão Rua {msg} pressionado")
            controller.button_pressed(road=int(msg))

    # --- Captura e detecção ---
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()

    count1, annotated1 = detector.detect(frame1) if ret1 else (0, None)
    count2, annotated2 = detector.detect(frame2) if ret2 else (0, None)

    # --- Atualizar máquina de estados ---
    cmd = controller.update(count1, count2)
    if cmd:
        send_command(cmd)

    # --- Exibição ---
    if annotated1 is not None:
        overlay_info(annotated1, "Rua 1", count1,
                     controller.car_rua1, controller.ped_rua1,
                     controller.green_rua1)
        cv2.imshow("Rua 1", annotated1)

    if annotated2 is not None:
        frame2_small = cv2.resize(annotated2, (640, 480))
        overlay_info(frame2_small, "Rua 2", count2,
                     controller.car_rua2, controller.ped_rua2,
                     controller.green_rua2)
        cv2.imshow("Rua 2", frame2_small)



# ---------------------------------------------------------------------------
# Limpeza
# ---------------------------------------------------------------------------
cap1.release()
cap2.release()
cv2.destroyAllWindows()

if arduino:
    arduino.close()

print("[MAIN] Encerrado.")
