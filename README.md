# mollusc
Web portal for viewing cowrie logs

## Deployment
Mollusc can be installed on the same machine as your cowrie or it can be installed on a remote server.
If deployed to a remote server multiple honeypots can be fed in.

Mollusc requires a mongo database. this can be installed on the same server or on its own server. 

### Mongo

Mollusc requires a mongo database in order to store analysis results. There are 3 tested configurations

 - Local installation
 
    Follow the official steps to install the correct Mongo v3.2 on your system. (Anything 3.0 or higher will work)
    https://docs.mongodb.org/v3.2/tutorial/install-mongodb-on-ubuntu/
 
 - Remote Installation
 
    Just point your config file at the IP and port as described in the configuration section.
 
 - Offical Mongo Docker Image
    
    Create a container with ```sudo docker run -d -p 27017:27017 --name mollusc-mongo mongo```
    Stop a container with ```sudo docker stop mollusc-mongo```
    Restart a container with ```sudo docker start mollusc-mongo``` 
    
    
### Mongo Authentication
If you are allowing remote connections to your mongo database it is advisable to enable authentication

In order to configure mongo to use authenitcation you need to connect using the mongo shell and create some user accounts. 
First connect to mongo and create an admin user

```
# mongo
> use admin
> db.createUser(
  {
    user: "username",
    pwd: "securepassword",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
  }
)
```

create a cowrie user that can only access its own database

```
> use cowrie
> db.createUser(
  {
    user: "cowrie",
    pwd: "securepassword",
    roles: [ { role: "readWrite", db: "cowrie" }]
  }
)
```

exit mongo  ```exit```

configure the service to set authentication

for ubuntu 14.04 using 

```sudo nano /etc/mongo.conf```

change the security options to match

```
security:
  authorization: enabled
```


For Ubuntu 16.04 using systemd

```sudo nano /etc/systemd/system/mongodb.service```

change the ExecStart line from

```ExecStart=/usr/bin/mongod --quiet --config /etc/mongod.conf```

to

```ExecStart=/usr/bin/mongod --auth --quiet --config /etc/mongod.conf```

### Mollusc Installation

- sudo apt-get install git libjpeg-dev python-dev python-pip python-numpy python-matplotlib geoip-database
- git clone https://github.com/kevthehermit/mollusc
- cd mollusc
- sudo pip install -r requirements.txt
- cp mollusc.conf.sample mollusc.conf

### Mollusc Configuration
The mollusc conf file needs to be populated with all the required information. 

It is important that the mongouri matches the mongo installation and the cowrie configuration as described later. 

Mollusc has web authentication built in. To enable the auth modules follow these steps.

set the enabled flag to true in the conf file

run the following commands from the mollusc directory and follow the prompts
- ```python manage.py migrate```
- ```python manage.py createsuperuser```



In order to use the geo mapping element you need to generate an API key for google maps 
https://developers.google.com/maps/documentation/javascript/get-api-key

and install the maxmind geoip database

- ```wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-City.mmdb.gz```
- ```gzip -d GeoLite2-City.mmdb.gz```
- ```mv GeoLite2-City.mmdb /usr/share/GeoIP/```


Other optional elements can be configured with their own API keys to enable functions. 

### Cowrie Configuration
Your cowrie installations need to be configured to point to mongo database that mollusc is reading. 

In the cowrie.cfg file locate the mongo section and update as required

```
# MongoDB logging module
#
# MongoDB logging requires an extra Python module: pip install pymongo
#
[output_mongodb]
connection_string = mongodb://username:password@host:port/cowrie
database = cowrie
```
If you are not using auth and are local you can use
```
# MongoDB logging module
#
# MongoDB logging requires an extra Python module: pip install pymongo
#
[output_mongodb]
connection_string = mongodb://localhost/cowrie
database = cowrie
```

make sure you install pymongo on your cowrie install if using virtualenv as per the cowrie install guide

- ```source cowrie-env/bin/activate```
- ```pip install pymongo```
- ```deactivate```


Now start cowrie as normal. 


### Migrate Cowrie Logs

If you have JSON logs that are not already in a mongo database you can use the json_migrate script to enter these sessions in to the DB

```python json_migrate.py -l /path/to/cowrie/log -t /path/to/cowrie/ -d cowrie -m 127.0.0.1```

### Running
To start the application run this command from the mollusc directory
```python manage.py runserver 0.0.0.0:8080```
You can replace 0.0.0.0 with a specific IP and 8080 with a suitable port.


## Warnings
To simplify deployment mollusc runs with djangos development server by default. 
This can allow debug messages to be shown externally if enabled on a public IP address. 

To mitigate this there are a couple of options. 

You can disable the development server and run with wsgi / apache 

make sure your entire mollusc directory is in /opt/

mv mollusc/ /opt/

- sudo apt-get install apache2 libapache2-mod-wsgi
- sudo nano /etc/apache2/sites-availiable/mollusc.conf

```
<VirtualHost _default_:80>
    ServerName yourdomainname.com
    Alias /robots.txt /opt/mollusc/web/static/robots.txt
    Alias /favicon.ico /opt/mollusc/web/static/images/favicon.ico
    
    # Static Files
    Alias /static/ /opt/mollusc/web/static/
    <Directory /opt/mollusc/web/static>
      Require all granted
    </Directory>
    
    # The app
    
    WSGIDaemonProcess mollusc user=www-data group=www-data python-path=/opt/mollusc
    WSGIScriptAlias / /opt/mollusc/mollusc/wsgi.py process-group=mollusc application-group=%{GLOBAL}
    
    <Directory /opt/mollusc/mollusc>
      <Files wsgi.py>
        Require all granted
      </Files>
    </Directory>

    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/mollusc_error.log
    CustomLog ${APACHE_LOG_DIR}/mollusc_access.log combined
</VirtualHost>
```

- nano /opt/mollusc/mollusc/settings.py

change debug = True to debug = False

- sudo chown -R www-data:www-data /opt/mollusc
- cd /etc/apache2/sites-availiable
- sudo a2dissite 000-default.conf
- sudo a2ensite mollusc.conf
- sudo service apache2 reload



Or you 
You can edit the settings.py file and modify the allowed hosts file. 

