from abc import ABC, abstractclassmethod

from rich import inspect, print

from config import StorageMode, settings
from entities import Place, ResInfo
from exceptions import MissingEnvVariable
from facades import SQSEmitter
import pymongo

class BaseStorage(ABC):
    @abstractclassmethod
    def save(self, place: Place):
        ...


class DebugStorage(BaseStorage):
    def save(self, place: Place):
        print(f"[yellow]{'=' * 100}[/yellow]")
        inspect(place)
        print(f"[yellow]{'=' * 100}[/yellow]")


class SqsStorage(BaseStorage):
    def __init__(self) -> None:
        if not settings.SCRAPED_EVENT_SQS_URL:
            raise MissingEnvVariable("SCRAPED_EVENT_SQS_URL")

        self.emitter = SQSEmitter(settings.SCRAPED_EVENT_SQS_URL)

    def save(self, place: Place):
        self.emitter.emit(place)

class MongoStorage(BaseStorage):
    def __init__(self) -> None:
        self.myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    
    def save(self, mylist):
        mydb = self.myclient['data']
        # mycol = mydb['restaurant']
        mycol = mydb['fastfood']
        mycol.insert_many(mylist)

def get_storage() -> BaseStorage:
    if settings.STORAGE_MODE == StorageMode.DEBUG:
        return DebugStorage()

    if settings.STORAGE_MODE == StorageMode.SQS:
        return SqsStorage()

    if settings.STORAGE_MODE == StorageMode.MONGO:
        return MongoStorage()

    raise ValueError(f"{settings.STORAGE_MODE} is unknown")
