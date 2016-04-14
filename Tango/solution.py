#!/usr/bin/python

def answer(population, x, y, strength):
  pos_iterate_for_y = 0
  neg_iterate_for_y = 0
  pos_iterate_for_x = 0
  neg_iterate_for_x = 0
  if population[y][x] <= strength:
    population[y][x] = -1

    while y + pos_iterate_for_y < len(population):
      while pos_iterate_for_x < len(population[y]) - 1:
        if population[y + pos_iterate_for_y][x + pos_iterate_for_x] <= strength:
          population[y + pos_iterate_for_y][x + pos_iterate_for_x] = -1
          pos_iterate_for_x += 1
          print "positive x", pos_iterate_for_x
          print "2"
        else:
          print "breaking first x"
          break
      pos_iterate_for_x = 0
      while x - neg_iterate_for_x >= 0:
        if population[y + pos_iterate_for_y][x - neg_iterate_for_x] <= strength:
          population[y + pos_iterate_for_y][x - neg_iterate_for_x] = -1
          neg_iterate_for_x += 1
          print "3"
        else:
          print "breaking second x"
          break
      neg_iterate_for_x = 0
      pos_iterate_for_y += 1

    while y - neg_iterate_for_y >= 0:
      if population[y - neg_iterate_for_y][x] <= strength:
        population[y - neg_iterate_for_y][x] = -1
        neg_iterate_for_y += 1
        print "4"
      else:
        break
      while pos_iterate_for_x < len(population[y]) - 1:
        if population[y - neg_iterate_for_y][x + pos_iterate_for_x] <= strength:
          population[y - neg_iterate_for_y][x + pos_iterate_for_x] = -1
          pos_iterate_for_x += 1
          print "5"
        else:
          break
      pos_iterate_for_x = 0
      while x - neg_iterate_for_x >= 0:
        if population[y - neg_iterate_for_y][x - neg_iterate_for_x] <= strength:
          population[y - neg_iterate_for_y][x - neg_iterate_for_x] = -1
          neg_iterate_for_x += 1
          print "6"
        else:
          break
      neg_iterate_for_x = 0

  for i in population:
    print i
"""
      while pos_iterate_for_x < len(population[y]) - 1:
        print population[y]
        print population[y][x]
        print pos_iterate_for_x
        if population[y][x + pos_iterate_for_x] <= strength:
          population[y][x + pos_iterate_for_x] = -1
          pos_iterate_for_x += 1
        else:
          break
      while x - neg_iterate_for_x >= 0:
        if population[y][x - neg_iterate_for_x] <= strength:
          population[y][x - neg_iterate_for_x] = -1
          neg_iterate_for_x += 1
        else:
          break




      #if x > 0:
        #while traverse_along_x < len(population[traverse_along_y]):
          #traverse_along_y += 1

"""






answer(([[2,1,2,2,2],[3,2,2,2,2],[3,2,2,2,2],[2,2,2,4,2],[2,2,2,2,2],[2,2,2,2,2]]), 2, 10, 2)



