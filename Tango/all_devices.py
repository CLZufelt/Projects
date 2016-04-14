#!/usr/bin/python

import argparse
import os
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('-s', action='store', nargs="*",
                  dest='serial_number',
                  help='Serial number for specific device or devices.')
parser.add_argument('--push', action='store', nargs='*',
                  dest='push_name',
                  help='Provide file to push, and location on device to push to'
                       '\nEx: test.txt sdcard/Photos/')
parser.add_argument('--pull', action='store', nargs='*',
                  dest='pull_name',
                  help='Provide file(s) to pull, and destination'
                       '\nEx: sdcard/Photos/ ~/Pictures')
parser.add_argument('-v | --version', action='store_true',
                  default=False, dest='version_info',
                  help='Display version information, and nothing else.')
argParser = parser.parse_args()

version = 1.0

devices = [device[0]
          for device in [line.split("\t")
          for line in os.popen('adb devices').read().split("\n")
          if len(line.split("\t")) == 2]]

if len(devices) > 0:
  lastDevice = devices[-1]

if argParser.serial_number:
  devices = argParser.serial_number


def push():
  fileName = argParser.push_name[0]
  destination = argParser.push_name[1]
  for serial in devices:
    os.system("adb -s %s root" % serial)
    time.sleep(1)
    os.system("adb -s %s remount ; adb -s %s push %s %s" %
             (serial, serial, fileName, destination))

def pull():
  fileName = argParser.pull_name[0]
  destination = argParser.pull_name[1]
  for serial in devices:
    os.system("adb -s %s root" % serial)
    time.sleep(1)
    os.system('adb -s %s remount' % serial)
    os.system("adb -s %s pull %s %s"%
             (serial, fileName, destination))

def reboot():
  for serial in devices:
    print "Rebooting now."
    os.system("adb -s %s reboot" % serial)

def install():
  fileName = argParser.install
  for serial in devices:
     os.system("adb -s %s install -rd %s" % (serial, fileName))

if argParser.file_name:
  push()
if argParser.reboot:
  reboot()
if argParser.install:
  install()
if argParser.pull:
  pull()
