#!/usr/bin/python

import os
import subprocess
import time

devices = [device[0]
  for device in [line.split("\t")
  for line in os.popen('adb devices').read().split("\n")
  if len(line.split("\t")) == 2]]

for dev in devices:
  subprocess.call(['adb', '-s', dev, 'reboot', 'bootloader'])
  time.sleep(1)
  subprocess.call(['fastboot', '-s', dev, 'oem', 'unlock'])
  time.sleep(3)
  subprocess.check_call(["fastboot", "-s", dev, "reboot"])
  print "Device unlocked"


