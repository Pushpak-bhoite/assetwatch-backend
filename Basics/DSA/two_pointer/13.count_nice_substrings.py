# u can solve this question with normal cnt. i intentionally used dict for practice
def numberOfOddSubarrays(nums, k): # nice substring means counting number of odd numbers == k 
    cnt = 0
    for i in range(len(nums)):
        map_odd ={}
        for j in range(i, len(nums)):
            if nums[j] % 2 != 0:
                if nums[j] in map_odd:
                    map_odd[nums[j]] = map_odd[nums[j]]  + 1
                else:
                    map_odd[nums[j]] = 1
            # print(map_odd)
            sum = 0 
            for y  in map_odd.values():
                sum =    sum + y
            if sum == k :
                print(nums[i:j+1])
                cnt += 1
    return cnt

# nums = [4, 8, 2] 
# k = 1 
nums = [1, 1, 2, 1, 1]
k = 3 
print(numberOfOddSubarrays( nums, k))
        