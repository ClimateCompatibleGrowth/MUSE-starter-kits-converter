import logging
from pathlib import Path
import glob


class Transformer:
    def __init__(self, path):
        self.path = Path(path)

    def get_full_dataset(self):
        logger = logging.getLogger(__name__)
        logger.info("Getting full dataset.")
