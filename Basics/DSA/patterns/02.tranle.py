def triangle(k):
    for i in range(int(k/2)):
        x = int(k/2)
        for j in range(int(k)):
            if j <= x + i and j >= x -i:
                print("*", end="")
            else :
                print("-", end="")
            
        print() 

triangle(9)

print(int(8/2))