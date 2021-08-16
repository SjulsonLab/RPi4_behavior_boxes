#include "stdio.h"
#include "wiringPi.h"
#include "time.h"
#include "stdlib.h"

#define STEP_PER_MM 1600

#define POKE1_PIN   21
#define POKE2_PIN   22
#define POKE3_PIN   26
#define LED1_PIN    11
#define LED2_PIN    10
#define LED3_PIN    13
#define BEEP1_PIN   3
#define BEEP2_PIN   1
#define BEEP3_PIN   0
#define PWM1_PIN    24
#define PWM2_PIN    28
#define PWM3_PIN    29
#define PWM_EN      6

unsigned int Elimination_Buffeting_Time[3] = {10, 10, 10};
unsigned int Trigger_Time[3] = {1000, 1000, 1000};
float Bolus_Step[3] = {0.1f, 0.1f, 0.1f};
unsigned long long Stop_Time[3] = {0, 0, 0};
unsigned long long timer_counter = 0;
unsigned char Alert_Flag[3] = {0, 0, 0};

PI_THREAD (Timer_Task){
    while (1){
        timer_counter++;
        delay(1);
    }
}

PI_THREAD (PWM_Universal){
    while (1)
    {
        if (Alert_Flag[0] != 0) {
            Alert_Flag[0]--;
            digitalWrite(LED1_PIN, !digitalRead(LED1_PIN));
            digitalWrite(BEEP1_PIN, HIGH);
        } else {
            digitalWrite(LED1_PIN, LOW);
            digitalWrite(BEEP1_PIN, LOW);
        }
        if (Alert_Flag[1] != 0) {
            Alert_Flag[1]--;
            digitalWrite(LED2_PIN, !digitalRead(LED2_PIN));
            digitalWrite(BEEP2_PIN, HIGH);
        } else {
            digitalWrite(LED2_PIN, LOW);
            digitalWrite(BEEP2_PIN, LOW);
        }
        if (Alert_Flag[2] != 0) {
            Alert_Flag[2]--;
            digitalWrite(LED3_PIN, !digitalRead(LED3_PIN));
            digitalWrite(BEEP3_PIN, HIGH);
        } else {
            digitalWrite(LED3_PIN, LOW);
            digitalWrite(BEEP3_PIN, LOW);
        }
        delay(500);
    }
}

PI_THREAD (PWM1_Out) {
    piLock(0);
    int step = (STEP_PER_MM * Bolus_Step[0]) / 1;
    for (unsigned int counter = 0; counter < step; counter++) {
        digitalWrite(PWM1_PIN, HIGH);
        delayMicroseconds(100);
        digitalWrite(PWM1_PIN, LOW);
        delayMicroseconds(100);
    }
    piUnlock(0);
    Stop_Time[0] = timer_counter;
    return 0;
}

PI_THREAD (PWM2_Out) {
    piLock(1);
    int step = (STEP_PER_MM * Bolus_Step[1]) / 1;
    for (unsigned int counter = 0; counter < step; counter++) {
        digitalWrite(PWM2_PIN, HIGH);
        delayMicroseconds(100);
        digitalWrite(PWM2_PIN, LOW);
        delayMicroseconds(100);
    }
    piUnlock(1);
    Stop_Time[1] = timer_counter;
    return 0;
}

PI_THREAD (PWM3_Out) {
    piLock(2);
    int step = (STEP_PER_MM * Bolus_Step[2]) / 1;
    for (unsigned int counter = 0; counter < step; counter++) {
        digitalWrite(PWM3_PIN, HIGH);
        delayMicroseconds(100);
        digitalWrite(PWM3_PIN, LOW);
        delayMicroseconds(100);
    }
    piUnlock(2);
    Stop_Time[2] = timer_counter;
    return 0;
}

int Init_IOs(unsigned int uElimination_Buffeting_Time1,
             unsigned int uElimination_Buffeting_Time2,
             unsigned int uElimination_Buffeting_Time3,
             unsigned int uTrigger_Time1, unsigned int uTrigger_Time2, unsigned int uTrigger_Time3,
             double uBolus_Step1, double uBolus_Step2, double uBolus_Step3) {
    Elimination_Buffeting_Time[0] = uElimination_Buffeting_Time1;
    Elimination_Buffeting_Time[1] = uElimination_Buffeting_Time2;
    Elimination_Buffeting_Time[2] = uElimination_Buffeting_Time3;
    Trigger_Time[0] = uTrigger_Time1;
    Trigger_Time[1] = uTrigger_Time2;
    Trigger_Time[2] = uTrigger_Time3;
    Bolus_Step[0] = (float) uBolus_Step1;
    Bolus_Step[1] = (float) uBolus_Step2;
    Bolus_Step[2] = (float) uBolus_Step3;
    if (-1 == wiringPiSetup()) {
        printf("wiringPi Setup Error\n");
        fflush(stdout);
        return -1;
    }
    pinMode(POKE1_PIN, INPUT);
    pullUpDnControl(POKE1_PIN, PUD_DOWN);
    pinMode(POKE2_PIN, INPUT);
    pullUpDnControl(POKE2_PIN, PUD_DOWN);
    pinMode(POKE3_PIN, INPUT);
    pullUpDnControl(POKE3_PIN, PUD_DOWN);
    pinMode(PWM1_PIN, OUTPUT);
    pullUpDnControl(PWM1_PIN, PUD_OFF);
    pinMode(PWM2_PIN, OUTPUT);
    pullUpDnControl(PWM2_PIN, PUD_OFF);
    pinMode(PWM3_PIN, OUTPUT);
    pullUpDnControl(PWM3_PIN, PUD_OFF);
    pinMode(LED1_PIN, OUTPUT);
    pullUpDnControl(LED1_PIN, PUD_OFF);
    pinMode(LED2_PIN, OUTPUT);
    pullUpDnControl(LED2_PIN, PUD_OFF);
    pinMode(LED3_PIN, OUTPUT);
    pullUpDnControl(LED3_PIN, PUD_OFF);
    pinMode(BEEP1_PIN, OUTPUT);
    pullUpDnControl(BEEP1_PIN, PUD_OFF);
    pinMode(BEEP2_PIN, OUTPUT);
    pullUpDnControl(BEEP2_PIN, PUD_OFF);
    pinMode(BEEP3_PIN, OUTPUT);
    pullUpDnControl(BEEP3_PIN, PUD_OFF);
    pinMode(PWM_EN, OUTPUT);
    pullUpDnControl(PWM_EN, PUD_OFF);
    digitalWrite(PWM1_PIN, LOW);
    digitalWrite(PWM2_PIN, LOW);
    digitalWrite(PWM3_PIN, LOW);
    piThreadCreate(Timer_Task);
    piThreadCreate(PWM_Universal);
    return 0;
}

int join(void)
{
    if (digitalRead(POKE1_PIN) == 1) {
        delay(Elimination_Buffeting_Time[0]);
        if (digitalRead(POKE1_PIN) == 1 &&
            (timer_counter - Stop_Time[0]) > Trigger_Time[0]) {
            Stop_Time[0] = timer_counter;
            printf("Poke1 Trigged\r\n");
            fflush(stdout);
            piThreadCreate(PWM1_Out);
            Alert_Flag[0] = 20;
            return 1;
        }
    }
    if (digitalRead(POKE2_PIN) == 1) {
        delay(Elimination_Buffeting_Time[1]);
        if (digitalRead(POKE2_PIN) == 1 &&
            (timer_counter - Stop_Time[1]) > Trigger_Time[1]) {
            Stop_Time[1] = timer_counter;
            printf("Poke2 Trigged\r\n");
            fflush(stdout);
            piThreadCreate(PWM2_Out);
            Alert_Flag[1] = 20;
            return 2;
        }
    }
    if (digitalRead(POKE3_PIN) == 1) {
        delay(Elimination_Buffeting_Time[2]);
        if (digitalRead(POKE3_PIN) == 1 &&
            (timer_counter - Stop_Time[2]) > Trigger_Time[2]) {
            Stop_Time[2] = timer_counter;
            printf("Poke3 Trigged\r\n");
            fflush(stdout);
            piThreadCreate(PWM3_Out);
            Alert_Flag[2] = 20;
            return 3;
        }
    }
    delay(1);
    return 0;
}
