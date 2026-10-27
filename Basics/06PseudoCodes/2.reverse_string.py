
s = " Mourhenio"
def func(s):
    rev = ""
    for i in s: 
        rev = i + rev
        
    print(rev)
    
func(s)

# ========= Optimized way ===========

s = s[::-1]
print(s)