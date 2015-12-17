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

parser = argparse.ArgumentParser()
parser.add_argument('-build', action='store_true',
                    default=False, dest='user_build',
                    help='Set user build or user debug. Default user debug.')
parser.add_argument('-unlock', action='store_true',
                    default=False, dest='unlock',
                    help='Use this option to unlock devices before flashing.')
parser.add_argument('-f', action='store_true',
                    default= False, dest='flash_device',
                    help='Do not flash device(s).')
parser.add_argument('-i', action='store_true',
                    default= False, dest='push_apps',
                    help='Do not install apps or TangoCore.')
parser.add_argument('-b', action='store_true',
                    default= False, dest='unzip_bsp',
                    help="Do not unzip bsp image.")
parser.add_argument('-a', action='store_true',
                    default= False, dest='unzip_apps',
                    help='Do not unzip apps/TangoCore.')
parser.add_argument('-c', action='store_true',
                    default= False, dest='tango_core',
                    help='Installs TangoCore and no apps.')
parser.add_argument('-s', action='store', nargs="*",
                    dest='serial_number',
                    help='Serial number for specific device or devices.')
parser.add_argument('-v | --version', action='store_true',
                    default= False, dest='version_info',
                    help='Display version information, and nothing else.')
argParser = parser.parse_args()

version = "2.4"
if argParser.version_info:
  print version
  quit()

# This makes it possible to run the script on a Mac the same as on Linux.
whatami = platform.system()

whoami = os.popen("whoami").read().split("\n")[0]

if whatami == "Linux":
  rootpath = "/home/" + whoami + "/bsp-tests/"
  downloads = "/home/" + whoami + "/Downloads/"
elif whatami == "Darwin":
  rootpath = "/Users/" + whoami + "/Documents/bsp-tests/"
  downloads = "/Users/" + whoami + "/Downloads/"
else:
  # Compatibility for Windows requires a lot more things to change.
  "Sorry. This program is not compatible with Windows."
  rootpath = None
  downloads = None
  quit()

bspPath = rootpath + "bsp/"
appPath = rootpath + "apps/"

# Bsp's and apps are stored under a folder with the current date.
bspDate = "ardbeg-img-" + datetime.date.today().strftime("%y%m%d")
appDate = datetime.date.today().strftime("%Y%m%d")

buildDatePath = bspPath + bspDate + "-user-build"
debugDatePath = bspPath + bspDate + "-user-debug"

appDatePath = appPath + appDate + "-" + \
raw_input("An abbreviation representing the current build, please:").upper()
appUnzipPath = appDatePath + "/Apps/"

zipFilePath = downloads + "*.zip"

# Creates a list with the device serial numbers.
devices = [[device[0]
          for device in [line.split("\t")
          for line in os.popen('adb devices').read().split("\n")
          if len(line.split("\t")) == 2]]]

if argParser.serial_number:
  devices = argParser.serial_number


def unlock(devices=devices):
  for device in devices:
    subprocess.call(['adb', '-s', device, 'reboot', 'bootloader'])
    time.sleep(1)
    subprocess.call(['fastboot', '-s', device, 'oem', 'unlock'])
    time.sleep(3)

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

# TODO: (charlesz) use Drive API to download apps and bsps from Drive.
def zipPath(searchTerm, destPath):
  """Determines the correct .zip file from the Downloads directory.

  Globs the .zip folders in the Downloads directory, and selects
  one based on searchTerm. Extracts contents to destPath.

  Args:
    searchTerm: A string representing either the apk's .zip, or the bsp's .zip.
    destPath: A string telling the function where to unzip to.
  """
  if not argParser.user_build:
    exclude = "_002.zip"
  else:
    exclude = "_001.zip"
  lst = [x for x in glob.glob(zipFilePath) if not x.endswith(exclude)]
  for name in lst:
    with zipfile.ZipFile(name, 'r') as z:
      for item in z.namelist():
        if searchTerm in item:
          z.extractall(destPath)
          break

def bspFile():
  """Uses zipPath to unzip the bsp.

  Tells zipPath which .zip to unzip, and where to unzip it for bsp's.
  Capable of distinguishing between user-debug and user-build images.
  """
  if not argParser.unzip_bsp:
    if not argParser.user_build:
      if not os.path.exists(debugDatePath):
        print "Unzipping user-debug image to" + debugDatePath
        zipPath("boot.img", debugDatePath)
      else:
        print "Image folder exists"
        if len(glob.glob(debugDatePath + "/*")) > 0:
          print "... and it has things in it."
          overwrite = raw_input("Overwrite? (y/N)")
          if overwrite.lower() == "y":
            zipPath("boot.img", debugDatePath)
        else:
          print "... but it's empty."
          zipPath("boot.img", debugDatePath)
    else:
      if not os.path.exists(buildDatePath):
        print "Unzipping user-build image to" + buildDatePath
        zipPath("boot.img", buildDatePath)
      else:
        print "Image folder exists"
        if len(glob.glob(buildDatePath + "/*")) > 0:
          print "... and it has things in it. We'll use what's in this folder."
        else:
          print "But it's empty, so we'll unzip here."
          zipPath("boot.img", buildDatePath)

def appFile():
  """Uses zipPath to unzip the apps.

  Tells zipPath which .zip to unzip, and where to unzip it for apps.
  """
  if not argParser.unzip_apps:
    if not os.path.exists(appDatePath):
      print "Unzipping apps to " + appDatePath
      zipPath("Apps", appDatePath)
    else:
      print "App folder exists"
      if len(glob.glob(appUnzipPath + "*.apk")) > 0:
        print "And it's already full."
        overwrite = raw_input("Overwrite? (y/N)")
        if overwrite.lower() == "y":
          for app in glob.glob(appUnzipPath + "*"):
            os.remove(app)
          zipPath("Apps", appDatePath)
      else:
        zipPath("Apps", appDatePath)
  rename()

def flashDevices(userBSP, devices=devices):
  """Flashes devices by serial number.

  Select device by serial number, and run through the commands
  to flash a new image.

  Args:
    userBSP: Path to the bsp image.
  """
  if not argParser.flash_device:
    imagePath = userBSP
    lastDevice = len(devices) -1
    if argParser.unlock:
      unlock(devices)
    for serial in devices:
      print "Flashing %s ..." % serial
      subprocess.check_call(["adb", "-s", serial, "reboot", "bootloader"])
      time.sleep(1)
      subprocess.check_call(["fastboot", "-s", serial, "flash",
                  "bootloader", imagePath + "/bootloader.bin"])
      subprocess.check_call(["fastboot", "-s", serial, "flash", "dtb",
                  imagePath + "/tegra124-ardbeg.dtb"])
      subprocess.check_call(["fastboot", "-s", serial, "flash", "boot",
                  imagePath + "/boot.img"])
      subprocess.check_call(["fastboot", "-s", serial, "flash", "system",
                  imagePath + "/system.img"])
      subprocess.check_call(["fastboot", "-s", serial, "flash", "recovery",
                  imagePath + "/recovery.img"])
      subprocess.check_call(["fastboot", "-s", serial, "-w"])
      subprocess.check_call(["fastboot", "-s", serial, "reboot"])
      print "-"*25 + "Flash Finished for device " + serial + "-"*25
      print "Device will now reboot. This takes about 4 minutes."
      if serial == devices[lastDevice]:
        countdown(245)

def installApks(datePath, unzipPath):
  """Install apps by serial number.

  Select device by serial number, and install all the apks in the Apps
  folder.

  Args:
    datePath: Path to Apps and TangoCore.
    unzipPath: Path to apks.
  """
  lastDevice = len(devices) -1
  if not argParser.push_apps:
    for device in devices:
      print "Installing TangoCore..."
      if os.path.exists(datePath + "/SingleTangoFiles"):
        os.system("adb -s %s install -r %s" %
                  (device, datePath + "/SingleTangoFiles/TangoCore*.apk"))
      elif os.path.exists(datePath + "/signedTangoCore"):
        os.system("adb -s %s install -r %s" %
                  (device, datePath + "/signedTangoCore/TangoCore*.apk"))
      if not argParser.tango_core:
        for app in glob.glob(unzipPath + "*.apk"):
          print "Installing " + app
          os.system("adb -s %s install -r %s" % (device, app))
      print "Rebooting device. This takes about 45 seconds..."
      os.system("adb -s %s reboot" % device)
      if device == devices[lastDevice]:
        countdown(45)

def rename():
  """Rename app names.

  Apps must be renamed, because some of them have unnecessary spaces,
  parenthesis, and numbers.
  """
  for name in glob.glob(appUnzipPath + "*"):
    os.rename(name, name.replace(" ", ""))
  for name in glob.glob(appUnzipPath + "*([1234]).apk"):
    os.rename(name, name[:name.find("(")] + ".apk")

def cleanup():
  """Gives the user the option to delete .zip folders from Downloads."""
  if glob.glob(zipFilePath) > 0:
    removeApp = raw_input("Remove app zip? (y/N)")
    removeBsp = raw_input("Remove bsp zip? (y/N)")
    if "y" in removeApp.lower():
      for zip in glob.glob(zipFilePath):
        if "documents" in zip:
          os.remove(zip)
    if "y" in removeBsp.lower():
      for zip in glob.glob(zipFilePath):
        if "ardbeg" in zip:
          os.remove(zip)
  print "The build is: ", subprocess.check_output(
  ["adb", "shell", "getprop", "ro.build.type"])

def chrono():
  """Determine the most recent bsp image for flashing."""
  datelist = []
  if argParser.user_build:
    include = "user-build"
  else:
    include = "user-debug"
  bsplist = [x for x in glob.glob(bspPath + "*") if x.endswith(include)]
  for i in range(len(bsplist)):
    datelist.append(
      bsplist[i][bsplist[i].find("1"):bsplist[i].find(("-"),
              bsplist[i].find("1"))])
  datelist = sorted(datelist)
  for item in datelist:
    if item == max(datelist):
      if argParser.user_build:
        return "ardbeg-img-%s-user-build" % item
      else:
        return "ardbeg-img-%s-user-debug" % item


def main():
  bspFile()
  appFile()
  flashDevices(bspPath + chrono())
  installApks(appDatePath, appUnzipPath)
  cleanup()


if __name__ == "__main__":
  main()