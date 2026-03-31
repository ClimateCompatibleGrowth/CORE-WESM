"""

Workflow script for creating the input data set of and run CORE-WESM 

Copyright (C) 2026 Leonhard Hofbauer, licensed under a MIT license

"""

# Load relevant Python libraries
import yaml
import logging
import warnings
import pandas as pd
import data_pipeline_functions as dp
import run_pipeline_functions as rp

# Suppress certain warnings for better readibility of logs
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

# Set up the logger
dp.setup_logger("INFO")
logger = logging.getLogger(__name__)

#%% Load configurations files

# Load the workflow configuration file
with open("config_files/pipeline_config.yaml") as stream:
    try:
        pcfg = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# Load the run configuration file
with open("config_files/run.yaml") as stream:
    try:
        rcfg = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        
# Load the analysis file
with open("config_files/analysis_config_"+rcfg["name"]+".yaml") as stream:
    try:
        acfg = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        
logger.info("Config files loaded.")

#%% Convert the datafile to a spreadsheet file
dp.convert_datafile(dataconfig_file = pcfg["filepaths"]["data_config_file_NM"],
                    data_file = pcfg["filepaths"]["national_data_file"],
                    output_file = pcfg["filepaths"]["national_spreadsheet_file"],
                    overwrite=True)


#%% Downscale to a county-resolved model
dp.downscale(input_file = pcfg["filepaths"]["national_spreadsheet_file"],
              dataconfig_file = pcfg["filepaths"]["data_config_file_NM"],
              tech_sector_mapping = pcfg["filepaths"]["tech_to_sector_mapping_file"],
              comm_sector_mapping = pcfg["filepaths"]["comm_to_sector_mapping_file"],
              list_counties = pcfg["filepaths"]["list_counties_file"],
              pop_file = pcfg["filepaths"]["pop_file"],
              pop_file_ruur = pcfg["filepaths"]["pop_file_ruur"],
              gdp_file = pcfg["filepaths"]["gdp_file"],
              county_sectors = pcfg["downscaling"]["downscaled_sectors"],
              remove_fte_tech_mode = pcfg["downscaling"]["remove_fte_tech_mode"],
              output_path = pcfg["filepaths"]["downscaled_model_path"],
              overwrite=True)


#%% Process the model (this again makes use of the filepaths and parameters set out in the configuration file)
dp.process_county_model(input_path = pcfg["filepaths"]["downscaled_model_path"],
                        dataconfig_file = pcfg["filepaths"]["data_config_file_NM"],
                        datasets = pcfg["county_processing"]["datasets"],
                        output_path = pcfg["filepaths"]["county_processed_path"],
                        overwrite=True
                        )


#%% Run the model for each of the selected scenarios and save the results

rp.run_model(dataconfig_file = pcfg["filepaths"]["data_config_file_CW"],
              input_path = pcfg["filepaths"]["county_processed_path"],
              model_file_path= acfg["runs"]["model_file"],
              scenario_list = acfg["scenarios"],
              spatial_config = acfg["runs"]["spatial_config"],
              output_path = pcfg["filepaths"]["results_path"]+rcfg["name"]+"/"+rcfg["run_id"],
              rename_set = {"COMMODITY":"FUEL"},
              glpk_dir = pcfg["filepaths"]["glpk_dir"],
              agg_years = acfg["runs"]["agg_years"],
              agg_config = acfg["runs"]["agg_cfg"],
              agg_timeslices = acfg["runs"]["agg_ts"],
              solve = "optimize")
