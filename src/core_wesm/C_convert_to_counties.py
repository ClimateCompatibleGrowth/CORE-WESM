#%%
import pandas as pd
import os
import shutil
import logging
from utils import empty_folder, is_int, check_duplicates, calculate_share_factor
from concurrent.futures import ThreadPoolExecutor

#%%
# Configuration
sectors_to_disaggregate = ['Agriculture', 'Backstop', 'Services', 'Residential', 'Supply']
sectors_to_disaggregate_with_pop = ['Residential']
sectors_to_also_keep_national = 'Supply.xlsx'
column_counties_id = 'COUNTY Id'

#Paths
national_sectoral_model_path = '../Sectoral_model/' #path to the national sectoral model
output_path = '../Counties_model/'                  #path to the output folder
counties_file = 'list_counties.csv'                 #file with the list of counties

input_data_path = '../1_Data/KNBS/'
pop_file = 'counties_population_KNBS.csv'
gdp_file = 'Gross County Product GCP 2021_KNBS.csv'

# Parameters
columns_to_modify = ['REGION']
parameters_to_disaggregate = ['ResidualCapacity', 'AccumulatedAnnualDemand', 'SpecifiedAnnualDemand',
                            'TotalTechnologyAnnualActivityLo'] #'SpecifiedDemandProfile',

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Read county data
counties = pd.read_csv(counties_file, keep_default_na=False)
list_counties = counties[column_counties_id].tolist()
duplicates = check_duplicates(list_counties)
if duplicates:
    raise ValueError('There will be errors because of the following duplicates: ', duplicates)

#%%
# Create output directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)
# Empty the output path before writing
empty_folder(output_path)

#%%
# Read population data
county_to_pop = pd.read_csv(os.path.join(input_data_path, pop_file), keep_default_na=False).set_index(column_counties_id)
years_population_data = [int(col) for col in county_to_pop.columns if is_int(col)]
years_total_population = county_to_pop.sum()

# Read GDP data
county_to_gdp = pd.read_csv(os.path.join(input_data_path, gdp_file), keep_default_na=False).set_index(column_counties_id)
if 'Administrative Unit' in county_to_gdp.columns:
    county_to_gdp = county_to_gdp.drop('Administrative Unit', axis=1)
gdp_share_data = pd.DataFrame(index=county_to_gdp.index)
for year in county_to_gdp.columns:
    kenya_gdp = county_to_gdp.loc['Kenya', year]
    gdp_share_data[year] = county_to_gdp[year] / kenya_gdp if kenya_gdp != 0 else 0
years_average_gdp_data = ['2015', '2016', '2017', '2018', '2019']
gdp_share_data_factor = gdp_share_data[years_average_gdp_data].mean(axis=1)


#%%
# Read GCP data 2020 earliest
# The file GCP_Intro has the key to the columns in each GCP file
gcp_data = pd.read_csv("../1_Data/GCP/GCP_2020.csv",
                       dtype={'COUNTY Id': str},
                       keep_default_na=False, na_values=[]
                       )

#%%
# Remove rows and columns where all values are NA
gcp_data = gcp_data.dropna(axis=0, how='all')  # Remove rows where all values are NA
gcp_data = gcp_data.dropna(axis=1, how='all')  # Remove columns where all values are NA
gcp_data = gcp_data.drop('COUNTY Name', axis=1).set_index(column_counties_id)
gcp_data = gcp_data.apply(pd.to_numeric, errors='coerce')

#%%
## List of sectors ##
# Agriculture
agriculture_list = ['Sec_1']
# Industry
industry_list = ['Sec_2', 'Sec_3', 'Sec_6']
# Services
services_list = ['Sec_4', 'Sec_5', 'Sec_7', 'Sec_9', 'Sec_10', 'Sec_11', 'Sec_12',
                  'Sec_13', 'Sec_14', 'Sec_15', 'Sec_16', 'Sec_17', 'Sec_18', 'Sec_19']
# Transport
transport_list = ['Sec_8']

#%%
#Agriculture share
gcp_share_factor_agri = calculate_share_factor(gcp_data, agriculture_list)
#Services share
gcp_share_factor_serv = calculate_share_factor(gcp_data, services_list)
#Industry share
gcp_share_factor_ind = calculate_share_factor(gcp_data, industry_list)
#Transport share
gcp_share_factor_trans = calculate_share_factor(gcp_data, transport_list)


#%%
# Create an empty set of commodity counties and technology counties
commodities_counties = set()
technology_counties = set()
initial_technologies = set() #before adding 'NAT' to the technology name

def process_county(county_id):
    try:
        # Create county folder
        county_folder = os.path.join(output_path, str(county_id))
        if not os.path.exists(county_folder):
            os.makedirs(county_folder)
            logging.info(f'Created {county_folder}')
        
        # Process each sectoral file
        for sector in sectors_to_disaggregate:
            sector_file = os.path.join(national_sectoral_model_path, f"{sector}.xlsx")
            if not os.path.exists(sector_file):
                logging.warning(f'Beware, {sector_file} does not exist!')
                continue

            # Copy sector file to county folder
            shutil.copy(sector_file, county_folder)
            county_file_path = os.path.join(county_folder, f"{sector}.xlsx")
            excel_data = pd.ExcelFile(sector_file)
            with pd.ExcelWriter(county_file_path, engine='openpyxl') as writer:
                for sheet_name in excel_data.sheet_names:
                    df = excel_data.parse(sheet_name)
                    for column in columns_to_modify:
                        if column in df.columns:
                            df[column] = county_id
                    if 'COMMODITY' in df.columns and sheet_name not in parameters_to_disaggregate:
                        df_new = df[df['COMMODITY'] == 'ELC003'].copy()
                        df_new['COMMODITY'] = ':RE1:ELC003'
                        if 'TECHNOLOGY' in df_new.columns:
                            df_new['TECHNOLOGY'] = df_new['TECHNOLOGY'] + 'NAT'
                            technology_counties.update(df_new['TECHNOLOGY'].tolist())
                            if sheet_name == 'InputActivityRatio':
                                initial_technologies.update(df_new['TECHNOLOGY'].str.replace('NAT', '').tolist())
                        df = pd.concat([df, df_new])
                    #ensure there is connection between the commodity and technology 'NAT' in the outputactivityratio sheet    
                    if sheet_name == 'OutputActivityRatio':
                        if 'TECHNOLOGY' in df.columns:
                            df['TECHNOLOGY'] = df['TECHNOLOGY'].apply(lambda x: x + 'NAT' if x in initial_technologies else x)
                    # all parameters stay the same except demand and stock where it's disaggregated per population
                    if sheet_name in parameters_to_disaggregate:
                        #print(sector, sheet_name)
                        if sector == 'Residential':
                            for col in df.columns:
                                if not is_int(col):
                                    continue
                                year = int(col)
                                closest_year = str(year if year in years_population_data else max(years_population_data))
                                population_county = county_to_pop.loc[county_id, closest_year]
                                total_population = years_total_population[closest_year]
                                df[col] = (df[col] * (population_county / total_population)).round(4)
                        elif sector == 'Agriculture':
                            for col in df.columns:
                                if not is_int(col):
                                    continue
                                df[col] = (df[col] * gcp_share_factor_agri[county_id]).round(4)
                        elif sector == 'Services':
                            for col in df.columns:
                                if not is_int(col):
                                    continue
                                df[col] = (df[col] * gcp_share_factor_serv[county_id]).round(4)
                        elif sector == 'Industry':
                            for col in df.columns:
                                if not is_int(col):
                                    continue
                                df[col] = (df[col] * gcp_share_factor_ind[county_id]).round(4)
                        elif sector == 'Transport':
                             for col in df.columns:
                                if not is_int(col):
                                    continue
                                df[col] = (df[col] * gcp_share_factor_trans[county_id]).round(4)
                        else:
                            for col in df.columns:
                                if not is_int(col):
                                    continue
                                df[col] = (df[col] * gdp_share_data_factor[county_id]).round(4)
                           
                    df.insert(0, 'MODEL', '#ALL')
                    df.insert(1, 'SCENARIO', '#ALL')
                    df.insert(2, 'PARAMETER', sheet_name)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
               
    except Exception as e:
        logging.error(f"Error processing county {county_id}: {e}")

# Parallelize county processing
with ThreadPoolExecutor() as executor:
    executor.map(process_county, list_counties)

# Process national files
def process_national_files():
    try:
        national_counties_folder = os.path.join(output_path, 'national')
        if not os.path.exists(national_counties_folder):
            os.makedirs(national_counties_folder)
        for file_name in os.listdir(national_sectoral_model_path):
            file_path = os.path.join(national_sectoral_model_path, file_name)
            if os.path.isfile(file_path) and file_name.split('.')[0] not in sectors_to_disaggregate:
                shutil.copy(file_path, national_counties_folder)
                destination_file = os.path.join(national_counties_folder, file_name)
                excel_data = pd.ExcelFile(file_path)
                with pd.ExcelWriter(destination_file, engine='openpyxl') as writer:
                    for sheet_name in excel_data.sheet_names:
                        df = excel_data.parse(sheet_name)
                        df.insert(0, 'MODEL', '#ALL')
                        df.insert(1, 'SCENARIO', '#ALL')
                        df.insert(2, 'PARAMETER', sheet_name)
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
        # Copy the supply file
        source_file = os.path.join(national_sectoral_model_path, sectors_to_also_keep_national)
        destination_file = os.path.join(national_counties_folder, sectors_to_also_keep_national)
        shutil.copy(source_file, destination_file)
        excel_data = pd.ExcelFile(source_file)
        with pd.ExcelWriter(destination_file, engine='openpyxl') as writer:
            for sheet_name in excel_data.sheet_names:
                df = excel_data.parse(sheet_name)
                df.insert(0, 'MODEL', '#ALL')
                df.insert(1, 'SCENARIO', '#ALL')
                df.insert(2, 'PARAMETER', sheet_name)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        logging.info('National folder created')
    except Exception as e:
        logging.error(f"Error processing national files: {e}")

process_national_files()

# Update Set.xlsx file
def update_set_file():
    try:
        set_file_path = os.path.join(output_path, 'national', 'Set.xlsx')
        set_data = pd.read_excel(set_file_path, sheet_name=None)
        existing_commodities = set_data['COMMODITY']['VALUE'].tolist()
        existing_technologies = set_data['TECHNOLOGY']['VALUE'].tolist()
        new_commodities = list(commodities_counties.union(set(existing_commodities)))
        new_technologies = list(technology_counties.union(set(existing_technologies)))
        set_data['COMMODITY'] = pd.DataFrame({'VALUE': new_commodities})
        set_data['TECHNOLOGY'] = pd.DataFrame({'VALUE': new_technologies})

        # YeasSplit wide format
        ys = set_data['YearSplit'][['TIMESLICE', 'YEAR', 'VALUE']]
        ys = ys.pivot(index='TIMESLICE', columns='YEAR', values='VALUE').reset_index()
        ys.columns.name = None #erase index name
        # Update the 'YearSplit' sheet 
        set_data['YearSplit'] = ys

        with pd.ExcelWriter(set_file_path, engine='openpyxl') as writer:
            for sheet_name, df in set_data.items():
                if sheet_name in ['COMMODITY', 'TECHNOLOGY', 'YearSplit']:
                    df.insert(0, 'MODEL', '#ALL')
                    df.insert(1, 'SCENARIO', '#ALL')
                    df.insert(2, 'PARAMETER', sheet_name)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        logging.info('Set.xlsx updated')
    except Exception as e:
        logging.error(f"Error updating Set.xlsx: {e}")

update_set_file()

logging.info('Done!!')



# %%
