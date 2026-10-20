# EX: "with" helps us connect to db, bt in case anything happens then it can rollback or undo the changes 

# -------------------------------

# file = open("books.txt", "w") # Variable Assignment

# with open("books.txt", "w") as file # Contextual Aliasing 


# In this ex file's data won't be written in file until and unless we don't close file with file.close()
# data stay's in buffer  
# Run this same code on notebook, u will have diff output.
#  ============================= Normal ==================================
# file = open("book.txt", "w") 
# file.write("Odyssey \n") 
# file.write("A Lucifer \n")
# # a = 1/0 # this causes err and in that case close never runs(bt with Context Manager "with" automatically handles close & so the text will be written in file ) 
# file.write("God Father \n")
# file.close()

# fileRead = open("book.txt", "r")
# print(fileRead.read())
# fileRead.close()

# # ==============================  WITH  =================================================
# with open("books.txt", "w") as file:
#     file.write("hello\n")
#     file.write("marvelous\n")
    
# =========== 2 operations (read, sort & write) with "with" ================


with open("book.txt", "r") as file:
    with open("catalog.txt", "w") as fileWrite:
        # ---------- 1st - sort -----------
        fr = file.read()
        titles = fr.split("\n")
        # ---------- 2nd - sort -----------
        titles.sort() 
        # ---------- 3rd - sort -----------
        text = "\n".join(titles)
        fileWrite.write(text)
                
