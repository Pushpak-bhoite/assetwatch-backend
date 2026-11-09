# # Longest substring with at most k distinct character

def longest_substring(s):
    left = 0 
    right = 0
    seen = set()
    lStr = ""
    maxLen = 0
    storeStr = ""
    while right < len(s) :
        seen.add(s[right])
        print("seen->", seen)
        
        if len(seen) < 4 :
            lStr += s[right]
            right += 1
            
        else:
            lStr = lStr[1:]
            left += 1
            seen = set(lStr)
            
        if len(lStr) > maxLen :
            maxLen = len(lStr)
            storeStr = lStr
            
            
    print(storeStr)        
    return storeStr
    
    
s = "ffghaaabbccd"
print(set(s))
longest_substring(s)

# print("==============with brute force==================")
def longest_substring_brute(s):
    lStr = ""
    maxLen = 0
    for i in range(len(s)):
        windowStr = ""
        seen =set()
        for j in range(i, len(s)):
            seen.add(s[j])
            if len(seen) < 4:
                windowStr += s[j]
            else:
                seen = set(windowStr)
            
            if len(windowStr) > maxLen    :
                lStr = windowStr
                maxLen = len(windowStr)
    return lStr
            
print(longest_substring_brute(s))