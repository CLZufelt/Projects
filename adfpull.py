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

dev_list = [line.split("\t") for line in os.popen('adb devices').read().split("\n") if len(line.split("\t")) == 2]
devices = [device[0] for device in dev_list]


def get_adf_list(devices):
  get_raw_adf_list = "adb -s %s shell ls data/data/com.projecttango.tangomapper/files/" % devices
  adfs = "adb -s %s shell ls data/data/com.projecttango.tango/files/Tango/ADFs/" % devices
  raw = [line.split("\r") for line in os.popen(get_raw_adf_list).read().split("\n") if len(line.split("\r")) == 2]
  adflist = [line.split("\r") for line in os.popen(adfs).read().split("\n") if len(line.split("\r")) ==2]
  if raw[0][0].endswith("No such file or directory"):
    print  "This device, %s, has no adf's to pull." % devices
    raw_data = None
    adf = None
  else:
    raw_data = [data[0] for data in raw]
    adf = [i[0] for i in adflist]
  return raw_data, adf


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
  return fileName

def adf_pull(devices):
  for device in devices:
    raw_data, adf = get_adf_list(device)
    start = time.time()
    for data in raw_data:
      time.sleep(5)
      start = time.time()
      pull_from = "data/data/com.projecttango.tangomapper/files/" + data
      os.system("adb -s %s pull %s %s" % (device, pull_from, mkdir(fileName)))
      print "The pull took: "
      countup(start)
    countup(start)


def countup(start_time):
  """Generates a count-up timer

  Timer that tells you how long it took to run a command.

  Args:
    start_time: Time the command started at, stored in a variable, and passed.
    to countup().
  """
  end = time.time() - start_time
  days = int(end) / 86400
  hours = (int(end % 86400) / 3600)
  minutes = ((int(end) % 86400) % 3600) / 60
  seconds = int(end) % 60
  print "%02d:%02d:%02d:%02d" % (days, hours, minutes, seconds)


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
  #adf_pull(devices)
  for device in devices:
    raw_data, adf = get_adf_list(device)
    print raw_data
    print adf
  pass




if __name__ == "__main__":
  main()

