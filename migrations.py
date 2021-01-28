#!/usr/bin/env python3
import couchconnection
import json
import re
import sys
import urllib.request, urllib.parse, urllib.error

LATEST_MIGRATION_VERSION = 11

(db, conn) = couchconnection.arsnova_connection("/etc/arsnova/arsnova.properties")

migrations_document_id = "arsnova_migrations"
db_url = "/" + db
migrations_url = db_url + "/" + migrations_document_id

def bump(next_version):
    conn.request("GET", migrations_url)
    res = conn.getresponse()
    migration = json.loads(res.read())
    migration["version"] = next_version
    res = conn.json_put(migrations_url, json.dumps(migration))
    return res.read()

def migrate(migration):
    global db_url, migrations_url
    all_docs_url = db_url + "/_all_docs"
    bulk_url = db_url + "/_bulk_docs"
    cleanup_url = db_url + "/_view_cleanup"
    current_version = migration["version"]
    if current_version >= LATEST_MIGRATION_VERSION:
        print("Database is already up to date.")
        sys.exit(0)
    else:
        conn.require_legacy_couchdb_version()

    # Changes to 'skill_question' and 'skill_question_answer':
    #   added 'questionVariant' field, defaulting to 'lecture' value
    if current_version == 0:
        def question_migration():
            questions = "{ \"map\": \"function(doc) { if (doc.type == 'skill_question') emit(doc._id, doc); }\" }"
            answers = "{ \"map\": \"function(doc) { if (doc.type == 'skill_question_answer') emit(doc._id, doc); }\" }"

            # We are doing three steps:
            #   1) Load all documents we are going to migrate in bulk
            #   2) Each document that is not migrated yet is changed
            #   3) Update all changed documents in bulk
            #
            # Because the documents could change in the database while
            # we perform any of these steps, we will get an error for
            # those documents. To solve this we repeat all steps until
            # no more errors occur.
            def migrate_with_temp_view(temp_view):
                while True:
                    res = conn.temp_view(db_url, temp_view)
                    doc = json.loads(res.read())
                    ds = []
                    for col in doc["rows"]:
                        val = col["value"]
                        if "questionVariant" not in val:
                            ds.append(val)
                    for d in ds:
                        d["questionVariant"] = "lecture"
                    res = conn.json_post(bulk_url, json.dumps({"docs":ds}))
                    result_docs = json.loads(res.read())
                    errors = []
                    for result in result_docs:
                        if "error" in result:
                            errors.append(result)
                    if not errors:
                        # All documents were migrated.
                        # jump out of loop and exit this function
                        break
            print("Migrating all Question documents...")
            migrate_with_temp_view(questions)
            print("Migrating all Answer documents...")
            migrate_with_temp_view(answers)

        # skill_question
        question_migration()
        # bump database version
        current_version = 1
        print(bump(current_version))

    if current_version == 1:
        print("Deleting obsolete food vote design document...")
        if not conn.delete(db_url + "/_design/food_vote"):
            print("Food vote design document not found")
        # bump database version
        current_version = 2
        print(bump(current_version))

    if current_version == 2:
      print("Deleting obsolete user ranking, understanding, and admin design documents...")
      if not conn.delete(db_url + "/_design/user_ranking"):
          print("User ranking design document not found")
      if not conn.delete(db_url + "/_design/understanding"):
          print("Understanding design document not found")
      if not conn.delete(db_url + "/_design/admin"):
          print("Admin design document not found")
      # bump database version
      current_version = 3
      print(bump(current_version))

    if current_version == 3:
        def add_variant_to_freetext_abstention_answers():
            answers = "{ \"map\": \"function(doc) { if (doc.type == 'skill_question_answer' && typeof doc.questionVariant === 'undefined' && doc.abstention == true) emit(doc._id, doc.questionId); }\" }"

            # get all bug-affected answer documents
            res = conn.temp_view_with_params(db_url, "?include_docs=true", answers)
            doc = json.loads(res.read())
            questions = []
            answers = []
            for col in doc["rows"]:
                questions.append(col["value"])
                answers.append(col["doc"])
            # bulk fetch all (unique) question documents of which we found problematic answers
            res = conn.json_post(all_docs_url + "?include_docs=true", json.dumps({"keys":list(set(questions))}))
            result_docs = json.loads(res.read())
            # we need to find the variant of each question so that we can put it into the answer document
            questions = []
            for result in result_docs["rows"]:
                questions.append(result["doc"])
            for answer in answers:
                for question in questions:
                    if answer["questionId"] == question["_id"]:
                        answer["questionVariant"] = question["questionVariant"]
            # bulk update the answers
            res = conn.json_post(bulk_url, json.dumps({"docs":answers}))
            result_docs = json.loads(res.read())
            print(result_docs)

        print("Fixing freetext answers (abstentions) with missing question variant (#13313)...")
        add_variant_to_freetext_abstention_answers()
        # bump database version
        current_version = 4;
        print(bump(current_version))

    if current_version == 4:
        print("Deleting obsolete learning_progress design documents...")
        if not conn.delete(db_url + "/_design/learning_progress_course_answers"):
            print("course_answers design document not found")
        if not conn.delete(db_url + "/_design/learning_progress_maximum_value"):
            print("maximum_value design document not found")
        if not conn.delete(db_url + "/_design/learning_progress_user_values"):
            print("learning_progress_user_values design document not found")
        # bump database version
        current_version = 5
        print(bump(current_version))

    if current_version == 5:
        print("Deleting misspelled 'statistic' design document...")
        if not conn.delete(db_url + "/_design/statistic"):
            print("'statistic' design document not found")
        # bump database version
        current_version = 6
        print(bump(current_version))

    if current_version == 6:
        print("Transforming pre-picture-answer freetext questions into text only questions (#15613)...")
        def add_text_answer_to_freetext_questions():
            old_freetext_qs = "{ \"map\": \"function(doc) { if (doc.type == 'skill_question' && doc.questionType == 'freetext' && typeof doc.textAnswerEnabled === 'undefined') emit(doc._id); }\" }"

            # get all bug-affected documents
            res = conn.temp_view_with_params(db_url, "?include_docs=true", old_freetext_qs)
            doc = json.loads(res.read())
            questions = []
            for result in doc["rows"]:
                questions.append(result["doc"])
            # add missing properties
            for question in questions:
                question["imageQuestion"] = False
                question["textAnswerEnabled"] = True
            # bulk update the documents
            res = conn.json_post(bulk_url, json.dumps({"docs":questions}))
            result_docs = json.loads(res.read())
            print(result_docs)

        add_text_answer_to_freetext_questions()
        # bump database version
        current_version = 7
        print(bump(current_version))

    if current_version == 7:
        print("Transforming session documents to new learning progress options format (#15617)...")
        def change_learning_progress_property_on_session():
            sessions = "{ \"map\": \"function(doc) { if (doc.type == 'session' && doc.learningProgressType) emit(doc._id); }\" }"

            res = conn.temp_view_with_params(db_url, "?include_docs=true", sessions)
            doc = json.loads(res.read())
            sessions = []
            for result in doc["rows"]:
                sessions.append(result["doc"])
            # change property 'learningProgressType' to 'learningProgressOptions'
            for session in sessions:
                currentProgressType = session.pop("learningProgressType", "questions")
                progressOptions = { "type": currentProgressType, "questionVariant": "" }
                session["learningProgressOptions"] = progressOptions
            # bulk update sessions
            res = conn.json_post(bulk_url, json.dumps({"docs":sessions}))
            result_docs = json.loads(res.read())
            print(result_docs)

        change_learning_progress_property_on_session()
        # bump database version
        current_version = 8
        print(bump(current_version))

    if current_version == 8:
        print("Migrating DB and LDAP user IDs to lowercase...")
        conn.request("GET", db_url + "/_design/user/_view/all")
        res = conn.getresponse()
        doc = json.loads(res.read())
        affected_users = {}
        unaffected_users = []
        bulk_docs = []

        # Look for user documents where user ID is not in lowercase
        #   1) Delete document if account has not been activated
        #   2) Lock account if a lowercase version already exists
        #   3) Convert user ID to lowercase if only one captitalization exists
        for user_doc in doc["rows"]:
            if user_doc["key"] != user_doc["key"].lower():
                # create a list of user documents since there might be multiple
                # items for different captitalizations
                affected_users.setdefault(user_doc["key"].lower(), []).append(user_doc["value"])
            else:
                unaffected_users.append(user_doc["key"])
        for uid, users in affected_users.items():
            migration_targets = []
            for user in users:
                if "activationKey" in user:
                    print("User %s has not been activated. Deleting document %s..." % (user["username"], user["_id"]))
                    conn.delete(db_url + "/" + user["_id"])
                elif uid in unaffected_users:
                    print("Migration target exists. Locking duplicate user %s (document %s)..." % (user["username"], user["_id"]))
                    user["locked"] = True
                    bulk_docs.append(user)
                else:
                    migration_targets.append(user)
            if len(migration_targets) > 1:
                print("Cannot migrate some users automatically. Conflicting duplicate users found:")
                for user in migration_targets:
                    print("Locking user %s (document %s)..." % (user["username"], user["_id"]))
                    user["locked"] = True
                    bulk_docs.append(user)
            elif migration_targets:
                print("Migrating user %s (document %s)..." % (user["username"], user["_id"]))
                user["username"] = uid
                bulk_docs.append(user)

        # Look for data where assigned user's ID is not in lowercase
        #   1) Migrate if user ID was affected by previous migration step
        #   2) Exclude Facebook and Google account IDs
        #   3) Exclude guest account IDs
        #   4) Migrate all remaining IDs (LDAP)
        def reassign_data(type, user_prop):
            print("Reassigning %s data to migrated users..." % type)
            migration_view = "{ \"map\": \"function(doc) { function check(doc, type, uid) { return doc.type === type && uid !== uid.toLowerCase() && uid.indexOf('Guest') !== 0; } if (check(doc, '%s', doc.%s)) { emit(doc._id, doc); }}\" }" % (type, user_prop)
            res = conn.temp_view(db_url, migration_view)
            doc = json.loads(res.read())
            print("Documents: %d" % len(doc["rows"]))
            for affected_doc in doc["rows"]:
                val = affected_doc["value"]
                print(affected_doc["id"], val[user_prop])
                # exclude Facebook and Google accounts from migration (might be
                # redundant)
                if (not re.match("https?:", val[user_prop]) and not "@" in val[user_prop]) or val[user_prop].lower() in affected_users:
                    val[user_prop] = val[user_prop].lower()
                    bulk_docs.append(val)
                else:
                    print("Skipped %s (Facebook/Google account)" % val[user_prop])

        reassign_data("session", "creator")
        reassign_data("interposed_question", "creator")
        reassign_data("skill_question_answer", "user")
        reassign_data("logged_in", "user")
        reassign_data("motdlist", "username")

        # bulk update users and assignments
        res = conn.json_post(bulk_url, json.dumps({"docs": bulk_docs}))
        if res:
            res.read()
            # bump database version
            current_version = 9
            print(bump(current_version))

    if current_version == 9:
        print("Migrating MotD documents...")
        migration_view = "{ \"map\": \"function(doc) { if (doc.type === 'motd' && doc.audience === 'session' && !doc.sessionId) { emit(null, doc); } }\" }"
        res = conn.temp_view(db_url, migration_view)
        docs = json.loads(res.read())
        print("Documents: %d" % len(docs["rows"]))
        bulk_docs = []
        for affected_doc in docs["rows"]:
            val = affected_doc["value"]
            print(affected_doc["id"], val["motdkey"])
            conn.request("GET", db_url + "/_design/session/_view/by_keyword?key=" + '"%s"' % val["sessionkey"])
            session_res = conn.getresponse()
            session_docs = json.loads(session_res.read())
            if len(session_docs["rows"]) > 0:
                val["sessionId"] = session_docs["rows"][0]["id"]
                bulk_docs.append(val)
            else:
                print("No session document found for " + val["sessionkey"])

        # bulk update MotDs
        res = conn.json_post(bulk_url, json.dumps({"docs": bulk_docs}))
        if res:
            res.read()
            # bump database version
            current_version = 10
            print(bump(current_version))

    if current_version == 10:
        print("Deleting 'sort_order' design document...")
        if not conn.delete(db_url + "/_design/sort_order"):
            print("'sort_order' design document not found")
        # bump database version
        current_version = 11
        print(bump(current_version))

    if current_version == 11:
        # Next migration goes here
        pass

    conn.json_post(cleanup_url)

conn.request("GET", migrations_url)
res = conn.getresponse()
mig = res.read()
if res.status == 404:
    res = conn.json_post(db_url, json.dumps({"_id":migrations_document_id, "version":0}))
    res.read()
    migrate({"version":0})
else:
    migrate(json.loads(mig))
