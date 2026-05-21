# This is used in python for memory optimization
# stall is having reference of whole function in memory
# yield pauses the function function & resumes the function call from that call where he left 

def serve_chai():
    yield "Cup 1"
    yield "Cup 2"
    yield "Cup 3"
    
stall = serve_chai()

for cup in stall:
    print(cup)
    
# In this case the result will be diff
def serve_chai():
    yield "Cup 1"
    yield "Cup 2"
    yield "Cup 3"
    
chai = serve_chai()
print(chai) # itll print ref of memory 
print(next(chai)) # it'll print value and pause state in memory 
print(next(chai)) # resumes where it paused


    