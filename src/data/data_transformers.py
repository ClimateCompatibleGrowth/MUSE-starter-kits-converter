import logging
from pathlib import Path
import glob
import pandas as pd
from src.defaults import PROJECT_DIR


class Transformer:
    def __init__(self, input_path, output_path, start_year, end_year, benchmark_years):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.start_year = int(start_year)
        self.end_year = int(end_year)
        self.benchmark_years = int(benchmark_years)

        self.folder = str(self.input_path).split("/")[-1]
        self.raw_tables = self.get_raw_data()

    def create_muse_dataset(self):
        logger = logging.getLogger(__name__)
        logger.info("Converting raw data for {}.".format(self.folder))

        muse_data = {}

        muse_data["existing_plants"] = self.convert_installed_power_plants()
        muse_data["technoeconomic_power"] = self.convert_technoeconomic_power()

    def get_raw_data(self):
        table_directories = glob.glob(str(self.input_path / Path("*.csv")))

        tables = {}
        for table_directory in table_directories:
            table_name = table_directory.split("/")[-1].split("_")[0]
            tables[table_name] = pd.read_csv(table_directory)

        return tables

    def convert_installed_power_plants(self):
        logger = logging.getLogger(__name__)
        installed_capacity = self.raw_tables["Table1"]
        installed_capacity = installed_capacity.rename(
            columns={"Power Generation Technology": "Technology"}
        )
        latest_installed_capacity = installed_capacity[
            installed_capacity.Year == installed_capacity["Year"].max()
        ]

        technoeconomics = self.raw_tables["Table2"]

        installed_capacity_cf = latest_installed_capacity.merge(
            technoeconomics[technoeconomics.Parameter == "Average Capacity Factor"],
            on="Technology",
        )
        installed_capacity_cf = installed_capacity_cf.rename(
            columns={
                "Value_y": "average_capacity_factor",
                "Value_x": "estimated_installed_capacity_MW",
            }
        )
        installed_capacity_cf = installed_capacity_cf.drop(
            columns=["Parameter_y", "Parameter_x"]
        )

        installed_capacity_cf["estimated_installed_capacity_PJ_y"] = (
            installed_capacity_cf.estimated_installed_capacity_MW
            * 365
            * installed_capacity_cf.average_capacity_factor
        )

        installed_capacity_pj_y = installed_capacity_cf.drop(
            columns=["estimated_installed_capacity_MW", "average_capacity_factor"]
        )

        installed_capacity_pj_y_wide = installed_capacity_pj_y.pivot(
            index="Technology",
            columns="Year",
            values="estimated_installed_capacity_PJ_y",
        ).reset_index()

        unknown_cols = list(
            range(
                self.start_year + self.benchmark_years,
                self.end_year + self.benchmark_years,
                self.benchmark_years,
            )
        )
        for col in unknown_cols:
            installed_capacity_pj_y_wide[col] = 0

        installed_capacity_pj_y_wide.insert(1, "RegionName", "R1")
        installed_capacity_pj_y_wide.insert(2, "Unit", "PJ/y")
        muse_installed_capacity = installed_capacity_pj_y_wide.rename(
            columns={"Technology": "ProcessName"}
        ).set_index("ProcessName")

        return muse_installed_capacity

    def convert_technoeconomic_power(self):
        logger = logging.getLogger(__name__)
        technoeconomic_data = self.raw_tables["Table2"]

