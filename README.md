# ARSnova

ARSnova is a modern approach to Audience Response Systems (ARS).
It is released under the GPLv3 license and is offered as a Software as a Service free of charge.
Head over to [arsnova.eu](https://arsnova.eu/) to see it in action.

![ARSnova](src/site/resources/showcase.png)

This repository is used to initialize the database for ARSnova.

## Usage

To create the database and to install or update the views, simply run:

	./tool.py

If you are updating from an ARSnova version before 2.6,
you also need to run the data migration script:

	./migrations.py

*Note:* These scripts require Python 2. `migrations.py` does not support CouchDB 2.x.
If you still need to run data migrations, make sure to do so before updating CouchDB.
On larger installations, ARSnova might respond with timeout errors when accessed for the first time after running those scripts.
Just give the database system a few minutes to create the updated views in the background in this case.


## Credits

ARSnova is powered by Technische Hochschule Mittelhessen - University of Applied Sciences.
