.. _installation:

============
Installation
============

To download and set up the CORE-WESM model workflow, the following steps need to be followed:


1. **Clone the repository:**

   .. code-block:: bash

      git clone https://github.com/lhofbauer/CORE-WESM.git

2. **Navigate to the repository directory:**

   .. code-block:: bash

      cd CORE-WESM

3. **Create and activate the conda environment:**

   .. code-block:: bash

      conda update conda

      conda env create -f environment.yaml

      conda activate corewesm

4. **Install solvers following instructions on the relevant websites. The workflow script currently works with the** `HiGHS <https://highs.dev/>`_  **and** `cbc <https://github.com/coin-or/Cbc#DownloadandInstall>`_ **solvers**.


