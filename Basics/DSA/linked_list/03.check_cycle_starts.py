# https://leetcode.com/problems/linked-list-cycle-ii/description/
# check cycle starting point
class ListNode:
    def __init__(self, val):
        self.val = val
        self.next = None
    
ln1 = ListNode(1) 
ln2 = ListNode(2) 
ln3 = ListNode(3) 
ln4 = ListNode(4) 
ln1.next = ln2
ln2.next = ln3
ln3.next = ln2
class Solution:
    def check_cycle_starting_point(self, head: ListNode):
        fast = head
        slow = head
        
        while fast != None and fast.next != None:
            slow = slow.next
            fast = fast.next.next
            if fast == slow:
                slow = head
                while slow != fast:      #now the point where they will meet is the begining
                   slow = slow.next
                   fast = fast.next
                   
                return slow.val

sol = Solution()
print(sol.check_cycle_starting_point(ln1))
            
        