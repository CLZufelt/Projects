#!/usr/bin/python

import os, sys
import time

os.system("adb root")
time.sleep(1)
os.system("adb shell 'rm -rf /data/data/com.projecttango.tango/files/datasets/*'")
print "Deleted datasets"
os.system("adb shell 'rm -rf /sdcard/tangomapscreator/*'")
print "Deleted adf's"
