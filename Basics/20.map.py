# map() returns memory efficient lazy iterator. 

y = map(lambda x: x * 2, {3,4,2,1,})
print(list(y)) ## as set is unordered, so sequence could be anything. 

x = map(lambda a,b,c: a + b + c, [1], [4,5,6], [7,8,9])
print(list(x))

