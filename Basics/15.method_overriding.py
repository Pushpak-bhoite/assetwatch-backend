# A. Overriding - means using the same method name in a parent and child class; 
# B. overloading - means using the same method name with different parameters.
# But Python doesn't support traditional method overloading by defining muliple methods


# =========== Overriding ============
class Parent:
    def show(self):
        print("Parent")

class Child(Parent):
    def show(self):
        print("Child")

obj = Child()
obj.show()


# ============== Overloading ==================
class Calculator: 
    def add(self, a, b): 
        return a + b
    
    def add(self, a, b, c):
        return a + b + c
    
obj  = Calculator()
# obj.add(2,4)  # this throws "TypeError-missing one required positional argument" error becoz  latest function defination replaces the first one, 
# because the class namespace maps a name to a single value ( it's like they store class name & value as key & value  in dictionary). 

# yeah bt we can achieve overloading using *args or **kwargs

class Calculator1:
    def add(self, a,b): 
        return a + b
     
    def add(self, *args):
        return sum(args)
    
    def add(self, **kwargs):
        return sum(kwargs.values())
    
obj1 =  Calculator1()
# print(obj1.add(1, 2, 3, 4))
print(obj1.add(a = 2, b = 5))




class Calculator2:
    def add(self, *args, **kwargs):
        if args:
            return sum(args)
        return sum(kwargs.values())

obj1 = Calculator2()

print(obj1.add(1, 2, 3, 4))  # 10
print(obj1.add(a=2, b=5))    # 7