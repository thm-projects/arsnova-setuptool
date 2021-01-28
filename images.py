#!/usr/bin/env python3
#
# This is a one-off script to list all documents containing inline images.
# Once these images are removed from the database, this script can be
# deleted. See #16995 for details.
#
import couchconnection
import json
import base64
import tempfile
import os
import shutil
import sys
import argparse

(db, conn) = couchconnection.arsnova_connection(
    "/etc/arsnova/arsnova.properties")
conn.require_legacy_couchdb_version()
db_url = "/" + db
all_docs_url = db_url + "/_all_docs"

argparser = argparse.ArgumentParser(
    description="CouchDB inline image analyzer.")
argparser.add_argument('--dump', dest='target',
                       help='download all images into target directory')
args = argparser.parse_args()


def load_image_metadata():
    documents_with_inline_images = """{ \"map\": \"
        function(doc) {
            var propertyNames = [];

            function pushImage(property) {
                if (doc[property] && doc[property].indexOf('http') !== 0) {
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
    return json.loads(res.read())


def dump_images(doc, target_dir):
    # Fix 'incorrect padding' error, see http://stackoverflow.com/a/9807138
    def decode_base64(data):
        """Decode base64, padding being optional.

        :param data: Base64 data as an ASCII byte string
        :returns: The decoded byte string.

        """
        missing_padding = 4 - len(data) % 4
        if missing_padding:
            data += b'=' * missing_padding
            return base64.decodestring(data)

    def extract_image_data(str):
        content = str.split(",", 1)
        if len(content) < 2:
            return (None, None)

        header = content[0]
        data = content[1]

        data_prefix = "data:"
        prefix_end = header.find(data_prefix) + len(data_prefix)

        clean_header = header[prefix_end:]
        # format will be "[mime type][;charset=<charset>][;base64]"
        # note that all entries are optional!
        header_entries = clean_header.split(";")

        # Assume sane defaults
        mimetype = "image/jpeg"
        encoding = "base64"
        for entry in header_entries:
            if entry.startswith("charset"):
                continue
            elif entry.startswith("base64"):
                continue
            elif len(entry) > 0:
                mimetype = entry

        extension = mimetype.split("/")[1]
        return (data, extension)

    target_dir = os.path.abspath(target_dir)
    if os.path.exists(target_dir):
        print("Error: Target directory already exists.")
        sys.exit()

    # Which properties of which documents should we examine?
    document_ids = []
    properties = {}
    for col in doc["rows"]:
        val = col["value"]
        properties[col["id"]] = val["propertyNames"]
        document_ids.append(col["id"])

    # bulk fetch all image documents
    res = conn.json_post(all_docs_url + "?include_docs=true",
                         json.dumps({"keys": document_ids}))
    result_docs = json.loads(res.read())
    image_data = {}
    for col in result_docs["rows"]:
        image_data[col["id"]] = []
        doc = col["doc"]
        props = properties[col["id"]]
        for p in props:
            image_data[col["id"]].append({"name": p, "data": doc[p]})

    # dump the images
    temp_dir = tempfile.mkdtemp(prefix="image_dump_couchdb_")
    (temp_dir_path, temp_dir_name) = os.path.split(temp_dir)
    for (k, v) in image_data.items():
        for vi in v:
            filename = k + "." + vi["name"] + ".img"
            fullpath = os.path.join(temp_dir, filename)
            f = open(fullpath, 'w')
            f.write(vi["data"])
            f.close()

    # convert images to native format
    for f in os.listdir(temp_dir):
        filename = os.path.join(temp_dir, f)
        with open(filename, "r") as img:
            (image_data, extension) = extract_image_data(img.read())
            if extension:
                with open(img.name + "." + extension, "wb") as img_bin:
                    img_bin.write(decode_base64(image_data))
        os.remove(filename)

    shutil.move(temp_dir, target_dir)
    image_dir = os.path.join(target_dir, temp_dir_name)
    return image_dir


doc = load_image_metadata()
if args.target:
    dump_images(doc, args.target)

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

print("""
List of documents containing images:
%(document_list)s

Summary:
    documents: %(documents)d
    images: %(images)d
    total size (bytes): %(total_size)d
""" % {"document_list": document_ids, "documents": documents, "images": images, "total_size": total_size})
