# For deployment on pythonanywhere.com
# Your account username
_accountUsername = ""
# Your MySQL database password
_dbPassword = ""
# Name of your database. For a database named `druvin$test`, set this value to `test`
_dbName = ""
HOSTNAME = f"{_accountUsername}.mysql.pythonanywhere-services.com"
PORTNUMBER = 3306
USERNAME = _accountUsername
PASSWORD = _dbPassword
DATABASE = f"{_accountUsername}${_dbName}"
