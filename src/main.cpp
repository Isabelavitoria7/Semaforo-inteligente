#include <Arduino.h>

/*
  Semáforo Inteligente — Cruzamento de 2 vias de mão única
  =========================================================
  Mapeamento de pinos:
    Rua 1  — Carros : Verde=4 | Vermelho=5
    Rua 2  — Carros : Verde=6 | Vermelho=7
    Ped Rua 1 (2 semáforos sincronizados): Verde=8  | Vermelho=9
    Ped Rua 2 (2 semáforos sincronizados): Verde=10 | Vermelho=11
    Botão pedestre Rua 1 : pino 2 (interrupção INT0)
    Botão pedestre Rua 2 : pino 3 (interrupção INT1)

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
#define RUA1_CAR_AMAR 12
#define RUA1_CAR_VERM 5

// --- Pinos Rua 2 (carros) ---
#define RUA2_CAR_VERDE 6
#define RUA2_CAR_AMAR 13
#define RUA2_CAR_VERM 7

// --- Pinos Pedestre Rua 1 (2 semáforos sincronizados) ---
#define PED_RUA1_VERDE 8
#define PED_RUA1_VERM 9

// --- Pinos Pedestre Rua 2 (2 semáforos sincronizados) ---
#define PED_RUA2_VERDE 10
#define PED_RUA2_VERM 11

// --- Botões ---
#define BTN_RUA1 2 // INT0
#define BTN_RUA2 3 // INT1

// --- Debounce ---
#define DEBOUNCE_MS 200

volatile bool btn1Pressed = false;
volatile bool btn2Pressed = false;
unsigned long lastBtn1 = 0;
unsigned long lastBtn2 = 0;

// Interrupções dos botões
void ISR_btn1()
{
  unsigned long now = millis();
  if (now - lastBtn1 > DEBOUNCE_MS)
  {
    btn1Pressed = true;
    lastBtn1 = now;
  }
}

void ISR_btn2()
{
  unsigned long now = millis();
  if (now - lastBtn2 > DEBOUNCE_MS)
  {
    btn2Pressed = true;
    lastBtn2 = now;
  }
}

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

  // Interrupções nos flancos de descida (botão pressionado = LOW)
  attachInterrupt(digitalPinToInterrupt(BTN_RUA1), ISR_btn1, FALLING);
  attachInterrupt(digitalPinToInterrupt(BTN_RUA2), ISR_btn2, FALLING);

  Serial.begin(9600);

  // Estado inicial: Rua 1 aberta para carros
  setRua1Aberta();
}

void loop()
{
  // Reportar botões ao Python
  if (btn1Pressed)
  {
    btn1Pressed = false;
    Serial.write('1');
  }
  if (btn2Pressed)
  {
    btn2Pressed = false;
    Serial.write('2');
  }

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
