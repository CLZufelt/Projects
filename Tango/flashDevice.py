#!/usr/bin/python
# Copyright 2016 Google Inc. All Rights Reserved.
# Distributed under the Project Tango Preview Development Kit (PDK) Agreement.
# CONFIDENTIAL. AUTHORIZED USE ONLY. DO NOT REDISTRIBUTE.

# Authors: charlesz@google.com

################################################################################
# This script is used by ops for flashing devices with a system image,
# installing apk's en masse, nvflashing when needed, unlocking devices when
# needed, and finally restarting the device so that changes may take effect.
# This script will also unzip packed app and bsp folders to be used in flashing/
# installing.
#
# This script requires the pick library to be installed:
#   sudo pip install pick
#
################################################################################

import argparse
import datetime
import glob
import os
import platform
import subprocess

try:
  subprocess.check_call("pip --version", shell=True)
except subprocess.CalledProcessError:
  print "Pip package installer not available, installing now using: 'sudo easy_install pip'"
  if platform.system() == "Linux":
    os.system("sudo apt-get install python-pip")
  if platform.system() == "Darwin":
    os.system("sudo easy_install pip")

import sys
import threading
import time
import zipfile
try:
  from pick import pick
except ImportError:
  print "Pick library missing, installing now using: 'sudo pip install pick'"
  os.system("sudo pip install pick")

parser = argparse.ArgumentParser()
parser.add_argument('--build', action='store_true',
                    default=False, dest='user_build',
                    help='Set user build or user debug. Default user debug.')
parser.add_argument('--reboot', action='store_true',
                    default=False, dest='reboot',
                    help='Reboot connected devices.')
parser.add_argument('--nvflash', action='store_true',
                    default=False, dest='nv_flash_device',
                    help='NVflash device. Only works on Linux at the moment.')
parser.add_argument('-f', action='store_true',
                    default=False, dest='flash_device',
                    help='Flash device(s).')
parser.add_argument('-u', action='store_true',
                    default=False, dest='unlock_device',
                    help='Unlock device.')
parser.add_argument('-i', action='store_true',
                    default=False, dest='push_apps',
                    help='Install apps and TangoCore.')
parser.add_argument('-n', action='store_true',
                    default=False, dest='no_core',
                    help='Install apps and do not install TangoCore')
parser.add_argument('-c', action='store_true',
                    default=False, dest='tango_core',
                    help='Installs TangoCore and no apps.')
parser.add_argument('-b', action='store_true',
                    default=False, dest='unzip_bsp',
                    help="Unzip bsp image.")
parser.add_argument('-a', action='store_true',
                    default=False, dest='unzip_apps',
                    help='Unzip apps/TangoCore.')
parser.add_argument('-p', action='store_true',
                    default=False, dest='pull_calib',
                    help='Pull calibration files from device, and restore them'
                         'after flash.')
#TODO Use pick for -s
parser.add_argument('-s', action='store', nargs="*",
                    dest='serial_number',
                    help='Serial number for specific device or devices.')
parser.add_argument('-v', action='store_true',
                    default=False, dest='version_info',
                    help='Display version information, and nothing else.')
argParser = parser.parse_args()

version = "3.7"

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
  print "Sorry. This program is not compatible with Windows."
  rootpath = None
  downloads = None
  quit()

bspPath = rootpath + "bsp/"
appPath = rootpath + "apps/"
nvPath = bspPath, "out/target/product/ardbeg/"

# Bsp's and apps are stored under a folder with the current date.
bspDate = "ardbeg-img-" + datetime.date.today().strftime("%y%m%d")
appDate = datetime.date.today().strftime("%Y%m%d")

buildDatePath = bspPath + bspDate + "-user-build"
debugDatePath = bspPath + bspDate + "-user-debug"

incrementer = ""

if argParser.push_apps or argParser.unzip_apps:
  incrementer = raw_input("An abbreviation representing the current"
                          " build, please:").upper()
appDatePath = appPath + appDate + "-" + incrementer
appUnzipPath = appDatePath + "/Apps/"

zipFilePath = downloads + "*.zip"

# Creates a list with the device serial numbers.
devices = [device[0]
           for device in [line.split("\t")
           for line in os.popen("adb devices").read().split("\n")
           if len(line.split("\t")) == 2]]
if len(devices) > 0:
  lastDevice = devices[-1]

if argParser.serial_number:
  devices = argParser.serial_number


def unlock(device):
  subprocess.call(["adb", "-s", device, "reboot", "bootloader"])
  time.sleep(1)
  subprocess.call(["fastboot", "-s", device, "oem", "unlock"])
  time.sleep(3)
  subprocess.check_call(["fastboot", "-s", device, "reboot"])
  print "~"*20, "Device unlocked, rebooting now","~"*20
  if device == lastDevice:
    countdown(260)

def pull_calib(device):
  os.system("adb -s {0} pull /sdcard/config/calibtraion.xml "
            "{0}/calibration.xml".format(device))
  os.system("adb -s {0} pull /sdcard/config/online-calibration.xml "
            "{0}/online-calibration.xml".format(device))


def push_calib(device):
  os.system("adb -s {0} push {0}/calibration.xml sdcard/config".format(device))
  os.system("adb -s {0} push {0}/online-calibration.xml sdcard/config".format(device))

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
  #TODO Change date to date on the image, not today's date
  """Uses zipPath to unzip the bsp.

  Tells zipPath which .zip to unzip, and where to unzip it for bsp's.
  Capable of distinguishing between user-debug and user-build images.
  """
  if not argParser.user_build:
    if not os.path.exists(debugDatePath):
      print "Unzipping user-debug image to " + debugDatePath
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
      print "Unzipping user-build image to " + buildDatePath
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

def flashDevices(userBSP, device):
  """Flashes devices by serial number.

  Checks if the device is locked before flashing.
  Flash a new image onto the device.

  Args:
    userBSP: Path to the bsp image.
  """
  if argParser.pull_calib:
    print "Pulling calibration files from {0}".format(device)
    pull_calib(device)
  print "Flashing %s ..." % device
  subprocess.check_call(["adb", "-s", device, "reboot", "bootloader"])
  time.sleep(1)
  subprocess.check_call(["fastboot", "-s", device, "flash",
              "bootloader", userBSP + "/bootloader.bin"])
  subprocess.check_call(["fastboot", "-s", device, "flash", "dtb",
              userBSP + "/tegra124-ardbeg.dtb"])
  subprocess.check_call(["fastboot", "-s", device, "flash", "boot",
              userBSP + "/boot.img"])
  subprocess.check_call(["fastboot", "-s", device, "flash", "system",
              userBSP + "/system.img"])
  subprocess.check_call(["fastboot", "-s", device, "flash", "recovery",
              userBSP + "/recovery.img"])
  subprocess.check_call(["fastboot", "-s", device, "-w"])
  subprocess.check_call(["fastboot", "-s", device, "reboot"])
  print "~"*25 + "Flash Finished for device " + device + "~"*25
  print "Device will now reboot. This takes about 4 minutes."
  if device == lastDevice:
    countdown(245)
  if argParser.pull_calib:
    push_calib(device)
    print "Checking sdcard/config on device {0}".format(device)
    print "adb -s {0} shell 'ls sdcard/config'".format(device)

def nvFlash(device):
  subprocess.check_call(["bash", nvPath + "flash.sh"])

def installApks(datePath, device, unzipPath):
  """Install apps by serial number.

  Install all the apks in the Apps folder, onto the device.

  Args:
    datePath: Path to Apps and TangoCore.
    unzipPath: Path to apks.
  """
  if not argParser.no_core:
    if os.path.exists(datePath + "/SingleTangoFiles"):
      os.system("adb -s %s install -rd %s" %
               (device, datePath + "/SingleTangoFiles/TangoCore*.apk"))
    elif os.path.exists(datePath + "/signedTangoCore"):
      os.system("adb -s %s install -rd %s" %
               (device, datePath + "/signedTangoCore/TangoCore*.apk"))
    else:
      print "No Tango Core found, skipping this step."
  if not argParser.tango_core:
    for app in glob.glob(datePath + "/Apps/*.apk"):
      print app
      os.system("adb -s %s install -rd %s" % (device, app))
  print "Rebooting device: %s. This takes about 45 seconds..." % device
  os.system("adb -s %s reboot" % device)

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
    if argParser.unzip_apps:
      removeApp = raw_input("Remove app zip? (y/N)")
      if "y" in removeApp.lower():
        for zip in glob.glob(zipFilePath):
          if "Apps" in [i for i in zipfile.ZipFile(zip, 'r').namelist()][1]:
            os.remove(zip)
    if argParser.unzip_bsp:
      removeBsp = raw_input("Remove bsp zip? (y/N)")
      if "y" in removeBsp.lower():
        for zip in glob.glob(zipFilePath):
          if "ardbeg" in zip:
            os.remove(zip)


def BSPChrono():
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

def AppChrono():
  exclude = appPath + "_install_all_apps.sh"
  applist = [y.split('-')[0] for y in
             [x.split("/")[-1] for x in glob.glob(appPath + "*")
             if not x.endswith(exclude)] if y.endswith(incrementer)]
  applist = sorted(applist)
  return appPath + max(applist)


def reboot(devices):
  for device in devices:
    os.system("adb -s %s reboot" % device)


def main(devices=devices):
  if argParser.version_info:
    print version
  if argParser.unzip_bsp:
    bspFile()
  if argParser.unzip_apps:
    appFile()
  if argParser.unlock_device:
    for device in devices:
      #unlockThread =threading.Thread(target=unlock,
      #                               args=(device))
      #unlockThread.start()
      #unlockThread.join()
      unlock(device)
  if argParser.nv_flash_device:
    nv_title = "This will nvFlash your device, are you sure?"
    nv_options = ["yes","no"]
    _, nv_flash = pick(nv_options, nv_title)
    if nv_flash == 0:
      for device in devices:
        nvFlash(device)
  if argParser.flash_device:
    title = "Are all devices ready to flash?"
    options = ["yes", "no"]
    _, nextStep = pick(options, title)
    if nextStep == 0:
      for device in devices:
        #flashThread = threading.Thread(target=flashDevices,
        #                          args=(bspPath + BSPChrono(), device))
        #flashThread.start()
        #flashThread.join()
        flashDevices(bspPath + BSPChrono(), device)
  if argParser.push_apps or argParser.tango_core:
    for device in devices:
      installApks(AppChrono() + "-" + incrementer, device, appUnzipPath)
  if argParser.reboot:
    reboot(devices)
  cleanup()


if __name__ == "__main__":
  main()
