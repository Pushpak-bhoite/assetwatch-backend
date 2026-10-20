def foo(*, a=None, b=None): ## the first * is for making keywords only arguments. 
    print(f"a = {a}, b = {b}")
    
    
foo()


def boo(id, value):
    print("id:", id , "value:", value)
    
boo(id=3, value=44)