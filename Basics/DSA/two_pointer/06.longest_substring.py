# From takeUforword L3
# Longest substring without repeating characters. 
# *** string are immutable in python and in js as well. ***


def longest_substring_practice(s):
    lStr = ""
    for i in range(len(s)):
        seen = ""
        for j in range(i,len(s)):
            if s[j] in seen: break
            else:
                seen += s[j]
                if len(seen) > len(lStr) :
                    lStr = seen
    return lStr
                  
def longest_substring_optimized(s):
    left = 0
    right = 0 
    seen = ""
    maxLen = ""
    while right < len(s):
        # print(s[right] not in seen)
        if s[right] not in seen:
            seen += s[right]
            right += 1
        else : #in else left will be chasing right unless it doesn't find uniqness in seen
            if len(seen) > len(maxLen):
                maxLen = seen
            
            seen = seen[1:]    
            left += 1 
        print(f"seen->{right} - ", seen)

    return maxLen
    
myStr = "cadbazxcyvf"  
print(longest_substring_optimized(myStr))

# print(longest_substring_practice(myStr))

# print(myStr[1:]) # create new str# strings are immutable 
# seen.replace("a","", 1) # replace 1st occurrence of that char
