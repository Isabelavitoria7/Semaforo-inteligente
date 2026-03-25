/*
  Sistema de semáforo inteligente para pedestres e carros
  Recebe comandos via Serial ('G' para verde pedestre, 'R' para vermelho pedestre)
  Controla LEDs para simular os sinais
*/

#define LED_PED_VERDE 2    // LED verde do pedestre
#define LED_PED_VERMELHO 3 // LED vermelho do pedestre
#define LED_CAR_VERDE 4    // LED verde da rua
#define LED_CAR_VERMELHO 5 // LED vermelho da rua

void setup()
{
    pinMode(LED_PED_VERDE, OUTPUT);
    pinMode(LED_PED_VERMELHO, OUTPUT);
    pinMode(LED_CAR_VERDE, OUTPUT);
    pinMode(LED_CAR_VERMELHO, OUTPUT);
    Serial.begin(9600);
    // Estado inicial: pedestre vermelho, carro verde
    digitalWrite(LED_PED_VERDE, LOW);
    digitalWrite(LED_PED_VERMELHO, HIGH);
    digitalWrite(LED_CAR_VERDE, HIGH);
    digitalWrite(LED_CAR_VERMELHO, LOW);
}

void loop()
{
    if (Serial.available())
    {
        char comando = Serial.read();
        if (comando == 'G')
        {
            // Abrir sinal para pedestre
            digitalWrite(LED_PED_VERDE, HIGH);
            digitalWrite(LED_PED_VERMELHO, LOW);
            digitalWrite(LED_CAR_VERDE, LOW);
            digitalWrite(LED_CAR_VERMELHO, HIGH);
        }
        else if (comando == 'R')
        {
            // Fechar sinal para pedestre
            digitalWrite(LED_PED_VERDE, LOW);
            digitalWrite(LED_PED_VERMELHO, HIGH);
            digitalWrite(LED_CAR_VERDE, HIGH);
            digitalWrite(LED_CAR_VERMELHO, LOW);
        }
    }
}
