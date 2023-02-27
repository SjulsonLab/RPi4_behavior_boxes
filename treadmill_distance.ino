// when the treadmil encoder is located in the front
// include rev output for stablity
//#include <digitalWriteFast.h>
#include <Wire.h>
#include <I2C_Anything.h> //developed by Nick Gammon.

#define VERSION "20220130"
// ===== VERSIONS ======
#define MAXSPEED    1000.0f  // maximum speed for dac out (mm/sec)
#define MAXDACVOLTS 2.5f    // DAC ouput voltage at maximum speed
#define MAXDACCNTS  4095.0f // maximum dac value
//float maxDACval = MAXDACVOLTS * MAXDACCNTS / 3.3; // limit dac output to max allowed
float maxDACval = MAXDACVOLTS * MAXDACCNTS / 3.3 / 2; // limit dac output to max allowed // JR edit 5/28/19 make in both directions
#define encAPin 0
#define encBPin 1
//#define dacPin  A14
//#define idxPin  2  // not used here
// counts per rotation of treadmill encoder wheel
// 200 counts per rev
// 1.03" per rev
// so - 1.03 * 25.4 * pi / 200 /1000 = microns/cnt
#define MM_PER_COUNT 410950  // actually 1/10^6mm per count since we divide by usecs
#define DIST_PER_COUNT ((float)MM_PER_COUNT/1000000.0)
//(float)0.41095
#define SPEED_TIMEOUT 50000  // if we don't move in this many microseconds assume we are stopped
static float runSpeed = 0;
static float lastSpeed = 0;
volatile uint32_t lastUsecs;
volatile uint32_t thisUsecs;
volatile uint32_t encoderUsecs;
volatile float distance = 0;
int counts = 0; // net count
int countAdj = 0; // 0-250 and 0-50 for negative 50-250 for positive
//int rev = 0;//count revolution
#define FW 1
#define BW -1
int dir = FW;
// ------------------------------------------
// interrupt routine for ENCODER_A rising edge
// ---------------------------------------------
void encoderInt()
{
  int ENCA = digitalRead(encAPin);  // always update output
  int ENCB = digitalRead(encBPin);

  thisUsecs = micros();
  encoderUsecs = thisUsecs - lastUsecs;
  lastUsecs = thisUsecs;

  if (ENCA == ENCB )    // figure out the direction
  {
    Serial.print('F');
    dir = FW;
    counts += 1;
    runSpeed = (float)MM_PER_COUNT / encoderUsecs;
    distance += DIST_PER_COUNT;
  }
  else
  {
    Serial.print('B');
    dir = BW;
    counts -= 1;
    runSpeed = (float)MM_PER_COUNT / encoderUsecs* -1;
    distance -= DIST_PER_COUNT;
  }
}
void setup()
{
//  Serial.begin(9600); //for Uno
  Serial.begin(19200); //for Teensy
  pinMode(encAPin, INPUT_PULLUP); // sets the digital pin as input
  pinMode(encBPin, INPUT_PULLUP); // sets the digital pin as input

  Serial.print("Treadmill Interface V: ");
  Serial.println(VERSION);
  Serial.println("distance,speed");
  Serial.println(maxDACval);

  Wire.begin(8);
//  Wire.setSDA(A4);
//  Wire.setSCL(A5);
  Wire.onRequest(sendData);

  lastUsecs = micros();
  attachInterrupt(encAPin, encoderInt, RISING); // check encoder every A pin rising edge
  Serial.println("setup finished"); // for debug purpose
}
void loop()
{
  noInterrupts();
//  Serial.println("loop started"); // debug purpose
  uint32_t now = micros();
  uint32_t lastU = lastUsecs;
  if ( (now > lastU) && ((now - lastU) > SPEED_TIMEOUT)  )
  { // now should never be < lastUsecs, but sometiems it is
    // I question if noInterupts works
    runSpeed = 0;
  }
  interrupts();
  if ( runSpeed != lastSpeed )
  {
    lastSpeed = runSpeed;
    //    float dacval = runSpeed / MAXSPEED * maxDACval;
    float dacval = (.5 + runSpeed / MAXSPEED) * maxDACval;
    if ( dacval < 0 ) dacval = 0;
    if ( dacval > maxDACval) dacval = maxDACval;
    //Serial.print(distance);
    countAdj = counts+50;
    if (countAdj>250)
    {
    counts=1;
    countAdj = 51;
    }
    if (counts<-50){
      counts = -50;
      countAdj = 0;
    }
    Serial.print(countAdj);
    Serial.print(",");
    Serial.println(distance);
    int a=(uint16_t)dacval-730; // what is a?
//    analogWrite(A14, (uint16_t) dacval);
    Serial.println("iiiiiiiiiiiiiii");
    Serial.println(a);
//    Serial.println(counts);

//    Serial2.write(counts);//Serial2.write(a);
  }
  //  Serial.println(distance);
}

void sendData()
{
//  long Dst = distance;
//  long Spd = runSpeed;
//  long data = (Dst << 8) | Spd;
//  Wire.write(data);
//  Serial.println(data);
  I2C_writeAnything (distance); //for transmitting the count as data
//  Wire.write("iiiiiiiiiiiiiii");
//  Wire.write(a);
}