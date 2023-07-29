// when the treadmil encoder is located in the front
// this version does not have the i2c feature
// include rev output for stablity
//#include <digitalWriteFast.h>
#define VERSION "20200302"
// ===== VERSIONS ======
#define MAXSPEED    1000.0f  // maximum speed for dac out (mm/sec)
#define MAXDACVOLTS 2.5f    // DAC ouput voltage at maximum speed
#define MAXDACCNTS  4095.0f // maximum dac value
//float maxDACval = MAXDACVOLTS * MAXDACCNTS / 3.3; // limit dac output to max allowed
float maxDACval = MAXDACVOLTS * MAXDACCNTS / 3.3 / 2; // limit dac output to max allowed // JR edit 5/28/19 make in both directions
#define encAPin 0
#define encBPin 1
#define dacPin  A14
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
  if (ENCA == ENCB )    // figure out the direction
  {
    Serial.print('F');
    dir = FW;
    thisUsecs = micros();
    encoderUsecs = thisUsecs - lastUsecs;
    lastUsecs = thisUsecs;
    runSpeed = (float)MM_PER_COUNT / encoderUsecs;
    distance += DIST_PER_COUNT;
    counts += 1;
  }
  else
  {
    Serial.print('B');
    dir = BW;
    thisUsecs = micros();
    encoderUsecs = thisUsecs - lastUsecs;
    lastUsecs = thisUsecs;
    runSpeed = (float)MM_PER_COUNT / encoderUsecs* -1;
    distance -= DIST_PER_COUNT;
    counts -= 1;
  }
}
void setup()
{
  //Serial.begin(115200);
  //Serial2.begin(115200);
  Serial.begin(19200);
  Serial2.begin(19200);
  //while ( !Serial);  // if no serial USB is connected, may need to comment this out
  pinMode(encAPin, INPUT_PULLUP); // sets the digital pin as input
  pinMode(encBPin, INPUT_PULLUP); // sets the digital pin as input
  analogWriteResolution(12);
  Serial.print("Treadmill Interface V: ");
  Serial.println(VERSION);
  Serial.println("distance,speed");
  Serial.println(maxDACval);
  lastUsecs = micros();
  attachInterrupt(encAPin, encoderInt, RISING); // check encoder every A pin rising edge
}
void loop()
{
  noInterrupts();
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
    Serial.println(runSpeed);
    int a=(uint16_t)dacval-730;
    analogWrite(A14, (uint16_t) dacval);
    Serial.println("iiiiiiiiiiiiiii");
    Serial.println(a);

    Serial2.write(counts);//Serial2.write(a);
  }
  //  Serial.println(distance);
}