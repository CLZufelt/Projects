#!/usr/bin/python

# Author: charlesz@google.com
# Trademark Google Inc., all rights reserved

import os
import subprocess
import time

devices = []
for line in os.popen('adb devices').read().split("\n"):
  device = line.split("\t")
  if len(device) == 2:
    devices.append(device[0])

def unlock_dev():
  for i in devices:
    print "Turning on device... \n%s" %i
    #subprocess.call(['adb', '-s', i, 'root'])
    #time.sleep(2)
    #subprocess.call(['adb', '-s', i, 'remount'])
    subprocess.call(["adb", "-s", i, "shell", "input", "keyevent", "26"])
    subprocess.call(["adb", "-s", i, "shell", "input", "keyevent", "82"])
    #time.sleep(3)

unlock_dev()


