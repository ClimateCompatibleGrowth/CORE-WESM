#%%
import os
import shutil
import pandas as pd
from utils import check_duplicates

#%%
county_folder = '../Counties_model/'                #path to the output folder
counties_file = 'list_counties.csv'                 #file with the list of counties


# Define the source folder (two levels up)
source = os.path.abspath(os.path.join("..", "multiscale"))

# Define the destination path
destination = os.path.abspath(os.path.join(county_folder, "multiscale"))

# Copy the entire directory recursively
shutil.copytree(source, destination)

# #%%
# # Read county data
# counties = pd.read_csv(counties_file, keep_default_na=False)
# list_counties = counties['COUNTY Id'].tolist()

# # Check for duplicates
# duplicates = check_duplicates(list_counties)
# if duplicates:
#     raise ValueError('There will be errors because of the following duplicates: ', duplicates)

# #%%
# # Append region 'RE1' to the list of counties
# list_counties.append('RE1')

# # List of sheet names to process
# sheet_names = ['ft_affiliation', 'ft_scale']  # Sheets to modify in the multiscale_params.xlsx file

# # Read the Excel file for the first sheet
# df_ft = pd.read_excel(destination + '/multiscale_params.xlsx', sheet_name=sheet_names[0])

# # Check if the unique values in 'REGION' match the list of counties
# if set(df_ft['REGION'].unique()) == set(list_counties):


# #%%


# # Loop through each sheet name
# for sheet_name in sheet_names:
#     # Read the Excel file for the current sheet
#     df = pd.read_excel(destination + '/multiscale_params.xlsx', sheet_name=sheet_name)
#     df['REGION'] = df['REGION'].astype(str)

#     # Check if the unique values in 'REGION' match the list of counties
#     if set(df['REGION'].unique()) == set(list_counties):
#         # If they are equal, skip filtering and continue to the next sheet
#         continue
    
#     # Filter the DataFrame 
#     df = df[df['REGION'].isin(list_counties)]
    
#     # Write the updated DataFrame back to the Excel file
#     with pd.ExcelWriter(destination + '/multiscale_params.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
#         df.to_excel(writer, sheet_name=sheet_name, index=False)

# # %%
