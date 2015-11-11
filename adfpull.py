#!/usr/bin/python

# Author: charlesz@google.com
# Trademark Google Inc., all rights reserved

import argparse
import datetime
import glob
import os
import platform
import subprocess
import sys
import time
import zipfile


country = "US" #raw_input("Country (Ex. US): ")
state = "CA" #raw_input("State Abbreviation (Ex. CA): ")
city = "MTV" #raw_input("City Code (Ex. MTV for Mountain View): ")
location = "GoogleSB65" #raw_input("Collect Location (Ex. GoogleSB65): ")
today = time.strftime("%Y%m%d")

fileName = "/home/atap/" + country
fileName += "_" + state
fileName += "_" + city
fileName += "_" + location
fileName += "_" + today

devices = []
for line in os.popen('adb devices').read().split("\n"):
  device = line.split("\t")
  if len(device) == 2:
    devices.append(device[0])

raw_data = []
for line in os.popen("adb -s %s shell ls data/data/com.projecttango.tangomapper/files/" % serial).read().split("\n"):
  line = line.split("\r")
  if len(line) == 2:
    raw_data.append(line[0])

adf = []
for line in os.popen("adb -s %s shell ls data/data/com.projecttango.tango/files/Tango/ADFs/" % serial).read().split("\n"):
  line = line.split("\r")
  if len(line) == 2:
    adf.append(line[0])


def mkdir(fileName):
  if os.path.exists(fileName + "_01"):
    for x in range(2, 11):
      if not os.path.exists(fileName + "_%02d" % x):
        os.system("mkdir " + fileName + "_%02d" % x)
        fileName += "_%02d" % x
        break
  else:
    os.system("mkdir " + fileName + "_01")
    fileName += "_01"

def adf_pull():
  if len(devices) > 1:
    print "Pay attention now, I'm going to turn the devices on in order by serial number..."
    for serial in devices:
      print "Turning on %s now." % serial
      subprocess.call(["adb", "-s", serial, "shell", "input", "keyevent", "26"])
      subprocess.call(["adb", "-s", serial, "shell", "input", "keyevent", "82"])
      time.sleep(3)
    serial = raw_input("Input the serial number for the device you wish to pull from here: ")
  else:
    serial = devices[0]
  for d in raw_data:
    pull_from = "data/data/com.projecttango.tangomapper/files/" + d
    print "This takes some time, often as much as several hours. Please be patient."
    os.system("adb -s %s pull %s %s" % (serial, pull_from, fileName))



def countdown(seconds):
  """Generates a countdown timer

  Countdown timer continuously overwrites previous output, after flushing
  the standard out.

  Args:
    seconds: A pre-determined length of time in seconds.
  """
  for count in range(seconds, -1, -1):
    minute, second = divmod(count, 60)
    sys.stdout.write("Time remaining: " \
                     + "%02d:%02d" % (minute, second) + "\r" ,)
    sys.stdout.flush()
    time.sleep(1)





def main():
  mkdir(fileName)
  adf_pull()


if __name__ == "__main__":
  main()

