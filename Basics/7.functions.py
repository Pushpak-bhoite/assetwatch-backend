# 1. pure func
def pure_func(cups):
    return cups * 10

total_chai = 10

#2. Impure function - not recommended 
def impure_func(cups):
    global total_chai # helps access global variables
    total_chai += cups 

#3. built in function 
def chai_flavor(flavor="masala"):
    """This is doc string """# this is doc string, helps create this function as built in
    return flavor

print(chai_flavor.__name__)
print(chai_flavor.__doc__)