import hashlib
import sqlite3
import mysql.connector
import mysql
from enum import Enum
import atexit
from typing import IO, Any, BinaryIO, List, Iterable, Sequence
import math
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import pathlib
import typing
from datetime import datetime
import mysql_config


# Buffer size for file IO
BUF_SIZE = 65536
    
# Error Icon
ERROR_ICON_PATH = "/".join(["static", "error.png"])

# Folder inside `static` for images
IMAGE_FOLDER = "images"

# Type Aliases for typing covenience
Connection: typing.TypeAlias = (
    sqlite3.Connection
    | mysql.connector.pooling.PooledMySQLConnection
    | mysql.connector.MySQLConnection
    # | mysql.connector.CMySQLConnection
)
Cursor: typing.TypeAlias = sqlite3.Cursor | mysql.connector.cursor.MySQLCursor # type: ignore

# The default host and ports for a local MySQL install can be obtained by running `SHOW VARIABLES WHERE Variable_name in ('port','hostname');` in the MySQL terminal.
# In MySQL workbench, accounts using this default hostname have the value of host matching set to `%`.

# These values are stored in a seperate file as the values are going to be different for everyone involved.
# Values are expected to be switched by changing the appropriate import. Default values point to a `pythonanywhere.com` instance on my (BoseV's) account.


class DbType(Enum):
    SQLITE = 1
    MYSQL = 2


def sqlParam(param: str, style: DbType):
    match style:
        case DbType.MYSQL:
            # Assuming all types are strings
            return f"%({param})s"
        case DbType.SQLITE:
            return f":{param}"


# Code taken from https://stackoverflow.com/a/1319675
class UnknownDbTypeException(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)


# NOTE: Remember to check and throw an exception if `dbConnection` is None
class Db:
    # Having all function calls share the same connection leads to thread safety issues.
    # This happens because Flask spawns a seperate thread for each connection/request.
    # dbConnection: sqlite3.Connection
    # dbCursor: sqlite3.Cursor
    dbLocation: str
    dbType: DbType

    def _connect(
        self,
    ) -> Connection:
        """Function to connect this class to a database.

        This function must be called first before using any other action.
        """
        match self.dbType:
            case DbType.SQLITE:
                return sqlite3.connect(self.dbLocation)
            case DbType.MYSQL:
                return mysql.connector.connect(
                    user=mysql_config.USERNAME,
                    password=mysql_config.PASSWORD,
                    host=mysql_config.HOSTNAME,
                    port=mysql_config.PORTNUMBER,
                    database=mysql_config.DATABASE,
                )
            case _:
                raise UnknownDbTypeException(message=f"Unknown DbType {self.dbType}")

    def _getCursor(self, dbConnection) -> Cursor:
        "This initialises the cursor for any future operations on the database."
        if self.dbType == DbType.MYSQL:
            # https://stackoverflow.com/a/33632767
            return dbConnection.cursor(buffered=True)
        else:
            return dbConnection.cursor()
        # return dbConnection.cursor()

    def __init__(self, dbLocation, dbType: DbType = DbType.SQLITE):
        """Initialise the database.

        The database is ready to interact with after this function is done running.
        """
        self.dbLocation = dbLocation
        self.dbType = dbType
        imageFolder = pathlib.Path(os.path.join("static", IMAGE_FOLDER))
        if not imageFolder.exists():
            imageFolder.mkdir()

    # This code is very project specific and will need to be modified
    # TODO: Implement a DB migration function for when we inevtably end up changing DB schema
    # This function relies on the fact that `_connect` and `_setCursor` have been called in `__init__`. Update the function if this not true in the future.
    def dbInit(self):
        """Creates an empty database.

        This will not re-init the database if it already exists. Consider manually deleting it through other means if needed.
        """
        # Table for user data
        if self.dbType == DbType.MYSQL:
            self.executeScript(
                """CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTO_INCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL,
                        profile_picture TEXT)"""
            )
            self.executeScript(
                """CREATE TABLE IF NOT EXISTS posts(
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    author_id INTEGER REFERENCES users(id),
                    content TEXT,
                    created_at INTEGER DEFAULT UNIX_TIMESTAMP() NOT NULL,
                    parent_id INTEGER REFERENCES posts(id),
                    root_id INTEGER REFERENCES posts(id)
                    )"""
            )
        else:
            self.executeScript(
                """CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL,
                        profile_picture TEXT)"""
            )
            self.executeScript(
                """CREATE TABLE IF NOT EXISTS posts(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author_id INTEGER REFERENCES users(id),
                    content TEXT,
                    created_at INTEGER NOT NULL,
                    parent_id INTEGER REFERENCES posts(id),
                    root_id INTEGER REFERENCES posts(id)
                    )"""
            )
        # Taken from https://stackoverflow.com/a/41627098
        # No longer needed as we no longer mantain a global connection for all requests.
        # atexit.register(self.cleanup)
        return

    def _getDb(self) -> tuple[Connection, Cursor]:
        conn = self._connect()
        cur = self._getCursor(conn)
        return (conn, cur)

    def executeOneQuery(
        self, sql: str, parameters: dict[str, str | None] = {}
    ) -> tuple[Connection, Cursor]:
        """Execute ONE SQL query with the given parameters. Returns a handle to the cursor that was used to execute the query.

        Use named-style placeholders in SQL queries eg. `INSERT INTO lang VALUES(:name, :year)`.
        Supply params as `({"name": "C", "year": 1972})`.

        This is done to make substitutions explicit and to ensure style consistency with :py:func:`~db.executeManyQuery`.

        For docs on dicts, see [docs here](https://docs.python.org/3/library/stdtypes.html#dict).
        """
        (dbConnection, dbCursor) = self._getDb()
        try:
            dbCursor.execute(sql, parameters)
            dbConnection.commit()
        except:
            # The expected usage pattern for this function is `(dbConn, dbCursor) = self.executeOneQuery()`.
            # This does not yield itself to the function being able to clean up wasily if an error occours at this stage of the process.
            # Therefore, this function takes it upon itself to close its connection.
            # Commiting changes is avoided here as a broken query is assumed to have no changes that are left to commit.
            dbConnection.close()
            raise

        return (dbConnection, dbCursor)

    def executeManyQuery(
        self, sql: str, parameters=List[dict[str, str | None]]
    ) -> tuple[Connection, Cursor]:
        """Exectue ONE SQL query for each parameter in Iterable.  Returns a handle to the cursor that was used to execute the query.

        Use named-style placeholders in SQL queries eg. `INSERT INTO lang VALUES(:name, :year)`.
        Supply params as `[{"name": "C", "year": 1972},{"name": "Fortran", "year": 1957}]`.

        This is done to make substitutions explicit and to ensure style consistency with :py:func:`~db.executeOneQuery`.

        For docs on dicts, see [docs here](https://docs.python.org/3/library/stdtypes.html#dict).
        """
        (dbConnection, dbCursor) = self._getDb()
        try:
            # Ignoring here as this is verified to tho be safe by mypy
            dbCursor.executemany(sql, parameters)  # type: ignore
            dbConnection.commit()
        except:
            # The expected useage pattern for this function is `(dbConn, dbCursor) = self.executeManyQuery()`.
            # This does not yield itself to the function being able to clean up wasily if an error occours at this stage of the process.
            # Therefore, this function takes it upon itself to close its connection.
            # Commiting changes is avoided here as a broken query is assumed to have no changes that are left to commit.
            dbConnection.close()
        return (dbConnection, dbCursor)

    def executeScript(self, sql_script: str) -> tuple[Connection, Cursor]:
        """Execute SQL statements in sql_script. Returns a handle to the cursor that was used to execute the query."""
        (dbConnection, dbCursor) = self._getDb()
        try:
            dbCursor.execute(sql_script)
            dbConnection.commit()
        except:
            # The expected useage pattern for this function is `(dbConn, dbCursor) = self.executeScript()`.
            # This does not yield itself to the function being able to clean up wasily if an error occours at this stage of the process.
            # Therefore, this function takes it upon itself to close its connection.
            # Commiting changes is avoided here as a broken query is assumed to have no changes that are left to commit.
            dbConnection.close()
        return (dbConnection, dbCursor)
    #  the code for post starts from here
    def createPost(
        self,
        user_id: int,
        content: str,
        parent_id: int | None = None,# Id of post
        root_id: int | None = None # Id of orignal post
    ):
        
        '''
        This function crerates post as well as it can create replies to the post
        '''
        if( root_id is None):    
            (dbConn, dbCursor) = self.executeOneQuery(
                f"INSERT INTO posts (author_id, content,created_at) VALUES ({sqlParam('authorId',self.dbType)}, {sqlParam('content',self.dbType)}, {sqlParam('currTime',self.dbType)})",
                {
                    "authorId": str(user_id),
                    "content": content,
                    "currTime" : str(math.floor((datetime.now() - datetime(1970, 1, 1)).total_seconds()))
                }
            )

        else:
            (dbConn, dbCursor) = self.executeOneQuery(
                f"INSERT INTO posts (author_id, content,created_at, parent_id, root_id) VALUES ({sqlParam('authorId',self.dbType)}, {sqlParam('content',self.dbType)}, {sqlParam('currTime',self.dbType)}, {sqlParam('parentId',self.dbType)}, {sqlParam('rootId',self.dbType)})",
                {
                    "authorId": str(user_id),
                    "content": content,
                    "parentId" : str(root_id) if parent_id is None else str(parent_id),
                    "rootId": str(root_id),
                    "currTime" : str(math.floor((datetime.now() - datetime(1970, 1, 1)).total_seconds()))
                }
                )

        dbConn.close()


    def deletePost(
            self,
            postId:int) -> None:
        (dbConn,dbCursor) = self.executeOneQuery(
            f"DELETE FROM posts WHERE id ={sqlParam("postid",self.dbType)}",
            {
                "postId" : str(postId)
            }
        )
        dbConn.close()
        
    def getAllPost(
            self,
            count:int|None = None) -> list[Any]:
        
        ''' this function gives the list of post details in form of
            username , content , profile picture, created_at
        '''
        (dbConn,dbCursor) = self.executeOneQuery(
            f"SELECT users.username,posts.content,users.profile_picture,posts.created_at FROM posts JOIN users ON posts.author_id = users.id WHERE posts.root_id IS NULL"
        )
        if count is None:
            res = self.getResults(dbCursor )
        else :
            res = self.getResults(dbCursor , count) 

        dbConn.close()

        return res

    # TODO:
    def getAllRepies(
            self,
            postId:int,
            rootId:int,
            range:int) -> list[Any]:
        ''' this function returns data in folooing format
            username , content , profile_picture ,created_at
            '''
        
        return[]
    # TODO: create a function to get result from given range
    
    def getResultsInRange(
            self,
            dbCursor: Cursor,
            range: list[int]
              ) -> list[Any]:
        return []
    



    def getResults(self, dbCursor: Cursor, count: int |None = None) -> list[Any]:
        """Returns `count` number of results from the supplied cursor.

        If `count` is not defined, all rows are returned.
        """
        res: list[Any]
        tmp: Any
        if count is None:
            res = dbCursor.fetchall()
        elif count == 0:
            res = []
        elif count == 1:
            tmp = dbCursor.fetchone()
            if tmp is None:
                res = []
            else:
                res = [tmp]
        else:
            res = dbCursor.fetchmany(size=count)
        return res

    def getAllUsers(self) -> List[dict[str, str]]:
        """Does NOT return the passwords for security reasons.

        To get the password, set `pwd` to `True`.
        """

        (dbConn, dbCursor) = self.executeOneQuery(
            "SELECT username,email,profile_picture FROM users"
        )
        # Cursor returns data in the order they are requested in
        res = self.getResults(dbCursor)
        dbConn.close()
        return res

    def getUser(self, username: str) -> dict[str, str] | None:
        """Get details for user having specific username.

        Returns `None` if no matching entries are found.

        This searches one user only as `executeManyQuery` can only execute DML queries.
        """
        (dbConn, dbCursor) = self.executeOneQuery(
            # "SELECT username,email,profile_picture FROM users WHERE username=:username",
            f"SELECT id ,username,email,profile_picture FROM users WHERE username={sqlParam('username',self.dbType)}",
            {"username": username},
        )
        rawResult = self.getResults(dbCursor)[0]
        dbConn.close()

        if rawResult == []:
            return None

        print(rawResult)
        formattedResults = {
            "id" : rawResult[0],
            "username": rawResult[1],
            "email": rawResult[2],
            "profile_picture": rawResult[3],
        }
        return formattedResults

    def isUsernameTaken(self, username: str) -> bool:
        (dbConn, dbCursor) = self.executeOneQuery(
            f"SELECT 1 FROM users WHERE username={sqlParam('name',self.dbType)}",
            {
                "name": username,
            },
        )
        res = self.getResults(dbCursor)
        dbConn.close()
        if len(res) > 0:
            return True
        else:
            return False

    def isEmailTaken(self, email: str) -> bool:
        (dbConn, dbCursor) = self.executeOneQuery(
            f"SELECT 1 FROM users WHERE email={sqlParam('email',self.dbType)}",
            {
                "email": email,
            },
        )
        res = self.getResults(dbCursor)
        dbConn.close()
        if len(res) > 0:
            return True
        else:
            return False

    def validateUser(self, userName: str, password: str) -> dict[str, str] | None:
        """Returns details if combination is valid, `None` otherwise."""
        (dbConn, dbCursor) = self.executeOneQuery(
            # "SELECT username,email,profile_picture FROM users WHERE username=:name AND password=:password",
            f"SELECT username,email,profile_picture,id FROM users WHERE username={sqlParam('name',self.dbType)} AND password={sqlParam('password',self.dbType)}",
            {"name": userName, "password": password},
        )
        # Get atmost one result
        raw_result = self.getResults(dbCursor, count=1)
        dbConn.close()
        if raw_result == []:
            return None
        else:
            print(raw_result)
            raw_result = raw_result[0]
            return {
                "username": raw_result[0],
                "email": raw_result[1],
                "profile_picture": raw_result[2],
                "id": raw_result[3],
            }

    # The file object here is typed in a flask-specific manner. This will not work for other web frameworks.
    def createUser(
        self,
        username: str,
        password: str,
        email: str,
        profile_picture: FileStorage | None = None,
    ) -> None:
        """The main function to generate entries for a new user.

        This function expects the parameters to be dumped in directly from the `request` object returned by a flask server.
        """
        profile_picture_path: str | None
        if (
            (profile_picture is None)
            or (profile_picture.filename is None)
            or (profile_picture.filename == "")
        ):
            profile_picture_path = ERROR_ICON_PATH
        else:
            profile_picture_path = self.upload_image(profile_picture)
        (dbConn, dbCursor) = self.executeOneQuery(
            f"INSERT INTO users (username, email, password, profile_picture) VALUES ({sqlParam('username',self.dbType)}, {sqlParam('email',self.dbType)}, {sqlParam('password',self.dbType)}, {sqlParam('pic_path',self.dbType)})",
            {
                "username": username,
                "email": email,
                "password": password,
                "pic_path": profile_picture_path,
            },
        )
        dbConn.close()

    def deleteUser(self, username: str) -> None:
        (dbConn, dbCursor) = self.executeOneQuery(
            f"DELETE FROM users WHERE username = {sqlParam('name',self.dbType)}",
            {
                "name": username,
            },
        )
        dbConn.close()

    def updatePassword(self, username: str, oldPassword: str, newPassword: str) -> bool:
        usr = self.validateUser(userName=username, password=oldPassword)
        if usr is None:
            return False
        else:
            (dbConn, dbCursor) = self.executeOneQuery(
                f"UPDATE users SET password = {sqlParam('password',self.dbType)} WHERE username = {sqlParam('username',self.dbType)}",
                {
                    "username": username,
                    "password": newPassword,
                },
            )
            dbConn.close()
            return True

    def updatePicture(self, username, new_profile_picture) -> bool:
        new_pic_path = self.upload_image(new_profile_picture)
        if new_pic_path is None:
            return False
        (dbConn, dbCursor) = self.executeOneQuery(
            f"UPDATE users SET profile_picture = {sqlParam('pic',self.dbType)} WHERE username = {sqlParam('name',self.dbType)}",
            {
                "name": username,
                "pic": new_pic_path,
            },
        )
        dbConn.close()
        return True

    def dumpUsers(self) -> list[typing.Any]:
        (dbConn, dbCursor) = self.executeOneQuery("SELECT * FROM users")
        res = self.getResults(dbCursor=dbCursor)
        dbConn.close()
        return res

    def upload_image(
        self,
        image: FileStorage,
    ) -> str | None:
        """Uploads an image and returns the ref to the image in the database. Returns `None` if the file is invalid or was not stored.

        It is highly reccomended that the `iamegExtension` or `uploadedFileName` is set, ideally using .

        On the disk, the file is stored as `static/IMAGE_FOLDER/<file-md5-hash>.<file-extension>`.

        `md5` is used as it is fast and we don't care too much about hash collisions.

        Note that this removes the original file from disk.
        """
        profile_picture = image
        if profile_picture is None:
            return None
        if (profile_picture.filename is None) or (profile_picture.filename == ""):
            return None
        imgExt = profile_picture.filename.rsplit(".", 1)[1].lower()
        md5 = hashlib.md5()
        # Break out of loop manually once the entire file has been read
        imgStream = profile_picture.stream
        while True:
            # Read data in chunks to avoid running out of memory.
            data = imgStream.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)
        # The final file name
        fileName = md5.hexdigest()
        profile_picture_path = "/".join(
            ["static", IMAGE_FOLDER, f"{fileName}.{imgExt}"]
        )
        print(profile_picture_path)
        imgStream.seek(0)
        with open(pathlib.Path(profile_picture_path), "wb") as f:
            f.write(imgStream.read())
        return profile_picture_path

def getImageExtensionFromFilename(filename: str) -> str:
    """Get the file extension from filename/path.

    Performs NO sanitation.
    """
    # Assuming here that the filename is of the format `./././../hello.tar.gz` and extracting `tar.gz` from it.
    return ".".join(pathlib.PurePath(secure_filename(filename)).name.split(".")[1:])
