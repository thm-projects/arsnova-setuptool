#!/usr/bin/env python3
import couchconnection
import json
import sys
import socket
import os
from constants import LATEST_MIGRATION_VERSION, MIGRATIONS_DOCUMENT_ID


def database_exists(conn, db):
    conn.request("HEAD", "/" + db)
    res = conn.getresponse()
    res.read()
    return res.status == 200


def database_create(conn, db):
    conn.request("PUT", "/" + db)
    res = conn.getresponse()
    res.read()
    return res.status == 201


def set_migration_version_to_latest(conn, db):
    db_url = "/" + db
    res = conn.json_post(db_url, json.dumps(
        {"_id": MIGRATIONS_DOCUMENT_ID, "version": LATEST_MIGRATION_VERSION}))
    res.read()


def view_exists(conn, view_url):
    conn.request("HEAD", view_url)
    res = conn.getresponse()
    res.read()
    return res.status == 200


def view_create(conn, view_url, view):
    conn.request("POST", view_url, view.read(), {
                 "Content-Type": "application/json"})
    res = conn.getresponse()
    res.read()
    return res.status == 201


def view_read(conn, view_url):
    conn.request("GET", view_url)
    res = conn.getresponse()
    return res.read()


def view_revision(conn, view_url):
    view_document = json.loads(view_read(conn, view_url).decode('utf-8'))
    return view_document["_rev"]


def view_update_revision(conn, view_url, view):
    view_updated = json.loads(view.read())
    view_updated["_rev"] = view_revision(conn, view_url)
    return json.dumps(view_updated)


def view_update(conn, view_url, view):
    conn.request("PUT", view_url, view_update_revision(
        conn, view_url, view), {"Content-Type": "application/json"})
    res = conn.getresponse()
    res.read()
    return res.status == 201


def view_process(conn, db, view):
    view_url = "/" + db + "/_design/" + os.path.basename(view)
    if not view_exists(conn, view_url):
        if not view_create(conn, "/" + db, open(view, "r")):
            print("... creation FAILED!")
    else:
        if not view_update(conn, view_url, open(view, "r")):
            print("... update FAILED!")


scriptpath = os.path.dirname(os.path.realpath(__file__))
viewpath = scriptpath + "/src/main/resources/views"

(db, conn) = couchconnection.arsnova_connection(
    "/etc/arsnova/arsnova.properties")
try:
    if not database_exists(conn, db):
        print(("Creating database '" + db + "'..."))
        if not database_create(conn, db):
            print("... FAILED")
        else:
            set_migration_version_to_latest(conn, db)
    else:
        print(("Database '" + db + "' already exists."))

    for view in os.listdir(viewpath):
        print(("Creating view '" + view + "'..."))
        view_process(conn, db, viewpath + "/" + view)
except socket.error as e:
    print(("Could not connect to CouchDB <" + str(e) + ">! Exiting..."))
    sys.exit(1)
