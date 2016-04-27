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
                  dest='push',
                  help='Provide file to push, and location on device to push to'
                       '\nEx: test.txt sdcard/Photos/')
parser.add_argument('--pull', action='store', nargs='*',
                  dest='pull',
                  help='Provide file(s) to pull, and destination'
                       '\nEx: sdcard/Photos/ ~/Pictures')
parser.add_argument('--update', action='store_true',
                    default=False, dest='update_library',
                    help='Update library for all connected devices.')
parser.add_argument('--install', action='store_true',
                    default=False, dest='install',
                    help='Install app(s) to all devices.')
parser.add_argument('--reboot', action='store_true',
                    default=False, dest='reboot',
                    help='Reboot all connected devices.')
parser.add_argument('--shutdown', action='store_true',
                    default=False, dest='shutdown',
                    help='Shutdown all connected devices.')
parser.add_argument('-v | --version', action='store_true',
                  default=False, dest='version_info',
                  help='Display version information, and nothing else.')
argParser = parser.parse_args()

version = 1.3

devices = [device[0]
          for device in [line.split("\t")
          for line in os.popen('adb devices').read().split("\n")
          if len(line.split("\t")) == 2]]

if len(devices) > 0:
  lastDevice = devices[-1]

if argParser.serial_number:
  devices = argParser.serial_number


def push():
  fileName = argParser.push[0]
  destination = argParser.push[1]
  for serial in devices:
    os.system("adb -s %s root" % serial)
  time.sleep(1)
  for serial in devices:
    os.system("adb -s %s remount" % serial)
  for serial in devices:
    os.system("adb -s %s push %s %s" % (serial, fileName, destination))

def pull():
  fileName = argParser.pull[0]
  destination = argParser.pull[1]
  for serial in devices:
    os.system("adb -s %s root" % serial)
  time.sleep(1)
  for serial in devices:
    os.system('adb -s %s remount' % serial)
  for serial in devices:
    os.system("adb -s %s pull %s %s"%
             (serial, fileName, destination))

def update_library():
  file_to_push = 'libexternal_freak.so'
  destination = '/system/lib'
  for serial in devices:
    os.system('adb -s %s root' % serial)
    time.sleep(2)
    os.system('adb -s %s remount' % serial)
    os.system('adb -s %s push %s %s' % (serial, file_to_push, destination))

def reboot():
  for serial in devices:
    print "Rebooting now."
    os.system("adb -s %s reboot" % serial)

def shutdown():
  for serial in devices:
    print "Shutting down now."
    os.system("adb -s %s shell 'reboot -p'" %serial)

def install():
  fileName = argParser.install
  for serial in devices:
     os.system("adb -s %s install -rd %s" % (serial, fileName))

def main():
  if argParser.push:
    push()
  if argParser.update_library:
    update_library()
  if argParser.reboot:
    reboot()
  if argParser.shutdown:
    shutdown()
  if argParser.install:
    install()
  if argParser.pull:
    pull()

if __name__ == "__main__":
  main()
