import hashlib
import sqlite3
from enum import Enum
import atexit
from typing import IO, Any, BinaryIO, List, Iterable
import math
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import pathlib

# Buffer size for file IO
BUF_SIZE = 65536

# Error Icon
ERROR_ICON_PATH = os.path.join("static", "error.png")


class DbType(Enum):
    SQLITE = 1


# Code taken from https://stackoverflow.com/a/1319675
class UnknownDbTypeException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


# NOTE: Remember to check and throw an exception if `dbConnection` is None
class Db:
    dbConnection: sqlite3.Connection
    dbCursor: sqlite3.Cursor

    def _connect(self, dbLocation, dbType: DbType = DbType.SQLITE):
        """Function to connect this class to a database.

        This function must be called first before using any other action.
        """
        match dbType:
            case DbType.SQLITE:
                self.dbConnection = sqlite3.connect(dbLocation)
            case _:
                raise UnknownDbTypeException(message=f"Unknown DbType {dbType}")

    def _setCursor(self):
        "This initialises the cursor for any future operations on the database."
        self.dbCursor = self.dbConnection.cursor()

    def __init__(self, dbLocation, dbType: DbType = DbType.SQLITE):
        """Initialise the database.

        The database is ready to interact with after this function is done running.
        """
        self._connect(dbLocation=dbLocation, dbType=dbType)
        self._setCursor()

    # This code is very project specific and will need to be modified
    # TODO: Implement a DB migration function for when we inevtably end up changing DB schema
    # This function relies on the fact that `_connect` and `_setCursor` have been called in `__init__`. Update the function if this not true in the future.
    def dbInit(self):
        """Creates an empty database.

        This will not re-init the database if it already exists. Consider manually deleting it through other means if needed.
        """
        # Table for user data
        self.executeScript(
            """CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT NOT NULL,
                      email TEXT NOT NULL,
                      password TEXT NOT NULL,
                      profile_picture TEXT)"""
        )
        # Taken from https://stackoverflow.com/a/41627098
        atexit.register(self.cleanup)
        return

    def cleanup(self):
        self.dbConnection.commit()
        self.dbConnection.close()
        return

    def executeOneQuery(self, sql: str, parameters: dict[str, str] = {}):
        """Execute ONE SQL query with the given parameters.

        Use named-style placeholders in SQL queries eg. `INSERT INTO lang VALUES(:name, :year)`.
        Supply params as `({"name": "C", "year": 1972})`.

        This is done to make substitutions explicit and to ensure style consistency with :py:func:`~db.executeManyQuery`.

        For docs on dicts, see [docs here](https://docs.python.org/3/library/stdtypes.html#dict).
        """
        self.dbCursor.execute(sql, parameters)
        self.dbConnection.commit()
        return

    def executeManyQuery(self, sql: str, parameters=List[dict[str, str]]) -> None:
        """Exectue ONE SQL query for each parameter in Iterable.

        Use named-style placeholders in SQL queries eg. `INSERT INTO lang VALUES(:name, :year)`.
        Supply params as `[{"name": "C", "year": 1972},{"name": "Fortran", "year": 1957}]`.

        This is done to make substitutions explicit and to ensure style consistency with :py:func:`~db.executeOneQuery`.

        For docs on dicts, see [docs here](https://docs.python.org/3/library/stdtypes.html#dict).
        """
        # Ignored issue on floowing line as it is verified by `mypy`.
        self.dbCursor.executemany(sql, parameters)  # type: ignore
        self.dbConnection.commit()
        return

    def executeScript(self, sql_script: str) -> None:
        """Execute SQL statements in sql_script."""
        self.dbCursor.execute(sql_script)
        self.dbConnection.commit()
        return

    def getResults(self, count: int | None = None) -> list[Any]:
        """Returns `count` number of results.

        If `count` is not defined, all rows are returned.
        """
        if count is None:
            return self.dbCursor.fetchall()
        elif count == 0:
            return []
        elif count == 1:
            result = self.dbCursor.fetchone()
            if result is None:
                return []
            else:
                return [result]
        else:
            return self.dbCursor.fetchmany(size=count)

    def getAllUsers(self, pwd: bool = False) -> List[dict[str, str]]:
        """Does NOT return the passwords by default for security reasons.

        To get the password, set `pwd` to `True`.
        """
        self.executeOneQuery("SELECT username,email,profile_picture FROM users")
        # Cursor returns data in the order they are requested in
        return self.getResults()

    # This function accepts a list of names because it is meant to be used in situations like getting a list of friends, etc.
    def getUser(self, usernames: List[str]) -> dict[str, str] | None:
        """Get details for user having specific username.

        Returns `None` if no matching entries are found.
        """
        self.executeManyQuery(
            "SELECT username,email,profile_picture FROM users WHERE username=:userName",
            # Ignoring as this is verified by `mypy`.
            [{"username": x} for x in usernames],  # type: ignore
        )
        rawResult = self.getResults()

        if rawResult == []:
            return None

        formattedResults = {
            "username": rawResult[0],
            "email": rawResult[1],
            "profile_picture": rawResult[2],
        }
        return formattedResults

    def validateUser(self, userName: str, password: str) -> dict[str, str] | None:
        """Returns details if combination is valid, `None` otherwise."""
        self.executeOneQuery(
            "SELECT (username,email,profile_picture) FROM users WHERE username=:name AND password=:password",
            {"username": userName, "password": password},
        )
        # Get atmost one result
        raw_result = self.getResults(count=1)
        if raw_result == []:
            return None
        else:
            return {
                "username": raw_result[0],
                "email": raw_result[1],
                "profile_picture": raw_result[2],
            }

    # The file object here is typed in a flask-specific manner. This will not work for other web frameworks.
    def createUser(
        self, username: str, password: str, email: str, profile_picture: FileStorage
    ) -> None:
        """The main function to generate entries for a new user.

        This function expects the parameters to be dumped in directly from the `request` object returned by a flask server.
        """
        if profile_picture_path is None:
            profile_picture_path = ERROR_ICON_PATH
        else:
            profile_picture_path = self.upload_image(profile_picture.stream)
        self.executeOneQuery(
            "INSERT INTO users (username, email, password, profile_picture) VALUES (:username, :email, :password, :pic_path)",
            {
                "username": username,
                "email": email,
                "password": password,
                "pic_path": profile_picture_path,
            },
        )

    def upload_image(
        self,
        imageStream: IO[bytes],
        imageExtension: str = "",
        uploadedFileName: str | None = None,
    ) -> str | None:
        """Uploads an image and returns the ref to the image in the database. Returns `None` if the file is invalid or was not stored.

        It is highly reccomended that the `iamegExtension` or `uploadedFileName` is set, ideally using .

        On the disk, the file is stored as `static/images/<file-md5-hash>.<file-extension>`.

        `md5` is used as it is fast and we don't care too much about hash collisions.

        Note that this removes the original file from disk.
        """
        # File hashing implementation taken from https://stackoverflow.com/a/22058673
        md5 = hashlib.md5()
        # Break out of loop manually once the entire file has been read
        while True:
            # Read data in chunks to avoid running out of memory.
            data = imageStream.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
        # The final file name
        fileName = md5.hexdigest()
        if (imageExtension == "") and (not (uploadedFileName is None)):
            imageExtension = getImageExtensionFromFilename(uploadedFileName)

        fileName = f"{fileName}.{imageExtension}"

        imagePath = pathlib.Path(
            os.path.join("static", "images", f"{fileName}.{imageExtension}")
        )

        if not (imagePath.exists()):
            # Skip writing file to disk if it already exists.

            # Open file for writing binary data
            imageHandle = imagePath.open("+wb")

            while True:
                # Read data in chunks to avoid running out of memory.
                data = imageStream.read(BUF_SIZE)
                if not data:
                    break
                imageHandle.write(data)

            imageHandle.close()

        return imagePath


def getImageExtensionFromFilename(filename: str) -> str:
    """Get the file extension from filename/path.

    Performs NO sanitation.
    """
    # Assuming here that the filename is of the format `./././../hello.tar.gz` and extracting `tar.gz` from it.
    return ".".join(pathlib.PurePath(secure_filename(filename)).name.split(".")[1:])
