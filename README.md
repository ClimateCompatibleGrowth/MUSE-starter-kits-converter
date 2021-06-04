CCG Starter Kits to MUSE input files
====================================

The MUSE data can be generated with the following command in the root directory:
```
make data start_year=2020 end_year=2050 milestone_year=5
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
    ├── models             <- Trained and serialized models, model predictions, or model summaries
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
