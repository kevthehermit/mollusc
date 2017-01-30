#!/usr/bin/env python
'''
Copyright (C) 2017 Kevin Breen.
Part of Mollusc
migrate logs from json to mongo
'''

import os
import sys
import json
import pymongo
from optparse import OptionParser

def main():

    def insert_one(collection, event):
        try:
            object_id = collection.insert_one(event).inserted_id
            return object_id
        except Exception as e:
            print 'mongo error - {0}'.format(e)

    def update_one(collection, session, doc):
        try:
            object_id = collection.update({'session': session}, doc)
            return object_id
        except Exception as e:
            print 'mongo error - {0}'.format(e)


    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option("-m", "--mongouri", dest='mongouri', default='127.0.0.1', help="Mongo Connection String")
    parser.add_option("-d", "--dbname", dest='db_name', default='cowrie', help='Database Name')
    parser.add_option("-t", "--ttylogs", dest='ttylogs', default=False, help='Add ttylogs to database')
    parser.add_option("-l", "--logs", dest='log_path', help='JSON Logs Dir')

    (options, args) = parser.parse_args()

    print options

    if not options.log_path:
        print "You need to specify a log path with -l /path/to/cowrie/log/"
        parser.print_help()
        sys.exit()

    # Connect to Mongo

    try:
        mongo_client = pymongo.MongoClient(options.mongouri)
        mongo_db = mongo_client[options.db_name]
        # Define Collections.
        col_sensors = mongo_db['sensors']
        col_sessions = mongo_db['sessions']
        col_auth = mongo_db['auth']
        col_input = mongo_db['input']
        col_downloads = mongo_db['downloads']
        col_input = mongo_db['input']
        col_clients = mongo_db['clients']
        col_ttylog = mongo_db['ttylog']
        col_keyfingerprints = mongo_db['keyfingerprints']
        col_event = mongo_db['event']
    except Exception, e:
        print 'output_mongodb: Error: %s' % str(e)


    for filename in os.listdir(options.log_path):
        print filename
        if filename.startswith('cowrie.json'):
            for line in open(os.path.join(options.log_path, filename)).readlines():
                entry = json.loads(line)

                eventid = entry["eventid"]

                if eventid == 'cowrie.session.connect':
                    # Check if sensor exists, else add it.
                    doc = col_sensors.find_one({'sensor': entry['sensor']})
                    if doc:
                        sensorid = doc['sensor']
                    else:
                        sensorid = insert_one(col_sensors, entry)

                    # Prep extra elements just to make django happy later on
                    entry['starttime'] = entry['timestamp']
                    entry['endtime'] = None
                    entry['sshversion'] = None
                    entry['termsize'] = None
                    print 'Session Created'
                    insert_one(col_sessions, entry)

                elif eventid in ['cowrie.login.success', 'cowrie.login.failed']:
                    insert_one(col_auth, entry)

                elif eventid in ['cowrie.command.success', 'cowrie.command.failed']:
                    insert_one(col_input, entry)

                elif eventid == 'cowrie.session.file_download':
                    # ToDo add a config section and offer to store the file in the db - useful for central logging
                    # we will add an option to set max size, if its 16mb or less we can store as normal,
                    # If over 16 either fail or we just use gridfs both are simple enough.
                    insert_one(col_downloads, entry)

                elif eventid == 'cowrie.client.version':
                    doc = col_sessions.find_one({'session': entry['session']})
                    if doc:
                        doc['sshversion'] = entry['version']
                        update_one(col_sessions, entry['session'], doc)
                    else:
                        pass

                elif eventid == 'cowrie.client.size':
                    doc = col_sessions.find_one({'session': entry['session']})
                    if doc:
                        doc['termsize'] = '{0}x{1}'.format(entry['width'], entry['height'])
                        update_one(col_sessions, entry['session'], doc)
                    else:
                        pass

                elif eventid == 'cowrie.session.closed':
                    doc = col_sessions.find_one({'session': entry['session']})
                    if doc:
                        doc['endtime'] = entry['timestamp']
                        update_one(col_sessions, entry['session'], doc)
                    else:
                        pass

                elif eventid == 'cowrie.log.closed':
                    # ToDo Compress to opimise the space and if your sending to remote db
                    if options.ttylogs:
                        try:
                            new_tty_path = os.path.join(options.ttylogs, entry['ttylog'])
                            with open(new_tty_path) as ttylog:
                                entry['ttylogpath'] = entry['ttylog']
                                entry['ttylog'] = ttylog.read().encode('hex')
                            insert_one(col_ttylog, entry)
                        except Exception as e:
                            print e

                elif eventid == 'cowrie.client.fingerprint':
                    insert_one(col_keyfingerprints, entry)

                # Catch any other event types
                else:
                    insert_one(col_event, entry)





if __name__ == "__main__":
    main()