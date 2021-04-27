import logging
from pathlib import Path
import glob
import pandas as pd
from src.defaults import PROJECT_DIR


class Transformer:
    def __init__(self, input_path, output_path):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.folder = str(self.input_path).split("/")[-1]
        self.raw_tables = self.get_data()

    def create_muse_dataset(self):
        logger = logging.getLogger(__name__)
        logger.info("Importing raw data for {}.".format(self.folder))

    def get_raw_data(self):
        table_directories = glob.glob(str(self.input_path / Path("*.csv")))

        tables = {}
        for table_directory in table_directories:
            table_name = table_directory.split("/")[-1].split("_")[0]
            tables[table_name] = pd.read_csv(table_directory)

        return tables

    def convert_installed_power_plants(self):
        plant_data = self.raw_tables['Table1']
        
        pass

