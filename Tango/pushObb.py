#!/usr/bin/python

import os

devices = [device[0]
          for device in [line.split("\t")
          for line in os.popen('adb devices').read().split("\n")
          if len(line.split("\t")) == 2]]

for device in devices:
  os.system("adb -s %s adb push main.1.com.uppercut_games.dodgers.obb "
            "/sdcard/Android/obb/com.uppercut_games.dodgers/main.1.com.uppercut_games.dodgers.obb" % device)