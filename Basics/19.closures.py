# Closures - is a function object that has access to variables in it's lexical scope, even that scope is no linger available. 
# In simple lang = when an inner function remembers the var from it's outer function, even after the outer function has finished it's execution. 

# =============== simple ex ====================

def outer_func():
    x=10
    def inner_func():
        print(x)
    
    return inner_func

inner = outer_func()
inner() # 10 

# =============== Tech with tim (Hard to understand ) ==============
def add(value) : 
    def inner_func(base):
        return base + value  
    
    return inner_func

basic = add(8) # here i'll be returned inner func 
print("basic->", basic.__name__) # see here "value" is already passed here & returned new func, & when we call that returned function "value" still available 
added_num = basic(5)
print("added_num->", added_num)






    