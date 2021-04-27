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

    def create_muse_dataset(self):
        logger = logging.getLogger(__name__)
        logger.info("Getting full dataset.")
        logger.info("Project dir: {}".format(PROJECT_DIR))

    def installed_power_plants(self):
        # pd.read_csv("")
        pass

