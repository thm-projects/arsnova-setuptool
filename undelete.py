import couchconnection
import json

(db, conn) = couchconnection.arsnova_connection("/etc/arsnova/arsnova.properties")

db_url = "/" + db

# Iterate command line arguments (excluding the script file name).
# Each argument is assumed to be an ID that should be undeleted.
for arg in sys.argv[1:]:
	# TODO: Validate _id format
	url = db_url + "/" + arg
	res = conn.get(url)
	doc = json.loads(res.read())
	# only consider deleted documents
	if "error" in doc and doc["reason"] == "deleted":
		# retrieve document meta info
		url = url + "?revs=true&open_revs=all"
		res = conn.get(url)
		body = res.read()
		# remove non-json data, then create object
		clean_body = body[body.find("{"):body.rfind("}")+1]
		doc = json.loads(clean_body)
		# first id is the deleted document, second id (index=1) is the document before it was deleted
		rev_number = doc["_revisions"]["start"] - 1
		rev_hash = doc["_revisions"]["ids"][1]
		last_rev = str(rev_number) + "-" + rev_hash

		url = db_url + "/" + arg + "?rev=" + last_rev
		res = conn.get(url)
		restored_doc = json.loads(res.read())
		if not "error" in restored_doc:
			# successfully restored the document, now push it back to the db
			rev_number = doc["_revisions"]["start"]
			rev_hash = doc["_revisions"]["ids"][0]
			last_rev = str(rev_number) + "-" + rev_hash
			restored_doc["_rev"] = last_rev

			url = db_url + "/" + arg + "?rev=" + last_rev
			res = conn.json_put(url, json.dumps(restored_doc))
			print res.read()
