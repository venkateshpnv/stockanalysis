# importing pandas as pd 
import pandas as pd 

# Creating the Index 
df=pd.Index([17.3, 69.221, 33.1, 15.5, 19.3, 74.8, 10, 5.5]) 

print("Dtype before applying function: \n", df) 

print("\nAfter applying astype function:") 
# Convert df datatype to 'int64' 
df = df.astype('int64') 
print("Dtype before applying function: \n", df) 

