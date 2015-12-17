#!/usr/bin/python

# Author: charlesz@google.com
# Trademark Google Inc., all rights reserved

import argparse
import calendar
import datetime
import os
import platform
import subprocess
import sys
import time
import tarfile


parser = argparse.ArgumentParser()
parser.add_argument("--json", action='store_true',
                    default=False, dest='json',
                    help='Change the json files from default.')
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

DEFAULT_DIR = rootpath + "/Desktop"

country = "US" #raw_input("Country (Ex. US): ")
state = "CA" #raw_input("State Abbreviation (Ex. CA): ")
city = "Mountain View" #raw_input("City Code (Ex. MTV for Mountain View): ")
location = "GoogleSB65" #raw_input("Collect Location (Ex. GoogleSB65): ")
date = time.strftime("%Y%m%d")

dest_dir = "/home/atap/" + country
dest_dir += "_" + state
dest_dir += "_" + city
dest_dir += "_" + location
dest_dir += "_" + date

devices = [device[0]
          for device in [line.split("\t")
          for line in os.popen('adb devices').read().split("\n")
          if len(line.split("\t")) == 2]]


def get_adf_list(serial):
  get_raw_data = "adb -s %s shell ls " \
                     "data/data/com.projecttango.tangomapper/files/" % serial
  raw_data = [line.split("\r")[0] for line in
         os.popen(get_raw_data).read().split("\n")
         if len(line.split("\r")) == 2]
  for i in raw_data:
    if i.endswith("No such file or directory"):
      print  "This device, %s, has no adf's to pull." % serial
  return raw_data

def datetime_stamps(devices=devices):
  for i in devices:
    print "Device serial number: %s" % i
    raw_data = get_adf_list(i)
    for data in range(len(raw_data) - 1):
      datetime_stamp = ["%04d%02d%02d%04d" % (int(raw_data[data][0:4]),
             int(list(calendar.month_abbr).index(raw_data[data][4:7])),
             int(raw_data[data][7:9]),
             int(raw_data[data].split("_")[1][0:4]))]
      print datetime_stamp

def mkdir(dest_dir):
  if not os.path.exists(dest_dir):
    os.system("mkdir " + dest_dir)

def adf_pull(devices):
  for device in devices:
    raw_data = get_adf_list(device)
    begin = time.time()
    for data in raw_data:
      time.sleep(5)
      start = time.time()
      pull_from = "data/data/com.projecttango.tangomapper/files/" + data
      os.system("adb -s %s pull %s %s" % (device, pull_from, mkdir(dest_dir)))
      print "The pull took: %s" % countup(start)
    countup(begin)

def create_json(destination_dir=DEFAULT_DIR):
  if argParser.json:
    with open(destination_dir + "/properties.json", 'w') as properties:
      properties_file = "{\n\t\"collection_timestamp\" : \"%s %s\",\n"\
      % (str(datetime.date.today()), str(raw_input("Time of collect: "
      "(hh:mm:ss)\n")))
      properties_file += "\n\t\"tags\"\n\" : [\"collection_method_%s\", " \
      % raw_input("Collection method:\nhandheld\nheadset\n")
      properties_file += "\"lighting_%s\", " % raw_input("Lighting type:\n"
      "varied\nstore\ndim\noutdoors_sunny\noutdoors_overcast"
      "\nhouse_dim\nhouse_bright\n")
      properties_file += "\n\t\t\"tilt_%s\", " % raw_input("Tilt:\n"
      "vertical\ntilted\nhorizontal\nvaried\n")
      properties_file += "\"layout_%s\", " % raw_input("Layout type:\n"
      "portrait\nlandscape\nportrait_and_landscape\n")
      properties_file += "\"device_yellowstone\", "
      properties_file += "\n\t\t\"orientation_%s\"]\n}\"" \
      % raw_input("Orientation:\nuniform\nvaried\n")
      properties.write(properties_file)
    with open(destination_dir + "/adf_properties.json", 'w') as adf_properties:
      adf_json = "{\n\t\"tags\" : [\"%s\", " % \
      raw_input("Algorithm scale (select all that apply):\n"
      "\"algorithm_matching_small_scale\"\n"
      "\"algorithm_matching_medium_scale\"\n"
      "\"algorithm_matching_large_scale\"\n"
      "\"algorithm_retrieval_small_scale\"\n"
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
  else:
    with open(destination_dir + "/properties.json", 'w') as properties:
      properties_file = "{\n    \"collection_timestamp\" : \"%s %s\",\n"\
      % (str(raw_input("Date of collect: \n")),
         str(raw_input("Time of collect: \n")))
      properties_file += "    \"tags\" : [\"collection_method_handheld\", " \
      "\"lighting_store\",\n\t\"tilt_tilted\", \"layout_landscape\", " \
      "\"device_yellowstone\", \n\t\"orientation_uniform\"]\n}"
      properties.write(properties_file)
    with open(destination_dir + "/adf_properties.json", 'w') as adf_properties:
      adf_json = "{\n    \"tags\" : [\"algorithm_matching_medium_scale\", " \
      "\"construction_VIWLS\", \"floor_single\", \"compression_none\", " \
      "\"summarization_none\", \"area_indoors\", " \
      "\"collection_method_handheld\", \"lighting_store\", \"tilt_tilted\", " \
      "\"layout_landscape\", \"device_yellowstone\"]\n}"
      adf_properties.write(adf_json)


def compress_files(destination, source_dir):
  with tarfile.open(destination, "w:gz") as tar:
    tar.add(source_dir, arcname=os.path.basename(source_dir))
    return destination

def upload(destination, source_dir=dest_dir):
  push_destination = "gs://project-tango-internal-data/" + destination
  subprocess.call(["gsutil", "cp", "-r", source_dir, push_destination])


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


def main(devices=devices):
  for device in devices:
    print get_adf_list(device)
  datetime_stamps()


if __name__ == "__main__":
  main()
