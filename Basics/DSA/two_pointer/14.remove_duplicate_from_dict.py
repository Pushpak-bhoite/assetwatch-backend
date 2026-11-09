# ---------------Remove elements from this where keys having same value ------------

def  remove_duplicate(data): 

  seen = set()
  for i, j in list(data.items()):
    if j in seen:
      del data[i]
      pass
    else :
      seen.add(j)
  print(data)


data = {"akash": 1, "ram": 2, "sham": 3, "messi": 2}

remove_duplicate(data)

# print(list(data.items()))