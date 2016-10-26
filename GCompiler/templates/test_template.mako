#include <Servo.h>
#include "${header_name}"

void setup()
{
  Serial.begin(9600);
% for c in components:
  ${c.var_name}.setup();
% endfor
  
}

void loop()
{
${test_code}
}