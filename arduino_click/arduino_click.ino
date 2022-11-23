/* 
 * July 26th 2022
 * Updated with debugging 11/20/2022
 * dennisjcox@gmail.com
 */

const int PTTSeconds = 5000; // they have 5 seconds to get 5 clicks
const int PlayBackDelay = 30000; // 30 seconds between play backs

int WeatherReportCount = 0;
int A0Value = 0;                        // value intialization
int count = 0;
int timedOut = 0;
int diffTimeFlag = 0;


int PTTClickCount = 0; // Count # of clicks

unsigned long boardTime = 0;
unsigned long diffTime = 0;

int start = 0;

void setup() {
  // initialize serial communications at 9600 bps:
    Serial.begin(9600);                   // Communication rate
}

void loop() 
{

 if(start == 0)
  {
//    Serial.println("Click listener process started");
    start = 1;
  }
  

  // A0 goes to the Red wire
  A0Value = analogRead(A0);


// Another way of reading... this one works on the 2nd board
  if((A0Value > 666 && A0Value < 671) || (A0Value  == 1023))
  {
//    Serial.println(A0Value); 
    count++;
  }
  else
  {
    count = 0;
  }

  // count is used to make sure the values held for at least 5 milliseconds
    if(count > 5)
      {
           Serial.print("PTT Pressed ");
	         PTTClickCount++;
	         Serial.println(PTTClickCount);
	         delay(40);
	         count = 0;
      }

  // 5 clicks plays the weather
    if(PTTClickCount == 5)
      {
          Serial.println("Play Weather");
          delay(PlayBackDelay);

    // reset variables
        count = 0;
        PTTClickCount = 0;
        diffTime = 0;
        boardTime = 0;
        diffTimeFlag =0;
      }

  if(PTTClickCount == 1 && diffTimeFlag == 0)
    {
        diffTime = millis();
        diffTimeFlag = 1;
    }
        if(diffTime > 0)
        {
           boardTime = millis();
           timedOut = boardTime - diffTime;

     if(timedOut > PTTSeconds)
      {
/*
        Serial.print("# of Clicks: ");
        Serial.print(PTTClickCount);
        Serial.print(" Board: ");
        Serial.print(boardTime);
        Serial.print(" Diff: ");
        Serial.print(diffTime);
        Serial.print(" TimedOut: ");
        Serial.print(timedOut);
        Serial.println("Timed out");
*/
        // reset variables
        PTTClickCount = 0;
        diffTime = 0;
        boardTime = 0;
        diffTimeFlag = 0;
          }
      }

  // just a delay
    delay(10);
 }
