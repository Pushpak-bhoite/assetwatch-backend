# max water in container
# https://leetcode.com/problems/container-with-most-water/description/
from turtle import width
from typing import List

# area formula = w*l (width is vertical here and length horizonatal)
def maxArea( height: List[int]) -> int:
    left = 0
    right = len(height)-1
    width = min(height[left], height[right])
    max = width * (right - left )
    
    for i in range(len(height)):
        for j in range(i+1, len(height)):
            length = j-i 
            width = min(height[i], height[j])
            area = length * width
            if max < area:
                max = area

    return max
             
height= [1,8,6,2,5,4,8,3,7]
print(maxArea(height))
# ===================== Optimized way =================================

height = [1,8,6,2,5,4,8,3,7]
 
def max_area(height): 
  left = 0 
  right = len(height) -1 
  max = (right - left) * min(height[right], height[left])
  
  while left < right : 
    if height[left] > height[right]: 
      right -= 1
    else:
      left += 1 
      
    area = (right - left) * min(height[right], height[left])
    if max < area: 
      max = area

  return max

print(max_area(height))
      
    

