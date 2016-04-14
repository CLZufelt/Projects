import os
import sys
import subprocess


print "subprocess.call\t", subprocess.call("adb remount root", shell=True)
print "subprocess.check_call\t", subprocess.check_call("adb remount root", shell=True)
print "subprocess.check_output\t", subprocess.check_output("adb remount root", shell=True)

print "os.system\t", os.system("adb remount root")
ospopen = os.popen("adb remount root").read().split("\n")
print "os.popen\t", ospopen[0]
print "Newline?"
