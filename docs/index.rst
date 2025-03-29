=========
CORE-WESM
=========

This is the documentation of the COunty-REsolved Whole Energy System Model for Kenya (**CORE-WESM**). The CORE-WESM is a whole energy system model of Kenya with a representation of each of Kenya's 47 counties.


Background
==========

The CORE-WESM has been developed to support the integration of county and national energy planning in Kenya in line with the Integrated National Energy Plan (INEP) development process. The model aims to support the integration of county energy plans (CEPs) and priorities into county-national integrated energy planning process. It does not intend to replace modelling to inform CEP development.

More information on the context and background to the model can be found in this `preprint`_.



Overarching approach and workflow
================================
The CORE-WESM is a county-disaggregated version of the open-source whole energy system model OSeMOSYS-Kenya. OSeMOSYS-Kenya is a linear optimization model built using the open-source modelling framework OSeMOSYS. The development and application of the CORE-WESM model is based on a workflow with two overarching steps:


#. The creation of a county-resolved model input data set based on the disaggregation of OSeMOSYS-Kenya and inclusion of different county-level data.
#. The flexible application of the county-resolved model through an multi-scale modelling framework wrapped around the OSeMOSYS framework.

Both steps are explained in more detail on the respective pages of the documentation linked in the navigation panel on the left and below.


.. warning::
   The current CORE-WESM version can be considered a minimal viable product (MVP) with several limitations. Further development of the model for policy applications is envisaged.


Related material
================

* Both OSeMOSYS-Kenya and CORE-WESM are based on the **OSeMOSYS framework**. More information on OSeMOSYS can be found on its  `GitHub repository <https://github.com/OSeMOSYS/OSeMOSYS>`_ and `documentation <https://osemosys.readthedocs.io/en/latest/index.html>`_. 
* CORE-WESM is a county-resolved version of the **OSeMOSYS-Kenya WESM**. More information on OSeMOSYS-Kenya can be found on its  `GitHub repository <https://github.com/ClimateCompatibleGrowth/osemosys_kenya_wesm>`_ and `documentation <https://osemosys-kenya-wesm.readthedocs.io/en/latest/>`_.  
* The multi-scale functionality of the CORE-WESM is based on the **fratoo** framework. More information on fratoo can be found on its  `GitHub repository <https://github.com/>`_ and `documentation <https://www.readthedocs.io/>`_. 


Contents
========

.. toctree::
   :maxdepth: 2

   Input data creation <data>
   Model application <model>
   Contributions & Help <contributing>
   License <license>
   Authors <authors>
   Changelog <changelog>
   Module Reference <api/modules>




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



Acknowledgements
================

This material has been produced with support from the UK Partnering for Accelerated Climate Transitions (UK PACT) programme and the Climate Compatible Growth (CCG) programme. UK PACT and CCG are funded by UK Aid from the UK Government. Views expressed herein do not necessarily reflect the UK government's official policies.



.. _toctree: https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html
.. _reStructuredText: https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html
.. _references: https://www.sphinx-doc.org/en/stable/markup/inline.html
.. _Python domain syntax: https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#the-python-domain
.. _Sphinx: https://www.sphinx-doc.org/
.. _Python: https://docs.python.org/
.. _Numpy: https://numpy.org/doc/stable
.. _SciPy: https://docs.scipy.org/doc/scipy/reference/
.. _matplotlib: https://matplotlib.org/contents.html#
.. _Pandas: https://pandas.pydata.org/pandas-docs/stable
.. _Scikit-Learn: https://scikit-learn.org/stable
.. _autodoc: https://www.sphinx-doc.org/en/master/ext/autodoc.html
.. _Google style: https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings
.. _NumPy style: https://numpydoc.readthedocs.io/en/latest/format.html
.. _classical style: https://www.sphinx-doc.org/en/master/domains.html#info-field-lists
.. _wesm docs : https://osemosys-kenya-wesm.readthedocs.io/en/latest/
.. _wesm github : https://github.com/ClimateCompatibleGrowth/osemosys_kenya_wesm
.. _preprint : https://zenodo.org/
