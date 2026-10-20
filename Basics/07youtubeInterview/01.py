# You have 2 hash maps you need to merge only the distinct keys into one hash map.
# (actually HashMap = Dictionary in python, Hash Map is DSA concept & dictionary internally implement this. In Java we have HashMap)

map1 = {
    "a": 10,
    "b": 20,
    "c": 30
}

map2 = {
    "b": 50,
    "d": 40,
    "e": 60
}

map3 = map1.copy()
for key, value in map2.items():
    if key in map3.keys():  ##we dont even need condition as 
        continue
    map3[key] = value
print(map3)

# map3 = map1 + map2  # doesn't work, same with set 

a = {1, 2, 3}
b = {3, 4, 5}

# c= a + b # don't work 
c = a | b
print("Set union =>", c)