import sys
import os

tool_path = r" !! change this to your Aurora Tool folder path !!" 
#make sure to use forward slash /

user_setup = os.path.join(os.path.expanduser("~"), 
                          "Documents", "maya", "2026", "scripts", "userSetup.py")

line = '\nsys.path.insert(0, "{}")\n'.format(tool_path.replace("\\", "/"))

with open(user_setup, "a") as f:
    f.write(line)

print("Aurora Tool installed. Restart Maya.")