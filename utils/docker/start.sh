#!/bin/bash
echo Configuring Mollusc
# edit the config file with ENV
cp /opt/mollusc/mollusc.conf.sample /opt/mollusc/mollusc.conf
# Set Mongo URI
sed -i "s|mongodb://localhost|$MONGO_URI|g" /opt/mollusc/mollusc.conf
# Set auth to enabled
sed -i "s|enable = False|enable = $AUTH|g" /opt/mollusc/mollusc.conf
# Set Maps Key
sed -i "s|mapskey|$MAP_KEY|g" /opt/mollusc/mollusc.conf
# Set debug mode
sed -i "s|DEBUG = True|DEBUG = False|g" /opt/mollusc/mollusc/settings.py
echo Printing Config File to screen
cat /opt/mollusc/mollusc.conf
echo
echo Starting Mollusc
chown -R www-data:www-data /opt/mollusc
service apache2 restart


# Tail out the log file
tail -f /opt/mollusc/mollusc.log