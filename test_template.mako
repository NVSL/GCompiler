% for r in required:
#include "${r}"
% endfor
#include "${header_name}"

void setup()
{
% for c in components:
  ${c.var_name}.setup();
% endfor
}

void loop()
{
${test_code}
}