#!/usr/bin/python
# Copyright 2016 Google Inc. All Rights Reserved.
# Distributed under the Project Tango Preview Development Kit (PDK) Agreement.
# CONFIDENTIAL. AUTHORIZED USE ONLY. DO NOT REDISTRIBUTE.

# Authors: charlesz@google.com, slynen@google.com

################################################################################
# This script is used by ops for downloading datasets from device and uploading
# them to a cloud storage bucket from where they can be consumed for algorithm
# evaluation and ADF creation. The script can also process a local directory to
# which datasets have been previously downloaded using the adbfastpullbyserial
# script.
#
# This script requires the pick and enum libraries to be installed:
#   sudo pip install pick
#   sudo pip install enum
#
################################################################################

import argparse
import calendar
import datetime
import fnmatch
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import threading
import time
try:
  from enum import Enum
except ImportError:
  print "Enum library missing, installing now using: 'sudo pip install enum'"
  print "Script will restart after installation completes."
  os.system("sudo pip install enum")
  os.execv(__file__,sys.argv)
try:
  from pick import pick
except ImportError:
  print "Pick library missing, installing now using: 'sudo pip install pick'"
  print "Script will restart after installation completes."
  os.system("sudo pip install pick")
  os.execv(__file__,sys.argv)


# In order to decide if we need to ask the user once for the location of the
# collect or for every dataset individually.
class DatasetOrigin(Enum):
  SingleBuilding = 0
  MultipleBuildings = 1


# To decide where and in which format the datasets should be uploaded. This
# script can be used for operator production dataset as well as ground-truth
# dataset collects.
class DatasetType(Enum):
  GroundTruth = 0
  Operations = 1


  # Timer that tells you how long it took to run a command.
def countup(start_time):
  """Generates a count-up timer tells how long a command ran.
  Args:
    start_time: Time the command started at, stored in a variable, and passed.
    to countup().
  """
  end = time.time() - start_time
  days = int(end) / 86400
  hours = (int(end % 86400) / 3600)
  minutes = ((int(end) % 86400) % 3600) / 60
  seconds = int(end) % 60
  return "%02d:%02d:%02d:%02d" % (days, hours, minutes, seconds)


# Obtain a list of the datasets that are available in the specified application
# storage on a given device (specified by serial number).
# application_data_space is the private app directory where the datasets are stored.
def list_datasets_on_device(serial, application_data_space):
  get_raw_data = "adb -s %s shell ls %s" % (serial, application_data_space)

  directory_listing = os.popen(get_raw_data).read()
  raw_data = [line.split("\r")[0]
              for line in directory_listing.split("\n")
              if len(line.split("\r")) == 2]

  if not raw_data:
    title = (
        "There is not a single dataset on device {0}, please double-check. ".format(
            serial))
    pick(["OK"], title)
    return None

  if raw_data[0].endswith("Permission denied"):
    run_adb_command("adb -s %s root" % serial)
    time.sleep(3)
    run_adb_command("adb -s %s remount" % serial)
    raw_data = list_datasets_on_device(serial, application_data_space)
    if raw_data[0].endswith("Permission denied"):
      print "Error counld not get access to the device."
      exit(1)
  if raw_data[0].endswith("No such file or directory"):
    print "This device, %s, has no datasets to pull." % serial
  return raw_data


# Get the date and time stamps from a given dataset string.
def get_date_and_time_from_dataset_folder(data):
  # Date encoded with month name.
  if len(data) > 15:
    date_stamp = "%04d%02d%02d" % (
        int(data[0:4]), int(list(calendar.month_abbr).index(data[4:7])),
        int(data[7:9]))
  else:
    date_stamp = "%08d" % int([str(data)][0].split("_")[0])

  time_stamp = "%06d" % int([str(data)][0].split("_")[1][0:6])
  return date_stamp, time_stamp


# Create the directory if it doesn't exist.
def mkdir(destination_directory):
  if not os.path.exists(destination_directory):
    os.makedirs(destination_directory)
  return str(destination_directory)


# Create a dataset unique identifier from the venue name, date and time.
def make_dataset_id(venue, date_stamp, time_stamp):
  return "_".join([venue, date_stamp, time_stamp])


# Create the output directory to store the files on disk.
def make_output_dir(root_dir, venue, date_stamp, time_stamp):
  identifier = make_dataset_id(venue, date_stamp, time_stamp)
  directory = os.path.join(root_dir, identifier)
  mkdir(directory)
  return directory


# Run a given adb command and echo if the command returns an output.
def run_adb_command(command):
  result = os.popen(command).readlines()
  if len(result) > 0:
    print "ADB returned unexpected: %s" % result


# Get the size of a file in bytes on device via adb.
def adb_get_file_size(device, file):
  get_filesize = "adb -s %s shell ls -l %s" % (device, file)
  file_size_raw = os.popen(get_filesize).read().split()
  if len(file_size_raw) < 4:
    return -1
  return int(file_size_raw[3])


# Download a dataset from the given device and application folder and store it
# into a folder defined by venue name, date and time.
def adb_pull_dataset(root_dir, venue, device, application_space, dataset,
                     date_stamp, time_stamp):
  destination_dir = make_output_dir(root_dir, venue, date_stamp, time_stamp)
  print "Saving dataset to %s " % destination_dir
  start = time.time()
  pull_from = os.path.join(application_space, dataset)
  all_files = []

  # Get all files in this dataset.
  get_dataset = "adb -s %s shell ls %s" % (device, pull_from)
  directory_listing = os.popen(get_dataset).read()
  raw_data = [line.split("\r")[0]
              for line in directory_listing.split("\n")
              if len(line.split("\r")) == 2]

  # Find out if we have HAL datasets or sensor-data.
  data_sub_dir = ""
  if raw_data.count("bag") > 0:
    raw_data.remove("bag")
    data_sub_dir = "bag"

  if raw_data.count("sensors") > 0:
    raw_data.remove("sensors")
    data_sub_dir = "sensors"

  # Download all auxiliarly files.
  pull_commands = []
  for file_name in raw_data:
    file_source_path = os.path.join(pull_from, file_name)
    file_destination_path = os.path.join(destination_dir, file_name)
    filesize = adb_get_file_size(device, file_source_path)

    # Get current size on disk to determine if we can skip the file.
    file_size_disk = 0
    if os.path.exists(file_destination_path):
      file_size_disk = os.path.getsize(file_destination_path)

    if filesize == file_size_disk:
      print("Skipping download of %s since already on disk as %s with same size"
            % (file_source_path, file_destination_path))
    else:
      print "Queueing download: %s\n\t-> %s" % (file_source_path,
                                                file_destination_path)
      pull_commands.append(("adb -s %s pull %s %s" % (device, file_source_path,
                                                      file_destination_path),
                            file_destination_path, filesize))

    # Get all sensor data files in this dataset.
  dataset_pull_path = os.path.join(pull_from, data_sub_dir)
  get_dataset = "adb -s %s shell ls %s" % (device, dataset_pull_path)
  directory_listing = os.popen(get_dataset).read()
  sensor_raw_data = [line.split("\r")[0]
                     for line in directory_listing.split("\n")
                     if len(line.split("\r")) == 2]

  destination_sensor_data_dir = os.path.join(destination_dir, data_sub_dir)

  # Parallel pull files. Skip those that area already on disk.
  for file_name in sensor_raw_data:
    file_source_path = os.path.join(dataset_pull_path, file_name)
    file_destination_path = os.path.join(destination_sensor_data_dir, file_name)
    filesize = adb_get_file_size(device, file_source_path)

    # Get current size on disk to determine if we can skip the file.
    file_size_disk = 0
    if os.path.exists(file_destination_path):
      file_size_disk = os.path.getsize(file_destination_path)

    if filesize == file_size_disk:
      print("Skipping download of %s since already on disk as %s with same size"
            % (file_source_path, file_destination_path))
    else:
      print "File size bytes %s (disk)" % filesize
      print "Downloading %s\n\t-> %s" % (file_source_path,
                                         file_destination_path)
      pull_commands.append(("adb -s %s pull %s %s" % (device, file_source_path,
                                                      file_destination_path),
                            file_destination_path, filesize))

  threads = []
  for command, file_destination_path, filesize in pull_commands:
    t = threading.Thread(target=run_adb_command, args=(command,))
    threads.append(t)
    t.start()

  found_unfinished_thread = True
  while found_unfinished_thread == True:
    found_unfinished_thread = False
    for thread in threads:
      if thread.is_alive():
        found_unfinished_thread = True
        break

    progress = []
    num_complete = 0
    for command, file_destination_path, filesize in pull_commands:
      # Get the current filesize on disk.
      if os.path.isfile(file_destination_path):
        current_disk_size = os.path.getsize(file_destination_path)
      else:
        current_disk_size = 0

      percent = current_disk_size / float(filesize)
      mb_file = filesize / 1024. / 1024.
      mb_disk = current_disk_size / 1024. / 1024.
      file_name = os.path.split(file_destination_path)[-1]
      if (current_disk_size < filesize):
        progress.append("\tFile {:<40}: {:.2%} ({:.2f}/{:.2f} MB)".format(
            file_name, percent, mb_disk, mb_file))
      else:
        num_complete += 1

    print("Download progress for %s: (%d/%d files completed)." %
          (device, num_complete, len(pull_commands)))
    print "\n".join(progress)

    if found_unfinished_thread == True:
      time.sleep(1)

  print "The pull took: %s" % countup(start)
  return destination_dir


def cleanup_temp_folder(uploaded_datasets, root_dir):
  dataset_information = []
  for uploaded_dataset in uploaded_datasets:
    folder_size_bytes = float(get_directory_size(uploaded_dataset[
        "dataset_dir"]))

    dataset_information.append("{:<40} {:.2}MB -- Upload OK: {:<}".format(
        os.path.split(uploaded_dataset["dataset_dir"])[-1], folder_size_bytes /
        1024. / 1024., str(uploaded_dataset["upload_ok"])))

  folder_information = []
  for dir_name in os.listdir(root_dir):
    folder_size_bytes = float(get_directory_size(os.path.join(root_dir,
                                                              dir_name)))
    folder_information.append("{:<40} {:.2}MB".format(
        dir_name, folder_size_bytes / 1024. / 1024.))

  title = ("Status of datasets:\n\t" + "\n\t".join(dataset_information) + "\n\n"
           "The following temporary files will be deleted from disk:\n\t" +
           "\n\t".join(folder_information))

  _, ok = pick(["Cancel", "OK"], title)
  if ok == 0:
    print "Aborting deletion of %s." % root_dir
    return
  shutil.rmtree(root_dir)


def cleanup_devices(pulled_datasets, dataset_type):
  devices = set()
  for pulled_dataset in pulled_datasets:
    if pulled_dataset["device"] is not None:
      devices.add(pulled_dataset["device"])

  device_information = []
  if devices:
    title = (
        "The following devices will be emptied:\n\t" + "\n\t".join(devices))

    _, ok = pick(["Cancel", "OK"], title)
    if ok == 0:
      print "Aborting cleaning of\n%s." % "\n\t".join(devices)
      return

    for device in devices:
      if dataset_type == DatasetType.Operations:
        run_adb_command("adb -s %s shell rm -rf /sdcard/tangomapscreator/*" %
                        device)
        run_adb_command(
            "adb -s %s shell rm -rf "
            "/data/data/com.projecttango.tango/files/datasets/*"
            % device)

      else:
        assert dataset_type == DatasetType.GroundTruth
        run_adb_command(
            "adb -s %s shell rm -rf "
            "/data/data/com.projecttango.tangomapper/files/*"
            % device)


# Compress the dataset and metadata files into an archive for upload.
def compress_files(source_dir, tar_name):
  if not os.path.isfile(tar_name):
    with tarfile.open(tar_name, "w:gz") as tar:
      print "Compressing %s to %s" % (source_dir, tar_name)
      tar.add(source_dir, arcname=os.path.basename(source_dir))
  else:
    print "Skipped compressing %s since %s already exists." % (source_dir,
                                                               tar_name)
  return tar_name


# Upload the contents of a folder to GCS.
def upload_folder(source_file, bucket_name, subdir):
  destination_dir = "gs://{0}/{1}".format(bucket_name, subdir)
  source_dir = os.path.dirname(os.path.realpath(source_file))
  command = ["gsutil", "-m", "rsync", source_dir, destination_dir]
  print "Running upload command: %s" % " ".join(command)
  subprocess.call(command)


  # Upload the contents of a folder and it's subfolders to GCS.
def upload_folder_recursive(source_dir, bucket_name, subdir):
  destination_dir = "gs://{0}/{1}".format(bucket_name, subdir)
  # First we check that the remote directory exists (this seems to be necessary
  # on osx).
  marker_file_name = os.path.join(source_dir, "upload_started")
  with open(marker_file_name, "w") as marker_file:
    marker_file.write("upload started")
  command = ["gsutil", "cp", marker_file_name,
             destination_dir + "/upload_started"]

  command = ["gsutil", "-m", "rsync", "-r", source_dir, destination_dir]
  print "Running upload command: %s" % " ".join(command)
  subprocess.call(command)


# Handle the uploading of ground-truth files to GCS.
def handle_gt_upload_to_bucket(pulled_datasets, destination_sub_directory):
  cloud_bucket_name = "project-tango-internal-data"
  dataset_type = DatasetType.GroundTruth
  uploaded_datasets = []
  for dataset_information in pulled_datasets:
    assert os.path.exists(dataset_information["dataset_dir"])
    # Ground-truth collects are compressed and uploaded.
    try:
      identifier = make_dataset_id(dataset_information["venue"],
                                   dataset_information["date_stamp"],
                                   dataset_information["time_stamp"])
      archive_sync_path = os.path.join(dataset_information["dataset_dir"],
                                       "upload")
      mkdir(archive_sync_path)
      archive_filename = os.path.join(archive_sync_path, identifier + ".tar.gz")
      # Store the archive into a subdir which we can then rsync at once.
      archive_name = compress_files(dataset_information["dataset_dir"],
                                    archive_filename)
      bucket_destination = dataset_information["venue"]
      if destination_sub_directory is None:
        bucket_destination += "/staging"
      else:
        bucket_destination += "/" + destination_sub_directory

      upload_folder(archive_name, cloud_bucket_name, bucket_destination)
      dataset_information["upload_ok"] = True
      uploaded_datasets.append(dataset_information)
    except IOError as e:
      dataset_information["upload_ok"] = False
      uploaded_datasets.append(dataset_information)
      print "Error processing list_datasets_on_device %s %s." % (
          dataset_information["dataset_dir"], e)

  return uploaded_datasets


# Return the size of a directory.
def get_directory_size(start_path):
  total_size = 0
  for dirpath, dirnames, filenames in os.walk(start_path):
    for filename in filenames:
      file = os.path.join(dirpath, filename)
      total_size += os.path.getsize(file)
  return total_size


# Handle the uploading of operations collect dataset to GCS.
def handle_ops_upload_to_bucket(root_dir, ops_annotations_folder,
                                pulled_datasets):
  cloud_bucket_name = "project-tango-ops-collects-staging"
  dataset_type = DatasetType.Operations

  dataset_collection_groups = {}

  uploaded_datasets = []

  annotations_directory = os.path.join(root_dir, ops_annotations_folder)

  # Get the list of all dataset UUIDs that we are processing.
  available_datasets = set()
  for dataset_information in pulled_datasets:
    assert os.path.exists(dataset_information["dataset_dir"])
    metadata_file_path = os.path.join(dataset_information["dataset_dir"],
                                      "dataset_metadata.yaml")
    with open(metadata_file_path, "r") as metadata_file:
      all_meta = metadata_file.readlines()
      dataset_metadata = all_meta[0]
      dataset_id = dataset_metadata.split(":")[1].strip()
      available_datasets.add(dataset_id)

  # Collect all navigation datasets.
  available_navigation_datasets = []
  backup_dataset = None
  for _, dirnames, _ in os.walk(annotations_directory):
    for adf_uuid in dirnames:
      dataset_uuid_file = os.path.join(annotations_directory, adf_uuid,
                                       adf_uuid + "-dataset-uuid.txt")
      if os.path.exists(dataset_uuid_file):
        with open(dataset_uuid_file) as f:
          for adf_metadata in f.readlines():
            adf_dataset_id = adf_metadata.split(":")[1].strip()
            if adf_metadata.find("adf") != -1:
              alignments_file = os.path.join(annotations_directory, adf_uuid,
                                             adf_uuid + "-alignments")
              if os.path.exists(alignments_file):
                available_navigation_datasets.append((adf_uuid, adf_dataset_id))
              else:
                backup_dataset = (adf_uuid, adf_dataset_id)

  if backup_dataset is None and not available_navigation_datasets:
    title = (
        "There is not a single navigation dataset for venue: {0} this script "
        "won't work. ".format(dataset_information["venue"]))
    pick(["OK"], title)
    exit(-1)

  available_navigation_datasets.append(backup_dataset)

  # Go over all datasets and gather information about alignment, type etc.
  for dataset_information in pulled_datasets:
    assert os.path.exists(dataset_information["dataset_dir"])
    print "Processing dataset: %s" % dataset_information["dataset_dir"]

    # If running in ops mode, also copy the files from maps creator.
    # The metadata files such as FLP measurements, alignment data etc. are stored
    # in /sdcard/tangomapscreator by tango-maps creator in a directory named by
    # the adf-uuid. The dataset in contrast is stored in the private app space of
    # tango core. We can match both (and package them correctly together for
    # upload) by parsing the dataset-uuid from the dataset_metadata.yaml stored
    # in the dataset folder and by matching it against the dataset-uuid stored
    # in the ${adf_uuid}-dataset-uuid.txt file which is stored by maps-creator.
    # At the moment the script is not robust to these files missing since this
    # essentially means that the data is incomplete.
    dataset_id = None
    metadata_file_path = os.path.join(dataset_information["dataset_dir"],
                                      "dataset_metadata.yaml")
    with open(metadata_file_path, "r") as metadata_file:
      all_meta = metadata_file.readlines()
      dataset_metadata = all_meta[0]
      dataset_id = dataset_metadata.split(":")[1].strip()
      print "\tGot dataset ID: %s" % dataset_id

    matching_adf_uuid = None
    is_navigation_dataset = False
    flp_file_name = None

    # Find the correct annotations (adf) subdirectory. We don't know which
    # adf uuid corresponds to which dataset so we need to iterate over all
    # available, read out the ${adf_uuid}-dataset-uuid.txt and check if the
    # dataset uuids match. If this is the case we know which folder contents
    # need to be copied to the dataset directory.
    print "\tSearching the corresponding adf uuid in the annotations directory."
    # Store the uuid of one of the datasets for which we have alignment
    # information.
    some_adf_uuid_of_venue = available_navigation_datasets[0][0]

    for _, dirnames, _ in os.walk(annotations_directory):
      for adf_uuid in dirnames:
        # Parse the dataset uuids to find the navigation dataset uuid.
        dataset_uuid_file = os.path.join(annotations_directory, adf_uuid,
                                         adf_uuid + "-dataset-uuid.txt")
        adf_dataset_id = None

        # Check if the metadata file in this data collect mentions the current
        # dataset. Datasets are mentioned to belong to a particular ADF if their
        # ID is listed in the X-dataset-uuid.txt file.
        adf_metadata = []
        if os.path.exists(dataset_uuid_file):
          with open(dataset_uuid_file) as f:
            for adf_metadata in f.readlines():
              adf_dataset_id = adf_metadata.split(":")[1].strip()
              print "Looking at dataset ID: %s <-> %s" % (adf_dataset_id,
                                                          dataset_id)
              if adf_dataset_id == dataset_id:
                matching_adf_uuid = adf_uuid
                if adf_metadata.find("adf") != -1:
                  is_navigation_dataset = True
                  print("\t\tDataset %s with ID %s is a navigation dataset to "
                        "adf-ID: %s" % (dataset_information["dataset_dir"],
                                        dataset_id, matching_adf_uuid))
                else:
                  assert adf_metadata.find("feature") != -1
                  is_navigation_dataset = False
                  print(
                      "Dataset %s with ID %s is a coverage dataset to adf-ID: %s"
                      % (dataset_information["dataset_dir"], dataset_id,
                         matching_adf_uuid))
                break

    # Store the gathered information into the metadata.
    with open(metadata_file_path, "r") as metadata_file:
      all_meta = metadata_file.readlines()
      # Append venue, time and date information to the metadata file if it's not there yet.
      if not any("venue" in s for s in all_meta):
        with open(metadata_file_path, "a") as metadata_file_write:
          metadata_file_write.write("venue: %s\n" %
                                    dataset_information["venue"])
          metadata_file_write.write("date: %s\n" %
                                    dataset_information["date_stamp"])
          metadata_file_write.write("time: %s\n" %
                                    dataset_information["time_stamp"])
          print "\tAnnotated metadata with venue and time information"
      if not any("is_navigation_dataset" in s for s in all_meta):
        with open(metadata_file_path, "a") as metadata_file_write:
          metadata_file_write.write("is_navigation_dataset: %s\n" %
                                    is_navigation_dataset)
          print "\tAnnotated metadata with dataset type."

    # If there is not a single navigation dataset, then something is so bad that
    # we can't continue. In fact it means that there are coverage datasets
    # without a navigation dataset which should never happen.
    if some_adf_uuid_of_venue is None:
      title = ("There is not a single dataset with alignment information. "
               "Please go back into maps creator and align at least one ADF "
               "from building/venue: {:<}".format(dataset_information["venue"]))
      pick(["OK"], title)
      exit(-1)

    if matching_adf_uuid is None:
      dataset_folder = dataset_information["dataset_dir"]
      total_dataset_size = get_directory_size(dataset_folder)
      dataset_size_mb = float(total_dataset_size) / 1024. / 1024.
      title = (
          "Dataset {:<} is not a navigation dataset nor referenced anywhere.\n"
          "Probably this is the result of a TangoMapsCreator crash.\n\n"
          "**** It consists of {:.2f} MB of data. ****\n\n"
          "Assuming this is an extra (coverage) dataset to ADF: {:<}. \n\n"
          "Do you want to keep this dataset?".format(
              dataset_folder, dataset_size_mb, some_adf_uuid_of_venue))

      _, ok = pick(["yes", "no"], title)
      if ok == 1:
        print "Skipping dataset %s on user request." % dataset_folder
        dataset_information["upload_ok"] = False
        uploaded_datasets.append(dataset_information)
        continue

      matching_adf_uuid = some_adf_uuid_of_venue
      print(
          "Dataset %s with ID %s is an orphaned dataset, associated to adf-ID: %s"
          % (dataset_information["dataset_dir"], dataset_id, matching_adf_uuid))
      is_navigation_dataset = False
      # Copy the flp data to the navigation dataset directory if it is in the
      # root annotations folder.
      copy_from = os.path.join(annotations_directory, dataset_id + "-flp")
      dir_copy_to = os.path.join(annotations_directory, matching_adf_uuid)
      copy_to = os.path.join(dir_copy_to, dataset_id + "-flp")
      if os.path.exists(copy_from):
        shutil.copy(copy_from, copy_to)
      else:
        open(copy_to, "a").close()  # Touch the flp file.

    if matching_adf_uuid not in dataset_collection_groups:
      dataset_collection_groups[matching_adf_uuid] = {"navigation_dataset": {},
                                                      "coverage_datasets": []}

    # Store all information about the dataset and assign coverage datasets to the corresponding navigation dataset.
    if is_navigation_dataset:
      dataset_collection_groups[matching_adf_uuid][
          "navigation_dataset"] = {"dataset_id": dataset_id,
                                   "dataset_information": dataset_information}
    else:
      dataset_collection_groups[matching_adf_uuid]["coverage_datasets"].append(
          {"dataset_id": dataset_id,
           "dataset_information": dataset_information})

    # If everything goes south, there can be adf uuids that list coverage datasets,
    # but no navigation dataset. We give the user the possibility to just assign
    # the coverage datasets to a different navigation dataset.
  list_of_healthy_nav_datasets = []
  list_of_healthy_nav_dataset_names = []
  for adf_uuid, dataset_collection in dataset_collection_groups.iteritems():
    navigation_dataset = dataset_collection["navigation_dataset"]
    if navigation_dataset:
      list_of_healthy_nav_datasets.append((adf_uuid, navigation_dataset))
      list_of_healthy_nav_dataset_names.append(navigation_dataset[
          "dataset_information"]["dataset_dir"].split("/")[-1])

  for adf_uuid, dataset_collection in dataset_collection_groups.iteritems():
    navigation_dataset = dataset_collection["navigation_dataset"]
    if not navigation_dataset:
      title = (
          "ADF uuid {0} has {1} coverage datasets, but no navigation dataset "
          "assigned. Which ADF do you want to assign the coverage adfs to?".format(
              adf_uuid, len(dataset_collection["coverage_datasets"])))

      if not list_of_healthy_nav_dataset_names:
        print "Not a single navigation dataset available. Can't recover."
        exit(-1)

      _, index = pick(list_of_healthy_nav_dataset_names, title)
      dataset_collection_groups[adf_uuid][
          "navigation_dataset"] = list_of_healthy_nav_datasets[index][1]

    ##############################################################################
    # For all dataset groups copy together the annotation files and upload data.
    # Now copy the annotation files to the output directory of the corresponding dataset.
  for adf_uuid, dataset_collection in dataset_collection_groups.iteritems():
    print "Working on adf uuid %s" % adf_uuid
    navigation_dataset = dataset_collection["navigation_dataset"]
    print "Num coverage datasets %s " % len(dataset_collection[
        "coverage_datasets"])
    assert len(navigation_dataset) > 0

    print navigation_dataset
    venue = navigation_dataset["dataset_information"]["venue"]

    folder_to_copy_from = os.path.join(annotations_directory, adf_uuid)
    navigation_dataset_uuid = navigation_dataset["dataset_id"]
    navigation_dataset_dir = navigation_dataset["dataset_information"][
        "dataset_dir"]
    print "Copying annotation/flp files %s -> %s" % (folder_to_copy_from,
                                                     navigation_dataset_dir)
    src_dest_files = [(adf_uuid + "-alignments", "geo-alignments"),
                      (adf_uuid + "-annotation.buf", "annotation.buf"),
                      (adf_uuid + "-junction.buf", "junction.buf"),
                      (adf_uuid + "-dataset-uuid.txt", "dataset-uuids.txt"),
                      (navigation_dataset_uuid + "-flp", "flp")]

    if not os.path.exists(os.path.join(folder_to_copy_from, adf_uuid +
                                       "-alignments")):
      title = (
          "Dataset {:<} does not have alignment information.\n\n"
          "This can be ok, in case you went into alignment mode but "
          "didn't move the ADF because the alignment was already good.\n\n"
          "Do you want to continue or abort to fix this in MapsCreator?".format(
              folder_to_copy_from))
      _, ok = pick(["continue", "abort"], title)
      if ok == 1:
        print "Abort processing on user request."
        exit(-1)

    for source_file, dest_file in src_dest_files:
      copy_from = os.path.join(folder_to_copy_from, source_file)
      copy_to = os.path.join(navigation_dataset_dir, dest_file)
      if os.path.exists(copy_from):
        shutil.copy(copy_from, copy_to)
      else:
        print("File %s not found for copying, this is likely a problem in the "
              "recording app.") % copy_from

      # Upload the navigation dataset.
    bucket_destination = os.path.join(venue, navigation_dataset_uuid,
                                      navigation_dataset_uuid)
    upload_folder_recursive(navigation_dataset_dir, cloud_bucket_name,
                            bucket_destination)
    navigation_dataset["dataset_information"]["upload_ok"] = True
    uploaded_datasets.append(navigation_dataset["dataset_information"])

    # Copy the flp files for the coverage datasets.
    for coverage_dataset in dataset_collection["coverage_datasets"]:
      coverage_dataset_uuid = coverage_dataset["dataset_id"]
      coverage_dataset_dir = coverage_dataset["dataset_information"][
          "dataset_dir"]
      print "Copying flp file %s -> %s" % (folder_to_copy_from,
                                           coverage_dataset_dir)
      copy_from = os.path.join(folder_to_copy_from,
                               coverage_dataset_uuid + "-flp")
      copy_to = os.path.join(coverage_dataset_dir, "flp")
      if os.path.exists(copy_from):
        shutil.copy(copy_from, copy_to)
      else:
        print("File %s not found for copying, this is likely a problem in the "
              "recording app.") % copy_from

      # Upload the coverage dataset.
      bucket_destination = os.path.join(venue, navigation_dataset_uuid,
                                        coverage_dataset_uuid)
      upload_folder_recursive(coverage_dataset_dir, cloud_bucket_name,
                              bucket_destination)

      coverage_dataset["dataset_information"]["upload_ok"] = True
      uploaded_datasets.append(coverage_dataset["dataset_information"])

  # Now release the entire data collection for processing, by marking the upload as complete.
    print "Marking the dataset %s as complete." % navigation_dataset_dir
    marker_file_name = os.path.join(navigation_dataset_dir, "upload_complete")
    with open(marker_file_name, "w") as marker_file:
      marker_file.write("upload complete")
    bucket_destination = os.path.join(cloud_bucket_name, venue,
                                      navigation_dataset_uuid)
    command = ["gsutil", "cp", marker_file_name,
               "gs://" + os.path.join(bucket_destination, "upload_complete")]
    print "Running upload command: %s" % " ".join(command)
    subprocess.call(command)

    print("*****************************************************************")
    print(
        "* Upload of datasets collected at %s containing %d coverage collects "
        "is complete." % (venue, len(dataset_collection["coverage_datasets"])))
    print("*****************************************************************")

  return uploaded_datasets


# Handle the downloading of datasets and annotation files from the device.
def handle_device_download(root_dir, venue, ops_annotations_folder,
                           dataset_type, dataset_origin,
                           destination_sub_directory):
  # Depending on which type of data we have, the destination bucket changes.
  # Depending on which application we are running, switch the app path from
  # which to download.
  application_data_space = "/data/data/com.projecttango.tangomapper/files/"
  if dataset_type == DatasetType.GroundTruth:
    application_data_space = "/data/data/com.projecttango.tangomapper/files/"
  else:
    if dataset_type == DatasetType.Operations:
      application_data_space = "/data/data/com.projecttango.tango/files/datasets/"
    else:
      print "Error unknown dataset type"
      exit(-1)

      # Set defaults for cases where we have a per dataset selection.
  country = "US"
  state = "CA"
  city = "MTV"
  location = "GoogleSB65"

  devices = [device[0]
             for device in [line.split("\t")
                            for line in os.popen("adb devices").readlines()
                            if len(line.split("\t")) == 2]]

  devices_and_folders = []

  for device in devices:
    # If we are in ops collection mode, download first all files from maps creator.
    if dataset_type == DatasetType.Operations:
      print "Downloading annotation files from MapsCreator..."
      directory = os.path.join(root_dir, ops_annotations_folder)
      mkdir(directory)
      file_source_path = "/sdcard/tangomapscreator/"
      command = "adb -s %s pull %s %s" % (device, file_source_path, directory)
      result = os.popen(command).readlines()
      if len(result) > 0:
        print "ADB returned unexpected: %s" % result

    # Now download the raw datasets.
    raw_data = list_datasets_on_device(device, application_data_space)
    if raw_data == None:
      continue

    # Drop the subfolder containing robustness logging datasets.
    if raw_data.count("robustness"):
      raw_data.remove("robustness")

    for dataset_path in raw_data:
      date_stamp, time_stamp = get_date_and_time_from_dataset_folder(
          dataset_path)

      # Check the time and date.
      parsed_date = (2000, 0, 0)
      parsed_time = (0, 0, 0)
      while parsed_date[0] < 2012:  # Before Twizzler was alive.
        try:
          parsed_date = time.strptime(date_stamp, "%Y%m%d")
        except ValueError:
          print("Failed to parse date from {0}".format(date_stamp))

        try:
          parsed_time = time.strptime(time_stamp, "%H%M%S")
        except ValueError:
          try:
            parsed_time = time.strptime(time_stamp, "%H%M")
            # Append missing seconds.
            parsed_time = (parsed_time, 0)
          except ValueError:
            print("Failed to parse time from {0}".format(time_stamp))

        # Catch unset device times.
        if parsed_date[0] < 2012:  # Before Twizzler was alive.
          date_stamp = raw_input(
              "Device {0} date seems to be unset. Please provide "
              "a date for the dataset collect in the format "
              "YYYYMMDD (current: {1}):".format(device, date_stamp))
          time_stamp = raw_input(
              "Device {0} time seems to be unset. Please provide "
              "a time for the dataset collect in the format "
              "HHMMSS (current: {1}):".format(device, time_stamp))

        # If not all datasets are from the same location, query the user per dataset.
      if dataset_origin == DatasetOrigin.MultipleBuildings:
        while True:
          print "Please provide information for device {0} and dataset {1} {2}".format(
              device, date_stamp, time_stamp)

          # Get the location information for this collect.
          country = raw_input("Country [{0}]: ".format(country)) or country
          state = raw_input("State Abbreviation [{0}]: ".format(state)) or state
          city = raw_input("City Code [{0}]: ".format(city)) or city
          location = raw_input("Collect Location ({0}): ".format(
              location)) or location

          venue = "_".join([country, state, city, location])

          title = "Will store data as: {0}_{1}_{2}. OK?".format(
              venue, date_stamp, time_stamp)
          _, ok = pick(["yes", "no"], title)
          if ok == 0:
            break

      devices_and_folders.append((device, dataset_path, venue, date_stamp,
                                  time_stamp))

  pulled_datasets = []

  # Download all datasets from all devices.
  for device, dataset_path, venue, date_stamp, time_stamp in devices_and_folders:
    print "From device {0} pulling dataset {1}".format(device, dataset_path)
    dataset_dir = adb_pull_dataset(root_dir, venue, device,
                                   application_data_space, dataset_path,
                                   date_stamp, time_stamp)

    pulled_datasets.append({"device": device,
                            "dataset": dataset_path,
                            "venue": venue,
                            "date_stamp": date_stamp,
                            "time_stamp": time_stamp,
                            "dataset_dir": dataset_dir,
                            "dataset_type": dataset_type,
                            "upload_ok": False})

  return pulled_datasets


def folder_is_in_raw_format(directory):
  try:
    get_date_and_time_from_dataset_folder(directory[:15])
    return True
  except:
    return False


def collect_downloaded_dataset_info(data_directory, root_dir, venue,
                                    dataset_type, dataset_origin,
                                    destination_sub_directory):
  existing_datasets = []
  for _, dirs, _ in os.walk(data_directory):
    for dataset_dir in dirs:
      if dataset_dir in ["bag", "sensors"]:
        continue
      if (not os.path.exists(os.path.join(data_directory, dataset_dir, "bag"))
          and not os.path.exists(os.path.join(data_directory, dataset_dir,
                                              "sensors"))):
        continue

      try:
        date_stamp = None
        time_stamp = None
        if folder_is_in_raw_format(dataset_dir):
          date_stamp, time_stamp = get_date_and_time_from_dataset_folder(
              dataset_dir[:15])
        else:
          destination_dir = dataset_dir

          dataset_name_components = dataset_dir.split("_")

          detected_venue = venue
          if detected_venue is None:
            detected_venue = "_".join(dataset_name_components[:-2])
            print "Extracted venue %s from %s " % (detected_venue, dataset_dir)

          date_stamp = dataset_name_components[-2]
          time_stamp = dataset_name_components[-1]

        existing_datasets.append({"device": None,
                                  "dataset": None,
                                  "venue": detected_venue,
                                  "date_stamp": date_stamp,
                                  "time_stamp": time_stamp,
                                  "dataset_dir": os.path.join(data_directory,
                                                              dataset_dir),
                                  "dataset_type": dataset_type})
      except:
        print "Error processing %s" % dataset_dir
        raise

  return existing_datasets


def main():
  parser = argparse.ArgumentParser(description="Pull datasets from device or " \
                                   "directory, compress them and upload to a "\
                                   "cloud bucket.")
  parser.add_argument("-c",
                      action="store_true",
                      default=False,
                      dest="compress",
                      help='Don\'t compress into a tarball.')
  parser.add_argument("-u",
                      action="store_true",
                      default=False,
                      dest="upload",
                      help='Don\'t upload datasets.')
  parser.add_argument("--data_directory", required=False,
                      help="The data directory that the datasets are " \
                      "stored in; if previously downloaded from device.")
  parser.add_argument("--destination_sub_directory",
                      required=False,
                      help="The sub directory in the bucket to store to.")

  args = parser.parse_args()

  # Set defaults.
  country = "US"
  state = "CA"
  city = "MTV"
  location = "GoogleSB65"

  # The temporary directory where we drop the data.
  root_dir = os.path.expanduser("~") + "/Desktop/datasets/"
  ops_annotations_folder = "global_ops_annotations"

  # What was this collect for?
  dataset_type = DatasetType.GroundTruth
  title = "Is the data you are uploading for ground-truth or operations? "
  options = ["Operations (Maps Creator)", "Ground-truth (Tango Mapper)"]
  _, selection_index = pick(options, title)
  if selection_index == 0:
    dataset_type = DatasetType.Operations
  else:
    dataset_type = DatasetType.GroundTruth

  # Where did this collect take place?
  dataset_origin = DatasetOrigin.SingleBuilding
  venue = None
  if args.data_directory is None:
    title = "Are all datasets from the same location (building)? "
    options = ["All from same building", "From different buildings"]
    _, selection_index = pick(options, title)
    if selection_index == 0:
      dataset_origin = DatasetOrigin.SingleBuilding
    else:
      dataset_origin = DatasetOrigin.MultipleBuildings

    if dataset_origin == DatasetOrigin.SingleBuilding:
      while True:
        print "Please provide information about the location of this collect."

        # Get the location information for this collect.
        country = raw_input("Country [{0}]: ".format(country)) or country
        state = raw_input("State Abbreviation [{0}]: ".format(state)) or state
        city = raw_input("City Code [{0}]: ".format(city)) or city
        location = raw_input("Collect Location ({0}): ".format(
            location)) or location

        venue = "_".join([country, state, city, location])

        title = "Will store data with location: {0}. OK?".format(venue)
        _, ok = pick(["yes", "no"], title)
        if ok == 0:
          break

    venue = "_".join([country, state, city, location])

  pulled_datasets = []
  # If the user has provided a directory to upload, traverse the directory.
  if args.data_directory is None:
    pulled_datasets = handle_device_download(
        root_dir, venue, ops_annotations_folder, dataset_type, dataset_origin,
        args.destination_sub_directory)
  else:
    pulled_datasets = collect_downloaded_dataset_info(
        args.data_directory, root_dir, venue, dataset_type, dataset_origin,
        args.destination_sub_directory)

  if not pulled_datasets:
    exit(-1)

  uploaded_datasets = []
  # Now upload all datasets to the bucket.
  if dataset_type == DatasetType.Operations:
    uploaded_datasets = handle_ops_upload_to_bucket(
        root_dir, ops_annotations_folder, pulled_datasets)
  else:
    assert dataset_type == DatasetType.GroundTruth
    uploaded_datasets = handle_gt_upload_to_bucket(
        pulled_datasets, args.destination_sub_directory)

  cleanup_temp_folder(uploaded_datasets, root_dir)
  cleanup_devices(uploaded_datasets, dataset_type)


if __name__ == "__main__":
  main()