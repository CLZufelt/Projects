#!/usr/bin/python

import os
import random
import sys

def diceroll(sides, modifier=0):
  print random.randint(modifier, sides)

for i in range(0, int(sys.argv[1])):
  diceroll(int(sys.argv[1]), int(sys.argv[2]))

