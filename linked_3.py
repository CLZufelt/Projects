#!/usr/bin/python

class Node:
  data = None
  nextNode = None

class LinkedList:
  head = None

  def __init__(self, data):
    newNode = Node()
    newNode.data = data
    self.head = newNode
  
  def setat(self, index, data):
    

  def insert(self, index, data):
    newNode = Node()
    newNode.data = data
    newNode.nextNode = index + 1
    node1 = self.head
    for range(index):
      node1

  def get(self, index):
    
    return some_data

  def delete(self, index):
    pass

def testLinkedList():
  lst = LinkedList("This is a website")

  lst.insert(0, "a")

  if lst.get(0) != "a":
    print "Failed to set index 0"
    quit()

  lst.insert(1, "b")

  lst.setat(0, "c")

  lst.delete(0)
  lst.delete(1)

testLinkedList()
