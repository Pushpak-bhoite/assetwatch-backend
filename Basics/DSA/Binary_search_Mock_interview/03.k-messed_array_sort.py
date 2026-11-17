# K-Messed Array Sort
# Given an array of integers arr where each element is at most k places away from its sorted position, code an efficient function sortKMessedArray that sorts arr. For instance, for an input array of size 10 and k = 2, an element belonging to index 6 in the sorted array will be located at either index 4, 5, 6, 7 or 8 in the input array.

# Analyze the time and space complexities of your solution.
# Ex:
# input:  arr = [1, 4, 5, 2, 3, 7, 8, 6, 10, 9], k = 2

# output: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# --> It's very easy solve it. 

from typing import List

def find_duplicates(arr1: List[int], arr2: List[int]) -> List[int]:
    N = len(arr1)
    M = len(arr2)
    new_arr = []
    if N >  M :
        smallArr = arr1
        bigArr = arr2
    else:
        smallArr = arr2 
        bigArr = arr1
      
    for target in smallArr:
        i = 0
        j = len(bigArr) - 1
        while i <= j:
            if target == bigArr[i] or target == bigArr[j]:
                new_arr.append(target)
                break
            
            mid = (i + j) // 2 
            print(i, j, mid)
            if  target > bigArr[mid] :
                i = mid
            else :
                j = mid
            if i == mid and j == mid:
              print("-------------")
              break
              
    return new_arr
  
# debug your code below
print(find_duplicates([1, 2, 3, 5, 6, 7], [3, 6, 7, 8, 20]))
