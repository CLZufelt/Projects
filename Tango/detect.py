#!/usr/bin/python

# Author: charlesz@google.com
# Trademark Google Inc., all rights reserved

import os
import subprocess
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--on", action='store_true',
                    default=False, dest='power_on',
										help='Toggle device power on.')
parser.add_argument("--off", action='store_true',
                    default=False, dest='power_off',
										help='Toggle device power off.')
argParser = parser.parse_args()


devices = [device[0]
           for device in [line.split("\t")
           for line in os.popen('adb devices').read().split("\n")
           if len(line.split("\t")) == 2]]

def root():
  subprocess.call(['adb', '-s', i, 'root'])
  subprocess.call(['adb', '-s', i, 'remount'])

def on():
  for i in devices:
    print "Powering on device: %s" %i
    subprocess.call(["adb", "-s", i, "shell", "input", "keyevent", "26"])
    subprocess.call(["adb", "-s", i, "shell", "input", "keyevent", "82"])

def off():
  for i in devices:
    print "Powering off device: %s" %i
    subprocess.call(['adb', '-s', i, 'shell', 'input', 'keyevent', '26'])


if argParser.power_off:
  off()
if argParser.power_on:
  on()

