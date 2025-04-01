#%%
import pandas as pd
from utils import check_duplicates
import numpy as np
from concurrent.futures import ThreadPoolExecutor

#%%
# Read county data
counties_file = 'list_counties.csv'

# Define the output path ##
output_path = '../Counties_model/'

counties = pd.read_csv(counties_file, keep_default_na=False)
list_counties = counties['COUNTY Id'].tolist()
rural_dem = ['DEMRC2', 'DEMRK2', 'DEMRL2', 'DEMRO2']

#%%


#%%
# Check for duplicates
duplicates = check_duplicates(list_counties)
if duplicates:
    raise ValueError('There will be errors because of the following duplicates: ', duplicates)

def process_county_demand(county_id):
    try:
        # Define the file path
        file_path = f"{output_path}{county_id}/Residential.xlsx"
        # Check if the county has no urban areas
        df = counties[counties['COUNTY Id'] == county_id]

        if not df.empty and df['rural'].any() == 0:
            print(f"County {county_id} has no rural areas.")
                       
            # Read the Excel file demand
            res_dem = pd.read_excel(file_path, sheet_name='SpecifiedAnnualDemand')

            # Define the range of columns to update (2019 to 2050)
            columns_to_update = list(range(2019, 2051))

            # Replace all values in rows where 'COMMODITY' is in the rural_dem list
            res_dem.loc[res_dem['COMMODITY'].isin(rural_dem), columns_to_update] = 0
        
        # Save the updated DataFrame back to the Excel file
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            res_dem.to_excel(writer, sheet_name='SpecifiedAnnualDemand', index=False)

        print(f"Processed county: {county_id}")

    except Exception as e:
        print(f"Error processing county {county_id}: {e}")
with ThreadPoolExecutor() as executor:
    executor.map(process_county_demand, list_counties)

# update lower_limits
def process_county_with_technology(county_id):
    try:
        # Define the file path
        file_path = f"{output_path}{county_id}/Residential.xlsx"

        # Read the Excel file demand
        res_dem = pd.read_excel(file_path, sheet_name='TotalTechnologyAnnualActivityLo')

        # Define the range of columns to update (2019 to 2050)
        columns_to_update = list(range(2019, 2051))

        # Replace all values in rows where 'TECHNOLOGY' contains 'rk2', 'rl2', or 'ro2'
        res_dem.loc[res_dem['TECHNOLOGY'].str.contains('rk2|rl2|ro2|rc2', case=False, na=False), columns_to_update] = 0

        # Save the updated DataFrame back to the Excel file
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            res_dem.to_excel(writer, sheet_name='TotalTechnologyAnnualActivityLo', index=False)

        print(f"Processed county with TECHNOLOGY filter: {county_id}")

    except Exception as e:
        print(f"Error processing county {county_id}: {e}")

# Use ProcessPoolExecutor to parallelize the process_county_with_technology function
with ThreadPoolExecutor() as executor:
    executor.map(process_county_with_technology, list_counties)
    
#%%

# Read fraction derived from DHS surveys
dhs_fraction = pd.read_csv('DHS_stoves_fuel_fraction.csv')

# Define the range of years
years = np.arange(2019, 2051)

# Function to generate the series and round the values to 4 decimal places
def generate_series(initial_value):
    return np.round(np.linspace(initial_value, 0, len(years)), 4)

# Define the process_county function
def process_county(county_id):
    try:
        # Define the file path
        file_path = f"{output_path}{county_id}/Residential.xlsx"

        # Read the Excel file demand
        res_dem = pd.read_excel(file_path, sheet_name='SpecifiedAnnualDemand')

        #Urban ckg demand
        area_dem = ['DEMRK1', 'DEMRK2']
        ckg_urb = res_dem[res_dem['COMMODITY']==area_dem[0]][2019]
        ckg_rur = res_dem[res_dem['COMMODITY']==area_dem[1]][2019]

        #Fraction from DHS
        fraction = dhs_fraction[(dhs_fraction['COUNTY Id']==county_id)][['hv025', 'WESM', 'fraction']]
        fraction['low_lim'] = fraction.apply(
            lambda row: round(row['fraction'] * ckg_urb.values[0] * 0.99, 4) if row['hv025'] == 'urban'
            else round(row['fraction'] * ckg_rur.values[0] * 0.99, 4), axis=1)
        

        ## Dataframe with series, from the DHS fraction ##

        fraction['series'] = fraction['low_lim'].apply(generate_series)
        # Convert the series to a DataFrame for better visualization
        series_df = pd.DataFrame(fraction['series'].tolist(), index=fraction.index, columns=years)

        # Add the 'WESM' column to the series DataFrame
        series_df['TECHNOLOGY'] = fraction['WESM']

        ## UPDATED IN THE COOKING SECTOR ##

        # Define the range of years you want to select
        start_year = 2030 # Kerosene is phased out by 2030
        end_year = 2050

        # Get the column indices for the specified range of years
        start_index = series_df.columns.get_loc(start_year)
        end_index = series_df.columns.get_loc(end_year) + 1  # +1 to include the end year

        # Select the columns from series_df based on the indices
        filtered_series_df = series_df.iloc[:, start_index:end_index]

        # Replace all values in rows where 'TECHNOLOGY' contains 'KER'
        series_df.loc[series_df['TECHNOLOGY'].str.contains('KER'), filtered_series_df.columns] = 0

        # Add the additional columns to the series DataFrame
        series_df['MODEL'] = '#ALL'
        series_df['SCENARIO'] = '#ALL'
        series_df['PARAMETER'] = 'TotalTechnologyAnnualActivityLo'
        series_df['REGION'] = county_id

        ## Read the Excel file ## Lower Limits ##
        low_lim = pd.read_excel(file_path, sheet_name='TotalTechnologyAnnualActivityLo')
        # Change values to zeros for all technologies that have 'RK' in the name
        low_lim.loc[low_lim['TECHNOLOGY'].str.contains('RK'), years] = 0
        # Remove all technologies that have 'RK' in the name
        low_lim = low_lim[~low_lim['TECHNOLOGY'].isin(fraction['WESM'])]
        
        # Combine the DataFrames from the DHS fractions and the low limits
        df_combined = pd.concat([low_lim, series_df], ignore_index=True)
             
        # Write the updated DataFrame back to the Excel file
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_combined.to_excel(writer, sheet_name='TotalTechnologyAnnualActivityLo', index=False)


        ## Read the Excel file ## Upper Limits ##
        up_lim = pd.read_excel(file_path, sheet_name='TotalTechnologyAnnualActivityUp')
        up_lim_filtered = up_lim.copy()
        up_lim_filtered = up_lim_filtered[up_lim_filtered['TECHNOLOGY'].str.contains('RK')]
        up_lim_filtered = up_lim_filtered[up_lim_filtered['TECHNOLOGY'].isin(fraction['WESM'])]

        # Merge the two DataFrames on the 'TECHNOLOGY' column
        df_merged = pd.merge(
            up_lim_filtered[['TECHNOLOGY', 2019]],
            series_df[['TECHNOLOGY', 2019]],
            on='TECHNOLOGY',
            suffixes=('_up_lim', '_series'))
        # Subtract the values in the '2019' column
        df_merged['difference_2019'] = df_merged['2019_up_lim'] - df_merged['2019_series']

        # # Add a column to indicate if the difference is negative
        df_merged = df_merged[df_merged['difference_2019'] < 0]
        df_merged['fraction'] = 1.05 * df_merged['2019_series'] / df_merged['2019_up_lim']
        
        # Create a dictionary with 'TECHNOLOGY' as keys and 'fraction' as values
        technology_fraction_dict = df_merged.set_index('TECHNOLOGY')['fraction'].to_dict()

        # Define the range of columns to update
        columns_to_update = list(range(2019, 2051))

        # Update the values in 'up_lim' for the technologies in the dictionary
        for technology, fraction in technology_fraction_dict.items():
            up_lim.loc[up_lim['TECHNOLOGY'] == technology, columns_to_update] *= fraction

        # Round the updated values to 4 decimal places
        up_lim[columns_to_update] = up_lim[columns_to_update].round(4)

        # Read the existing Excel file
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            # Write the combined DataFrame to the specified sheet
            up_lim.to_excel(writer, sheet_name='TotalTechnologyAnnualActivityUp', index=False)
        
        print(f"Processed county: {county_id}")
    
    except Exception as e:
        print(f"Error processing county {county_id}: {e}")

# Use ProcessPoolExecutor to parallelize the process_county function
with ThreadPoolExecutor() as executor:
    executor.map(process_county, list_counties)


