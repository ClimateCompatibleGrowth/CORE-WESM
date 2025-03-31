"""

Script to run the CORE-WESM workflow

Copyright (C) 2025 Leonhard Hofbauer, licensed under a MIT license

"""

import sys
import logging
import yaml

import pandas as pd

# the ospro and fratoo modules need to currently be copied into the folder
# that also includes this script – these will be packaged in future
import ospro as op

import graphing_library as gl

#%% Set up logger
root_logger = logging.getLogger()

# remove existing handlers
if root_logger.hasHandlers():
    for h in root_logger.handlers:
        root_logger.removeHandler(h)

console = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
console.setFormatter(formatter)
root_logger.addHandler(console)

root_logger.setLevel("INFO")

logger = logging.getLogger(__name__)


#%% Load config files

# load workflow config
CONFIG = "config_files/workflow_config.yaml"

with open(CONFIG) as s:
    try:
        pcfg = yaml.safe_load(s)
    except yaml.YAMLError as exc:
        logger.error(exc)
        
# load data config file
with open(pcfg["model_files"]["data_config"]) as s:    
    try:
        dcfg = yaml.safe_load(s)
    except yaml.YAMLError as exc:
        logger.error(exc)  
        
#%% Load CORE-WESM data and process data

# load model data
data = op.read_spreadsheets(pcfg["model_files"]["input_data"], pcfg, dcfg)

# rename set
if pcfg["data_processing"]["set_rename"] is not False:
    data, dcfg = op.rename_set(pcfg["data_processing"]["set_rename"],
                               data, pcfg, dcfg)


### Aggregate years
if pcfg["data_processing"]["agg_years"] is not False:
    ysa = pd.read_csv(pcfg["data_processing"]["agg_years"],index_col="VALUE")["AGG"]
    tap = pd.read_csv(pcfg["data_processing"]["agg_config"],index_col="PARAM")["VALUE"]
    
    for s in data.keys():
        for n,df in data[s].items():
            if "YEAR" in df.index.names:
                df = df.rename(index=ysa.to_dict())
                if n not in tap.index:
                    logger.info(f"Aggregation method not defined for {n}, assuming sum.")
                    df = df.groupby(df.index.names).sum()
                elif tap.loc[n] == "eq":
                    df = df.groupby(df.index.names).mean()
                else:
                    df = df.groupby(df.index.names).sum()
            elif n=="YEAR":
                df = pd.DataFrame(ysa.unique(),columns=["VALUE"])
            
            data[s][n] = df
        
### Aggregate timeslices
if pcfg["data_processing"]["agg_timeslices"] is not False:
    tsa = pd.read_csv(pcfg["data_processing"]["agg_timeslices"],
                      index_col="VALUE")["AGG"]
    
    for s in data.keys():
        for n,df in data[s].items():
            if "TIMESLICE" in df.index.names:
                df = df.rename(index=tsa.to_dict())
                
                if n=="CapacityFactor":
                    df = df.groupby(df.index.names).mean()
                else:
                    df = df.groupby(df.index.names).sum()
            elif n=="TIMESLICE":
                df = pd.DataFrame(tsa.unique(),columns=["VALUE"])
            
            data[s][n] = df


#%% Process to multi-scale fratoo model and get run data

mod = op.create_multiscale_model(data,dcfg)


#%% Get run data and run optimization

# get list of counties
cs = [c for c in mod["Reference"].ms_struct["ft_scale"].index.to_list() if c!="RE1"]

if isinstance(pcfg["run"]["spatial_config"],list):
    runs = pcfg["run"]["spatial_config"]

elif pcfg["run"]["spatial_config"] == "full":
    runs = cs
    
elif pcfg["run"]["spatial_config"] == "full-sep":
    runs = [[c] for c in cs]

elif pcfg["run"]["spatial_config"] == "full-agg":
    runs = [cs]


# if single optimization, get run data and run
if (isinstance(pcfg["run"]["spatial_config"],list)
    or "sep" not in pcfg["run"]["spatial_config"]):
    data,dcfg = op.get_multiscale_run_data(mod,
                                           runs,
                                           pcfg, dcfg)
    # perform checks on model data
    op.check_data(data, pcfg, dcfg)
    
    # write datafile if to be used with OSeMOSYS cloud, etc. 
    
    # op.write_datafile(data, "./", pcfg, dcfg)
    # op.write_spreadsheet(data, "./", pcfg, dcfg)
    if pcfg["run"]["solve"] == "datafile":
        op.write_datafile(data, "./", pcfg, dcfg)

    elif pcfg["run"]["solve"] == "spreadsheet":
        op.write_spreadsheet(data, "./", pcfg, dcfg)

    # run model
    elif pcfg["run"]["solve"]:
        # run single optimization
        op.run_model(data, pcfg, dcfg)
        
        
        ### Process and save results
        
        res = op.load_results(pcfg, dcfg, data)
        
        res = op.expand_results(res)
        
        res = op.demap_multiscale_results(res,pcfg, dcfg)
    
        op.save_results(res, pcfg, dcfg)
    
elif "sep" in pcfg["run"]["spatial_config"]:


    res = list()
    
    for i,run in enumerate(runs):
    
        data,dcfg = op.get_multiscale_run_data(mod,
                                          run,
                                          pcfg, dcfg)
        # check data
        op.check_data(data, pcfg, dcfg)
        
        if pcfg["run"]["solve"] == "datafile":
            op.write_datafile(data, "./", pcfg, dcfg)
            continue
        elif pcfg["run"]["solve"] == "spreadsheet":
            op.write_spreadsheet(data, "./", pcfg, dcfg)
            continue
        # run model
        elif pcfg["run"]["solve"]:
            op.run_model(data, pcfg, dcfg)
    
            # load and expand results
            res.append(op.load_results(pcfg,dcfg,data))

    if pcfg["run"]["solve"]:
        # aggregate results
        s = pcfg["run"]["scenarios"][0]
        result = res[0][s]
        
        for k,v in result.items():
            v = pd.concat([r[s][k] for r in res],
                          axis=0,join="inner")
            
            if k not in mod[s].ms_struct["ft_param_agg"].index:
                if k.isupper():
                    logger.warning(f"Aggregation method for result component '{k}' "
                                   "not defined. Assuming 'merge'")
                    result[k] = v.drop_duplicates()
                else:    
                     logger.warning(f"Aggregation method for result component '{k}' "
                                    "not defined. Assuming 'sum'.")
                     result[k] = v.groupby(level=[i for i in
                                           range(v.index.nlevels)]).sum()
        
            elif  mod[s].ms_struct["ft_param_agg"].loc[k, "VALUE"] == "sum":
                result[k] = v.groupby(level=[i for i in
                                      range(v.index.nlevels)]).sum()
            elif  mod[s].ms_struct["ft_param_agg"].loc[k, "VALUE"] == "eq":
                result[k] = v.groupby(level=[i for i in
                                      range(v.index.nlevels)]).mean()
            else:
                raise ValueError("The aggregation method for parameter"+
                                     " values specified in ft_param_agg"+
                                     " is not implemented in fratoo.")
        
        res = {s:result}
    
    
        res = op.expand_results(res)
    
        res = op.demap_multiscale_results(res,pcfg, dcfg)

        # Use process data for plots or save
        op.save_results(res, pcfg, dcfg)

#%% Plotting

for p in pcfg["plotting"]:
    gl.plot_tech_sector(pcfg, results=res, parameter=p["parameter"],
                        scenario=p["scenario"],
                        sector=p["sector"],
                        geography=p["geography"],
                        xscale=pcfg["data_processing"]["agg_years"])