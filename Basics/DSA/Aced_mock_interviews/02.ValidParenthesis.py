# https://leetcode.com/problems/valid-parentheses/

# 20. Valid Parentheses
# Easy
# Topics
# premium lock icon
# Companies
# Hint
# Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.

# An input string is valid if:

# Open brackets must be closed by the same type of brackets.
# Open brackets must be closed in the correct order.
# Every close bracket has a corresponding open bracket of the same type.

# Example 1:

# Input: s = "()"

# Output: true

# Example 2:

# Input: s = "()[]{}"

# Output: true

# Example 3:

# Input: s = "(]"

# Output: false

# Example 4:

# Input: s = "([])"

# Output: true


class Solution:
    def isValid(self, myStr: str) -> bool:
        mapEval = {
            ")": "(", 
            "]": "[", 
            "}": "{"
        }
        stack = []
        for s in myStr:
            if s in "({[":
                stack.append(s)
            else:
                print("mapEval[i]->", mapEval[s])
                print("mapEval[i]->",mapEval[s] == stack[-1])
                print(stack)
                if mapEval[s] == stack[-1]:
                    stack.pop()
                else :
                    return False
                
        
        return True

# obj = Solution()
# print(obj.isValid("()"))
        