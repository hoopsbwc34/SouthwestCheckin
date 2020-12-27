import configparser
import mysql.connector as mysql

config = configparser.ConfigParser()
config.read('/home/matt/SouthwestCheckin/config.ini')

def connect():
    db = mysql.connect(
        host = config['mysqlDB']['host'],
        user = config['mysqlDB']['user'],
        passwd = config['mysqlDB']['pass'],
        database = config['mysqlDB']['db'],
        auth_plugin = 'mysql_native_password'
    )

    return db
