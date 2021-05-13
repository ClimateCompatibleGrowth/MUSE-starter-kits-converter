import logging
from pathlib import Path
import glob
import pandas as pd
from src.defaults import PROJECT_DIR, plant_fuels, units


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

        muse_data["power"] = {"ExistingCapacity": self.create_existing_capacity_power()}
        muse_data["power"]["Technodata"] = self.convert_power_technodata()
        muse_data["power"]["CommIn"] = self.get_comm_in(
            technodata=muse_data["power"]["Technodata"]
        )
        muse_data["power"]["CommOut"] = self.get_comm_out(
            technodata=muse_data["power"]["Technodata"]
        )
        muse_data["oil"] = {"Technodata": self.convert_oil_technodata()}
        muse_data["oil"]["CommIn"] = self.get_comm_in(
            technodata=muse_data["oil"]["Technodata"]
        )
        muse_data["oil"]["CommOut"] = self.get_comm_out(
            technodata=muse_data["oil"]["Technodata"]
        )
        muse_data["oil"]["ExistingCapacity"] = self.create_empty_existing_capacity(
            self.raw_tables["Table5"]
        )

        logger.info("Writing processed data for {}".format(self.folder))
        self.write_results(muse_data)

    def get_raw_data(self):
        table_directories = glob.glob(str(self.input_path / Path("*.csv")))

        tables = {}
        for table_directory in table_directories:
            table_name = table_directory.split("/")[-1].split("_")[0]
            tables[table_name] = pd.read_csv(table_directory)

        return tables

    def write_results(self, results_data):
        import os

        for sector in results_data:
            for csv in results_data[sector]:
                output_path = self.output_path / Path(sector)
                if not os.path.exists(output_path):
                    os.makedirs(output_path)
                results_data[sector][csv].to_csv(
                    str(output_path) + "/" + csv + ".csv", index=False
                )

    def create_existing_capacity_power(self):
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

    def create_empty_existing_capacity(self, technodata):
        techno = technodata
        techs = list(pd.unique(techno.Technology))

        existing_capacity_dict = {}
        for tech in techs:
            existing_capacity_dict[tech] = [tech, self.folder, "PJ/y"] + [0] * 17

        existing_capacity = pd.DataFrame.from_dict(
            existing_capacity_dict,
            orient="index",
            columns=["ProcessName", "RegionName", "Unit"] + list(range(2018, 2052, 2)),
        )
        return existing_capacity.reset_index(drop=True)

    def convert_power_technodata(self):
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

        return forwardfilled_projected_technoeconomic

    def convert_oil_technodata(self):
        logger = logging.getLogger(__name__)

        oil = self.raw_tables["Table5"]
        oil = oil.pivot(index="Technology", columns="Parameter", values="Value")
        oil = self._insert_constant_columns(oil, "energy", "oil")

        oil = oil.reset_index()
        oil_renamed = oil.rename(
            columns={
                "Capital Cost ($/kW in 2020)": "cap_par",
                "Operational Life (years)": "TechnicalLife",
                "Technology": "ProcessName",
            }
        )
        oil_renamed = oil_renamed.drop(columns="Output Ratio")
        oil_renamed

        muse_technodata = pd.read_csv(
            str(PROJECT_DIR)
            + "/data/external/muse_data/default/technodata/gas/Technodata.csv"
        )

        oil_renamed["Fuel"] = "oil"
        oil_renamed["efficiency"] = 1
        oil_renamed["ScalingSize"] = 1
        oil_renamed["UtilizationFactor"] = 1
        oil_renamed["fix_par"] = 1

        oil_renamed = oil_renamed.reindex(muse_technodata.columns, axis=1)

        oil_renamed = muse_technodata[muse_technodata.ProcessName == "Unit"].append(
            oil_renamed
        )

        return oil_renamed

    def get_comm_in(self, technodata):
        logger = logging.getLogger(__name__)

        power_types = technodata[technodata.ProcessName != "Unit"][
            ["ProcessName", "Fuel"]
        ].drop_duplicates()
        power_types["value"] = 1

        comm_in = power_types.pivot(
            index="ProcessName", columns="Fuel", values="value"
        ).reset_index()

        comm_in.insert(0, "RegionName", self.folder)
        comm_in.insert(1, "Time", 2020)
        comm_in.insert(2, "Level", "fixed")
        comm_in.insert(3, "electricity", 0)
        comm_in["CO2f"] = 0

        units_row = pd.DataFrame.from_dict(units, orient="columns")
        units_row
        comm_in = units_row.append(comm_in)
        comm_in = comm_in.fillna(0)

        return comm_in

    def get_comm_out(self, technodata):
        logger = logging.getLogger(__name__)

        emissions = self.raw_tables["Table7"]
        emissions.Value *= 0.000001
        emissions.Fuel = emissions.Fuel.str.lower()
        emissions.Fuel = emissions.Fuel.str.replace("natural gas", "gas")
        emissions.Fuel = emissions.Fuel.str.replace("crude oil", "oil")

        process_types = technodata[technodata.ProcessName != "Unit"][
            ["ProcessName", "Fuel"]
        ].drop_duplicates()

        process_types_emissions = process_types.merge(
            emissions.drop(columns="Parameter"), on="Fuel", how="left"
        ).fillna(0)
        process_types_emissions = process_types_emissions.rename(
            columns={"Value": "CO2f"}
        )

        process_types_emissions["value"] = 0

        comm_out = (
            process_types_emissions.pivot(
                index=["ProcessName", "CO2f"], columns="Fuel", values="value"
            )
            .fillna(0)
            .reset_index()
        )
        comm_out["electricity"] = 1

        comm_out.insert(1, "RegionName", self.folder)
        comm_out.insert(2, "Time", 2020)
        comm_out.insert(3, "Level", "fixed")

        units_row = pd.DataFrame.from_dict(units, orient="columns")
        units_row
        comm_out = units_row.append(comm_out)
        comm_out = comm_out.fillna(0)
        return comm_out

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

        return technoeconomic_data_wide

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
