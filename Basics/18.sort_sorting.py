        
# sort = sorts list in place
# sorted = creates new list, can iterate over any iterable 

# 2. sort() vs sorted()
# +-------------------+---------------------------+--------------------------------+
# | Feature           | list.sort()               | sorted()                       |
# +-------------------+---------------------------+--------------------------------+
# | Type              | List method               | Built-in function              |
# | Returns           | None                      | New sorted list                |
# | Works with        | Lists only                | Any iterable                   |
# | Common args       | key=, reverse=            | key=, reverse=                 |
# +-------------------+---------------------------+--------------------------------+

g = list[1,2,3,4]
print(g)
a = list("cdeab")
a.sort()
print(a)


b= tuple(["b","c","d","a"]) #tuple("abcd") this can also work
c = set("hello")


print(sorted(b))
print(sorted(c, reverse=True))

# b.sort() # it wont work