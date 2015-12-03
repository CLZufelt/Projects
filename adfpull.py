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
import tarfile


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

dev_list =
devices = [device[0]
           for device in [line.split("\t")
            for line in os.popen('adb devices').read().split("\n")
            if len(line.split("\t")) == 2]]


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
    begin = time.time()
    for data in raw_data:
      time.sleep(5)
      start = time.time()
      pull_from = "data/data/com.projecttango.tangomapper/files/" + data
      os.system("adb -s %s pull %s %s" % (device, pull_from, mkdir(fileName)))
      print "The pull took: "
      countup(start)
    countup(begin)

def create_json():
  with open("properties.json", 'w') as properties:
    properties_file = "{\n\t\"collection_timestamp\" : \"%s %s\",\n"\
    % (str(datetime.date.today()), str(raw_input("Time of collect: "
    "(hh:mm:ss)\n")))
    properties_file += "\ntags\n\" : [\"collection_method_%s\", " \
    % raw_input("Collection method:\nhandheld\nheadset\n")
    properties_file += "\"lighting_%s\", " % raw_input("Lighting type:\n"
    "varied\nstore\ndim\noutdoors_sunny\noutdoors_overcast"
    "\nhouse_dim\nhouse_bright\n")
    properties_file += "\"tilt_%s\", " % raw_input("Tilt:\n"
    "vertical\ntilted\nhorizontal\nvaried\n")
    properties_file += "\"layout_%s\", " % raw_input("Layout type:\n"
    "portrait\nlandscape\nportrait_and_landscape\n")
    properties_file += "device_yellowstone, "
    properties_file += "\"orientation_%s\"]\n}\"" % raw_input("Orientation:\n"
    "uniform\nvaried\n")
    properties.write(properties_file)
  with open("adf_properties.json", 'w') as adf_properties:
    adf_json = "{\n\t\"tags\" : [\"%s\", " % \
    raw_input("Algorithm scale (select all that apply):\n"
    "\"algorithm_matching_small_scale\"\n\"algorithm_matching_medium_scale\"\n"
    "\"algorithm_matching_large_scale\"\n\"algorithm_retrieval_small_scale\"\n"
    "\"algorithm_retrieval_medium_scale\"\n"
    "\"algorithm_retrieval_large_scale\"\n")
    adf_json += "\"construction_%s\", " % raw_input("Construction type:\n"
    "pose_graph\nVIWLS\npose_graph_with_structure\n")
    adf_json += "\"floor_%s\", " % raw_input("Floors:\nmultiple\nsingle\n")
    adf_json += "\"compression_%s\", " % raw_input("Compression type:\n"
    "none\npq\n")
    adf_json += "\"%s\", " % raw_input("Summarization:\n"
    "summarization_none\nkeyframe_pruning_every_2nd\n"
    "summarization_observation_count\n")
    adf_json += "\"area_%s\", " % raw_input("Area:\nindoors\noutdoors\n"
    "indoors_and_outdoors\n")
    adf_json += "\"collection_method_%s\", " % raw_input("Collection method:"
    "\nhandheld\nheadset\n")
    adf_json += "\"lighting_%s\", " % raw_input("Lighting type:\n"
    "varied\nstore\ndim\noutdoors_sunny\noutdoors_overcast"
    "\nhouse_natural_dim\nhouse_natural_overcast"
    "\nhouse_dim\nhouse_bright\n")
    adf_json += "\"tilt_%s\", " % raw_input("Tilt:\n"
    "vertical\ntilted\nhorizontal\nvaried\n")
    adf_json += "\"layout_%s\", " % raw_input("Layout type:\n"
    "portrait\nlandscape\nportrait_and_landscape\n")
    adf_json += "\"device_%s\"]\n}" % raw_input("Device:\nyellowstone\n")
    adf_properties.write(adf_json)

def compress_files(destination, source_dir):
  with tarfile.open(destination, "w:gz") as tar:
    tar.add(source_dir, arcname=os.path.basename(source_dir))

def upload():
  pass




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
