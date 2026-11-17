# Its from Aced.com
# Find The Duplicates
# Given two sorted arrays arr1 and arr2 of passport numbers, implement a function findDuplicates that returns an array of all passport numbers that are both in arr1 and arr2. Note that the output array should be sorted in an ascending order.

# Let N and M be the lengths of arr1 and arr2, respectively. Solve for two cases and analyze the time & space complexities of your solutions: M ≈ N - the array lengths are approximately the same M ≫ N - arr2 is much bigger than arr1.

# Example:input:  arr1 = [1, 2, 3, 5, 6, 7], arr2 = [3, 6, 7, 8, 20]

# output: [3, 6, 7] # since only these three values are both in arr1 and arr2

from typing import List

def find_duplicates(arr1: List[int], arr2: List[int]) -> List[int]:
    N = len(arr1)
    M = len(arr2)
    result = []
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

            mid = (i + j) // 2
            if target == bigArr[mid]:
                result.append(bigArr[mid])
                break
                
            if  target > bigArr[mid] :
                i = mid + 1
            else :
                j = mid - 1

    
    return result
  
# debug your code below
print(find_duplicates([1, 2, 3, 5, 6, 7], [3, 6, 7, 8, 20]))
