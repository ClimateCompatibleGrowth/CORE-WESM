#%%
import pandas as pd
from utils import check_duplicates, apply_technology_specific_trend
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import sys
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout)

#%%
# Define the output path ##
output_path = '../Counties_model_test/'

# Read county data
counties_file = 'list_counties_test.csv'

column_counties_id = 'COUNTY Id'
counties = pd.read_csv(counties_file,
                       dtype={column_counties_id: str}, keep_default_na=False,
                        na_values=[])

#list_counties = counties['COUNTY Id'].tolist()
# everything is a string
list_counties = [str(cid).strip() for cid in counties[column_counties_id].tolist()]



#%%
# Check for duplicates
duplicates = check_duplicates(list_counties)
if duplicates:
    raise ValueError('There will be errors because of the following duplicates: ', duplicates)


# Columns to update (2019 to 2050)
columns_to_update = list(range(2019, 2051))

def lower_limits(county_id):
    try:
        # Define the file path
        file_path = f"{output_path}{county_id}/Residential.xlsx"

        # Read the Excel file demand
        df = pd.read_excel(file_path, sheet_name='TotalTechnologyAnnualActivityLo')

        # Filter original data frame
        #df_filtered = df.copy()
        #df_original = df.copy()
        df_original = df[~((df['TECHNOLOGY'].str.contains('RK')) &
                                            (df['TECHNOLOGY'].str.contains('LPG|CHC005|ELC001|ETH')))]
        df_filtered = df[(df['TECHNOLOGY'].str.contains('RK')) &
                                            (df['TECHNOLOGY'].str.contains('LPG|CHC005|ELC001|ETH'))].copy()
        
        # Numerical columns are float to avoid dtype assignment issues
        df_filtered[columns_to_update] = df_filtered[columns_to_update].astype(float)

        base_year = 2019
        tech_increase_map = {
            'RK1LPG001': 0.025,  # 2.5% increase for RK1LPG001
            'RK2LPG001': 0.015,   # 1.5% increase for RK2LPG001
            'RK1CHC005': 0.015,   # 1.5% increase for RK1CHC005
            'RK2CHC005': 0.015,   # 1.5% increase for RK2CHC005
            'RK1ELC001': 0.015,   # 1.5% increase for RK1ELC001
            'RK2ELC001': 0.01,   # 1.% increase for RK2ELC001
            'RK1ETH001': 0.02,   # 2% increase for RK1ETH001
            'RK2ETH001': 0.01,   # 1.% increase for RK2ETH001
        }

        df_filtered = apply_technology_specific_trend(df_filtered, columns_to_update, base_year, tech_increase_map)
        df_updated = pd.concat([df_original, df_filtered], ignore_index=True)

        # Save the updated DataFrame back to the Excel file
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_updated.to_excel(writer, sheet_name='TotalTechnologyAnnualActivityLo', index=False)

        logging.info(f"Update lower limits: {county_id}")

    except Exception as e:
        logging.error(f"Error processing county {county_id}: {e}")
        
# Use ProcessPoolExecutor to parallelize the process_county_with_technology function
with ThreadPoolExecutor() as executor:
    executor.map(lower_limits, list_counties)


# # update increase decrease limits for all counties
# def process_county_increase(county_id):
#     try:           
#         # Define the file path
#         file_path = f"{output_path}{county_id}/Residential.xlsx"

#         # Read the Excel file demand
#         df = pd.read_excel(file_path, sheet_name='TechnologyActivityIncreaseByMod')

#                 # Replace all values in rows 
#         df.loc[
#             df['TECHNOLOGY'].str.contains('RK', case=False, na=False) &
#             df['TECHNOLOGY'].str.contains('BGS', case=False, na=False) &
#             (df['MODE_OF_OPERATION'] == 1), columns_to_update] = 0.020
#         # Replace all values in rows 
#         df.loc[
#             df['TECHNOLOGY'].str.contains('RK', case=False, na=False) &
#             df['TECHNOLOGY'].str.contains('BIO005', case=False, na=False) &
#             (df['MODE_OF_OPERATION'] == 1), columns_to_update] = 0.030
#         # Replace all values in rows 
#         df.loc[
#             df['TECHNOLOGY'].str.contains('RK', case=False, na=False) &
#             df['TECHNOLOGY'].str.contains('BIO001|CHC001', case=False, na=False) &
#             (df['MODE_OF_OPERATION'] == 1), columns_to_update] = 0.001
       
        
#         # Save the updated DataFrame back to the Excel file
#         with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
#             df.to_excel(writer, sheet_name='TechnologyActivityIncreaseByMod', index=False)

#         logging.info(f"Increase by mode: {county_id}")

#     except Exception as e:
#         logging.error(f"Error processing county {county_id}: {e}")

# # Use ProcessPoolExecutor to parallelize the process_county_with_technology function
# with ThreadPoolExecutor() as executor:
#     executor.map(process_county_increase, list_counties)



# # update increase decrease limits for all counties
# def process_county_decrease(county_id):
#     try:           
#         # Define the file path
#         file_path = f"{output_path}{county_id}/Residential.xlsx"

#         # Read the Excel file demand
#         df = pd.read_excel(file_path, sheet_name='TechnologyActivityDecreaseByMod')
        
#         # Replace all values in rows 
#         df.loc[
#             df['TECHNOLOGY'].str.contains('RK', case=False, na=False) &
#             df['TECHNOLOGY'].str.contains('BGS|BIO005', case=False, na=False) &
#             (df['MODE_OF_OPERATION'] == 1), columns_to_update] = 0.0001
        
        
#         # Save the updated DataFrame back to the Excel file
#         with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
#             df.to_excel(writer, sheet_name='TechnologyActivityDecreaseByMod', index=False)

#         logging.info(f"Decrease by mode: {county_id}")

#     except Exception as e:
#         logging.error(f"Error processing county {county_id}: {e}")

# # Use ProcessPoolExecutor to parallelize the process_county_with_technology function
# with ThreadPoolExecutor() as executor:
#     executor.map(process_county_decrease, list_counties)





