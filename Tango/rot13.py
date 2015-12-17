#!/usr/bin/python


lst = []

def encrypt(encrypt):
  for i in encrypt:
    if ord(i) + 13 > 122:
      i = ord(i) - 13
    else:
      i = ord(i) + 13
    lst.append(chr(i))
    #with open("message.txt", 'r+') as f:
    #  f.write(chr(lst))
  print "".join(lst)


encrypt(raw_input("Message here:\n"))
