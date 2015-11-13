#!/usr/bin/python

class Node:
  data = None
  nextNode = None

head = Node()

current = head

for x in range(10):
  n = Node()
  n.data = x
  current.nextNode = n
  current = n

current = head

for x in range(10):
  print current.nextNode.data,
  current = current.nextNode
