/* 
 * July 26th 2022
 * Updated with debugging 11/20/2022
 * dennisjcox@gmail.com
 * amendet by Johann Wiesheu; av.wiesheu@bayern-mail.de 31Dec2022:
 */

/* CAUTION: One or more of these values must be set */

/* Set this value to 1 to allow for 3 click support */
int THREECLICK = 1;

/* Set this value to 1 to allow for 5 click support */
int FIVECLICK = 1;

/* Set this value to 1 to allow for 7 click support */
int SEVENCLICK = 1;


const int PTTSeconds = 5000;  // NOTE: Change this value to the maximum click count you want - so 7000 for 7 seconds 5000 for 5 seconds  3000 for 3 seconds
//const int PlayBackDelay = 30000; // 30 seconds between actions - not needed any more because of RTS/CTS signal from rPi

int ClickSuccessFlag = 0;
int PTTClickCount = 0;         // Count # of clicks
int A0Value = 0;               // value intialization
int count = 0;
int timedOut = 0;
int diffTimeFlag = 0;
unsigned long boardTime = 0;
unsigned long diffTime = 0;

int checkserial=1;              // while loop
int blinker=3;
const unsigned int MAX_MESSAGE_LENGTH = 5;
static char message[MAX_MESSAGE_LENGTH]; //Create a place to hold the incoming message (Serial)
static unsigned int message_pos = 0;
int DinPin7 = 7;
int CTS;                   // for better sync of rPi and Arduino
int signallevel = 550;     // Icom Handheld radio output signal level - volume should be set to max.
//int signallevel = 500;   // Yaesu Handheld radio


int start = 0;

void setup() {
  // initialize serial communications at 9600 bps:
    Serial.begin(9600);            // Communication rate
    pinMode(LED_BUILTIN, OUTPUT);  // blink when triggerlevel is read valid from serial
    pinMode(DinPin7, INPUT);          // go for reading radio signal (for a better sync of rPi and Arduino)

}


void loop() 
{

 if(start == 0)
  {
//    serial_flush();
    signallevel=readTriggerlevel();
    Serial.print("click listener process started with triggerlevel ");
    Serial.println(signallevel);
    start = 1;
  }

  CTS = digitalRead(DinPin7);   // goes to rPi GPIO; wenn HIGH clear to read audio signal at A0

  if( CTS == LOW)
  {
    digitalWrite(LED_BUILTIN, LOW);
//    Serial.println("CTS= OFF");
    delay(500);
    return;                     // no clear to read radio audio level
  }

// else CTS = high -> go on
   digitalWrite(LED_BUILTIN, HIGH);   // go for reading

  // A0 goes to speaker out of the radio (red)
  A0Value = analogRead(A0);


/*   Debugging  */
//   Serial.println(A0Value);

// Another way of reading... this one works on the 2nd board
  if(A0Value  >= signallevel)
  {
    count++;
    Serial.print("Hit-----------Value: ");
    Serial.println(A0Value);

/*    Debug  */
//    Serial.print("count=");
//    Serial.println(count);
//    Serial.print("PTTClickCount=");
//    Serial.println(PTTClickCount);
  }
  else
  {
    count = 0;
  }

  // count is used to make sure the values held for at least 40 milliseconds (4 x delay(10))
  if(count > 4)
  {
     PTTClickCount++;
     Serial.print("PTT Pressed ");
     Serial.println(PTTClickCount);
     delay(400); //JW20221218 40-> 400 had to play around to distinguish between still pressed and next PTT
     count = 0;
  }

  if(SEVENCLICK && PTTClickCount == 7)
  {
    ClickSuccessFlag = 7;
  }
  else if(FIVECLICK && PTTClickCount == 5)
  {
    ClickSuccessFlag = 5;
  }
  else if(THREECLICK && PTTClickCount == 3)
  {
    ClickSuccessFlag = 3;
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
	      if(ClickSuccessFlag > 1)
       	{
	         Serial.print(ClickSuccessFlag);
       	   Serial.println(" Clicks");
           Serial.flush();
        }
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
        // reset variables
        count = 0;
        PTTClickCount = 0;
        ClickSuccessFlag = 0;
        diffTime = 0;
        boardTime = 0;
        diffTimeFlag = 0;

//      Serial.println("continue loop within 30sec for playin weather");
        Serial.println("continue loop when CTS is ON");
//    	  delay(PlayBackDelay);
//        Serial.println("continue loop");
        Serial.flush();
   	  }
  }
  // just a delay
  delay(10); 
}

int readTriggerlevel()
 {
    int triggerlevel;        // read triggerlevel from rPi (minimum valid signallevel from radio)
    Serial.println("start readTriggerlevel()");
    while (checkserial==1)
    {
       //Read the next available byte in the serial receive buffer
       char inByte = Serial.read();

       //Message coming in (check not terminating character) and guard for over message size
       if ( inByte != '\n' && (message_pos < MAX_MESSAGE_LENGTH - 1) )
       {
          //Add the incoming byte to our message
          message[message_pos] = inByte;
          message_pos++;
       }
       //Full message received...
       else
       {
           //Add null character to string
           message[message_pos] = '\0';
           delay(10);
           triggerlevel = atoi(message);
         if(triggerlevel>0)
             {
//                 Serial.print("Arduino: received via USB: ");
//                 Serial.println(triggerlevel);
             }
           if((triggerlevel > 199) && (triggerlevel < 1024))
           {
              blinker=4;
              while(blinker > 0)
              {
                 blinker = blinker-1;
                 digitalWrite(LED_BUILTIN, HIGH);
                 delay(250);
                 digitalWrite(LED_BUILTIN, LOW);
                 delay(250);
              }
              Serial.print("Arduino: Audio Trigger-Level received: ");
              Serial.println(triggerlevel);
              Serial.println("Arduino: setup complete, now continuing to main loop ...");
              Serial.flush();
              return(triggerlevel);
              checkserial = 0;
              delay(10);
           }

         //Reset for the next message
         message_pos = 0;
      }
//      return(triggerlevel);
  }  
 }
 void serial_flush(void) {
  while (Serial.available()) Serial.read();
}