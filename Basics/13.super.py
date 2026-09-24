# Yes. 👍 In normal Python OOP, you'll mostly use super() to call/access parent-class methods,
# not attributes/vars

# class ParentClass: 
#     def parent_method(self): 
#         print(f" Hello"f" Im in parent class")
    
# class ChildClass(ParentClass): 
#     def child_method(self):
#         print(f" Hello "f" Im in child class ") 
#         super().parent_method()     
    
    
# objChild = ChildClass()
# objParent = ParentClass()

# objChild.child_method()
# objChild.parent_method()

print("================ access vars ========================")

class ParentClass:
    id = 13 # class attribute - value can be accessed in any child class directly with super()
    # name = "smith" # class attribute  
    
    def __init__(self, id, name):
        self.id = 12  # instance attribute - They belong to a specific object.
        self.name = "Neo Doe" # instance attribute 
        print(ParentClass.id)
    
class ChildClass(ParentClass):
    def __init__(self, id, name, age):
        self.age = None
        super().__init__(id, name)
    def show_details(self, age):
        self.age = age
        print(f"user's id = {self.id}, name ={self.name}, age = {self.age}")
        print(ParentClass.id)  #it belongs to class level attr so we can access it with super()
        
childObj = ChildClass(11, "pushpak", 25)
print(childObj.show_details(25))
        
    

