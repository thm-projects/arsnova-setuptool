import http.client
import base64
import json
import configreader
import sys
from distutils.version import LooseVersion as V


class CouchConnection(http.client.HTTPConnection):
    """docstring for CouchConnection"""

    def __init__(self, host="127.0.0.1", port=5984, username="", password=""):
        http.client.HTTPConnection.__init__(self, host, port)
        self.username = username
        self.password = password

    def request(self, method, path, body="", header={}):
        if self.username != "" and self.password != "":
            creds = base64.encodestring(
                ('%s:%s' % (self.username, self.password)).encode()).decode().strip()
            header["Authorization"] = "Basic %s" % creds
        http.client.HTTPConnection.request(self, method, path, body, header)

    def get(self, path, header={}):
        self.request("GET", path, "", header)
        return self.getresponse()

    def post(self, path, body=None, header={}):
        self.request("POST", path, body, header)
        return self.getresponse()

    def json_post(self, path, body=None, header={}):
        h = {"Content-Type": "application/json"}
        self.request("POST", path, body, dict(
            list(h.items()) + list(header.items())))
        return self.getresponse()

    def put(self, path, body, header={}):
        self.request("PUT", path, body, header)
        return self.getresponse()

    def json_put(self, path, body, header={}):
        h = {"Content-Type": "application/json"}
        self.request("PUT", path, body, dict(
            list(h.items()) + list(header.items())))
        return self.getresponse()

    def delete(self, path, body=None, header={}):
        self.request("GET", path)
        res = self.getresponse()
        doc = json.loads(res.read())
        if "_rev" in doc:
            self.request("DELETE", path + "?rev=" + doc["_rev"], body, header)
            res = self.getresponse()
            return res.read()
        else:
            return False

    def temp_view(self, path, body, header={}):
        return self.json_post(path + "/_temp_view", body, header)

    def temp_view_with_params(self, path, params, body, header={}):
        return self.json_post(path + "/_temp_view" + params, body, header)

    def require_legacy_couchdb_version(self):
        self.request("GET", "/")
        res = self.getresponse()
        couchdb_info = json.loads(res.read())
        couchdb_version = V(couchdb_info["version"])
        version_str = "2.0.0"
        if couchdb_version >= V(version_str):
            sys.exit("This script does not support CouchDB %s or newer." %
                     version_str)


def arsnova_connection(propertypath):
    config = configreader.ConfigReader(propertypath)
    return (config.dbName, CouchConnection(config.host, config.port, config.username, config.password))
