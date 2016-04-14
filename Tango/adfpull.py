#!/usr/bin/python

# Author: charlesz@google.com
# Trademark Google Inc., all rights reserved

import argparse
import calendar
import datetime
import os
import platform
import subprocess
import time
import tarfile


parser = argparse.ArgumentParser()
parser.add_argument("--json", action='store_true',
                    default=False, dest='json',
                    help='Change the json files from default.')
parser.add_argument("-c", action='store_true',
                    default=False, dest='compress',
                    help='Don\'t compress into a tarball.')
parser.add_argument("-u", action='store_true',
                    default=False, dest='upload',
                    help='Don\'t upload.')
argParser = parser.parse_args()

whatami = platform.system()

whoami = os.popen("whoami").read().split("\n")[0]

if whatami == "Linux":
  rootpath = "/home/" + whoami
elif whatami == "Darwin":
  rootpath = "/Users/" + whoami
else:
  rootpath = None
  print "Not compatible with Windows."
  exit()

root_dir = rootpath + "/Desktop/"

country = raw_input("Country (Ex. US): ")
state = raw_input("State Abbreviation (Ex. CA): ")
city = raw_input("City Code (Ex. MTV for Mountain View): ")
location = raw_input("Collect Location (Ex. GoogleSB65): ")

dest_dir = country
dest_dir += "_" + state
dest_dir += "_" + city
dest_dir += "_" + location
#dest_dir += "/" + dest_dir

devices = [device[0]
           for device in [line.split("\t")
           for line in os.popen('adb devices').read().split("\n")
           if len(line.split("\t")) == 2]]


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

def raw_data_files(serial):
  get_raw_data = "adb -s %s shell ls " \
                     "data/data/com.projecttango.tangomapper/files/" % serial
  raw_data = [line.split("\r")[0] for line in
         os.popen(get_raw_data).read().split("\n")
         if len(line.split("\r")) == 2]
  if raw_data[0].endswith("Permission denied"):
    os.system("abd -s %s root" % serial)
    time.sleep(3)
    os.system("abd -s %s remount" % serial)
    raw_data = raw_data_files(serial)
  if raw_data[0].endswith("No such file or directory"):
    print  "This device, %s, has no adf's to pull." % serial
  return raw_data

def adfs(serial):
  get_adfs = "adb -s %s shell ls " \
              "data/data/com.projecttango.tango/files/Tango/ADFs/" % serial
  adf = [line.split("\r")[0] for line in
          os.popen(get_adfs).read().split("\n")
          if len(line.split("\r")) == 2]
  if adf[0].endswith("Permission denied"):
    os.system("abd -s %s root" % serial)
    time.sleep(3)
    os.system("abd -s %s remount" % serial)
    adf = adfs(serial)
  if adf[0].endswith("No such file or directory"):
    return "This device, %s, has no adf's to pull." % serial
  return adf

def datetime_stamps(data):
  date_stamp = "%04d%02d%02d" % (int(data[0:4]),
         int(list(calendar.month_abbr).index(data[4:7])),
         int(data[7:9]))
  time_stamp = "_%04d" % int([str(data)][0].split("_")[1][0:4])
  return date_stamp, time_stamp

def mkdir(date, time, destination_dir=root_dir + dest_dir):
  destination_dir += "_" + date + "/" + dest_dir + time
  if not os.path.exists(destination_dir):
    os.system("mkdir" + destination_dir)
  return str(destination_dir)

def adf_pull(device):
  begin = time.time()
  raw_data = raw_data_files(device)
  for data in raw_data:
    date_stamp, time_stamp = datetime_stamps(data)
    destination_dir = mkdir(date_stamp, time_stamp)
    start = time.time()
    pull_from = "data/data/com.projecttango.tangomapper/files/" + data
    os.system("adb -s %s pull %s %s" % (device, pull_from, destination_dir))
    print "The pull took: %s" % countup(start)
    create_json(data, destination_dir)
    adf = adfs(device)
    if adf > 0:
      for data in adf:
        pull_from = "data/data/com.projecttango.tango/files/Tango/ADFs/" + data
        os.system("adb -s %s pull %s %s" % (device, pull_from, destination_dir))
  print "Pull from all devices took: ", countup(begin)

def compress_files(destination, source_dir):
  with tarfile.open(destination + ".tar.gz", "w:gz") as tar:
    tar.add(source_dir, arcname=os.path.basename(source_dir))
    return destination

def upload(destination=dest_dir, source_dir=dest_dir):
  push_destination = "gs://project-tango-internal-data/" + destination
  subprocess.call(["gsutil", "cp", "-r", source_dir, push_destination])

def main(devices=devices):
  for device in devices:
    adf_pull(device)
    date_of_collect, time_of_collect = datetime_stamps(raw_data_files(device)[0])
    if os.path.exists(root_dir + dest_dir + "_" + date_of_collect):
      try:
        compress_files(root_dir + dest_dir + "_" + date_of_collect,
                       root_dir + dest_dir + "_" + date_of_collect)
      except IOError:
        print "Something went wrong with raw_data_files."
    #upload()

if __name__ == "__main__":
  main()
