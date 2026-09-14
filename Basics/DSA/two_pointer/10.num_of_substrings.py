# Number of substring containing all the characters a,b,c. 
s = "bbacba"
def number_of_substrings(s):
    left = 0
    right = 0
    window = ""
    seen = set()
    cnt = 0
    while right < len(s):
        if 'a' in seen and 'b' in seen and 'c' in seen :
            left += 1
            window = window[1:]
            cnt = cnt + 1
        else:
            window = window + s[right]
            right += 1
        seen = set(window)
        print("cnt->", cnt)
    if 'a' in seen and 'b' in seen and 'c' in seen :
        cnt += 1
    
    return cnt
           
# def by_brute_force(s):
#     cnt =0
#     for i in range(len(s)):
#         seen =""
#         for j in range(i, len(s)):
#             seen = seen + s[j]
#             if 'a' in seen and 'b' in seen and 'c' in seen:
#                 cnt += 1
#                 print(seen)
#                 break
#     return cnt
print(number_of_substrings(s))
# print(by_brute_force(s))