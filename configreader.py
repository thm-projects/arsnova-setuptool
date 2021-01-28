import configparser
import io
import os
import sys

MIN_PYTHON_VERSION = (3, 2)
if sys.version_info < MIN_PYTHON_VERSION:
    sys.exit("Python %s.%s or later is required." % MIN_PYTHON_VERSION)


class ConfigReader:
    def __init__(self, propertiesFile="/etc/arsnova/arsnova.properties"):
        self.readProperties(propertiesFile)
        self.host = os.environ.get("ARSNOVA_COUCHDB_HOST", self.host)
        self.port = os.environ.get("ARSNOVA_COUCHDB_PORT", self.port)
        self.dbName = os.environ.get("ARSNOVA_COUCHDB_NAME", self.dbName)
        self.username = os.environ.get(
            "ARSNOVA_COUCHDB_USERNAME", self.username)
        self.password = os.environ.get(
            "ARSNOVA_COUCHDB_PASSWORD", self.password)

    def readProperties(self, fileName):
        f = open(fileName, "r")
        properties = f.read()
        f.close()

        config = configparser.RawConfigParser()
        config.read_string("[arsnova]\n" + properties)
        self.host = config.get("arsnova", "couchdb.host")
        self.port = config.get("arsnova", "couchdb.port")
        self.dbName = config.get("arsnova", "couchdb.name")
        self.username = config.get("arsnova", "couchdb.username")
        self.password = config.get("arsnova", "couchdb.password")
