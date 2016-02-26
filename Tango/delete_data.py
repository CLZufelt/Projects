#!/usr/bin/python

import os, sys
import time


devices = [device[0]
          for device in [line.split("\t")
          for line in os.popen('adb devices').read().split("\n")
          if len(line.split("\t")) == 2]]

for dev in devices:
  os.system("adb root")
  time.sleep(1)
  os.system("adb shell 'rm -rf /data/data/com.projecttango.tango/files/datasets/*'")
  print "Deleted datasets"
  os.system("adb shell 'rm -rf /sdcard/tangomapscreator/*'")
  print "Deleted adf's"
