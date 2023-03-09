/* 
 * July 26th 2022
 * Updated with debugging 11/20/2022
 * dennisjcox@gmail.com
 */



const int PTTSeconds = 5000;  // NOTE: Change this value to the maximum click count you want - so 7000 for 7 seconds 5000 for 5 seconds  3000 for 3 seconds
const int PlayBackDelay = 30000; // 30 seconds between play backs

int ClickSuccessFlag = 0;
int WeatherReportCount = 0;
int A0Value = 0;                        // value intialization
int count = 0;
int timedOut = 0;
int diffTimeFlag = 0;

int PTTClickCount = 0; // Count # of clicks

unsigned long boardTime = 0;
unsigned long diffTime = 0;

int catchFallingFlag = 0; // this is used to make sure it isn't just 1023 non stop
int start = 0;

void setup() {
  // initialize serial communications at 9600 bps:
    Serial.begin(9600);                   // Communication rate
}



void loop() 
{

 if(start == 0)
  {
    Serial.println("Click listener process started");
    start = 1;
  }
  

  // A0 goes to the Red wire
  A0Value = analogRead(A0);

 // Serial.println(A0Value);
  
// Make sure its max press and that we aren't just holding the PTT
  if(A0Value == 1023 && catchFallingFlag == 0)
  {
 //   Serial.println(A0Value); 
    count++;
  }
  else
  {
    // we got a non-1023 value so we can say the person let go of the PTT
    catchFallingFlag = 0;
    count = 0;
  }

  // count is used to make sure the values held for at least 5 milliseconds
  if(count > 3)
  {
     // Count each time we get a press
     PTTClickCount++;
     catchFallingFlag = 1;
     Serial.print("PTT Pressed ");
     Serial.println(PTTClickCount);
     count = 0;
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
        Serial.println(" .");
*/

	if(PTTClickCount == 5)
	{
	  Serial.println("5 Clicks");
	  delay(PlayBackDelay);
	}
   
      
        // reset variables
	      count = 0;
        PTTClickCount = 0;
        diffTime = 0;
        boardTime = 0;
        diffTimeFlag = 0;
      }
    }

  // just a delay
    delay(10);
}
