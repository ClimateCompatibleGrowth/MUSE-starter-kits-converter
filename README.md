CCG Starter Kits to MUSE input files
====================================

The MUSE data can be generated with the following command in the root directory:
```
make data start_year=2020 end_year=2055 milestone_year=5
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

This will then generate the preset sector files.

Finally, if you have technologies that can only meet a certain percentage of demand, you must edit the `proportion_technology_demand.csv` file in `data/interim/maximum_capacity/proportion_technology_demand.csv`. However, this will only work if you have created the `demand.csv` file for your country.


Project Organization
------------

    ├── LICENSE
    ├── Makefile           <- Makefile with commands like `make data`
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
    │   
    └── data           <- Scripts to download or generate data
           └── make_dataset.py


--------

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
