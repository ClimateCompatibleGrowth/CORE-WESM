"""

Module with processing functions for OSeMOSYS input and results data

Copyright (C) 2025 Leonhard Hofbauer, licensed under a MIT license

"""

import os

import subprocess
import logging

import pandas as pd
import numpy as np

import otoole

try:
    import fratoo as ft
except ImportError:
    ft = None 
    
try:
    import highspy
except ImportError:
    highspy = None 


pd.set_option('future.no_silent_downcasting', True)

logger = logging.getLogger(__name__)


def read_spreadsheets(path, pcfg, dcfg):
    """ Read scenario data from spreadsheet files.
    
    Parameters
    ----------
    path : str
        Path to directory or spreadsheet file.
    pcfg : dict
        Dictionary that includes config parameters that specify the read
        strategy. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the same
        format as used for otoole).

    Returns
    -------
    data : dict of dicts
        Dictionary with a dictionary of DataFrames with parameters and set for
        each scenario.

    """
    
    logging.info("Parsing data tables from spreadsheet files.")
    
    # load data spreadsheets
    if not os.path.exists(path):
        raise FileNotFoundError("Directory/file does not exist.")
    if os.path.isfile(path):
        if not path.endswith(tuple(pcfg["read_strategy"]["fileext"])):
            raise ValueError("File extension is not recognized.")                     
        files = [os.path.join(os.path.dirname(path),os.path.basename(path))]
    elif pcfg["read_strategy"]["recursively"] is False:
        files = os.listdir(path)
        files = [os.path.join(path,f) for f in files if f.endswith(tuple(pcfg["read_strategy"]
                                                      ["fileext"]))]
    else:
        files = []
        for root, dirs, fs in os.walk(path):
            files = files + [os.path.join(root, f) for f in fs]
        
    logging.info("Spreadsheet file(s) being parsed: "+", ".join(files))

    # # add interface-specific elements to config
    # cfg["TECHGROUP"] = {"type":"set",
    #                     "dtype":"str"}   
     
    sets = [k for k,v in dcfg.items() if v["type"]=="set"]
        
    # list of data tables
    dts = list()

    # import all spreadsheet files
    for f in files:
        # import file
        sf = pd.read_excel(f,
                           sheet_name=None,
                           header=None,
                           na_values=[""],
                           keep_default_na=False)
        
        # iterate through sheets
        for df in sf.values():
            
            if pcfg["read_strategy"]["use_markers"] is False:
                dt = df
                # remove any additional rows
                if dt.iloc[:,0].isna().any():
                    li = dt.iloc[:,0].isna().idxmax()
                    dt = dt.loc[:li,:].iloc[:-1]
                
                # remove any additional columns
                if dt.iloc[0,:].isna().any():
                    lc = dt.iloc[0,:].isna().idxmax()
                    dt = dt.loc[:,:lc].iloc[:,:-1]   
                
                # set column names and reset index   
                dt.columns = dt.iloc[0]
                dt = dt[1:]
                dt = dt.reset_index(drop=True)
                
            else: 
                # get location of marker
                loc = np.where(df==pcfg["read_strategy"]["markers"]["table"])
                # skip to next sheet if no marker
                if loc[0].size == 0:
                    continue
                # iterate through each marker location
                for r,c in zip(loc[0],loc[1]):
                    dt = df.iloc[r:,c:]
                    
                    # remove any additional rows
                    if dt.iloc[:,0].isna().any():
                        li = dt.iloc[:,0].isna().idxmax()
                        dt = dt.loc[:li,:].iloc[:-1]
                    
                    # remove any additional columns
                    if dt.iloc[1,:].isna().any():
                        lc = dt.iloc[1,:].isna().idxmax()
                        dt = dt.loc[:,:lc].iloc[:,:-1]   
                    
                    # remove marker row
                    dt = dt.iloc[1:,:]
                    
                    # set column names and reset index   
                    dt.columns = dt.iloc[0]
                    dt = dt[1:]
                    dt = dt.reset_index(drop=True)
                    
            # check if PARAMETER is used instead of SET column and rename
            se = [n for n,v in dcfg.items() if v["type"] == "set"]
            if "PARAMETER" in dt.columns and dt.loc[0,"PARAMETER"] in se:
                dt = dt.rename(columns={"PARAMETER":"SET"})
            
            # replace short parameter names with full names
            ns ={v["short_name"]:n for n,v in dcfg.items()
                 if "short_name" in v.keys()}
            dt = dt.replace(ns)
            
            # add to list of data tables
            dts.append(dt)
                
    logging.info(f"{len(dts)} data tables read from the spreadsheet file(s).")
    
    # process data tables
    logging.info("Processing data tables.")

    # create dataframe for set and parameter data

        
    setsval = pd.concat([dt for dt in dts if "SET" in dt.columns])
    params = pd.concat([pd.DataFrame([],columns=sets+["VALUE"])]
                       +[dt for dt in dts if ("PARAMETER" in dt.columns)])

    # set default value for sets if provided and no value given in data files
    for k,v in pcfg["read_strategy"]["defaults"].items():
        if k in sets:
            params[k] = params[k].fillna(v)
 
    # create dict for scenario to write to spreadsheets
    md = dict()

    # iterate through scenarios and fill dictionary

    # for m,s,sc in modscen:
    for s in pcfg["scenarios"]:
        
            
        md[s["name"]] = dict()
        
        # iterate through parameters and sets
        for k,v in dcfg.items():
            
            # if set, process accordingly
            if v["type"] == "set":
                # get all relevant values
                md[s["name"]][k] = setsval.loc[((setsval["MODEL"] == s["model"]) |
                                       (setsval["MODEL"] == pcfg["read_strategy"]["markers"]["all"])) &
                                          ((setsval["SCENARIO"].str.split(",",expand=True).isin(s["levers"]).any(axis=1)) |
                                       (setsval["SCENARIO"] == pcfg["read_strategy"]["markers"]["all"])) &
                                       (setsval["SET"] == k)]
                md[s["name"]][k] =md[s["name"]][k].loc[:,[c for c in ["VALUE",
                                                       "DESCRIPTION",
                                                       "UNIT",
                                                       "TECHGROUP",
                                                       "UNITOFCAPACITY",
                                                       "UNITOFACTIVITY"]
                                           if c in md[s["name"]][k].columns]]
                
                if not md[s["name"]][k].empty:
                    md[s["name"]][k] = md[s["name"]][k].dropna(axis=1,how="all")
                    
                md[s["name"]][k] = md[s["name"]][k].sort_values("VALUE").reset_index(drop=True)
                
                # set dtype
                md[s["name"]][k].loc[:,"VALUE"] = md[s["name"]][k].loc[:,
                                                    "VALUE"].astype(v["dtype"])
                # if YEAR set, remove years not used
                if k == "YEAR":
                    md[s["name"]][k] = md[s["name"]][k].loc[md[
                                s["name"]][k]["VALUE"].isin(range(*s["timehorizon"]))]
                    
                # check if unique
                if not md[s["name"]][k]["VALUE"].is_unique:
                    md[s["name"]][k] = md[s["name"]][k].drop_duplicates(["VALUE"])
                    logging.warning(f"The values of set '{k}' are not unique "
                                    f"for scenario '{s['name']}' with model '{s['model']}'."
                                    " Deleted duplicates.")
                # check if empty
                if md[s["name"]][k].empty:
                    logging.debug(f"The set '{k}' is empty for scenario '{s['name']}'"
                                  f" with model '{s['model']}'.")
                    md[s["name"]][k].loc["",:] = ""
            
                # rename value column for TECHGROUP
                if k == "TECHGROUP":
                    md[s["name"]][k] = md[s["name"]][k].rename(columns={"VALUE":"TECHGROUP"})
                    
            # if parameter, process accordingly
            if v["type"] == "param":
                # get all relevant values
                md[s["name"]][k] = params.loc[((params["MODEL"] == s["model"]) |
                                       (params["MODEL"] == pcfg["read_strategy"]["markers"]["all"])) &
                                         ((params["SCENARIO"].str.split(",",expand=True).isin(s["levers"]).any(axis=1)) |
                                       (params["SCENARIO"] == pcfg["read_strategy"]["markers"]["all"])) &
                                       (params["PARAMETER"] == k)]
                # drop irrelevant columns
                md[s["name"]][k] = md[
                        s["name"]][k].drop(["MODEL","SCENARIO","PARAMETER"]
                                         + [c for c in md[s["name"]][k].columns
                                            if ("YEAR" in v["indices"])
                                            and c not in [s for s in v["indices"]
                                                          if s !="YEAR"]
                                            +list(range(*s["timehorizon"]))]
                                         + [c for c in md[s["name"]][k].columns
                                            if ("YEAR" not in v["indices"])
                                            and c not in (v["indices"]+["VALUE"])]
                                         ,axis=1)
                # set and sort index
                md[s["name"]][k] = md[
                        s["name"]][k].set_index([s for s in v["indices"]
                                               if s != "YEAR"])
                md[s["name"]][k] = md[s["name"]][k].sort_index()
            
                
                # set dtypes
                md[s["name"]][k] = md[s["name"]][k].astype(v["dtype"])
                md[s["name"]][k] = md[s["name"]][k].replace("nan",pd.NA)
                if "YEAR" in v["indices"]:
                    md[s["name"]][k].columns = md[s["name"]][k].columns.astype(dcfg["YEAR"]
                                                               ["dtype"])
                
                # remove years not to be used
                if "YEAR" in v["indices"]:
                    md[s["name"]][k] = md[s["name"]][k].loc[:,md[
                                s["name"]][k].columns.isin(range(*s["timehorizon"]))]
                    
                    
                # if float round if required
                if (v["dtype"] == "float") and (pcfg["read_strategy"]["rounding"] != False):
                    md[s["name"]][k] = md[s["name"]][k].round(pcfg["read_strategy"]["rounding"])
                    
                # rearrange params indexed over YEAR
                if "YEAR" in v["indices"]:
                    md[s["name"]][k].columns.name = "YEAR"
                    md[s["name"]][k] = md[s["name"]][k].stack()
                    md[s["name"]][k].name = "VALUE"
                    md[s["name"]][k] = md[s["name"]][k].to_frame()      
                
                # check for duplicates
                if md[s["name"]][k].index.has_duplicates:
                    # FIXME: potentially process duplicates in a logical way, e.g.,
                    # overwriting values set for all scenarios with ones set for
                    # a specific scenario
                    logging.error(f"The values of parameter '{k}' are not unique"
                                    f" for scenario '{s['name']}' with model '{s['model']}'.")
                    logging.debug("The duplicates are:")
                    logging.debug(md[s["name"]][k][md[s["name"]][k].index.duplicated(keep=False)])
                    raise ValueError(f"The values of parameter '{k}' are not "
                                    f"unique for scenario '{s['name']}' with model '{s['model']}'.")
                    
                if md[s["name"]][k].empty:
                    logging.debug(f"The values for parameter '{k}' are empty "
                                    f"for scenario '{s['name']}' with model '{s['model']}'.")
                    # md[s["name"]][k]= md[s["name"]][k].astype(str)
                    # md[s["name"]][k].loc["",:] = ""
                    
    logging.info("Processed data tables and arranged scenario data.")
    
    return md

def create_multiscale_model(data, dcfg=None):
    """ Create multi-scale model for each scenario using the fratoo package.
    
    Parameters
    ----------
    data : dict
        Data dictionary with one or more scenarios.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    mod : dict of fratoo.Model
        Dictionary of instances of fratoo models, one for each scenario
        (names as keys).

    """
    if ft is None:
            logger.warning("Multi-scale functionality is not available as"
                           " the required dependency (fratoo)"
                           " is not available.")
            return False

    logging.info("Creating fratoo model for each scenario.")
    
    mod = dict()
    
    for s in data.keys():
        mod[s] = ft.Model()
        mod[s].init_from_dictionary(data[s], config=dcfg, process=False)
        mod[s].process_input_data(sep="9")
        
    logging.info("Created fratoo model(s).")
    
    return mod


def get_multiscale_run_data(mod, regions, pcfg, dcfg):
    """ Create multi-scale model for each scenario using the fratoo package.
    
    Parameters
    ----------
    mod : dict of fratoo.Model
        Dictionary of instances of fratoo models, one for each scenario
        (names as keys).
    regions : List
        List of names of regions to be explicitely included in the run.
        Sublists can be used to aggregate regions.
    pcfg : dict
        Dictionary that includes config parameters that specify the read
        strategy. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    data : dict
        Data dictionary with one or more scenarios.
    dcfg : dict
        Updated configuration with fratoo parameters removed.
    

    """ 
    if ft is None:
            logger.warning("Multi-scale functionality is not available as"
                           " the required dependency (fratoo)"
                           " is not available.")
            return False

    logging.info("Creating run data for multiscale model.")
    
    data = dict()
    for s in mod.keys():
        rr = mod[s]._create_regions_for_run(regions,
                                            autoinclude=True,
                                            weights="SpecifiedAnnualDemand",
                                            syn=["","p"])
        data[s] = mod[s]._create_run_data(df_regions=rr,
                                          sep=pcfg["write_strategy"]["datafile"]["region_sep"],
                                          syn=["","p"],
                                          redset=False
                                          ,pyomo=False)
    
    logging.info("Created run data for multiscale model.")
    logging.info("Updating data configuration dictionary.")
    for k in list(dcfg.keys()):
        if k.startswith("ft_"):
            dcfg.pop(k)
            
    logging.info("Updated data configuration dictionary.")
    
    return data,dcfg


def rename_set(mapping, data, pcfg, dcfg):
    """ Rename a set name.
    
    Parameters
    ----------
    mapping : dict
        Dictionary mapping old to new set names.
    data : dict
        Data dictionary with one or more scenarios.
    pcfg : dict
        Dictionary that includes config parameters that specify the read
        strategy. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).
    
    Returns
    -------
    data : dict of dicts
        Dictionary with a dictionary of DataFrames with parameters and set for
        each scenario.
    dcfg : dict
        Updated config dictionary.
    
    """   
    logging.info("Rename set names.")
    
    for s in data.keys():
        # iterate through parameters and sets
        for k,v in dcfg.items():
            # if param, process accordingly
            if v["type"] == "param":
                for se in mapping.keys():
                    if se in v["indices"]:
                        data[s][k].index = data[s][k].index.rename([s if s!=se
                                                                else mapping[se]
                                                                for s
                                                                in data[s][k].index.names])
        # adjust set name
        for se in mapping.keys():
            data[s][mapping[se]] = data[s].pop(se)
            

    # adjust config file
    for k,v in dcfg.items():
        if dcfg[k]["type"]=="param":
            dcfg[k]["indices"] =  [i if i not in mapping.keys() else mapping[i]
                                  for i in dcfg[k]["indices"]]
    for se in mapping.keys():
        dcfg[mapping[se]] = dcfg.pop(se)
    
    logging.info("Renamed set names")
    
    return data, dcfg
        
def check_data(data, pcfg, dcfg):
    """ Check scenario data for issues.
    
    Parameters
    ----------
    data : dict
        Data dictionary with one or more scenarios.
    pcfg : dict
        Dictionary that includes config parameters that specify the read
        strategy. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    e : bool
        True if no issue was identified during checks, otherwise False.

    """
    # FIXME: implement more checks

    logging.info("Performing checks on data.")
    
    # check if all set values used to define parameters are in respective sets
    # iterate through models and scenarios
    
    e = True
    for s in data.keys():
        # iterate through parameters and sets
        for k,v in dcfg.items():
            # skip multi-scale parameters
            if k.startswith("ft"):
                continue
            # if param, check accordingly
            if v["type"] == "param":
                for ii in v["indices"]:
                    if ii == "YEAR":
                        continue
                    if not data[s][k].index.get_level_values(ii).isin(
                            data[s][ii]["VALUE"].tolist()+[""]).all():
                        # FIXME: raise exception (?)
                        undef = data[s][k][~data[s][k].index.get_level_values(ii).isin(
                            data[s][ii]["VALUE"].tolist())]
                        e=False
                        logging.error(f"The parameter '{k}' for scenario '{s}'"
                                    f" is defined for {ii} values"
                                    f" that are not part of the '{ii}' set. This"
                                    " can cause errors when running the"
                                    " model. The relevant entries are:"
                                    f"{undef}")

        lowerthan = {"ResidualCapacity":"TotalAnnualMaxCapacity",
                     "TotalAnnualMinCapacity":"TotalAnnualMaxCapacity",
                     "TotalTechnologyAnnualActivityLowerLimit":"TotalTechnologyAnnualActivityUpperLimit",
                     "TechnologyActivityByModeLowerLimit":"TechnologyActivityByModeUpperLimit",
                     "TotalAnnualMinCapacityInvestment":"TotalAnnualMaxCapacityInvestment"}
        for l,h in lowerthan.items():
        # check if TotalAnnualMinCapacity is lower than TotalAnnualMaxCapacity
            logging.debug(f"Checking contradictions between {l} and {h}.")
            if (data[s][l].reindex_like(
                data[s][h])>data[s][h]).any().any():
                vio = data[s][h][(data[s][l].reindex_like(
                    data[s][h])>data[s][h])].dropna(how="all").dropna(axis=1)
                e=False
                logging.error(f"{l} is higher than {h}"
                              f"in scenario {s},"
                              " violating the constraint: \n"
                              f"{vio}")
            
    logging.info("Performed checks on data.")
    
    return e

def write_datafile(data, path, pcfg, dcfg):
    """ Write data to GNU MathProg datafile(s).
    
    Parameters
    ----------
    data : dict
        Data dictionary with one or more scenarios.
    path : str
        Path to directory for writing the datafiles.
    pcfg : dict
        Dictionary that includes config parameters that specify the write
        strategy. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    -

    """

    logging.info("Rearrange data for saving.")
    
    # create deepcopy
    data = _create_data_deepcopy(data)

    # if required rename FUEL set
    # rename FUEL set to COMMODITY (UI - at one point -  required FUEL 
    # for import but uses COMMODITY for export, so this can be used to 
    # make datafiles consistent with datafiles exported from UI)
    if pcfg["write_strategy"]["datafile"]["fuel_rename"]:
        for s in data.keys():
            # iterate through parameters and sets
            for k,v in dcfg.items():
                # if param, process accordingly
                if v["type"] == "param":
                    if "FUEL" in v["indices"]:
                        data[s][k].index = data[s][k].index.rename([s if s!="FUEL"
                                                                else "COMMODITY"
                                                                for s
                                                                in data[s][k].index.names])
            # adjust set name
            data[s]["COMMODITY"] = data[s].pop("FUEL")
        
        # adjust config file
        for k,v in dcfg.items():
            if dcfg[k]["type"]=="param":
                dcfg[k]["indices"] =  [i if i!="FUEL" else "COMMODITY" 
                                      for i in dcfg[k]["indices"]]
        dcfg["COMMODITY"] = dcfg.pop("FUEL")

        
    # rearrange data for otoole and save a datafile for each model and scenario
    for s in data.keys():
        for k,v in dcfg.items():
            if k.startswith("ft_"):
                continue
            if v["type"] == "result":
                continue
            if v["type"] == "set":
                data[s][k] = data[s][k].loc[:,"VALUE"].to_frame()
            if k == "TECHGROUP":
                del data[s][k]
                continue
            if data[s][k].empty:
                data[s][k]= data[s][k].astype(str)
                data[s][k].loc["",:] = ""
                
            data[s][k] = data[s][k][data[s][k]["VALUE"]!=""].dropna()
        defaults = {k:v["default"] for k,v in dcfg.items() if v["type"]!="set"}
        
        logging.info(f"Writing data for scenario {s} to data file.")
        
        # FIXME: there seems to be a bug in otoole that means that it throws
        # an error when no defaults are given, and if they are given they are 
        # written to the datafile (and creating an unnecessarily large file)
        # - below is a workaround, otherwise the use of the write function would
        # be required (see commented out below)
        from otoole.convert import _get_user_config, _get_write_strategy
        write_strategy = _get_write_strategy(
                  dcfg, "datafile", write_defaults=False)
        write_strategy.write(data[s], os.path.join(path,"datafile_"+s+".txt"),
                              defaults)

        # otoole.write('config.yaml',
        #              "datafile","datafile_"+s+".txt",
        #               data[s],defaults)
        
    return

def write_spreadsheet(data, path, pcfg, dcfg):
    """ Write data to spreadsheet file(s).
    
    Parameters
    ----------
    data : dict
        Data dictionary with one or more scenarios.
    path : str
        Path to directory for writing the spreadsheet files.
    pcfg : dict
        Dictionary that includes config parameters that specify the write
        strategy. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    -

    """
    logging.info("Rearrange data for saving.")
    
    # create deepcopy
    data = _create_data_deepcopy(data)
    
    # if required rename FUEL set
    if pcfg["write_strategy"]["spreadsheet"]["fuel_rename"]:
        for s in data.keys():
            # iterate through parameters and sets
            for k,v in dcfg.items():
                # if param, process accordingly
                if v["type"] == "param":
                    if "FUEL" in v["indices"]:
                        data[s][k].index = data[s][k].index.rename([s if s!="FUEL"
                                                                else "COMMODITY"
                                                                for s
                                                                in data[s][k].index.names])
            # adjust set name
            data[s]["COMMODITY"] = data[s].pop("FUEL")
        
        # adjust config file
        for k,v in dcfg.items():
            if dcfg[k]["type"]=="param":
                dcfg[k]["indices"] =  [i if i!="FUEL" else "COMMODITY" 
                                      for i in dcfg[k]["indices"]]
        dcfg["COMMODITY"] = dcfg.pop("FUEL")
        
        
    # rearrange data and save a spreadsheet file for each model and scenario
    for s in data.keys():
        for k,v in dcfg.items():
            
            # rearrange params indexed over YEAR in line with UI input files
            if ((v["type"] == "param")
                and "YEAR" in v["indices"]
                and (len(v["indices"])>2)):
                data[s][k] = data[s][k].unstack("YEAR").droplevel(level=0,axis=1)
                
   
         
        logging.info(f"Writing data for scenario {s} to spreadsheet file.")
        

        with pd.ExcelWriter(os.path.join(path,"input_data_"+s+".xlsx")) as writer:
            # iterate through parameters and sets
            for k,v in dcfg.items():
                if k not in data[s].keys():
                    logging.warning(f"Data for parameter {k} for scenario {s} "
                                    "are not available and, thus, not saved.")
                    continue
                if "short_name" in v.keys():
                    n = v["short_name"]
                else:
                    n = k   
                if v["type"]=="set":
                    data[s][k].to_excel(writer, sheet_name=n,
                                        merge_cells=False,index=False)
                else:
                    data[s][k].to_excel(writer,
                                        merge_cells=False,
                                        sheet_name=n)
    return



def run_model(data, pcfg, dcfg):
    """ Run the model.
    
    Parameters
    ----------
    data : dict,str
        Data dictionary with one or more scenarios.
        Path to directory with model data files to run (all .txt files are
        are assumed to be datafiles), or filepath for single datafile (not yet
        implemented).
    pcfg : dict
        Dictionary that includes config parameters that specify the run
        configuration. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    data : dict of dicts
        Dictionary with a dictionary of DataFrames with parameters and set for
        each scenario.

    """


        
    if not os.path.exists(pcfg["run"]["results_dir"]):
        os.makedirs(pcfg["run"]["results_dir"])
      
    # FIXME: could add option to run scenarios from existing datafiles
    # if isinstance(data,str):
    # # get data files path
    #     if not os.path.exists(data):
    #         raise FileNotFoundError("Directory/file does not exist.")
    #     if os.path.isfile(data):
    #         if not data.endswith(".txt"):
    #             raise ValueError("File extension is not recognized.")                     
    #         data = [os.path.basename(data)]
    #         path = os.path.dirname(data)
    #     else:
    #         data = os.listdir(data)
    #         data = [f for f in data if f.endswith(".txt")]

    
    for s in pcfg["run"]["scenarios"]:
        
        logging.info(f"Running model for scenario {s}.")
        
        if s not in data.keys():
            logging.warning(f"Data for scenario {s} are not provided and, "
                            "thus, the scenario cannot be run.")
            continue
        
        
        filep = (pcfg["run"]["results_dir"]
                 +pcfg["run"]["run_id"]+"/"
                 +s)
        
        if not os.path.exists(filep):
            os.makedirs(filep)
            
        write_datafile({s:data[s]}, filep, pcfg, dcfg)
        
        
        # FIXME: this can be extended to allow for the use of other solvers
        if pcfg["run"]["solver"] == "cbc":
            subprocess.run([pcfg["run"]["glpk_dir"]+"glpsol",
                            "-m", pcfg["run"]["model_file"],
                            "-d", filep+"/"+"datafile_"+s+".txt",
                            "--wlp","opt.lp",
                            "--check"],
                            cwd=pcfg["run"]["solver_cwd"]
                            )
            subprocess.run(["cbc","opt.lp","solve","-solu","solution.sol",
                            #"-cross","off",
                            "-dualB","1.0e5",
                            "-dualT","1.0e-5",
                            "-primalT","1.0e-5"
                            ],
                            cwd=pcfg["run"]["solver_cwd"]
                            )
            
            
            otoole.convert_results(pcfg["model_files"]["data_config"], "cbc", "csv",
                                   pcfg["run"]["solver_cwd"]+"solution.sol",
                                   filep+"/"+"csv",
                                   "datafile",
                                   filep+"/"+"datafile_"+s+".txt")
        elif pcfg["run"]["solver"] == "highs":
            
            if highspy is None:
                logging.warning("The highs solver is not installed. The model"
                             " will not be solved. Install highs or choose a"
                             " different solver.")
                return False
            
            subprocess.run([pcfg["run"]["glpk_dir"]+"glpsol",
                            "-m", pcfg["run"]["model_file"],
                            "-d", filep+"/"+"datafile_"+s+".txt",
                            "--wlp","opt.lp",
                            "--check"],
                            cwd=pcfg["run"]["solver_cwd"]
                            )
            
            h = highspy.Highs()
            filename = pcfg["run"]["solver_cwd"]+"opt.lp"
            h.readModel(filename)
            h.run()
            h.writeSolution(pcfg["run"]["solver_cwd"]+"solution.sol",1)
            
            del h
            
            df = pd.read_csv(
                pcfg["run"]["solver_cwd"]+"solution.sol",
                header=None,
                sep='(',
                #sep="(",
                names=["valuevar","index"],
                skiprows=2,
            )  # type: pd.DataFrame
            
            df = df.dropna()
   
            df["VARIABLE"] = (
                df["valuevar"]
                .astype(str)
                .str.replace(r"^\*\*", "", regex=True)
                .str.split(expand=True)[6]
            )
            df["VALUE"] = (
                df["valuevar"]
                .astype(str)
                .str.replace(r"^\*\*", "", regex=True)
                .str.split(expand=True)[4]
            )
            df["DUAL"] = (
                df["valuevar"]
                .astype(str)
                .str.replace(r"^\*\*", "", regex=True)
                .str.split(expand=True)[5]
            )
            df["INDEX"] = (
                df["index"]
                .astype(str)
                .str.replace(r"\)|'", "",regex=True)
            )
            df = df.drop(columns=["valuevar","index"])
            
            
            var = ["RateOfActivity","NewCapacity","TotalCapacityAnnual",
                   "Demand.csv","AnnualEmissions"]
            dual = ["RateOfActivity","NewCapacity","TotalCapacityAnnual",
                   "Demand.csv","AnnualEmissions",
                   "EBb4_EnergyBalanceEachYear4_ICR",
                   "EBa10_EnergyBalanceEachTS4",
                   "EBa11_EnergyBalanceEachTS5",
                   "EBa9_EnergyBalanceEachTS3",
                   "EBb4_EnergyBalanceEachYear4"
                   ]
            # with open(CFP_c, "r") as file:
            #     cfg = yaml.safe_load(file)
                
            for v in var:
                d = df.loc[df["VARIABLE"]==v,["INDEX","VALUE"]]
                if d.empty:
                    continue
                d.index = pd.MultiIndex.from_tuples(d["INDEX"].str.split(","))
                d = d.drop(columns=["INDEX"])
                
                if v in dcfg.keys():
                    d.index.names = dcfg[v]["indices"]
                    
                d.to_csv(filep+"/"+"csv/"+v+".csv")
                
            for v in dual:
                d = df.loc[df["VARIABLE"]==v,["INDEX","DUAL"]]
                if d.empty:
                    continue
                d = d.rename(columns={"DUAL":"VALUE"})
                d.index = pd.MultiIndex.from_tuples(d["INDEX"].str.split(","))
                d = d.drop(columns=["INDEX"])
                
                if v in dcfg.keys():
                    d.index.names = dcfg[v]["indices"]
                # FIXME: currently causing issues, this needs fixing    
                # d.to_csv(filep+"/"+"csv/"+v+"_dual.csv")
                # df.to_csv(filep+"/"+"csv/"+"all_dual.csv")

        logging.info(f"Solved model for scenario {s}.")   


    
    logging.info("Completed process.")
    
    return True

def save_results(results, pcfg, dcfg):
    """ Save run results.
    
    Parameters
    ----------
    results : dict of dicts
        Dictionary with a dictionary of DataFrames with results for
        each scenario.
    pcfg : dict
        Dictionary that includes config parameters that specify the run
        configuration. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).


    Returns
    -------
    None

    """
    
    logging.info("Saving results.")
    
    
    for s in pcfg["run"]["scenarios"]:
        
        filep = (pcfg["run"]["results_dir"]
                 +pcfg["run"]["run_id"]+"/"
                 +s+"/csv/")
        
        
        if not os.path.exists(filep):
            os.makedirs(filep)
    
        for k,df in results[s].items():
            
            if df.empty:
                continue
            
            df.to_csv(filep+k+".csv")
                
    logging.info("Saved results.") 
       
    return

   
     

def load_results(pcfg, dcfg, data=None):
    """ Load run results.
    
    Parameters
    ----------
    pcfg : dict
        Dictionary that includes config parameters that specify the run
        configuration. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).
    data : dict, optional
        Model input data that will be added to results data if provided.

    Returns
    -------
    data : dict of dicts
        Dictionary with a dictionary of DataFrames with results for
        each scenario.

    """
    
    logging.info("Loading results.")
    
    results = dict()
    
    for s in pcfg["run"]["scenarios"]:
        
        results[s] = dict()
        
        filep = (pcfg["run"]["results_dir"]
                 +pcfg["run"]["run_id"]+"/"
                 +s)
        
        files = os.listdir(filep+"/csv/")
        
        for f in files:
            df = pd.read_csv(filep+"/csv/"+f)
            df = df.rename(columns={"r":"REGION",
                                    "t":"TECHNOLOGY",
                                    "y":"YEAR",
                                    "e":"EMISSION",
                                    "l" :"TIMESLICE",
                                    "m":"MODE_OF_OPERATION"})
            df.columns = [c for c in df.columns[:-1]]+["VALUE"]
            
            # strip ' in all str columns
            for c in df.columns:

                if df[c].dtype == "object":
                    df[c] = df[c].str.replace(r"\)|'", "",regex=True)
                    
            df = df.set_index([c for c in df.columns if c != "VALUE"])
            results[s][f.split(".")[0]] = df.copy()
            
        if data is not None:
            for k,v in data[s].items():
                results[s][k] = v.copy()
                
    logging.info("Loaded results.") 
       
    return results

def demap_multiscale_results(data, pcfg, dcfg):
    """ Rearrange multiscale results.
    
    Parameters
    ----------
    results : dict,
        Data dictionary with results data of one or more scenarios.
    pcfg : dict
        Dictionary that includes config parameters that specify the run
        configuration. See example config.yaml for details.
    dcfg : dict
        Dictionary that includes configuration of OSeMOSYS data (in the format
        used for otoole).

    Returns
    -------
    results : dict of dicts
        Data dictionary with processed results data of one or more scenarios.

    """
    
    if ft is None:
            logger.warning("Multi-scale functionality is not available as"
                           " the required dependency (fratoo)"
                           " is not available.")
            return False

    
    logging.info("Processing results for each scenario.")
    
    results = dict()
    mod = ft.Model()
    
    for s in data.keys():
        results[s] = mod._demap(data[s],sep=pcfg["write_strategy"]["datafile"]["region_sep"])
        
    logging.info("Created fratoo model(s).")
    
    return results


def expand_results(results):
    """ Adding additional results variables.
    
    Parameters
    ----------
    results : dict,
        Data dictionary with results data of one or more scenarios.

    Returns
    -------
    data : dict of dicts
        Dictionary with a dictionary of DataFrames with parameters and set for
        each scenario.

    """
    logging.info("Expanding results.")
    
    for s in results.keys():
        
        results[s]["ProductionByTechnologyAnnual"] = (
            results[s]["RateOfActivity"]
            *results[s]["OutputActivityRatio"]
            *results[s]["YearSplit"]).dropna().groupby(["REGION","TECHNOLOGY","FUEL","YEAR"]).sum()
        
        results[s]["TotalProductionByTechnologyAnnual"] = (
            results[s]["RateOfActivity"]
            *results[s]["OutputActivityRatio"]
            *results[s]["YearSplit"]).dropna().groupby(["REGION","TECHNOLOGY","YEAR"]).sum()
        
        results[s]["UseByTechnologyAnnual"] = (
            results[s]["RateOfActivity"]
            *results[s]["InputActivityRatio"]
            *results[s]["YearSplit"]).dropna().groupby(["REGION","TECHNOLOGY","FUEL","YEAR"]).sum()
        
        results[s]["AnnualEmissions"] = (
            results[s]["RateOfActivity"]
            *results[s]["EmissionActivityRatio"]
            *results[s]["YearSplit"]).dropna().groupby(["REGION","EMISSION","YEAR"]).sum()
        
        
        results[s]["CostInvestment"] = (results[s]["NewCapacity"]
                                           *results[s]["CapitalCost"]).dropna()
        # FIXME: this is just a simple estimate
        results[s]["CostCapital"] = (results[s]["TotalCapacityAnnual"]
                                           *results[s]["CapitalCost"]
                                           /results[s]["OperationalLife"]).dropna()
        results[s]["DiscountFactor"] = pd.concat([(1 + results[s]["DiscountRate"]["VALUE"]).pow(y - results[s]["YEAR"]["VALUE"].min() + 0.0) #.squeeze()
                                                     for y in results[s]["YEAR"]["VALUE"]],
                                               keys=results[s]["YEAR"]["VALUE"],
                                               names=["YEAR"]
                                                    ).to_frame()
        
        # results[s]["EBb4_EnergyBalanceEachYear4_ICR_dual"].index.names = ["REGION","FUEL","YEAR"]

        # results[s]["MarginalCost"] = (results[s]["EBb4_EnergyBalanceEachYear4_ICR_dual"]
        #                                    *results[s]["DiscountFactor"]).dropna()
        
        # results[s]["MarginalCost"].loc[results[s]["MarginalCost"]["VALUE"]>1000,
        #                                   "VALUE"] = pd.NA
        # results[s]["MarginalCost"] = results[s]["MarginalCost"].interpolate()
        
        # results[s]["CostperFuel"] = results[s]["MarginalCost"].copy()
        
    logging.info("Expanded results.")
    
    return results


         
def _create_data_deepcopy(data):
    
    d = dict()
    for s in data.keys():
        d[s] = dict()
        for k,v in data[s].items():
            d[s][k] = v.copy(deep=True)
            
    return d

