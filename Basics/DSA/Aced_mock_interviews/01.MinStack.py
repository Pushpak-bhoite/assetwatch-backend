# https://leetcode.com/problems/min-stack/description/

# Design a stack that supports push, pop, top, and retrieving the minimum element in constant time.

# Implement the MinStack class:

# MinStack() initializes the stack object.
# void push(int value) pushes the element value onto the stack.
# void pop() removes the element on the top of the stack.
# int top() gets the top element of the stack.
# int getMin() retrieves the minimum element in the stack.
# You must implement a solution with O(1) time complexity for each function.



class MinStack:
  def __init__(self):
    self.stack = []
    self.minStack = []
  
  def push(self, value: int) -> None:
    self.stack.append(value)
    if not self.minStack:
        self.minStack.insert(0, value)
    else:
        self.minStack.append(min(value, self.minStack[-1]))


  def pop(self):
    self.stack.pop()
    self.minStack.pop()
    
    return self.stack

  def top(self) -> int:
    return self.stack[-1]

  def getMini(self) -> int:
    return self.minStack[-1]

  def showStack(self):
    print(self.stack)

obj = MinStack()
obj.push(10)
obj.push(5)
obj.push(20)
obj.push(30)
# print("getmini->", obj.getMini())
# print("top->", obj.top())
print("pop->", obj.pop())
obj.showStack()




