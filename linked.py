#!/usr/bin/python

class Node:
  data = None
  nextNode = None

n = Node()

n.data = 7
n.nextNode = None

x = Node()

x.data = 6
x.nextNode = n

p = Node()

p.data = 5
p.nextNode = x

print p.data, p.nextNode.data, p.nextNode.nextNode.data
