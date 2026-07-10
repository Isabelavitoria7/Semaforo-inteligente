#include <Arduino.h>

/*
  Semáforo Inteligente — Cruzamento de 2 vias de mão única
  =========================================================
  Mapeamento de pinos:
    Rua 1  — Carros : Verde=4 | Amarelo=3 | Vermelho=2
    Rua 2  — Carros : Verde=7 | Amarelo=6 | Vermelho=5
    Ped Rua 1 (2 semáforos sincronizados): Verde=9  | Vermelho=8
    Ped Rua 2 (2 semáforos sincronizados): Verde=11 | Vermelho=10
    Botão pedestre Rua 1 : A0 (pino 14) — polling
    Botão pedestre Rua 2 : A1 (pino 15) — polling

  Protocolo Serial (Python → Arduino):
    'A' = Rua1 verde,   Rua2 vermelho, PedRua1 vermelho, PedRua2 verde
    'B' = Rua2 verde,   Rua1 vermelho, PedRua2 vermelho, PedRua1 verde
    'C' = Rua1 amarelo, Rua2 vermelho  (transição segura saindo de A)
    'D' = Rua2 amarelo, Rua1 vermelho  (transição segura saindo de B)
    'P' = Todos carros vermelho, todos pedestres verde

  Protocolo Serial (Arduino → Python):
    '1' = Botão pedestre Rua1 pressionado
    '2' = Botão pedestre Rua2 pressionado
*/

// --- Pinos Rua 1 (carros) ---
#define RUA1_CAR_VERDE 4
#define RUA1_CAR_AMAR 3
#define RUA1_CAR_VERM 2

// --- Pinos Rua 2 (carros) ---
#define RUA2_CAR_VERDE 7
#define RUA2_CAR_AMAR 6
#define RUA2_CAR_VERM 5

// --- Pinos Pedestre Rua 1 (2 semáforos sincronizados) ---
#define PED_RUA1_VERDE 9
#define PED_RUA1_VERM 8

// --- Pinos Pedestre Rua 2 (2 semáforos sincronizados) ---
#define PED_RUA2_VERDE 11
#define PED_RUA2_VERM 10

// --- Botões (A0=14, A1=15 — polling, sem interrupção no UNO) ---
#define BTN_RUA1 14 // A0
#define BTN_RUA2 15 // A1

// --- Debounce ---
#define DEBOUNCE_MS 200

unsigned long lastBtn1 = 0;
unsigned long lastBtn2 = 0;
bool lastState1 = HIGH;
bool lastState2 = HIGH;

// Aplica estado: Rua1 amarelo, Rua2 vermelho (todos pedestres fechados — transição)
void setRua1Amarela()
{
  digitalWrite(RUA1_CAR_VERDE, LOW);
  digitalWrite(RUA1_CAR_AMAR, HIGH);
  digitalWrite(RUA1_CAR_VERM, LOW);
  digitalWrite(RUA2_CAR_VERDE, LOW);
  digitalWrite(RUA2_CAR_AMAR, LOW);
  digitalWrite(RUA2_CAR_VERM, HIGH);
  digitalWrite(PED_RUA1_VERDE, LOW);
  digitalWrite(PED_RUA1_VERM, HIGH);
  digitalWrite(PED_RUA2_VERDE, LOW);
  digitalWrite(PED_RUA2_VERM, HIGH);
}

// Aplica estado: Rua2 amarelo, Rua1 vermelho (todos pedestres fechados — transição)
void setRua2Amarela()
{
  digitalWrite(RUA2_CAR_VERDE, LOW);
  digitalWrite(RUA2_CAR_AMAR, HIGH);
  digitalWrite(RUA2_CAR_VERM, LOW);
  digitalWrite(RUA1_CAR_VERDE, LOW);
  digitalWrite(RUA1_CAR_AMAR, LOW);
  digitalWrite(RUA1_CAR_VERM, HIGH);
  digitalWrite(PED_RUA1_VERDE, LOW);
  digitalWrite(PED_RUA1_VERM, HIGH);
  digitalWrite(PED_RUA2_VERDE, LOW);
  digitalWrite(PED_RUA2_VERM, HIGH);
}

// Aplica estado: Rua1 verde, Rua2 vermelho, PedRua1 vermelho, PedRua2 verde
void setRua1Aberta()
{
  digitalWrite(RUA1_CAR_VERDE, HIGH);
  digitalWrite(RUA1_CAR_AMAR, LOW);
  digitalWrite(RUA1_CAR_VERM, LOW);
  digitalWrite(RUA2_CAR_VERDE, LOW);
  digitalWrite(RUA2_CAR_AMAR, LOW);
  digitalWrite(RUA2_CAR_VERM, HIGH);
  digitalWrite(PED_RUA1_VERDE, LOW);
  digitalWrite(PED_RUA1_VERM, HIGH);
  digitalWrite(PED_RUA2_VERDE, HIGH);
  digitalWrite(PED_RUA2_VERM, LOW);
}

// Aplica estado: Rua2 verde, Rua1 vermelho, PedRua2 vermelho, PedRua1 verde
void setRua2Aberta()
{
  digitalWrite(RUA2_CAR_VERDE, HIGH);
  digitalWrite(RUA2_CAR_AMAR, LOW);
  digitalWrite(RUA2_CAR_VERM, LOW);
  digitalWrite(RUA1_CAR_VERDE, LOW);
  digitalWrite(RUA1_CAR_AMAR, LOW);
  digitalWrite(RUA1_CAR_VERM, HIGH);
  digitalWrite(PED_RUA2_VERDE, LOW);
  digitalWrite(PED_RUA2_VERM, HIGH);
  digitalWrite(PED_RUA1_VERDE, HIGH);
  digitalWrite(PED_RUA1_VERM, LOW);
}

// Aplica estado: Todos carros vermelho, todos pedestres verde
void setPedestreAberto()
{
  digitalWrite(RUA1_CAR_VERDE, LOW);
  digitalWrite(RUA1_CAR_AMAR, LOW);
  digitalWrite(RUA1_CAR_VERM, HIGH);
  digitalWrite(RUA2_CAR_VERDE, LOW);
  digitalWrite(RUA2_CAR_AMAR, LOW);
  digitalWrite(RUA2_CAR_VERM, HIGH);
  digitalWrite(PED_RUA1_VERDE, HIGH);
  digitalWrite(PED_RUA1_VERM, LOW);
  digitalWrite(PED_RUA2_VERDE, HIGH);
  digitalWrite(PED_RUA2_VERM, LOW);
}

void setup()
{
  // Saídas
  pinMode(RUA1_CAR_VERDE, OUTPUT);
  pinMode(RUA1_CAR_AMAR, OUTPUT);
  pinMode(RUA1_CAR_VERM, OUTPUT);
  pinMode(RUA2_CAR_VERDE, OUTPUT);
  pinMode(RUA2_CAR_AMAR, OUTPUT);
  pinMode(RUA2_CAR_VERM, OUTPUT);
  pinMode(PED_RUA1_VERDE, OUTPUT);
  pinMode(PED_RUA1_VERM, OUTPUT);
  pinMode(PED_RUA2_VERDE, OUTPUT);
  pinMode(PED_RUA2_VERM, OUTPUT);

  // Entradas com pull-up interno
  pinMode(BTN_RUA1, INPUT_PULLUP);
  pinMode(BTN_RUA2, INPUT_PULLUP);

  // A0 e A1 não suportam interrupções no UNO — usando polling no loop()

  Serial.begin(9600);

  // Estado inicial: Rua 1 aberta para carros
  setRua1Aberta();
}

void loop()
{
  // Leitura de botões por polling com debounce (A0/A1 não suportam interrupção)
  unsigned long now = millis();
  bool state1 = digitalRead(BTN_RUA1);
  bool state2 = digitalRead(BTN_RUA2);

  if (state1 == LOW && lastState1 == HIGH && (now - lastBtn1 > DEBOUNCE_MS))
  {
    lastBtn1 = now;
    Serial.write('1');
  }
  lastState1 = state1;

  if (state2 == LOW && lastState2 == HIGH && (now - lastBtn2 > DEBOUNCE_MS))
  {
    lastBtn2 = now;
    Serial.write('2');
  }
  lastState2 = state2;

  // Processar comandos recebidos do Python
  if (Serial.available())
  {
    char cmd = Serial.read();
    switch (cmd)
    {
    case 'A':
      setRua1Aberta();
      break;
    case 'B':
      setRua2Aberta();
      break;
    case 'C':
      setRua1Amarela();
      break;
    case 'D':
      setRua2Amarela();
      break;
    case 'P':
      setPedestreAberto();
      break;
    default:
      break;
    }
  }
}
