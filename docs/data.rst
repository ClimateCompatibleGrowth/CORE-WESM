.. _data:

================
Model input data
================

CORE-WESM follows a hierarchical approach to data sourcing. The approach allows for the generation of a complete model, despite limited data availability, as the basis for further development as part of the INEP process as and when further energy plans and data become available. CORE-WESM builds on three different types of input data sources:

   - **Source 1**: Data from county plans and administrations (highest priority).
   - **Source 2**: County-resolved datasets from national data providers.
   - **Source 3**: Downscaled national data where other data are not available (lowest priority).

The workflow itself starts with the lowest priority data (downscaled data), which are replaced or adjusted if other data are available. The three different data sources are explained in the following sections. More detail is also provided in the `scoping report`_ and `preprint2`. Source for all raw input data are provided in the `GitHub repository <https://github.com/ClimateCompatibleGrowth/CORE-WESM/blob/master/data/raw/SOURCES.txt>`_.


Downscaled data (Source 3)
==========================

The base (Source 3) dataset underlying CORE-WESM is a downscaled version of an input dataset of the  `OSeMOSYS Kenya whole energy system model <https://osemosys-kenya-wesm.readthedocs.io/en/latest/>`_. The dataset is downscaled by applying relevant proxies for each of the downscaled sectors to scale the relevant parameters for each county. For the residential sector, this uses population data as well as urbanization, for all other sectors it uses the respective sectoral gross county product as provided by Kenya National Bureau of Statistics (KNBS).

County-resolved (Source 2) and county-specific data (Source 1)
==============================================================

County-resolved and county-specific data are used to replace or adjust downscaled data where available. Currently, county-resolved datasets for the cooking sector are integrated for a more detailed representation of the sector. This can be extended as other data become available and as analyses require.

