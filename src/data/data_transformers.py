import logging
from pathlib import Path
import glob


class Transformer:
    def __init__(self, input_path, output_path):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)

    def create_muse_dataset(self):
        logger = logging.getLogger(__name__)
        logger.info("Getting full dataset.")
