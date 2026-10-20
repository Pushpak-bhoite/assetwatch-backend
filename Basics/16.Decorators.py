# Decorators act as a wrapper for ur original function 
# Common use cases - Timing, Logging


import time 

def time_interval(func): 
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took time taken: {end - start:.6f}") #this .2f only works with f string OR do round(end-start, 2)
    #__name__ is built attribute, It's part of data models. 
    return wrapper  #dont use wrapper()  otherwise decorators will execute before running file, or when we import it. 
                    # return wrapper() executes it immediately when the decorator is applied


@time_interval
def calc_square(numbers): 
    result = []
    for i in numbers:
        result.append( i * i )
        
    return result

@time_interval
def calc_cube(numbers): 
    
    result = []
    for i in numbers: 
        result.append( i * i * 1)
        
    return result

numbers = list(range(1,1000))

calc_square(numbers)
calc_cube(numbers)


class Calculator:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"Value: {self.value}"

obj = Calculator(10)
print(obj)


