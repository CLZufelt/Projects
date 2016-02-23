#!/usr/bin/python

import datetime
import glob
import os, sys

devices = [device[0]
           for device in [line.split("\t")
           for line in os.popen("adb devices").read().split("\n")
           if len(line.split("\t")) == 2]]

whoami = os.popen("whoami").read().split("\n")[0]

apk_path = "/Users/%s/Documents/bsp-tests/apps/" % whoami
globber = [x for x in glob.glob(apk_path + "*") if x.startswith("%sdocuments" % apk_path)]
apk_path += globber[0]


for i in devices:
  os.system("adb -s %s install ")
  pass



