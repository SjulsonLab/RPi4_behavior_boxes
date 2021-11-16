// EncoderInterfaceT3
//
//  Read the encoder and translate to a distance and send over USB-Serial and DAC
//  Teensy 3.2 Arduino 1.8.3 with Teensy Extensions
//
//  This designed to be easy to assemble. The cables are soldered directly to Teensy 3.2.
//  Encoder A - pin 2
//  Encoder B - pin 3
//  Encoder VCC - Vin
//  Encoder ground - GND
//  Analog Out - A4/DAC
//  Analog ground - AGND
//
// Steve Sawtelle
// jET
// Janelia
// HHMI 
//

#define VERSION "20180207"
// ===== VERSIONS ======

#include <Servo.h>
#include <Wire.h>
#include <digitalWriteFast.h>
#include <Bounce2.h>

#define MAXSPEED    1000.0f  // maximum speed for dac out (mm/sec)
#define MAXDACVOLTS 2.5f    // DAC ouput voltage at maximum speed
#define MAXDACCNTS  4095.0f // maximum dac value

float maxDACval = MAXDACVOLTS * MAXDACCNTS / 3.3; // limit dac output to max allowed

#define encAPin 2
#define encBPin 3
#define dacPin A14
//#define idxPin  2  // not used here

// counts per rotation of treadmill encoder wheel
// 200 counts per rev
// 1.03" per rev
// so - 1.03 * 25.4 * pi / 200 /1000 = microns/cnt

#define MM_PER_COUNT 410950  // actually 1/10^6mm per count since we divide by usecs
#define DIST_PER_COUNT ((float)MM_PER_COUNT/1000000 .0)
//(float)0.41095

#define SPEED_TIMEOUT 50000  // if we don't move in this many microseconds assume we are stopped

static float runSpeed = 0;
static float lastSpeed = 0;
volatile uint32_t lastUsecs;
volatile uint32_t thisUsecs;
volatile uint32_t encoderUsecs;
volatile float distance = 0;
long data = "";
unsigned int lastEncoded = 0;
unsigned int encoderValue = 0;

Bounce A = Bounce();
Bounce B = Bounce();

#define FW 1
#define BW -1
int dir = FW;

// ------------------------------------------
// interrupt routine for ENCODER_A rising edge
// ---------------------------------------------
void encoderInt()
{   
  int ENCA = A.read();  // always update output 
  int ENCB = B.read(); 

  int encoded = (ENCA << 1) | ENCB; //converting the 2 pin value to single number
  int sum  = (lastEncoded << 2) | encoded; //adding it to the previous encoded value
  if (sum == 0b1110 || sum == 0b0111 || sum == 0b0001 || sum == 0b1000)    // figure out the direction  
  {   
    //Serial.print('B');
    dir = BW;
    runSpeed = 0;
  }  
  if (sum == 0b1101 || sum == 0b0100 || sum == 0b0010 || sum == 0b1011)
  {
    //Serial.print('F');
    dir = FW;
    thisUsecs = micros();
    encoderUsecs = thisUsecs - lastUsecs;
    lastUsecs = thisUsecs;
    runSpeed = (float)MM_PER_COUNT / encoderUsecs;
    distance += DIST_PER_COUNT;
  }
  lastEncoded = encoded;  
}


void setup()
{
  Serial.begin(19200);
  while( !Serial);   // if no serial USB is connected, may need to comment this out
  A.attach(encAPin, INPUT_PULLUP); // sets the digital pin as input
  B.attach(encBPin, INPUT_PULLUP); // sets the digital pin as input
  A.interval(2);
  B.interval(2);
  //analogWriteResolution(12);

  Serial.print("Treadmill Interface V: ");
  Serial.println(VERSION);
  Serial.println("distance,speed");
  Serial.println(maxDACval);

  // setup pins for I2C
  Wire.setSDA(18)
  Wire.setSCL(19)

  Wire.begin(8);                // join i2c bus with address #8
  Wire.onRequest(sendData);  // register event

  lastUsecs = micros();
  attachInterrupt(digitalPinToInterrupt(2), encoderInt, CHANGE); // check encoder every A pin rising edge
  attachInterrupt(digitalPinToInterrupt(3), encoderInt, CHANGE);
}

void loop() 
{ 
  A.update();
  B.update();
  
  noInterrupts();
  uint32_t now = micros();
  uint32_t lastU = lastUsecs;
  if( (now > lastU) && ((now - lastU) > SPEED_TIMEOUT)  )
  {   // now should never be < lastUsecs, but sometiems it is
      // I question if noInterupts works
     runSpeed = 0;     
  }        
  interrupts(); 

  if( runSpeed != lastSpeed && runSpeed != 0)
  {   
      lastSpeed = runSpeed;
    
      float dacval = runSpeed/MAXSPEED * maxDACval; 
      if( dacval < 0 ) dacval = 0;
      if( dacval > maxDACval) dacval = maxDACval;
      Serial.print(distance);
      Serial.print(",");
      Serial.println(runSpeed);    
      analogWrite(A4,(uint16_t) dacval);
  }
}

void sendData()
{
  long Dst = distance;
  long Spd = runSpeed;
  long data = (Dst << 8) | Spd;
  Wire.write(data);
  Serial.println(data);
}
