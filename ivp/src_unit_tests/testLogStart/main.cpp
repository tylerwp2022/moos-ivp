#include <cstdio>
#include <iostream>
#include <string>
#include "LogUtils.h"

using namespace std;

int main(int argc, char** argv)
{
  if((argc > 2) || ((argc == 2) && (string(argv[1]) != "case=all"))) {
    cerr << "Usage: testLogStart [case=all]" << endl;
    return(1);
  }

  unsigned int checks = 0;
  unsigned int failures = 0;
  const auto check = [&](const string& header, double expected, const char* label) {
    checks++;
    double actual = getLogStart(header);
    if(actual != expected) {
      failures++;
      cerr << "FAIL " << label << ": expected " << expected << ", got " << actual << endl;
    }
  };

  check("%% LOGSTART 1234567890.25 ", 1234567890.25, "trailing space");
  check("%% LOGSTART 1", 1, "short number after a longer number");
  check("%% LOGSTART 1000000.5", 1000000.5, "fraction at end of line");
  check("%% LOGSTART 1000000.5\t", 1000000.5, "trailing tab");
  check("%%\tLOGSTART\t 1000000.5", 1000000.5, "mixed whitespace");
  check("", 0, "empty header");
  check("%% LOGSTART", 0, "missing timestamp");
  check("%% LOGSTART   ", 0, "blank timestamp");
  check("%% LOGSTART not-a-number", 0, "non-numeric timestamp");

  // Longer than the parser's fixed buffer: exercise both exit paths.
  const string oversized(600000, '0');
  check("%% LOGSTART " + oversized + " ", 0, "oversized value with delimiter");
  check("%% LOGSTART " + oversized, 0, "oversized value at end of line");

  cout << "checks=" << checks << ",failures=" << failures << endl;
  return(failures ? 1 : 0);
}
