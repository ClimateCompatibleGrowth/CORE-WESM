"""

Functions for processing downscaled model towards CORE-WESM dataset 


"""



import os
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


#%% Define util functions for dataset integration


def load_model(path):
    """ Load county model
    
    Parameters
    ----------
    path : str
        Path to folder with (unprocessed) county model to load.

    Raises
    ------
    FileExistsError
        Raised if model directory does not exist.

    Returns
    -------
    data : dict
        Model data.

    """
    
    # check if directory exists
    if not os.path.isdir(path):
        raise ValueError("Model directory does not exists or a file and not"
                         " a directory is provided.")
    
    # get list of all files
    files = [f for f in os.listdir(path) if f.endswith(".xlsx")]
    
    data = dict()
    
    for f in files:
        data[f] = pd.read_excel(path+f,sheet_name=None,
                                keep_default_na=False)

    return data

def save_model(path, data, overwrite=False):
    """ Save processed model

    Parameters
    ----------
    path : str
        Directory to save model to.
    data : dict
        Model data.
    overwrite : bool, optional
        If to overwrite if non-empty directory exists. The default is False.

    Returns
    -------
    None.

    """
    
    # check if directory exists, create if not
    if not os.path.exists(path):
        os.makedirs(path)
    # check if it exists and is non-empty, exit if the case and overwrite=False
    elif len(os.listdir(path)) != 0:
        if not overwrite:
            logger.warning("Model already exists and will not be overwritten."
                           " Set 'overwrite' to True to overwrite existing"
                           " models.")
            return True
        

    for k in data.keys():
        with pd.ExcelWriter(path+k, engine='openpyxl') as writer:
            for s in data[k].keys():
                data[k][s].to_excel(writer,merge_cells=False,
                            sheet_name=s, index=False)     

    logger.info("Saved updated data.")
    


#%% Define functions for the integration of county-resolved datasets


def cookstove_dataset(data,
                      list_counties,
                      housing_char,
                      housing_dem,
                      nat_scens,
                      el_access,
                      market_seg):
    """ Enhance cooking sector representation
    

    Parameters
    ----------
    data : dict
        Input data set to process.
    list_counties : str
        File path to list of counties.
    housing_char : str
        File path to data with housing characteristics.
    housing_dem : str
        File path to data with housing demographics.
    nat_scens : str
        Path to directory with national scenario data.
    el_access : str
        File path to data on electricity access.
    market_seg : str
        File path to data on clean cooking market segmentation.

    Returns
    -------
    dict
        Processed model input data set.

    """
    
    
    #%% helper functions
    def to_frac(df):
        df = df.divide(df.sum())
        return df
    def to_abs(df,total):
        df = df*total
        return df
   
    #%% load county data
    
    # load list of counties
    counties = pd.read_csv(list_counties,
                           keep_default_na=False)
    # load data tables
    cdf = pd.read_excel(housing_char,
                        sheet_name="Table 5.7",
                        skiprows=2,
                        usecols="A:S"
                        )

    cdf.columns = ['Geography',
                    'ELC001',
                    'ELC001',
                    'ELC001',
                    'ELC001',
                    'BGS001',
                    'LPG001',    
                    'ETH001',
                    'NA',
                    'BIO00X',
                    'BIO00X',
                    'CHC00X',
                    'BIO00X',
                    'BIO00X',
                    'BIO00X',
                    'KER001',
                    'NA',
                    'BIO00X',
                    'HH']
    
    cdf = cdf.set_index("Geography")
    cdf.columns.names = ["Stoves"]
    cdf = cdf.T.groupby("Stoves").sum()


    sdf = pd.read_excel(housing_char,
                        sheet_name="Table 5.8",
                        skiprows=1,
                        usecols="A:N"
                        )
    sdf.columns = ["Geography"] + list(sdf.columns[1:])
    sdf = sdf.set_index("Geography")
    sdf = sdf.T
    cdf.loc["BIO001",:] = cdf.loc["BIO00X",:]* (sdf.loc["Three stone stove/open fire",:]
                                                /(sdf.loc["Three stone stove/open fire",:]
                                                  +sdf.loc["Improved Firewood Jiko",:]))
    cdf.loc["BIO005",:] = cdf.loc["BIO00X",:]* (sdf.loc["Improved Firewood Jiko",:]
                                                /(sdf.loc["Three stone stove/open fire",:]
                                                  +sdf.loc["Improved Firewood Jiko",:]))
    cdf.loc["CHC001",:] = cdf.loc["CHC00X",:]* (sdf.loc["Ordinary Charcoal Jiko",:]
                                                /(sdf.loc["Ordinary Charcoal Jiko",:]
                                                  +sdf.loc["Improved Charcoal Jiko",:]))
    cdf.loc["CHC005",:] = cdf.loc["CHC00X",:]* (sdf.loc["Improved Charcoal Jiko",:]
                                                /(sdf.loc["Ordinary Charcoal Jiko",:]
                                                  +sdf.loc["Improved Charcoal Jiko",:])) 
    # load urban/rural fraction
    urdf = pd.read_excel(housing_dem,
                        sheet_name="Table 3.5",
                        skiprows=2,
                        usecols="A:D"
                        )
    urdf.columns = ["Geography","Rural","Urban","Total"]
    urdf = urdf.set_index("Geography")

    cdf = pd.concat([cdf,urdf.T])
    
    # estimate urban/rural fraction for each county
    for g in ["Urban","Rural"]:
        for s in ['BGS001','ELC001','ETH001','KER001','LPG001',
                  'BIO001','BIO005','CHC001','CHC005']:
        
            if g == "Urban":
                prefix = "RK1"
                oth = "Rural"
            else:
                prefix = "RK2"
                oth = "Urban"

            cdf.loc[prefix+s,:] = (cdf.loc[s,:]#*cdf.loc["Total",:]
                                   /(cdf.loc[g,:]+(cdf.loc[oth,:]
                                     *cdf.loc[s,oth]/
                                     cdf.loc[s,g]))
                                   )
            # Equations:
            #     rf = uf*f
            #     f = rf_t/uf_t
            #     tf*totalHH = uf * uHH + rf * rHH
            #     uf = (tf*totalHH)/(uHH+f*rHH)
            

    # clean up
    cdf = cdf.loc[[i for i in cdf.index if i.startswith("RK")]]
    cdf = cdf.rename(columns={"Nairobi City":"Nairobi",
                              "Homabay":"HomaBay",
                              "Taita-Taveta":"TaitaTaveta"})
    cdf.columns = cdf.columns.str.replace(" ","")       
    cdf = cdf.rename(columns=counties.loc[:,["ID","NAME"]].set_index("NAME")["ID"].to_dict())
    cdf = cdf.iloc[:,4:]
    cdf.index.names = ["TECHNOLOGY"]
    cdf.columns.names = ["REGION"]


    # calibrate to ensure percentages are adding up to one
    cdf.loc[cdf.index.str.startswith("RK1")] = cdf.loc[cdf.index.str.startswith("RK1")]/cdf.loc[cdf.index.str.startswith("RK1")].sum()
    cdf.loc[cdf.index.str.startswith("RK2")] = cdf.loc[cdf.index.str.startswith("RK2")]/cdf.loc[cdf.index.str.startswith("RK2")].sum()
    
    # rearrange dataframe
    cdf = cdf.stack()
    cdf = cdf.swaplevel()
    
    #%% load national data
    
    scenarios = ["S1","S2","S3","S4","S5"]
    
    # iterate through scenarios, processing data for each and adding to model
    # data
    for i,s in enumerate(scenarios):
        
        # get string for national data
        file = (nat_scens+"run"+str((i+1))
                +"/TotalTechnologyAnnualActivity.csv")# str((i+1))
        # load activity data for national scenario
        df = pd.read_csv(file)
        df = df.set_index(list(df.columns[:-1]))
        
        # filter for cooking techs
        df = df.loc[df.index.get_level_values("t").str.contains("RK1|RK2")]
        
        # rearrange dataframe
        df = df.unstack(fill_value=0).droplevel(level=0,axis=1)
        df = df.droplevel(level=0)
        df.index.names = ["TECHNOLOGY"]
        
        # split in urban and rural, calculate and save national totals
        nru = df.loc[df.index.get_level_values("TECHNOLOGY").str.contains("RK2")]
        nur = df.loc[df.index.get_level_values("TECHNOLOGY").str.contains("RK1")]
        nru = to_frac(nru)
        nur = to_frac(nur)
        
        # calculate and save county totals (demand)
        df = None
        for k in data.keys():
            if "SpecifiedAnnualDemand" in data[k].keys():
                if df is None:
                    df = data[k]["SpecifiedAnnualDemand"]
                else:
                    df = pd.concat([df,data[k]["SpecifiedAnnualDemand"]])
                    
        # FIXME: integrate choosing scenarios once used
        df = df.drop(["MODEL","SCENARIO","PARAMETER"],axis=1)
        df = df.loc[df["COMMODITY"].str.startswith("DEMRK")]
        ct = df.set_index(["REGION","COMMODITY"])
                
    
        # extend to county dataframe
        cru = pd.concat([nru]*len(counties["ID"]),
                        keys=list(counties["ID"]),
                        names=["REGION"])
        cur = pd.concat([nur]*len(counties["ID"]),
                        keys=list(counties["ID"]),
                        names=["REGION"])  
        
        # calculate absolut numbers
        crut = cru*ct.xs("DEMRK2",level="COMMODITY")
        curt = cur*ct.xs("DEMRK1",level="COMMODITY")

    
    #%% integrate county baseline data
    
        # apply to dataset
        baseyears = [2019,2020,2021,2022,2023,2024]
        for by in baseyears:
            cru.loc[:,by] = cdf
            cur.loc[:,by] = cdf
        cru = cru.fillna(0)
        cur = cur.fillna(0)


    #%% adjust pathway based on county baseline
    
        years = [2024,2030,2050]
        
        for ii in range(1,len(years)):
            
            ### rural calc
            
            # calc national totals per tech
            nrutt = to_abs(nru,ct.xs("DEMRK2",level="COMMODITY").sum())
            # overwrite with previous fractions
            cru.loc[:,years[ii]] = cru.loc[:,years[ii-1]] 
            
            # get rural county totals per tech
            crut = cru*ct.xs("DEMRK2",level="COMMODITY")
            
            # get national change with regard to baseyear
            diff = nrutt- crut.groupby("TECHNOLOGY").sum()
            
            # get techs that are phased down
            po_tech = diff.loc[diff[years[ii]]<0].index.to_list()
            

            # calc fraction of tech use in county with respect to total 
            # national use of tech (for techs being phased out)
            dedf = crut.loc[crut.index.get_level_values("TECHNOLOGY").isin(po_tech)]/crut.loc[crut.index.get_level_values("TECHNOLOGY").isin(po_tech)].groupby("TECHNOLOGY").sum()
            
            
            fr1 = crut.loc[crut.index.get_level_values("TECHNOLOGY").isin(po_tech)].groupby("REGION").sum()/crut.loc[crut.index.get_level_values("TECHNOLOGY").isin(po_tech)].sum()
           
            # get dataframe with difference copied across counties
            diffc = pd.concat([diff]*len(fr1),
                              names=["REGION"],
                              keys= fr1.index)
            # calculate fraction of additions (equals substractions per county)
            ded = dedf*diffc.loc[diffc.index.get_level_values("TECHNOLOGY").isin(po_tech)]
            addf = ded.groupby("REGION").sum()/ded.sum()
            add = addf*diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech)]
            
            ### adjusting addition to match local circumstances
            # load datasets shaping prioritization
            ela = pd.read_csv(el_access,
                              usecols=[2,4,5,6,7],
                              index_col=[0],
                              keep_default_na=False
                              )
            ela.index.names = ["REGION"]
            ela.columns = ela.columns.astype(int)
            
            ms = pd.read_csv(market_seg,
                              usecols=[3,4,5,6,7,8],
                              index_col=[0],
                              keep_default_na=False
                              )
            ms.loc[:,years[ii]] = (ms.loc[:,"Q4"]/(ms.loc[:,"Q3"]+ms.loc[:,"Q4"])).fillna(0)
            cf = cru.loc[cru.index.get_level_values("TECHNOLOGY").str.contains("ELC|LPG|BGS")].groupby("REGION").sum()
            
            ms.loc[:,years[ii]] = cf.loc[:,2019]+(1-cf.loc[:,2019])*ms.loc[:,years[ii]]
            ms.index.names = ["REGION"]
            ela = ela.mul(ms.loc[:,years[ii]],axis=0)
            ela = ela/ela.sum()
            
            prio = diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech),years[ii]]
            prio = prio.reset_index()
            
            prio = prio.merge(right= ela[years[ii]],
                                     on="REGION",
                                     how="left",
                                     suffixes=("","_ELC")
                                     )
            #bio = (crut.xs("RK2BIO001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            bio = (cru.xs("RK2BIO001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            bio = bio/bio.sum()
                   
            bio.name = str(years[ii])
            prio = prio.merge(right=bio ,
                              on="REGION",
                              how="left",
                              suffixes=("","_BIO005")
                              )
            #chc = (crut.xs("RK2CHC001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            chc = (cru.xs("RK2CHC001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            chc = chc/chc.sum()
            chc.name = str(years[ii])
            prio = prio.merge(right= chc,
                                     on="REGION",
                                     how="left",
                                     suffixes=("","_CHC005")
                                     )
            oth = ms.loc[:,years[ii]]
            oth = oth/oth.sum()
            oth.name = str(years[ii])
            prio = prio.merge(right= oth,
                                     on="REGION",
                                     how="left",
                                     suffixes=("","_OTH")
                                     )
            prio = prio.set_index(["REGION","TECHNOLOGY"])
            prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("ELC"),str(years[ii])] = prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("ELC"),str(years[ii])+"_ELC"]
            prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("BIO005"),str(years[ii])] = prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("BIO005"),str(years[ii])+"_BIO005"]
            prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005"),str(years[ii])] = prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005"),str(years[ii])+"_CHC005"]
            prio.loc[~prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005|BIO005|ELC"),str(years[ii])] = prio.loc[~prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005|BIO005|ELC"),str(years[ii])+"_OTH"]
            
            prio = prio.loc[:,str(years[ii])]
                                  
            prio = prio/prio.groupby("TECHNOLOGY").sum()
            

            # calculate allocation based on per county percentage and totals
            prio = prio*diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech),years[ii]]
            # calculate county fractions
            prio = prio/prio.groupby("REGION").sum()
            prio.name= years[ii]
            
            add_target = prio.to_frame()*addf*diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech)].groupby("REGION").sum()
            # add_target.groupby("TECHNOLOGY").sum()

            # calculate difference to national change that needs to be matched
            diff_adj = add.groupby("TECHNOLOGY").sum()-add_target.groupby("TECHNOLOGY").sum()
            
            # get techs that are phased down
            po_tech_adj = diff_adj.loc[diff_adj[years[ii]]<0].index.to_list()
            
            if len(po_tech_adj) > 0:
                dedf = add_target.loc[add_target.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)]/add_target.loc[add_target.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)].groupby("TECHNOLOGY").sum()
                
                # get dataframe with difference copied across counties
                diffc_adj = pd.concat([diff_adj]*len(fr1),
                                      names=["REGION"],
                                      keys= fr1.index)
                
                # calculate fraction of additions (equals substractions per county)
                ded_adj = dedf*diffc_adj.loc[diffc_adj.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)]
                addf = ded_adj.groupby("REGION").sum()/ded_adj.sum()
                
                add_adj = addf*diffc_adj.loc[~diffc_adj.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)]
                
                # adjust additions based on calculated prio while ensuring
                # county totals and national tech fractions are followed
                add = (add_target+pd.concat([add_adj,ded_adj])).clip(0)
            else:
                add = add_target

            # add/substract and overwrite with actual dataframe
            crut_ = (crut+pd.concat([add,ded])).clip(0)
            cru_ = crut_/crut_.groupby("REGION").sum()
            cru.loc[:,years[ii]] = cru_.loc[:,years[ii]]
            
            ### urban calc
            
            # calc national totals per tech
            nurtt = to_abs(nur,ct.xs("DEMRK1",level="COMMODITY").sum())
            # overwrite with previous fractions
            cur.loc[:,years[ii]] = cur.loc[:,years[ii-1]] 
            
            # get urban county totals per tech
            curt = cur*ct.xs("DEMRK1",level="COMMODITY")
            
            # get national change with regard to baseyear
            diff = nurtt- curt.groupby("TECHNOLOGY").sum()
            
            # get techs that are phased down
            po_tech = diff.loc[diff[years[ii]]<0].index.to_list()
            

            # calc fraction of tech use in county with respect to total 
            # national use of tech (for techs being phased out)
            dedf = curt.loc[curt.index.get_level_values("TECHNOLOGY").isin(po_tech)]/curt.loc[curt.index.get_level_values("TECHNOLOGY").isin(po_tech)].groupby("TECHNOLOGY").sum()
            
            fr1 = curt.loc[curt.index.get_level_values("TECHNOLOGY").isin(po_tech)].groupby("REGION").sum()/curt.loc[curt.index.get_level_values("TECHNOLOGY").isin(po_tech)].sum()
           
            # get dataframe with difference copied across counties
            diffc = pd.concat([diff]*len(fr1),
                              names=["REGION"],
                              keys= fr1.index)
            # calculate fraction of additions (equals substractions per county)
            ded = dedf*diffc.loc[diffc.index.get_level_values("TECHNOLOGY").isin(po_tech)]
            addf = ded.groupby("REGION").sum()/ded.sum()
            
            add = addf*diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech)]
            
            ### adjusting addition to match local circumstances
            
            # load datasets shaping prioritization
            ela = pd.read_csv(el_access,
                              usecols=[2,4,5,6,7],
                              index_col=[0],
                              keep_default_na=False
                              )
            ela.index.names = ["REGION"]
            ela.columns = ela.columns.astype(int)
            
            ms = pd.read_csv(market_seg,
                              usecols=[3,4,5,6,7,8],
                              index_col=[0],
                              keep_default_na=False
                              )
            ms.loc[:,years[ii]] = ms.loc[:,"Q2"]/(ms.loc[:,"Q1"]+ms.loc[:,"Q2"])
            cf = cur.loc[cur.index.get_level_values("TECHNOLOGY").str.contains("ELC|LPG|BGS")].groupby("REGION").sum()
            
            ms.loc[:,years[ii]] = cf.loc[:,2019]+(1-cf.loc[:,2019])*ms.loc[:,years[ii]]
            ms.index.names = ["REGION"]
            ela = ela.mul(ms.loc[:,years[ii]],axis=0)
            ela = ela/ela.sum()
            
            prio = diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech),years[ii]]
            prio = prio.reset_index()
            
            
            prio = prio.merge(right= ela[years[ii]],
                                     on="REGION",
                                     how="left",
                                     suffixes=("","_ELC")
                                     )
            #bio = (curt.xs("RK1BIO001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            bio = (cur.xs("RK1BIO001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            bio = bio/bio.sum()
            bio.name = str(years[ii])
            prio = prio.merge(right=bio ,
                              on="REGION",
                              how="left",
                              suffixes=("","_BIO005")
                              )
            #chc = (curt.xs("RK1CHC001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            chc = (cur.xs("RK1CHC001",level="TECHNOLOGY")[years[ii-1]]*(1- ms.loc[:,years[ii]]))
            chc = chc/chc.sum()
            chc.name = str(years[ii])
            prio = prio.merge(right= chc,
                                     on="REGION",
                                     how="left",
                                     suffixes=("","_CHC005")
                                     )
            oth = ms.loc[:,years[ii]]
            oth = oth/oth.sum()
            oth.name = str(years[ii])
            prio = prio.merge(right= oth,
                                     on="REGION",
                                     how="left",
                                     suffixes=("","_OTH")
                                     )
            prio = prio.set_index(["REGION","TECHNOLOGY"])
            prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("ELC"),str(years[ii])] = prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("ELC"),str(years[ii])+"_ELC"]
            prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("BIO005"),str(years[ii])] = prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("BIO005"),str(years[ii])+"_BIO005"]
            prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005"),str(years[ii])] = prio.loc[prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005"),str(years[ii])+"_CHC005"]
            prio.loc[~prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005|BIO005|ELC"),str(years[ii])] = prio.loc[~prio.index.get_level_values("TECHNOLOGY").str.contains("CHC005|BIO005|ELC"),str(years[ii])+"_OTH"]
            
            prio = prio.loc[:,str(years[ii])]
                                  
            prio = prio/prio.groupby("TECHNOLOGY").sum()

            # calculate allocation based on per county percentage and totals
            prio = prio*diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech),years[ii]]
            # calculate county fractions
            prio = prio/prio.groupby("REGION").sum()
            prio.name= years[ii]
            

            add_target = prio.to_frame()*addf*diffc.loc[~diffc.index.get_level_values("TECHNOLOGY").isin(po_tech)].groupby("REGION").sum()
            # add_target.groupby("TECHNOLOGY").sum()
            
            # calculate difference to national change that needs to be matched
            diff_adj = add.groupby("TECHNOLOGY").sum()-add_target.groupby("TECHNOLOGY").sum()
            
            # get techs that are phased down
            po_tech_adj = diff_adj.loc[diff_adj[years[ii]]<0].index.to_list()
            
            if len(po_tech_adj) > 0:
                dedf = add_target.loc[add_target.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)]/add_target.loc[add_target.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)].groupby("TECHNOLOGY").sum()
                
                # get dataframe with difference copied across counties
                diffc_adj = pd.concat([diff_adj]*len(fr1),
                                      names=["REGION"],
                                      keys= fr1.index)
                
                # calculate fraction of additions (equals substractions per county)
                ded_adj = dedf*diffc_adj.loc[diffc_adj.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)]
                addf = ded_adj.groupby("REGION").sum()/ded_adj.sum()
                
                add_adj = addf*diffc_adj.loc[~diffc_adj.index.get_level_values("TECHNOLOGY").isin(po_tech_adj)]
                
                # adjust additions based on calculated prio while ensuring
                # county totals and national tech fractions are followed
                add = (add_target+pd.concat([add_adj,ded_adj])).clip(0)
            else:
                add = add_target
            
            # add/substract and overwrite with actual dataframe
            curt_ = (curt+pd.concat([add,ded])).clip(0)
            cur_ = curt_/curt_.groupby("REGION").sum()
            cur.loc[:,years[ii]] = cur_.loc[:,years[ii]]
            
        # calculate totals  
        crut = cru*ct.xs("DEMRK2",level="COMMODITY")
        curt = cur*ct.xs("DEMRK1",level="COMMODITY")
    
    #%% replace selected years through interpolation
    
        iy = list(range(2025,2030))
        
        cru.loc[:,iy] = np.nan
        cru = cru.interpolate(axis=1)
        
        cur.loc[:,iy] = np.nan
        cur = cur.interpolate(axis=1)
        
        iy = list(range(2031,2050))
        
        cru.loc[:,iy] = np.nan
        cru = cru.interpolate(axis=1)
        
        cur.loc[:,iy] = np.nan
        cur = cur.interpolate(axis=1)


    #%% update model parameter and save
    
        # get absolute numbers
        crut = cru*ct.xs("DEMRK2",level="COMMODITY")
        curt = cur*ct.xs("DEMRK1",level="COMMODITY")
        
        # concat rural and urban, rearrange dataframe
        ow = pd.concat([crut,curt],
                       keys=[("#ALL",s,
                        "TotalTechnologyAnnualActivityLowerLimit")]
                        *(len(crut)+len(curt)),
                        names=["MODEL","SCENARIO","PARAMETER"])
    
        # add activity limits
        for k in data.keys():
            
            if "TotalTechnologyAnnualActivityLo" in data[k].keys():
                df = data[k]["TotalTechnologyAnnualActivityLo"]
                ind = ["MODEL",
                       "SCENARIO",
                       "PARAMETER",
                       "REGION",
                       "TECHNOLOGY"]
                df = df.set_index(ind)
                
                
                # FIXME: if structure of spreadsheet is changed (e.g., not all
                # county technologies together in one sheet), this might not
                # work
                cow = ow.loc[ow.index.get_level_values("REGION").isin(
                                df.index.get_level_values("REGION"))]            
                
                df = pd.concat([df,cow])
                
                # overwrite data
                data[k]["TotalTechnologyAnnualActivityLo"] = df.reset_index()
                
                # remove upper limit
                if "TotalTechnologyAnnualActivityUp" in data[k].keys():
                    dfu = data[k]["TotalTechnologyAnnualActivityUp"].set_index(ind)
                    # FIXME: just delete all cooking tech from limit?
                    fil = dfu.index.get_level_values("TECHNOLOGY").isin(crut.index.get_level_values("TECHNOLOGY").append(curt.index.get_level_values("TECHNOLOGY")))
                    dfu = dfu.loc[~fil,:]
                    
                    # overwrite data
                    data[k]["TotalTechnologyAnnualActivityUp"] = dfu.reset_index()
                
    return data
