# Requisitos para rodar este sistema:
# pip install opencv-python pyserial numpy
# Baixe os arquivos do modelo MobileNet SSD (prototxt e caffemodel) e coloque na mesma pasta deste script.

import cv2
import numpy as np
import serial
import argparse
import time


# Configurações
CAMERA_INDEX = 0  # 0 para webcam padrão
SERIAL_PORT = '/dev/ttyACM0'  # Ajuste conforme seu Arduino
BAUD_RATE = 9600
CAR_THRESHOLD = 5  # Número de carros para manter sinal fechado
GREEN_TIME = 5     # Tempo mínimo de sinal verde para pedestre (segundos)
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

while True:
    ret, frame = cap.read()
    if not ret:
        break

    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()

    car_count = 0
    for i in np.arange(0, detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > 0.5:
            idx = int(detections[0, 0, i, 1])
            if CLASSES[idx] == "car":
                car_count += 1
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
                label = f"Car: {confidence*100:.1f}%"
                cv2.putText(frame, label, (startX, startY-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

    # Lógica de controle do sinal
    now = time.time()
    if pedestrian_green:
        if now - last_switch > GREEN_TIME:
            if car_count >= CAR_THRESHOLD:
                pedestrian_green = False
                last_switch = now
                if arduino:
                    arduino.write(b'R')  # Sinal vermelho para pedestre
                elif args.simulador:
                    print("[SIMULADOR] Sinal de pedestre ficou VERMELHO")
    else:
        if now - last_switch > RED_TIME:
            if car_count < CAR_THRESHOLD:
                pedestrian_green = True
                last_switch = now
                if arduino:
                    arduino.write(b'G')  # Sinal verde para pedestre
                elif args.simulador:
                    print("[SIMULADOR] Sinal de pedestre ficou VERDE")

    # Exibe informações na tela
    status = "Pedestre: VERDE" if pedestrian_green else "Pedestre: VERMELHO"
    cv2.putText(frame, f"Carros: {car_count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
    cv2.putText(frame, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255) if not pedestrian_green else (0,255,0), 2)
    cv2.imshow("Deteccao de Carros", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()
