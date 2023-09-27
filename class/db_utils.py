import sqlite3
from enum import Enum
import atexit
from typing import List, Iterable


class DbType(Enum):
    SQLITE = 1


# Code taken from https://stackoverflow.com/a/1319675
class UnknownDbTypeException(Exception):
    def __init__(self, message, errors):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        # Now for your custom code...
        self.errors = errors


# NOTE: Remember to check and throw an exception if `dbConnection` is None
class db:
    dbConnection = None
    dbCursor = None

    def _connect(self, dbLocation, dbType: DbType = DbType.SQLITE):
        """Function to connect this class to a database.

        This function must be called first before using any other action.
        """
        match dbType:
            case DbType.SQLITE:
                self.dbConnection = sqlite3.connect(dbLocation)
            case _:
                raise UnknownDbTypeException

    def _setCursor(self):
        "This initialises the cursor for any future operations on the database."
        self.dbCursor = self.dbConnection.cursor()

    def __init__(self, dbLocation, dbType: DbType = DbType.SQLITE):
        """Initialise the database.

        The database is ready to interact with after this function is done running.
        """
        self.connect(dbLocation=dbLocation, dbType=dbType)
        self.setCursor()

    # This code is very project specific and will need to be modified
    # TODO: Implement a DB migration function for when we inevtably end up changing DB schema
    def dbInit(self):
        """Creates an empty database. Assumes that `connect` and `setCursor` have already been run.

        This will not re-init the database if it already exists. Consider manually deleting it through other means if needed.
        """
        self.dbCursor.execute(
            """CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT NOT NULL,
                      email TEXT NOT NULL,
                      password TEXT NOT NULL,
                      profile_picture TEXT)"""
        )
        self.dbConnection.commit()
        # Taken from https://stackoverflow.com/a/41627098
        atexit.register(self.cleanup)
        return

    def cleanup(self):
        self.dbConnection.commit()
        self.dbConnection.close()
        return

    def executeOneQuery(self, sql: str, parameters: dict = ({})):
        """Use named-style placeholders in SQL queries eg. `INSERT INTO lang VALUES(:name, :year)`.
        Supply params as `({"name": "C", "year": 1972})`.

        This is done to make substitutions explicit and to ensure style consistency with :py:func:`~db.executeManyQuery`
        """
        self.dbCursor.execute(sql, parameters)
        self.dbConnection.commit()
        return

    # This may not work perfectly
    def executeManyQuery(self, sqls: List[str], parameters=Iterable):
        self.dbCursor.executemany(sqls, parameters)
        self.dbConnection.commit()
        return
