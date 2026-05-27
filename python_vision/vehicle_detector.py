"""
vehicle_detector.py
-------------------
Encapsula o modelo MobileNet SSD para detecção de veículos em um frame de câmera.

Uso:
    detector = VehicleDetector(prototxt="...", model="...")
    count, annotated_frame = detector.detect(frame)
"""

import cv2
import numpy as np

# Rótulos do modelo MobileNet SSD
CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
    "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
    "sofa", "train", "tvmonitor",
]

VEHICLE_CLASSES = {"car", "bus", "motorbike"}
CONFIDENCE_THRESHOLD = 0.5


class VehicleDetector:
    """Detecta veículos (carro, ônibus, moto) em um frame usando MobileNet SSD."""

    def __init__(self, prototxt: str, model: str) -> None:
        self.net = cv2.dnn.readNetFromCaffe(prototxt, model)

    def detect(self, frame) -> tuple:
        """
        Executa a detecção no frame fornecido.

        Parâmetros
        ----------
        frame : np.ndarray
            Frame BGR capturado pela câmera.

        Retorna
        -------
        count : int
            Número de veículos detectados com confiança > CONFIDENCE_THRESHOLD.
        annotated : np.ndarray
            Cópia do frame com bounding boxes desenhados.
        """
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5
        )
        self.net.setInput(blob)
        detections = self.net.forward()

        count = 0
        annotated = frame.copy()

        for i in np.arange(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > CONFIDENCE_THRESHOLD:
                idx = int(detections[0, 0, i, 1])
                label_name = CLASSES[idx]
                if label_name in VEHICLE_CLASSES:
                    count += 1
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    cv2.rectangle(annotated, (startX, startY), (endX, endY), (0, 255, 0), 2)
                    text = f"{label_name}: {confidence * 100:.1f}%"
                    cv2.putText(
                        annotated, text, (startX, startY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2,
                    )

        return count, annotated
