from distutils.command.config import config
import logging.config
from enum import Enum
import yaml
from pydantic import BaseSettings


CONFIG_FILE_PATH = "/Users/brucelin/workplace/GMaps-Crawler/src/gmaps_crawler/config.yaml"

class FileCongfig():
    def __init__(self) -> None:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = yaml.safe_load(f)
        self.config = config['crawler_path']
        self.side_bar_res_xpath = self.config['SIDE_BAR_RESTAURANT_XPATH']
        self.res_name_xpath = self.config['RESTAURANT_NAME_XPATH']
        self.res_menu_xpath = self.config['RESTAURANT_MENU_XPATH']
        self.res_address_xpath = self.config['RESTAURANT_ADDRESS_XPATH']
        self.res_num_review_xpath = self.config['RESTAURANT_NUM_REVIEW_XPATH']
        self.res_rating_xpath = self.config['RATING_XPATH']
        self.base_url = self.config['BASE_URL']
        self.search_word = self.config['SEARCH']
        # self.start_location = self.config['START_LOCATION']



class StorageMode(Enum):
    DEBUG = "DEBUG"
    SQS = "SQS"
    MONGO = "MONGO"


class Settings(BaseSettings):
    STORAGE_MODE: StorageMode = StorageMode.MONGO
    SCRAPED_EVENT_SQS_URL: str = ""

    class Config:
        env_file = ".env"


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "default": {
            "format": "%(message)s",
            "datefmt": "[%X]",
        }
    },
    "handlers": {
        "rich": {
            "level": "INFO",
            "formatter": "default",
            "class": "rich.logging.RichHandler",
            "rich_tracebacks": True,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["rich"],
    },
}

logging.config.dictConfig(LOGGING_CONFIG)

settings = Settings()
fileconfig = FileCongfig()
