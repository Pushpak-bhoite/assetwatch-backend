import math
from typing import Optional

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
ln3.next = ln4

def middleNode(head: Optional[ListNode]) -> Optional[ListNode]:
        slow = head
        fast = head
        while fast != None and fast.next != None:
            slow = slow.next
            fast = fast.next.next

        return slow.val
    
print(middleNode(ln1))

print(math.ceil(5/2)) 