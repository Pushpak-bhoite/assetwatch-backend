class Solution:
    def numSubarraysWithSum(self, nums, goal):
        #your code goes here
        cnt = 0
        for i in range(len(nums)):
            total = 0 
            for j in range(i, len(nums)):
                total = total + nums[j]
                if total == goal:
                    print(nums[i:j+1])
                    cnt += 1
            
        return cnt


# nums =  [1, 1, 0, 1, 0, 0, 1]
# goal = 3
nums= [0, 0, 0, 0, 1] 
goal = 0
obj = Solution()
print(obj.numSubarraysWithSum(nums, goal))