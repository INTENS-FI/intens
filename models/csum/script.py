#!/usr/bin/python3

if __name__ != '__main__':
    raise RuntimeError("This is a script.  Run, don't import.")

import sys, time
time.sleep(5)
print(sum(int(s) for s in sys.argv[1:]))
