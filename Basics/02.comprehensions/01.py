# [expression for item in iterable if condition]

# expression → what you want to output
# item → each element
# iterable → list, range, etc.
# condition (optional) → filter


numbers = [1,2,3,4,5]
squares = []
squares2 = []

#1. normal method 
for n in numbers:
    squares2.append(n * n )

#2 comprehension with list 
squares = [n * n for n in numbers]

#3. comprehension with condition ( a very first "x" (expression) is where all calculated data gets returned )
squares3 = [x for x in range(10) if x % 2 == 0]
print(f"squares -> {squares}")
print(f"squares2 -> {squares2}")

