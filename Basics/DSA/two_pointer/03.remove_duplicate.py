# https://leetcode.com/problems/remove-duplicates-from-sorted-array/submissions/2113773814/
k = [1,2,3,4,5,5,5,5,9,0,0,5]

# def remove_dup(nums):
#     for i in range(len(nums)): # this range keeps shrinking as we remove elements from list 
#         j = i + 1 
#         print(range(len(nums))) 
#         while j < len(nums): 
#             if k[i] == k[j] : 
#                 del nums[j] #del index and pop()  works same 
#             else : 
#                 j += 1 
            
#     return nums

# print(remove_dup(k))
# print(k) #modifies original list


# def remove_duplicate_on_sorted(nums):
#     i = 0 
#     j = 1
#     print(len(nums)-1)
#     # len will keep updating as we remove elements
#     while j < len(nums): # 2 < 2 = False , so j will help stop at end, 
#         print("---------")
#         if nums[i] == nums[j]:
#             nums.pop(j)
#         else:
#             i = j
#             j +=1
#     return nums
# # k2 = [1,2,2,2,3,3,4,4,4,5,5]
# k2 = [1,2,2,2,2]
# print(remove_duplicate_on_sorted(k2))

print("=======================================")

def with_set(nums):
    seen = {nums[1]} # set([nums[1]]) #{nums[1]}  # Set does not keep order of elements 
    i =0
    j =1
    print(seen)
    while j < len(nums):
        print("i->",i)
        if nums[i] in seen:
            nums.pop(j)
        else :
            seen.add(nums[i])
            i = j
            j +=1
    return nums
k3 = k4= [1,1,2,2,2,2,3,4,5,6]

print("with_set =======>",with_set(k3))


print("========= stand way========  It's not complete yet")
# count method, we are moving all unique element to front side(left)
# as it's already sorted we just check if 2 consecutive elements are diff. 
k = [1,2,3,4,5,5,5,5,6,6,7,8]
def shift_no(k): 
  i = 0 
  j = 0
  for i in range(len(k)):
    if k[i] == 0 or k[i] != k[i-1]:
      k[j] = k[i]
      j += 1
  return k[:j]
print(shift_no(k))
print(k)