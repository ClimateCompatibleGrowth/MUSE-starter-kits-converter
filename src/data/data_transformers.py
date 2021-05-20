import logging
from pathlib import Path
import glob
import pandas as pd
from src.defaults import PROJECT_DIR, plant_fuels, units


class Transformer:
    def __init__(self, input_path, output_path, start_year, end_year, benchmark_years):
        """

        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.start_year = int(start_year)
        self.end_year = int(end_year)
        self.benchmark_years = int(benchmark_years)

        self.folder = str(self.input_path).split("/")[-1]
        self.raw_tables = self.get_raw_data()

    def create_muse_dataset(self):
        """
        Imports the starter kits datasets and converts them into a form used for MUSE.
        """
        logger = logging.getLogger(__name__)
        logger.info("Converting raw data for {}.".format(self.folder))

        muse_data = {}

        muse_data["input"] = {"GlobalCommodities": self.generate_global_commodities()}

        muse_data["input"]["Projections"] = self.generate_projections()

        muse_data["technodata"] = {"Agents": self.generate_agents_file()}

        muse_data["technodata"]["power"] = {
            "ExistingCapacity": self.create_existing_capacity_power()
        }
        muse_data["technodata"]["power"]["Technodata"] = self.convert_power_technodata()
        muse_data["technodata"]["power"]["CommIn"] = self.get_comm_in(
            technodata=muse_data["technodata"]["power"]["Technodata"]
        )
        muse_data["technodata"]["power"]["CommOut"] = self.get_comm_out(
            technodata=muse_data["technodata"]["power"]["Technodata"]
        )
        muse_data["technodata"]["oil"] = {"Technodata": self.convert_oil_technodata()}
        muse_data["technodata"]["oil"]["CommIn"] = self.get_comm_in(
            technodata=muse_data["technodata"]["oil"]["Technodata"]
        )
        muse_data["technodata"]["oil"]["CommOut"] = self.get_comm_out(
            technodata=muse_data["technodata"]["oil"]["Technodata"]
        )
        muse_data["technodata"]["oil"][
            "ExistingCapacity"
        ] = self.create_empty_existing_capacity(self.raw_tables["Table5"])

        logger.info("Writing processed data for {}".format(self.folder))
        self.write_results(muse_data)

    def get_raw_data(self):
        """
        Imports all starter kits data into pandas.
        """
        table_directories = glob.glob(str(self.input_path / Path("*.csv")))

        tables = {}
        for table_directory in table_directories:
            table_name = table_directory.split("/")[-1].split("_")[0]
            tables[table_name] = pd.read_csv(table_directory)

        return tables

    def write_results(self, results_data):
        """
        Writes all the processed starter kits to CSV files for use in MUSE.
        """
        import os

        for folder in results_data:
            output_path_folder = self.output_path / Path(folder)
            for sector in results_data[folder]:
                output_path = self.output_path / Path(folder) / Path(sector)
                if (
                    not os.path.exists(output_path)
                    and type(results_data[folder][sector]) is dict
                ):
                    os.makedirs(output_path)
                elif not os.path.exists(output_path_folder):
                    os.makedirs(output_path_folder)
                if type(results_data[folder][sector]) is pd.DataFrame:
                    results_data[folder][sector].to_csv(
                        str(output_path) + ".csv", index=False
                    )
                else:
                    for csv in results_data[folder][sector]:
                        results_data[folder][sector][csv].to_csv(
                            str(output_path) + "/" + csv + ".csv", index=False
                        )

    def generate_agents_file(self):
        agents = pd.read_csv("data/external/muse_data/default/technodata/Agents.csv")
        agents["RegionName"] = self.folder
        return agents

    def generate_global_commodities(self):

        commodities = self.raw_tables["Table7"]

        commodities["Commodity"] = commodities["Fuel"]
        commodities = commodities.drop(columns="Parameter")
        commodities["Fuel"] = (
            commodities["Fuel"]
            .str.lower()
            .str.replace("light fuel oil", "LFO")
            .str.replace("heavy fuel oil", "HFO")
            .str.replace("crude oil", "crude_oil")
            .str.replace("natural gas", "gas")
        )
        commodities = commodities.rename(
            columns={"Value": "CommodityEmissionFactor_CO2", "Fuel": "CommodityName"}
        )
        commodities["CommodityType"] = "energy"
        commodities["HeatRate"] = 1
        commodities["Unit"] = "kg CO2/GJ"

        CO2_row = {
            "Commodity": "CO2fuelcombustion",
            "CommodityType": "Environmental",
            "CommodityName": "CO2f",
            "CommodityEmissionFactor_CO2": 0,
            "HeatRate": 1,
            "Unit": "kt",
        }
        commodities = commodities.append(CO2_row, ignore_index=True)

        muse_commodities = pd.read_csv(
            "data/external/muse_data/default/input/GlobalCommodities.csv"
        )
        commodities = commodities.reindex(muse_commodities.columns, axis=1)

        additional_items = [
            "ProcessName",
            "RegionName",
            "Time",
            "Level",
            "CO2f",
            "crude_oil",
            "biomass",
            "coal",
            "LFO",
            "HFO",
            "gas",
        ]
        fuels = units.copy()

        for item in additional_items:
            fuels.pop(item)

        for commodity, _ in fuels.items():
            entries = [commodity, "energy", commodity, 0, 1, "kg C02/GJ"]
            new_row = {
                column: entry
                for column, entry in zip(list(commodities.columns), entries)
            }
            commodities = commodities.append(new_row, ignore_index=True)

        return commodities

    def generate_projections(self):
        from src.defaults import units

        costs = self.raw_tables["Table6"]

        import_costs = costs[~costs["Commodity"].str.contains("Extraction")].copy()
        import_costs["Commodity"] = import_costs["Commodity"].str.replace("Imports", "")
        import_costs["Commodity"] = import_costs["Commodity"].str.replace("Natural", "")
        import_costs["Commodity"] = import_costs["Commodity"].str.lower()
        import_costs["Commodity"] = import_costs["Commodity"].str.replace(
            "light fuel oil", "LFO"
        )
        import_costs["Commodity"] = import_costs["Commodity"].str.replace(
            "heavy fuel oil", "HFO"
        )

        import_costs["Commodity"] = import_costs["Commodity"].str.replace(" ", "")

        import_costs["Commodity"] = import_costs["Commodity"].str.replace(
            "crudeoil", "crude_oil"
        )

        fuels = list(pd.unique(import_costs.Commodity))

        projections = import_costs.pivot_table(
            index="Year", columns="Commodity", values="Value"
        )

        projections["RegionName"] = self.folder
        projections["Attribute"] = "CommodityPrice"

        projections = projections.reset_index()
        projections = projections.rename(columns={"Year": "Time"})

        col_order = ["RegionName", "Attribute", "Time"] + fuels
        projections = projections[col_order]

        commodities = units.copy()
        for item in [
            "ProcessName",
            "RegionName",
            "Time",
            "Level",
            "crude_oil",
            "biomass",
            "coal",
            "LFO",
            "HFO",
            "gas",
        ]:
            commodities.pop(item)

        for key, _ in commodities.items():
            projections[key] = 0

        projections

        units = {"RegionName": ["Unit"], "Attribute": ["-"], "Time": ["Year"]}
        for commodity in fuels + list(commodities.keys()):
            units[commodity] = ["$/GJ"]

        units_row = pd.DataFrame.from_dict(units, orient="columns")
        projections_out = units_row.append(projections)
        return projections_out

    def create_existing_capacity_power(self):
        """
        Calculates the existing power capacity from Table1 from the starter kits, 
        and transforms them into an ExistingCapacity dataframe for MUSE.
        """

        installed_capacity = self.raw_tables["Table1"]
        installed_capacity = installed_capacity.rename(
            columns={"Power Generation Technology": "Technology"}
        )

        installed_capacity["Technology"].replace(
            "Off-grid Solar PV", "Solar PV (Distributed with Storage)", inplace=True
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
            installed_capacity_cf.estimated_installed_capacity_MW * 8600 * 0.0000036
        )

        installed_capacity_pj_y = installed_capacity_cf.drop(
            columns=["estimated_installed_capacity_MW", "average_capacity_factor"]
        )

        installed_capacity_pj_y_wide = installed_capacity_pj_y.pivot(
            index="Technology",
            columns="Year",
            values="estimated_installed_capacity_PJ_y",
        ).reset_index()

        unknown_cols = list(range(self.start_year, self.end_year, self.benchmark_years))
        for col in unknown_cols:
            installed_capacity_pj_y_wide[col] = 0

        installed_capacity_pj_y_wide.insert(1, "RegionName", self.folder)
        installed_capacity_pj_y_wide.insert(2, "Unit", "PJ/y")
        muse_installed_capacity = installed_capacity_pj_y_wide.rename(
            columns={"Technology": "ProcessName"}
        )
        muse_installed_capacity = muse_installed_capacity.drop(columns=2020)
        muse_installed_capacity = muse_installed_capacity.rename(columns={2018: 2020})

        return muse_installed_capacity

    def create_empty_existing_capacity(self, technodata):
        """
        Creates an existing capacity for MUSE, where no data is available.
        """
        techno = technodata
        techs = list(pd.unique(techno.Technology))

        existing_capacity_dict = {}

        all_years = list(range(self.start_year, self.end_year, self.benchmark_years))
        for tech in techs:
            existing_capacity_dict[tech] = [tech, self.folder, "PJ/y"] + [0] * (
                len(all_years)
            )

        existing_capacity = pd.DataFrame.from_dict(
            existing_capacity_dict,
            orient="index",
            columns=["ProcessName", "RegionName", "Unit"] + all_years,
        )

        existing_capacity = existing_capacity.reset_index(drop=True)
        existing_capacity[2020] = 100
        return existing_capacity

    def convert_power_technodata(self):
        """
        Converts Table2 from the starter kits into a Power Technodata file for MUSE.
        """

        logger = logging.getLogger(__name__)
        technoeconomic_data = self.raw_tables["Table2"]

        muse_technodata = pd.read_csv(
            PROJECT_DIR
            / Path("data/external/muse_data/default/technodata/power/Technodata.csv")
        )

        technoeconomic_data_wide = technoeconomic_data.pivot(
            index="Technology", columns="Parameter", values="Value"
        )
        self._insert_constant_columns(technoeconomic_data_wide, "energy", "electricity")

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

        projected_capex_with_unknowns = pd.merge(
            projected_capex[["ProcessName", "Time"]],
            technoeconomic_data_wide_named[["ProcessName"]],
            how="cross",
        )
        with_years = (
            projected_capex_with_unknowns.drop(columns="ProcessName_x")
            .drop_duplicates()
            .rename(columns={"ProcessName_y": "ProcessName"})
        )

        filled_years = pd.merge(with_years, projected_capex, how="outer")
        combined_years = pd.merge(
            filled_years,
            technoeconomic_data_wide_named[["ProcessName", "cap_par"]],
            on="ProcessName",
        )
        combined_years["cap_par_x"] = combined_years["cap_par_x"].fillna(
            combined_years["cap_par_y"]
        )

        projected_capex_all_technologies = combined_years.drop(
            columns="cap_par_y"
        ).rename(columns={"cap_par_x": "cap_par"})
        projected_capex_all_technologies

        projected_technoeconomic = pd.merge(
            technoeconomic_data_wide_named,
            projected_capex_all_technologies,
            on=["ProcessName", "Time"],
            how="outer",
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
        """
        Creates the oil technodata from Table5 in the starter kits.
        """

        oil = self.raw_tables["Table5"]
        oil = oil.pivot(index="Technology", columns="Parameter", values="Value")
        oil = self._insert_constant_columns(oil, "energy", "LFO")

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

        oil_renamed["Fuel"] = "crude_oil"
        oil_renamed["efficiency"] = 1
        oil_renamed["ScalingSize"] = 1
        oil_renamed["UtilizationFactor"] = 1
        oil_renamed["fix_par"] = 1

        years_required = pd.Series(
            list(range(self.start_year, self.end_year, self.benchmark_years)),
            name="Time",
        )
        oil_renamed = pd.merge(oil_renamed, years_required, how="cross")
        oil_renamed = oil_renamed.drop(columns="Time_x").rename(
            columns={"Time_y": "Time"}
        )

        oil_renamed = oil_renamed.reindex(muse_technodata.columns, axis=1)

        oil_renamed = muse_technodata[muse_technodata.ProcessName == "Unit"].append(
            oil_renamed
        )

        return oil_renamed

    def get_comm_in(self, technodata):
        """
        Generates the CommIn dataframe for MUSE from Table7 in the starter kits.
        """

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

        # Replicate rows for each year
        comm_in_merged = pd.merge(
            comm_in,
            pd.Series(list(pd.unique(technodata.Time))[1:], name="Time"),
            how="cross",
        )
        comm_in_merged = comm_in_merged.drop(columns="Time_x")
        comm_in = comm_in_merged.rename(columns={"Time_y": "Time"})

        units_row = pd.DataFrame.from_dict(units, orient="columns")
        comm_in = units_row.append(comm_in)
        comm_in = comm_in.fillna(0)

        return comm_in

    def get_comm_out(self, technodata):
        """
        Generates the CommOut dataframe for MUSE from Table7 in the starter kits.
        """

        logger = logging.getLogger(__name__)

        emissions = self.raw_tables["Table7"]

        emissions.Value *= 0.000001
        emissions.Fuel = emissions.Fuel.str.lower()
        emissions.Fuel = emissions.Fuel.str.replace("natural gas", "gas")
        emissions.Fuel = emissions.Fuel.str.replace("crude oil", "crude_oil")

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
        if comm_out["ProcessName"].str.contains("Crude Oil Refinery Option").any():
            comm_out = self._calculate_oil_outputs(comm_out)
        else:
            comm_out["electricity"] = 1

        comm_out.insert(1, "RegionName", self.folder)
        comm_out.insert(2, "Time", 2020)
        comm_out.insert(3, "Level", "fixed")

        # Replicate rows for each year
        comm_out_merged = pd.merge(
            comm_out,
            pd.Series(list(pd.unique(technodata.Time))[1:], name="Time"),
            how="cross",
        )
        comm_out_merged = comm_out_merged.drop(columns="Time_x")
        comm_out = comm_out_merged.rename(columns={"Time_y": "Time"})

        units_row = pd.DataFrame.from_dict(units, orient="columns")
        units_row
        comm_out = units_row.append(comm_out)
        comm_out = comm_out.fillna(0)
        return comm_out

    def _calculate_oil_outputs(self, comm_out):
        raw_oil_technodata = self.raw_tables["Table5"]
        output_ratio = raw_oil_technodata[
            raw_oil_technodata.Parameter == "Output Ratio"
        ]
        output_ratio_list = output_ratio.Value.str.replace(" HFO", "").str.split(
            " LFO : "
        )
        comm_out[["HFO", "LFO"]] = pd.DataFrame(
            output_ratio_list.tolist(), index=comm_out.index
        )

        comm_out["crude_oil"] = 0

        return comm_out

    def _fill_unknown_data(self, projected_technoeconomic):
        """
        Fill unknown technodata for different technologies at different years.
        """

        projected_technoeconomic.cap_par_y.fillna(
            projected_technoeconomic.cap_par_x, inplace=True
        )

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
        """
        Insert columns which are constant for technodata
        """
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
        """
        Finds minimum scaling size based on the name of the plant.
        """
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

