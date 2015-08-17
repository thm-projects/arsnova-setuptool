#
# This is a one-off script to list all documents containing inline images.
# Once these images are removed from the database, this script can be
# deleted. See #16995 for details.
#
import couchconnection
import json

(db, conn) = couchconnection.arsnova_connection("/etc/arsnova/arsnova.properties")
db_url = "/" + db

documents_with_inline_images = """{ \"map\": \"
	function(doc) {
		var propertyNames = [];

		function pushImage(property) {
			if (doc[property]) {
				propertyNames.push(property);
			}
		}

		if (doc.type == 'skill_question') {
			/* Image uploaded with question */
			pushImage('image');
			/* Backside of a flashcard question */
			pushImage('fcImage');
		}
		if (doc.type == 'skill_question_answer') {
			/* Images uploaded as a freetext answer */
			pushImage('answerImage');
			pushImage('answerThumbnailImage');
		}
		if (doc.type == 'session') {
			/* Logo as part of the session info */
			pushImage('ppLogo');
		}
		if (propertyNames.length) {
			emit(doc._id, {
				type: doc.type,
				images: propertyNames.length,
				totalSizeInBytes: propertyNames.map(function (p) { return doc[p].length; }).reduce(function (a,b) { return a+b; }),
				propertyNames: propertyNames
			});
		}
	}\"
}""".replace('\n', '').replace('\t', '').strip()

res = conn.temp_view(db_url, documents_with_inline_images)
doc = json.loads(res.read())

# Calculate some statistics
document_ids = []
images = 0
documents = 0
total_size = 0
for col in doc["rows"]:
	val = col["value"]
	documents += 1
	images += val["images"]
	total_size += val["totalSizeInBytes"]
	document_ids.append(col["id"].encode('utf8'))

print """
List of documents containing images:
%(document_list)s

Summary:
	documents: %(documents)d
	images: %(images)d
	total size (bytes): %(total_size)d
""" % {"document_list": document_ids, "documents": documents, "images": images, "total_size": total_size}
