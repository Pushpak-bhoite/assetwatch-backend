# Video L8 = couldn't solve this at all. 
def longest_repeating_character(s, k):
    max = 0
    for i in range(len(s)):
        map_char = dict()   
        for j in range(i,len(s)):
            if s[j] in map_char:
                map_char[s[j]] = map_char[s[j]] + 1
            else:
                map_char[s[j]] = 1
        
            keys = list(map_char.keys())
            
            if len(keys) == 1 :
                total = map_char[keys[0]]
                if total > max:
                    max = total
                    
            if len(keys) == 2 :  
                if map_char[keys[0]] <= k or map_char[keys[1]] <= k :
                    second = map_char[keys[1]] if len(keys) > 1 else 0
                    total = map_char[keys[0]] + second
                    if total > max:
                        max = total
                else :
                    break    
        print(map_char)    
    print("max->", max )            

    # print(map_char)
s ="BAABAABBBAAA"
print(longest_repeating_character(s, 2))