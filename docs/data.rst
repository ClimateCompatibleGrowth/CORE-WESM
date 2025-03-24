.. _data:

=======
Model input data
=======

The input data file for the disaggregation of the county model is the Kenya Whole Energy System Model `(WESM) <https://osemosys-kenya-wesm.readthedocs.io/en/latest/>`_. This a linear optimization model of Kenya's entire energy system developed using OSeMOSYS. It offers a detailed overview of the power and major energy-demanding sectors, including agriculture, commerce, industry, residential, and transportation.

Implementing the disaggregation of a national model, such as the WESM, to the county level needs specific county-level data across various sectors. A hierarchy of data sources is proposed, prioritized as follows:

   - **Source 1**: Existing data from county plans and administrations (highest priority).
   - **Source 2**: County-level datasets from national providers (e.g., population data from KNBS).
   - **Source 3**: National datasets downscaled to county level (lowest priority), to be used when higher sources are unavailable.

Model Disaggregation and Data Downscaling
==========================================

The following section summarizes the disaggregating process from a national to a county-level model and details how to run the associated Python scripts.

Overview
--------
The disaggregation and downscaling process involves three main steps:

- **Box A: National Model**
  - The national model is stored in an (*.xlsx) file containing all parameters, sets, and commodities representing the model at a national scale. This (*.xlsx) file is obtained by converting the WESM.txt into Excel Data called WESM.xlsx:

   .. code-block:: bash
      
      otoole convert datafile excel wesm.txt wesm.xlsx config.yaml

   Alternatively, the workflow provides a Python script that converts the data from a text file to an Excel file.

   .. code-block:: bash

      python onvert_national_model.py

- **Box B: Sector-specific Disaggregation**
  - The script ``to_sector.py`` processes the national model (WESM.xlsx) and disaggregates it into sector-specific Excel files.
  - **Outputs include:**
    - **Sectoral Files:** One file per sector (e.g., Agriculture.xlsx, Electricity.xlsx) with disaggregated data.
    - **Set.xlsx:** Consolidates set-related data.
    - **Emission.xlsx:** Contains emission-related data.
    - **Other.xlsx:** Stores data not fitting into specific sector mappings.

- **Box C: County-level Downscaling**
  - The script ``to_counties.py`` processes the sectoral model to generate county-level models.
  - **Key functions:**
    - Allocates residential demand using population data from ``counties_population_KNBS.csv``.
    - Scales sectors like agriculture and services using GDP data from ``GCP 2021_KNBS.csv``.
  - **Outputs include:**
    - **County Folders:** Each contains sector-specific data tailored to county characteristics.
    - **National Folder:** Updated with non-disaggregated data to maintain consistency.

Running the Python Files
------------------------
To execute the disaggregation and downscaling scripts, follow these steps:

1. **Clone the Repository:**

   .. code-block:: bash

      git clone https://github.com/lhofbauer/CORE-WESM.git

2. **Navigate to the Repository Directory:**

   .. code-block:: bash

      cd CORE-WESM

3. **Run the Sector-specific Disaggregation Script:**

   .. code-block:: bash

      python to_sector.py

4. **Run the County-level Downscaling Script:**

   .. code-block:: bash

      python to_counties.py

Additional Details
------------------
- The initial downscaling approach uses GDP and population metrics to create a national county model.
- Detailed county-level data, such as Gross County Product (GCP) by economic activity from KNBS, can further refine the model by capturing sector-specific contributions (e.g., comparing agriculture in Nairobi vs. Meru).



