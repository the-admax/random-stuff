//
// Created by andrew on 05.07.18.
//
#include <TimerOne.h>
#include <Arduino.h>
#include <time.h>
#include <stdlib.h>

#if HW_PRODUCTION
#define PIN_TX_ENABLE       4
#define PIN_SOUND_OUTPUT    3

#define PIN_MODE0           A0
#define PIN_MODE1           A1
#define PIN_MODE2           A2
#else
#define PIN_TX_ENABLE       13
#define PIN_SOUND_OUTPUT    3

#define PIN_DISP_CK 7
#define PIN_DISP_CS 4
#define PIN_DISP_DO 8


#define PIN_MODE0           A0
#define PIN_MODE1           A1
#define PIN_MODE2           A2
#endif

#define TICKS_IN_SECOND     1000000

#define TX_CYCLE_DURATION   120u     ///< Длина цикла передачи для всех устройств (секунды)
#define TX_MODES_COUNT      5u       ///< Кол-во уникальных кодов лис
#define TX_QUANT_DURATION   (TX_CYCLE_DURATION/TX_MODES_COUNT)
#define TX_BEEP_FREQ        500

#define TX_MORSE_DOT_TIME   1000    ///< Продолжительность точки кода Морзе
#define TX_MORSE_DASH_TIME  (3*TX_MORSE_DOT_TIME)    ///< Продолжительность "тире"

static const char * codeMessages[TX_MODES_COUNT] PROGMEM = {
    "HELLO WORLD!",
    "MOM",
    ""
};

/*
        ! "   $   &   ( )   + , - . / 0
        1 2 3 4 5 6 7 8 9 : ;   =   ? @
        A B C D E F G H I J K L M N O P
        Q R S T U V W X Y Z         _ `
*/

static const uint8_t table_codes[54] PROGMEM  = {
    0b110101, 0b10010, 0b1001000, 0b10, 0b1101, 0b101101, 0b1010, 0b110011,
    0b100001, 0b101010, 0b1001, 0b11111, 0b11110, 0b11100, 0b11000, 0b10000, 0b0,
    0b1, 0b11, 0b111, 0b1111, 0b111, 0b10101, 0b10001, 0b1100, 0b10110, 0b10, 0b1,
    0b101, 0b1, 0b0, 0b100, 0b11, 0b0, 0b0, 0b1110, 0b101, 0b10, 0b11, 0b1, 0b111,
    0b110, 0b1011, 0b10, 0b0, 0b1, 0b100, 0b1000, 0b110, 0b1001, 0b1101, 0b11,
    0b101100, 0b11110
};

static const uint8_t table_lengths[54] PROGMEM = {
    6, 6, 7, 5, 5, 6, 5, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 5, 6, 6, 2,
    4, 4, 3, 1, 4, 3, 4, 2, 4, 3, 4, 2, 2, 3, 4, 4, 3, 3, 1, 3, 4, 3, 4, 4, 4, 6, 6
};

bool beepMorse(char c, uint8_t bitIndex) {
    uint8_t sym_offs;

    if (c >= '!' && c < '#') {
        sym_offs = (c - '!') + 0;
    }  else if (c == '$') {
        sym_offs = 2;
    }  else if (c == '&') {
        sym_offs = 3;
    }  else if (c >= '(' && c < '*') {
        sym_offs = (c - '(') + 4;
    }  else if (c >= '+' && c < '<') {
        sym_offs = (c - '+') + 6;
    }  else if (c == '=') {
        sym_offs = 23;
    }  else if (c >= '?' && c < '[') {
        sym_offs = (c - '?') + 24;
    }  else if (c >= '_' && c < 'a') {
        sym_offs = (c - '_') + 52;
    }  else {
        return false;
    }

    uint8_t n_bits = pgm_read_byte(table_lengths + sym_offs); // table_lengths[sym_offs];
    uint8_t word = pgm_read_byte(table_codes + sym_offs); // table_codes[sym_offs];

    if (n_bits >= bitIndex)
        return false;

    tone(PIN_SOUND_OUTPUT, TX_BEEP_FREQ);
    delay(((word >> bitIndex) & 1)? TX_MORSE_DASH_TIME : TX_MORSE_DOT_TIME);
    noTone(PIN_SOUND_OUTPUT);
    delay(TX_MORSE_DOT_TIME);

    return true;
}

inline void startTx()
{
    digitalWrite(PIN_TX_ENABLE, 1);
}

inline void stopTx()
{
    digitalWrite(PIN_TX_ENABLE, 0);
}

static time_t lastMessageTime = 0;      ///< Момент времени последней передачи сообщения


inline
uint8_t readDeviceIndex()
{
    return (uint8_t)(digitalRead(PIN_MODE0) + (digitalRead(PIN_MODE1) << 1) + (digitalRead(PIN_MODE1) << 2));
}

/**
 * @returns Задержку начала передачи сообщения (в секундах) для выбранного режима
 * */
inline
int getDeviceDelay( uint8_t modeIdx )
{
    return modeIdx * TX_QUANT_DURATION;
}

enum {
    DM_CONFIG,      // Режим настройки (если нужен)
    DM_WAIT,        // Режим ожидания своей очереди
    DM_TXING        // Режим передачи своего сообщения
} mode = DM_CONFIG;

static const char* codeStart = NULL; // Смещение относительно начала передаваемого сообщения
static const char* codeEnd = NULL;
static uint8_t deviceIndex = 0; // Номер устройства, считывается в режиме ожидания. В момент передачи изменение ни к чему не приведёт.


static volatile uint8_t raw_segment[4];
static volatile uint8_t current_segment = 0;
static volatile bool dot = false;

void showTime() {
    static const uint8_t SEG_MAP[] = {
        0b11000000,
        0b11111001,
        0b10100100,
        0b10110000,
        0b10011001,
        0b10010010,
        0b10000010,
        0b11111000,
        0b10000000,
        0b10010000
    };

    struct tm t;
    time_t ctime = time(NULL);
    gmtime_r(&ctime, &t);

    uint16_t val = 1234;

    // Print time to segment display
    div_t d;
    d = div(t.tm_min, 10);
    raw_segment[0] = SEG_MAP[d.rem];
    raw_segment[1] = SEG_MAP[d.quot];
    raw_segment[1] ^= (dot? 0x80 : 0x00); // Turn on the dot
    d = div(t.tm_sec, 10);
    raw_segment[2] = SEG_MAP[d.rem];
    raw_segment[3] = SEG_MAP[d.quot];

    dot != dot;

//    // else remove leading zeroes
//    if (val < 1000)
//        raw_segment[0] = 0xff;
//    if (val < 100)
//        raw_segment[1] = 0xff;
//    if (val < 10)
//        raw_segment[2] = 0xff;
    
}

void updateDisplay()
{
    static const uint8_t SEG_SEL[] = {0xf1, 0xf2, 0xf4, 0xf8};

    digitalWrite(PIN_DISP_CS ,LOW);
    shiftOut(PIN_DISP_DO, PIN_DISP_CK, MSBFIRST, raw_segment[current_segment]);
    shiftOut(PIN_DISP_DO, PIN_DISP_CK, MSBFIRST, SEG_SEL[current_segment]);
    digitalWrite(PIN_DISP_CS ,HIGH);
    current_segment = (current_segment > 3) ? 0 : current_segment + 1;
}

void setup()
{
    pinMode(PIN_TX_ENABLE, OUTPUT);
    pinMode(PIN_TX_ENABLE, 1);

    pinMode(PIN_SOUND_OUTPUT, OUTPUT);

    pinMode(PIN_DISP_DO, OUTPUT);
    pinMode(PIN_DISP_CS, OUTPUT);
    pinMode(PIN_DISP_CK, OUTPUT);
}

auto lastClockUpdate = 0l;
uint8_t symbolIndex = 0;

void loop()
{
    auto dt = millis() - lastClockUpdate;
    while(dt >= 1000) {
        dt -= 1000;
        lastClockUpdate += 1000;
        if (dt < 1000)
        {
            // Компенсировать время следующего цикла в случае проскальзывания предыдущего
            lastClockUpdate -= dt;
        }

        system_tick();
        showTime();
    }

    updateDisplay();
    delay(1);

    if (mode == DM_CONFIG)
    {
        // Режим конфигурирования
        mode = DM_WAIT;
    }
    else if (mode == DM_WAIT)
    {
        deviceIndex = readDeviceIndex();
        int dt = (int)(time(NULL) - lastMessageTime) - getDeviceDelay( deviceIndex );
        // Пока время не наступило, спим. Каждый цикл спрашиваем какой всё-таки номер выбран, чтобы можно было менять
        // задержку начала передачи в любой момент.
        if (dt < 0) {
            delay(100);
        } else {
            // С таким delay-ем dt == 0 будет всегда, компенсация dt нужна если delay > 1000.
            lastMessageTime = time(NULL) - dt;

            mode = DM_TXING;
        }
    }
    else if (mode == DM_TXING)
    {
        if (codeEnd == NULL) {
            codeStart = codeMessages[deviceIndex];
            codeEnd = codeMessages[deviceIndex];
            symbolIndex = 0;
        }

        if (codeStart < codeEnd) {
            if(!beepMorse(*codeStart, symbolIndex++)) {
                codeStart++;
                symbolIndex = 0;
            }
        } else {
            codeEnd = NULL;
            mode = DM_WAIT;
        }
    }
}