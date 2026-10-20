# 3. Leader in arrays leetcode question

arr = [16, 17, 4, 3, 5, 2]
leaderList = []
for i in range(len(arr)):
    leader = arr[i]
    flag = True
    for j in range(i, len(arr)):
        if arr[j] > leader : 
            flag = False
            break
    if flag:
        leaderList.append(arr[i])
        

print(leaderList)