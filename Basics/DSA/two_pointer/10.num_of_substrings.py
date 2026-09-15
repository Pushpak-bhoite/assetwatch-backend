#Video No-7: Both has big(n^2) time complexity, i haven't solved for big(n) time complexity
# Number of substring containing all the characters a,b,c. 
s = "bbacba"
def number_of_substrings(s):
    left = 0
    right = 0
    seen = set()
    cnt = 0
    while left < len(s):
        seen.add(s[right])
        right +=1 
        
        if 'a' in seen and 'b' in seen and 'c' in seen:
            print(s[left:right])
            cnt += 1
            
        if right == len(s):
            seen.clear()
            left += 1
            right = left 
    return cnt
           
def by_brute_force(s):
    cnt =0
    for i in range(len(s)):
        seen =""
        for j in range(i, len(s)):
            seen = seen + s[j]
            if 'a' in seen and 'b' in seen and 'c' in seen:
                cnt += 1
                print(seen)

    return cnt
print(number_of_substrings(s))
print(by_brute_force(s))