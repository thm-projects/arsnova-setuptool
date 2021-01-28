# ARSnova

ARSnova is a modern, web-based approach to Audience Response Systems (ARS).
It is the basis for the [online service Particify](https://particify.de) and released under an Open Source license.

![ARSnova](src/site/resources/showcase.png)

This repository is used to initialize the database for ARSnova 2.
It is no longer necessary for ARSnova 3.


## Usage

To create the database and to install or update the views, simply run:

    ./tool.py

If you are updating from an ARSnova version before 2.6,
you also need to run the data migration script:

    ./migrations.py

*Note:* These scripts require Python 3.2 or later.
The `migrations.py` and `images.py` scripts do not support CouchDB 2 or later.
If you still need to run data migrations, make sure to do so before updating CouchDB.
On larger installations, ARSnova might respond with timeout errors when accessed for the first time after running those scripts.
Just give the database system a few minutes to create the updated views in the background in this case.


## Credits

ARSnova is powered by [Technische Hochschule Mittelhessen - University of Applied Sciences](https://www.thm.de)
and [Particify](https://particify.de).
