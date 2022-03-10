CCG Starter Kits to MUSE input files
====================================

The MUSE data can be generated with the following command in the root directory:
```
make data start_year=2020 end_year=2055 milestone_year=5
```

You may need to add python to your path to run the make command above. This can be done by running the following on mac or linux:
```
 export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

The variables `start_year`, `end_year` and `milestone_year` are customisable to your requirements. However, only the parameters used above have been fully tested.

This command will take the starter kits data from:
```
data/raw/starter-kits/*
```

And produce the data in a MUSE friendly format at:
```
data/processed/starter-kits/*
```

There are a few editable files which you can adjust for your case study.

For instance, if you know the exogenous electricity demand for your country of interest, you have to edit the `demand.csv` file in `data/interim/electricity_demand/demand.csv`.

This will then generate the preset sector files. If you do not know the exogenous electricity demand in your case, we assume that the demand is the same as for Kenya for every country not in the the `demand.csv` file. Please note that it is highly recommended that you find realistic demands for your country.

Finally, if you have technologies that can only meet a certain percentage of demand, you must edit the `proportion_technology_demand.csv` file in `data/interim/maximum_capacity/proportion_technology_demand.csv`. However, this will only work if you have created the `demand.csv` file for your country.


Project Organization
------------

    ├── LICENSE
    ├── Makefile           <- Makefile to generate the data
    ├── README.md          <- The top-level README for developers using this project.
    ├── data
    │   ├── external       <- Data from third party sources.
    │   ├── interim        <- Intermediate data that has been transformed.
    │   ├── processed      <- The final, canonical data sets for modeling.
    │   └── raw            <- The original raw data.
    ├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
    │   └── figures        <- Generated graphics and figures to be used in reporting
    ├── requirements.txt   <- The requirements file for reproducing the analysis
    ├── src                <- Source code for use in this project.
    │   └── __init__.py    <- Makes src a Python module


--------

