# Requisitos para rodar este sistema:
# pip install opencv-python pyserial numpy
# Baixe os arquivos do modelo MobileNet SSD (prototxt e caffemodel) e coloque na mesma pasta deste script.


import cv2
import numpy as np
import serial
import argparse
import time
try:
    import RPi.GPIO as GPIO  # Para Raspberry Pi
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False


# Configurações
CAMERA_INDEX = 0  # 0 para webcam padrão
SERIAL_PORT = '/dev/ttyACM0'  # Ajuste conforme seu Arduino
BAUD_RATE = 9600
PEDESTRIAN_PRESENCE = False
PIR_PIN = 17  # GPIO para o sensor PIR (ajuste conforme necessário)
CAR_THRESHOLD = 3  # Número de carros para manter sinal fechado
GREEN_TIME = 15     # Tempo mínimo de sinal verde para pedestre (segundos)
RED_TIME = 10      # Tempo mínimo de sinal vermelho para pedestre (segundos)

# Argumentos de linha de comando
parser = argparse.ArgumentParser(description="Detector de carros com controle de semáforo para Arduino ou simulação.")
parser.add_argument('--simulador', action='store_true', help='Executa em modo simulador, sem Arduino')
args = parser.parse_args()

# Carregando modelo pré-treinado MobileNet SSD
import os
prototxt = os.path.abspath(os.path.join(os.path.dirname(__file__), 'MobileNetSSD_deploy.prototxt'))
model = os.path.abspath(os.path.join(os.path.dirname(__file__), 'MobileNetSSD_deploy.caffemodel'))
net = cv2.dnn.readNetFromCaffe(prototxt, model)

# Classes do modelo
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]


# Inicializa GPIO para PIR (se disponível)
if HAS_GPIO:
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)

# Inicializa câmera
cap = cv2.VideoCapture(CAMERA_INDEX)


# Inicializa comunicação serial (se não for simulador)
arduino = None
if not args.simulador:
    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Aguarda conexão
    except Exception as e:
        print(f"Erro ao conectar no Arduino: {e}")
        arduino = None



last_switch = time.time()
pedestrian_green = False
pedestrian_waiting = False
pedestrian_detected_time = None
pedestrian_queue = False  # Indica se há novo pedestre esperando durante o verde


while True:
    # Lê o sensor PIR
    if HAS_GPIO:
        PEDESTRIAN_PRESENCE = GPIO.input(PIR_PIN)
    else:
        # Simulação: pressione 'p' para simular pedestre
        if cv2.waitKey(1) & 0xFF == ord('p'):
            PEDESTRIAN_PRESENCE = True
        else:
            PEDESTRIAN_PRESENCE = False

    ret, frame = cap.read()
    if not ret:
        break

    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    vehicle_count = 0
    for i in np.arange(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            idx = int(detections[0, 0, i, 1])
            if CLASSES[idx] == "car" or CLASSES[idx] == "bus" or CLASSES[idx] == "motorbike":
                vehicle_count += 1
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                label = f"Car: {confidence*100:.1f}%"
                cv2.putText(frame, label, (startX, startY-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)


    now = time.time()

    # Lógica de detecção de pedestre

    if PEDESTRIAN_PRESENCE:
        if not pedestrian_green and not pedestrian_waiting:
            pedestrian_waiting = True
            pedestrian_detected_time = now
            print("Pedestre detectado, aguardando condições para fechar o sinal dos veículos...")
        elif pedestrian_green:
            # Se já está verde e chega outro pedestre, marca fila
            pedestrian_queue = True

    if pedestrian_waiting:
        tempo_espera = now - pedestrian_detected_time
        if vehicle_count >= 2 :
            # Sinal dos carros permanece aberto e do pedestre fechado durante os 15s
            if tempo_espera >= 15:
                pedestrian_green = True
                pedestrian_waiting = False
                last_switch = now
                pedestrian_queue = False
                if arduino:
                    arduino.write(b'G')  # Sinal verde para pedestre
                elif args.simulador:
                    print("[SIMULADOR] Sinal de pedestre ficou VERDE")
            # Caso contrário, mantém aguardando (carros abertos, pedestre fechado)
        else:
            # Se 2 ou menos carros, mantém lógica anterior (espera 5s)
            if tempo_espera >= 5:
                pedestrian_green = True
                pedestrian_waiting = False
                last_switch = now
                pedestrian_queue = False
                if arduino:
                    arduino.write(b'G')  # Sinal verde para pedestre
                elif args.simulador:
                    print("[SIMULADOR] Sinal de pedestre ficou VERDE")

    if pedestrian_green:
        # Se um novo pedestre chegou durante o verde, reinicia o tempo verde
        if pedestrian_queue:
            last_switch = now
            pedestrian_queue = False
        if now - last_switch > GREEN_TIME:
            if vehicle_count >= CAR_THRESHOLD or not PEDESTRIAN_PRESENCE:
                pedestrian_green = False
                last_switch = now
                if arduino:
                    arduino.write(b'R')  # Sinal vermelho para pedestre
                elif args.simulador:
                    print("[SIMULADOR] Sinal de pedestre ficou VERMELHO")
    else:
        if now - last_switch > RED_TIME:
            if vehicle_count < CAR_THRESHOLD and not PEDESTRIAN_PRESENCE:
                pedestrian_green = False
            # Mantém o sinal dos carros aberto se não houver pedestre

    # Exibe informações na tela


    # Corrige status para exibir corretamente durante a espera dos 15s
    if pedestrian_green:
        status = "Pedestre: VERDE"
        vehicle_signal = "Vermelho"
        vehicle_color = (0, 0, 255)  # Vermelho
    elif pedestrian_waiting:
        tempo_espera = now - pedestrian_detected_time if pedestrian_detected_time else 0
        if vehicle_count >= 2 and tempo_espera < 15:
            status = "Pedestre: VERMELHO"
            vehicle_signal = "Verde"
            vehicle_color = (0, 255, 0)  # Verde
        else:
            status = "Pedestre: AGUARDANDO"
            vehicle_signal = "Amarelo"
            vehicle_color = (0, 255, 255)  # Amarelo
    else:
        status = "Pedestre: VERMELHO"
        vehicle_signal = "Verde"
        vehicle_color = (0, 255, 0)  # Verde

    cv2.putText(frame, f"Carros: {vehicle_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(frame, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255) if not pedestrian_green else (0,255,0), 2)
    cv2.putText(frame, f"Sinal Veiculos: {vehicle_signal}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, vehicle_color, 2)
    cv2.imshow("Deteccao de Carros", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
if HAS_GPIO:
    GPIO.cleanup()
