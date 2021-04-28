import logging
from pathlib import Path
import glob
import pandas as pd
from src.defaults import PROJECT_DIR, plant_fuels


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

        installed_capacity_pj_y_wide.insert(1, "RegionName", self.folder)
        installed_capacity_pj_y_wide.insert(2, "Unit", "PJ/y")
        muse_installed_capacity = installed_capacity_pj_y_wide.rename(
            columns={"Technology": "ProcessName"}
        ).set_index("ProcessName")

        return muse_installed_capacity

    def convert_technoeconomic_power(self):
        logger = logging.getLogger(__name__)
        technoeconomic_data = self.raw_tables["Table2"]

        muse_technodata = pd.read_csv(
            PROJECT_DIR
            / Path("data/external/muse_data/default/technodata/power/Technodata.csv")
        )

        technoeconomic_data_wide = technoeconomic_data.pivot(
            index="Technology", columns="Parameter", values="Value"
        )
        self._insert_constant_columns(technoeconomic_data_wide, "energy", "Electricity")

        technoeconomic_data_wide = technoeconomic_data_wide.reset_index()
        technoeconomic_data_wide_named = technoeconomic_data_wide.rename(
            columns={
                "Average Capacity Factor": "UtilizationFactor",
                "Capital Cost ($/kW in 2020)": "cap_par",
                "Fixed Cost ($/kW/yr in 2020)": "fix_par",
                "Operational Life (years)": "TechnicalLife",
                "Technology": "ProcessName",
                "Efficiency ": "efficiency",
            }
        )

        technoeconomic_data_wide_named["Fuel"] = technoeconomic_data_wide_named[
            "ProcessName"
        ].map(plant_fuels)

        plants = list(pd.unique(technoeconomic_data_wide_named.ProcessName))

        plant_sizes = self._generate_scaling_size(plants)

        technoeconomic_data_wide_named["ScalingSize"] = technoeconomic_data_wide_named[
            "ProcessName"
        ].map(plant_sizes)

        technoeconomic_data_wide_named = technoeconomic_data_wide_named.apply(
            pd.to_numeric, errors="ignore"
        )

        projected_capex = self.raw_tables["Table3"]

        projected_capex = projected_capex.rename(
            columns={"Technology": "ProcessName", "Year": "Time", "Value": "cap_par"}
        )
        projected_capex = projected_capex.drop(columns="Parameter")

        projected_technoeconomic = pd.merge(
            technoeconomic_data_wide_named,
            projected_capex,
            on=["ProcessName", "Time"],
            how="right",
        )

        forwardfilled_projected_technoeconomic = self._fill_unknown_data(
            projected_technoeconomic
        )

        forwardfilled_projected_technoeconomic = forwardfilled_projected_technoeconomic.drop(
            columns="cap_par_x"
        )
        forwardfilled_projected_technoeconomic = forwardfilled_projected_technoeconomic.rename(
            columns={"cap_par_y": "cap_par"}
        )

        kw_columns = ["cap_par", "fix_par"]

        forwardfilled_projected_technoeconomic[kw_columns] *= 1000
        forwardfilled_projected_technoeconomic.reindex(muse_technodata.columns, axis=1)

        forwardfilled_projected_technoeconomic = muse_technodata[
            muse_technodata.ProcessName == "Unit"
        ].append(forwardfilled_projected_technoeconomic)

        logger.info(forwardfilled_projected_technoeconomic)

        return forwardfilled_projected_technoeconomic

    def _fill_unknown_data(self, projected_technoeconomic):
        backfilled_projected_technoeconomic = projected_technoeconomic.groupby(
            ["ProcessName"]
        ).apply(lambda group: group.fillna(method="bfill"))
        forwardfilled_projected_technoeconomic = backfilled_projected_technoeconomic.groupby(
            ["ProcessName"]
        ).apply(
            lambda group: group.fillna(method="ffill")
        )
        return forwardfilled_projected_technoeconomic

    def _insert_constant_columns(self, technoeconomic_data_wide, fuel_type, end_use):
        technoeconomic_data_wide["RegionName"] = self.folder
        technoeconomic_data_wide["Time"] = "2020"
        technoeconomic_data_wide["Level"] = "fixed"
        technoeconomic_data_wide["cap_exp"] = 1
        technoeconomic_data_wide["fix_exp"] = 1
        technoeconomic_data_wide["var_par"] = 0
        technoeconomic_data_wide["var_exp"] = 1
        technoeconomic_data_wide["Type"] = fuel_type
        technoeconomic_data_wide["EndUse"] = end_use
        technoeconomic_data_wide["Agent2"] = 1
        technoeconomic_data_wide["InterestRate"] = 0.1
        technoeconomic_data_wide["MaxCapacityAddition"] = 20
        technoeconomic_data_wide["MaxCapacityGrowth"] = 20
        technoeconomic_data_wide["TotalCapacityLimit"] = 20

    def _generate_scaling_size(self, plants):
        import re

        plant_sizes = {}
        for plant in plants:
            size = 1
            kw = False
            if "kW" in plant:
                kw = True
            if re.search(r"\d+", plant) is not None:
                size = float(re.search(r"\d+", plant).group())
                if kw:
                    size /= 1000
            plant_sizes[plant] = size
        return plant_sizes

