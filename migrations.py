import couchconnection
import json

(db, conn) = couchconnection.arsnova_connection("/etc/arsnova/arsnova.properties")

migrations_document_id = "arsnova_migrations"
db_url = "/" + db
migrations_url = db_url + "/" + migrations_document_id

def migrate(migration):
    global db_url, migrations_url
    bulk_url = db_url + "/_bulk_docs"
    current_version = migration["version"]
    
    # Changes to 'skill_question' and 'skill_question_answer':
    #   added 'questionVariant' field, defaulting to 'lecture' value
    if current_version == 0:
        def question_migration(view):
            res = conn.get(view)
            doc = json.loads(res.read())
            ds = []
            for col in doc["rows"]:
                val = col["value"]
                if not val.has_key("questionVariant"):
                    ds.append(val)
            for d in ds:
                d["questionVariant"] = "lecture"
            res = conn.post(bulk_url, json.dumps({"docs":ds}), { "Content-Type": "application/json" })
            ress = res.read()
            print ress
        # skill_question
        question_migration(db_url + "/_design/skill_question/_view/by_id")
        # skill_question_answer
        question_migration(db_url + "/_design/answer/_view/by_question_and_user")
        # bump database version
        current_version = 1
        migration["version"] = current_version
        res = conn.put(migrations_url, json.dumps(migration), { "Content-Type": "application/json" })
        ress = res.read()
        print ress
    
    if current_version == 1:
        # next migration goes here
        pass

conn.request("GET", migrations_url)
res = conn.getresponse()
mig = res.read()
if res.status == 404:
    res = conn.post(db_url, json.dumps({"_id":migrations_document_id, "version":0}), { "Content-Type": "application/json" })
    res.read()
    migrate({"version":0})
else:
    migrate(json.loads(mig))
