#!/usr/bin/python

class Node(object):
  data = None
  next_node = None

class LinkedList(Node):
  head = None
  longness = 0

  def prepend(self, new):
    new_node = Node()
    new_node.data = new
    new_node.next_node = self.head
    self.head = new_node
    self.longness += 1

  def get(self, index):
    i = 0
    current = self.head
    while i < index:
      i += 1
      current = current.next_node
    return current.data

  def length(self):
    return self.longness

  def insert(self, index, value):
    if index < 0:
      raise IndexError
    if index > self.length():
      raise IndexError
    i = 0
    current = self.head
    new_node = Node()
    new_node.data = value
    if index == 0:
      new_node.next_node = self.head
      self.head = new_node
    else:
      while i < index - 1:
        i += 1
        current = current.next_node
      new_node.next_node = current.next_node
      current.next_node = new_node
      self.longness += 1

#lst = LinkedList()

#lst.prepend("string")
#lst.prepend("string2")
#lst.prepend("string3")
#lst.insert(2, "string other than the other")
#for i in range(lst.length()):
#  print lst.get(i)



def test_linked_list():
  new_list = LinkedList()
  if new_list.length() == 0:
    print "Success"
  else:
    print "Failure"

  new_list.prepend("Something we haven't seen before.")
  if new_list.get(0) == "Something we haven't seen before.":
    print "Success"
  else:
    print "You suck dude..."

  new_list.insert(1, "Not a very long list.")
  if new_list.get(1) == "Not a very long list.":
    print "Success"
  else:
    print "This one didn't succeed.."

  for i in range(10):
    new_list.insert(i, "String" + str(i))
  if new_list.length() == 12:
    print "Success"
  else:
    print "Faaaiiiilllllllll!"
    print "new_list.length() == ", new_list.length()


  exception = False
  try:
    new_list.insert(-1, "New")
  except IndexError:
    exception = True
    print "IndexError Succeeded."
  else:
    print "Exception should have been raised here, and was not."
  if exception == False:
    print "Exception not raised."

  if new_list.length() == 13:
    print "List length is: ", new_list.length()
  else:
    "Sum-ting wong"

  for i in range(new_list.length()):
    print new_list.get(i)

  new_list.insert(0, "Another string")
  for i in range(new_list.length()):
    print new_list.get(i)

  another_list = LinkedList()
  try:
    another_list.insert(1, "First string")
  except IndexError:
    print "IndexError success...."
  else:
    print "Excpetion should have been raised here... wtg."
  for i in range(another_list.length()):
    print another_list.get(i)


test_linked_list()
