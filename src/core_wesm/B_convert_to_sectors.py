import pandas as pd
import os
from utils import empty_folder, is_int

input_path = '../National_parameter_model/'

input_file = 'model_smp.xlsx' # update the name of the file to be converted
output_path = '../Sectoral_model/' # update the path where the files will be saved

# Create the output directory if it doesn't exist
if not os.path.exists(output_path):
    os.makedirs(output_path)

# Load the Excel file into a pandas DataFrame
model_data = pd.ExcelFile(input_path + input_file)

# Get a list of all sheet names
sheets_list = model_data.sheet_names

# Create the list of demand parameters tab
demand_sheets_list = ['AccumulatedAnnualDemand',
                      'SpecifiedAnnualDemand',
                      'SpecifiedDemandProfile'
                      ]

# Create the list of reserve margin tab
reserve_margin_sheets_list = ['ReserveMargin',
                              'ReserveMarginTagFuel'
                              ]


# Create the list of RE tag tab
reTag_sheets_list = ['REMinProductionTarget',
                     'RETagFuel',
                     'RETagTechnology'
                     ]
# Create the list of parameters not used
notUsed_sheets_list = reTag_sheets_list + ['CapacityOfOneTechnologyUnit']

# Check that there are only zeros in these sheets
for sheet in reTag_sheets_list:
    # Read the sheet into a DataFrame
    df = model_data.parse(sheet)
    # Check that there are only zeros, otherwise print message error
    for col in df.columns:
        # retrieve population data for the county for each year
        if not is_int(col):
            continue
        year = int(col)
        # Check if any value in the column is non-zero
        if not (df[col] == 0).all():
            print(f"Sheet '{sheet}', column '{year}': Non-zero values found.")
    print(f"'{sheet}' has only zeros, it won't be included in the sectoral model")

# Initialize a list to store technology values
tech_list = set()
col_tech = 'TECHNOLOGY'

# Iterate through each sheet
for sheet in sheets_list:
    if sheet not in reTag_sheets_list and notUsed_sheets_list:
        # Read the sheet into a DataFrame
        df = model_data.parse(sheet)
        # Check if 'TECHNOLOGY' column exists
        if col_tech in df.columns:
            # Extract technology values from the 'TECHNOLOGY' column
            sheet_tech_list = df[col_tech].tolist()
            tech_list.update(sheet_tech_list)

# Convert the set to a sorted list
tech_list = sorted(list(tech_list))
# print(tech_list)

# load the tech to sector
tech_to_sector_data = pd.read_excel('tech_to_sector.xlsx')
tech_to_sector_dict = dict(zip(tech_to_sector_data['technology'], tech_to_sector_data['sector']))
# print(tech_to_sector_dict)

# Group technologies by sector
tech_by_sector = {}
for tech in tech_list:
    sector = tech_to_sector_dict.get(tech, 'Unknown')
    tech_by_sector.setdefault(sector, []).append(tech)
# print(tech_by_sector)

# load the demand commodities to sector
commodity_column = 'COMMODITY'
com_to_sector_data = pd.read_excel('dem_com_to_sector.xlsx')
com_to_sector_dict = dict(zip(com_to_sector_data['commodity'], com_to_sector_data['sector']))
# print(com_to_sector_dict)

# Group commodities by sector
com_by_sector = {}
for com in com_to_sector_data['commodity']:
    sector = com_to_sector_dict.get(com, 'Unknown')
    com_by_sector.setdefault(sector, []).append(com)
# print(tech_by_sector)

# Empty the output path before writing
empty_folder(output_path)

# Create a "Set" Excel file
set_file = 'Set.xlsx'
set_sheets_list = ['COMMODITY',
                   'EMISSION',
                   'TECHNOLOGY',
                   'DiscountRate',
                   'MODE_OF_OPERATION',
                   'REGION',
                   'TIMESLICE',
                   'YEAR',
                   'YearSplit']

# Create an "Emission" Excel file
emission_file = 'Emission.xlsx'
emission_sheets_list = ['AnnualEmissionLimit',
                        'AnnualExogenousEmission',
                        'EmissionsPenalty',
                        'ModelPeriodEmissionLimit',
                        'ModelPeriodExogenousEmission'
                        ]

# Create an "Other" Excel file
other_file = 'Other.xlsx'

# Create sector-specific Excel files and handle remaining data
for sheet_name in sheets_list:
    df = model_data.parse(sheet_name)
    df_copy = df.copy()

    if sheet_name in demand_sheets_list:
        for sector, coms in com_by_sector.items():
            output_file = output_path + f'{sector}.xlsx'
            # Check if file exists, create if not
            mode = 'a' if os.path.exists(output_file) else 'w'
            with pd.ExcelWriter(output_file, mode=mode, engine='openpyxl') as writer:
                df_sector = df_copy[df_copy[commodity_column].isin(coms)]

                if not df_sector.empty:
                    df_sector.to_excel(writer, sheet_name=sheet_name, index=False)
                    df_copy = df_copy[~df_copy.index.isin(df_sector.index)]

        # check if df_copy is empty or not
        if not df_copy.empty:
            # Go through the remaining rows, if there is a value different from 0, print an error message
            columns_to_skip = ['REGION', commodity_column, 'TIMESLICE']
            for index, row in df_copy.iterrows():
                row_values = row.drop(columns_to_skip, axis=0, errors='ignore')  # Skip specified columns

                if (row_values != 0).any():
                    commodity_value = row[commodity_column]
                    print(f"Error: Non-zero values found for commodity {commodity_value} in sheet {sheet_name}"
                          f" allocate the demand commodity to a sector")

    elif sheet_name in reserve_margin_sheets_list:
        output_file = output_path + 'Electricity.xlsx'
        # Check if file exists, create if not
        mode = 'a' if os.path.exists(output_file) else 'w'
        with pd.ExcelWriter(output_file, mode=mode, engine='openpyxl') as writer:
            if sheet_name == 'ReserveMargin':
                df_copy.to_excel(writer, sheet_name=sheet_name, index=False)

            elif sheet_name == 'ReserveMarginTagFuel':
                # Filter rows where all values except the two first columns are non-zero
                df_filtered = df[df.iloc[:, 2:].ne(0).all(axis=1)]
                # print(df_filtered)
                df_filtered.to_excel(writer, sheet_name=sheet_name, index=False)

    elif (sheet_name not in set_sheets_list and sheet_name not in emission_sheets_list
          and sheet_name not in notUsed_sheets_list):
        if col_tech in df.columns:
            for sector, techs in tech_by_sector.items():
                output_file = output_path + f'{sector}.xlsx'
                # Check if file exists, create if not
                mode = 'a' if os.path.exists(output_file) else 'w'
                with pd.ExcelWriter(output_file, mode=mode, engine='openpyxl') as writer:
                    df_sector = df_copy[df_copy[col_tech].isin(techs)]
                    if not df_sector.empty:
                        df_sector.to_excel(writer, sheet_name=sheet_name, index=False)
                        df_copy = df_copy[~df_copy.index.isin(df_sector.index)]

        # Write remaining data to "Other" file
        if not df_copy.empty:
            mode = 'a' if os.path.exists(output_path + other_file) else 'w'
            with pd.ExcelWriter(output_path + other_file, mode=mode, engine='openpyxl') as other_writer:
                df_copy.to_excel(other_writer, sheet_name=sheet_name, index=False)

    elif sheet_name in set_sheets_list:
        mode = 'a' if os.path.exists(output_path + set_file) else 'w'
        with pd.ExcelWriter(output_path + set_file, mode=mode, engine='openpyxl') as set_writer:
            df_copy.to_excel(set_writer, sheet_name=sheet_name, index=False)

    elif sheet_name in emission_sheets_list:
        mode = 'a' if os.path.exists(output_path + emission_file) else 'w'
        with pd.ExcelWriter(output_path + emission_file, mode=mode, engine='openpyxl') as emission_writer:
            df_copy.to_excel(emission_writer, sheet_name=sheet_name, index=False)

    else:
        if sheet_name not in notUsed_sheets_list:
            print('Error:', sheet_name + 'was not allocated')
