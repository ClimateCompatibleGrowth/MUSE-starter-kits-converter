# -*- coding: utf-8 -*-
import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
import glob
from data_transformers import Transformer
from src.defaults import PROJECT_DIR


@click.command()
@click.argument("input_filepath", type=click.Path(exists=True))
@click.argument("output_filepath", type=click.Path())
@click.argument("start_year", type=click.Path())
@click.argument("end_year", type=click.Path())
@click.argument("benchmark_years", type=click.Path())
def main(input_filepath, output_filepath, start_year, end_year, benchmark_years):
    """ Runs data processing scripts to turn raw data from (../raw) into
        cleaned data ready to be analyzed (saved in ../processed).
    """
    logger = logging.getLogger(__name__)
    logger.info("Converting starter kit data into a MUSE compatible form.")
    directories = get_starter_kits(input_filepath)

    transformers = [
        Transformer(
            input_path=path,
            output_path=output_filepath + "/" + path.split("/")[-2],
            start_year=start_year,
            end_year=end_year,
            benchmark_years=benchmark_years,
        )
        for path in directories
    ]

    logger.info("Making datasets")
    for transformer in transformers:
        logger.info("Creating dataset for {}".format(transformer.folder))
        transformer.create_muse_dataset()


def get_starter_kits(input_filepath):
    logger = logging.getLogger(__name__)
    logger.info("Getting starter kit folders.")
    directories = glob.glob(str(PROJECT_DIR) + "/" + str(input_filepath) + "/*/")
    logger.info("Retrieved folders:")
    for directory in directories:
        logger.info(directory)

    return directories


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # find .env automagically by walking up directories until it's found, then
    # load up the .env entries as environment variables
    load_dotenv(find_dotenv())

    main()
