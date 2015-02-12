import couchconnection
import json

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
                        if not val.has_key("questionVariant"):
                            ds.append(val)
                    for d in ds:
                        d["questionVariant"] = "lecture"
                    res = conn.json_post(bulk_url, json.dumps({"docs":ds}))
                    result_docs = json.loads(res.read())
                    errors = []
                    for result in result_docs:
                        if result.has_key("error"):
                            errors.append(result)
                    if not errors:
                        # All documents were migrated.
                        # jump out of loop and exit this function
                        break
            print "Migrating all Question documents..."
            migrate_with_temp_view(questions)
            print "Migrating all Answer documents..."
            migrate_with_temp_view(answers)

        # skill_question
        question_migration()
        # bump database version
        current_version = 1
        print bump(current_version)

    if current_version == 1:
        print "Deleting obsolete food vote design document..."
        if not conn.delete(db_url + "/_design/food_vote"):
            print "Food vote design document not found"
        # bump database version
        current_version = 2
        print bump(current_version)

    if current_version == 2:
      print "Deleting obsolete user ranking, understanding, and admin design documents..."
      if not conn.delete(db_url + "/_design/user_ranking"):
          print "User ranking design document not found"
      if not conn.delete(db_url + "/_design/understanding"):
          print "Understanding design document not found"
      if not conn.delete(db_url + "/_design/admin"):
          print "Admin design document not found"
      # bump database version
      current_version = 3
      print bump(current_version)

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
            print result_docs

        print "Fixing freetext answers (abstentions) with missing question variant (#13313)..."
        add_variant_to_freetext_abstention_answers()
        # bump database version
        current_version = 4;
        print bump(current_version)

    if current_version == 4:
      print "Deleting obsolete learning_progress design documents..."
      if not conn.delete(db_url + "/_design/learning_progress_course_answers"):
          print "course_answers design document not found"
      if not conn.delete(db_url + "/_design/learning_progress_maximum_value"):
          print "maximum_value design document not found"
      if not conn.delete(db_url + "/_design/learning_progress_user_values"):
          print "learning_progress_user_values design document not found"
      # bump database version
      current_version = 5
      print bump(current_version)

    if current_version == 5:
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
