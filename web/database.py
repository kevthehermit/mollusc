import json
import pymongo
from bson.objectid import ObjectId
from bson.son import SON
from common import parse_config
from common import convert_date

config = parse_config()

class Database():

    def __init__(self):
        try:
            # Create the connection
            if config['valid']:
                mongo_uri = config['database']['mongo_uri']
            else:
                mongo_uri = 'mongodb://localhost'

            connection = pymongo.MongoClient(mongo_uri)

            # Version Check
            server_version = connection.server_info()['version']
            if int(server_version[0]) < 3:
                raise UserWarning(
                    'Incompatible MongoDB Version detected. Requires 3 or higher. Found {0}'.format(server_version))

            # Connect to Databases.
            moldb = connection[config['database']['dbname']]

            # Get Collections
            self.col_sensors = moldb['sensors']
            self.col_sessions = moldb['sessions']
            self.col_auth = moldb['auth']
            self.col_input = moldb['input']
            self.col_downloads = moldb['downloads']
            self.col_clients = moldb['clients']
            self.col_ttylog = moldb['ttylog']
            self.col_keyfingerprints = moldb['keyfingerprints']
            self.col_event = moldb['event']


            # Index

            self.col_sessions.create_index([('$**', 'text')])


        except Exception as e:
            print 'Error', e


    def get_pagequery(self, collection, start, length, search_term, col_name, order):

        # If we want to search we need to do that first.

        # First run the query with the limits.
        query = self.col_sessions.find()[start:start+length]

        # Order the list

        if order == 1:
            query.sort(col_name, pymongo.ASCENDING)
        else:
            query.sort(col_name, pymongo.DESCENDING)

        rows = []

        if collection == 'sessions':
            for row in query:
                # Time Stuffs
                starttime = convert_date(row['starttime'])
                if row['endtime']:
                    endtime = convert_date(row['endtime'])
                else:
                    endtime = starttime
                time_delta = endtime - starttime
                rows.append([
                    row['session'],
                    row['src_ip'],
                    row['dst_port'],
                    starttime.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    endtime.strftime('%Y-%m-%d %H:%M:%S.%f'),
                    str(time_delta),
                    row['sensor']
                ])


        # return the query

        return rows

    def get_allsessions(self, start=0, length=25, search_term=None, col_name='starttime', order=1):
        #ToDo: This needs optimising a LOT
        if search_term and col_name:
            cursor = self.col_sessions.find({col_name: {"$regex": u"{}".format(search_term)}})
        else:
            cursor = self.col_sessions.find()

        if order == 1:
            cursor.sort(col_name, pymongo.ASCENDING)
        else:
            cursor.sort(col_name, pymongo.DESCENDING)
        sessions = cursor.skip(start).limit(length)

        return [s for s in sessions]

    def get_session(self, search):
        cursor = self.col_sessions.find_one(search)
        return cursor

    def get_timeline(self, starttime, endtime):
        sensors = self.col_sensors.find()
        data = {}
        for sensor in sensors:
            rows = self.col_sessions.find({'sensor': sensor['sensor'], 'starttime': {'$gte': starttime}}, {'starttime': 1})
            data[sensor['sensor']] = [x for x in rows]

        return data


    def find_auth(self, search):
        cursor = self.col_auth.find(search)
        return [x for x in cursor]

    def get_input(self, search):
        cursor = self.col_input.find(search)
        return [x for x in cursor]

    def get_downloads(self, search):
        cursor = self.col_downloads.find(search)
        return [x for x in cursor]

    def get_ttylog(self, search):
        cursor = self.col_ttylog.find_one(search)
        return cursor


    def get_sensors(self):
        sensors = self.col_sensors.find()
        data = []
        for sensor in sensors:
            last = self.col_sessions.find({'sensor': sensor['sensor']}, {'starttime': 1}).sort([('starttime', -1)]).limit(1)
            first = self.col_sessions.find_one()
            data.append({'sensor': sensor['sensor'], 'dst_ip': sensor['dst_ip'], 'last': last[0]['starttime'], 'first':first['starttime'] })
        return data

    def get_users(self):
        users = self.col_auth.find({}, {'username': 1, 'password': 1})
        return [x for x in users]

    ##
    # Counts
    ##

    def count_sessions(self):
        count = self.col_sessions.find().count()
        return count

    def count_passwords(self):
        pipeline = [
            {"$unwind": "$password"},
            {"$group": {"_id": "$password", "count": {"$sum": 1}}},
            {"$sort": SON([("count", -1), ("_id", -1)])}
            ]
        this = list(self.col_auth.aggregate(pipeline))
        return this

    def count_usernames(self):
        pipeline = [
            {"$unwind": "$username"},
            {"$group": {"_id": "$username", "count": {"$sum": 1}}},
            {"$sort": SON([("count", -1), ("_id", -1)])}
            ]
        this = list(self.col_auth.aggregate(pipeline))
        return this

    def count_commands(self):
        pipeline = [
            {"$unwind": "$input"},
            {"$group": {"_id": "$input", "count": {"$sum": 1}}},
            {"$sort": SON([("count", -1), ("_id", -1)])}
            ]
        this = list(self.col_input.aggregate(pipeline))
        return this

    def count_downloads(self):
        pipeline = [
            {"$unwind": "$url"},
            {"$group": {"_id": "$url", "count": {"$sum": 1}}},
            {"$sort": SON([("count", -1), ("_id", -1)])}
            ]
        this = list(self.col_downloads.aggregate(pipeline))
        return this


    ##
    # Feeds
    ##

    def get_feedusernames(self):
        query = self.col_auth.find({}, {'username': 1})
        return [x for x in query]

    def get_feedcommands(self):
        query = self.col_input.find({}, {'input': 1})
        return [x for x in query]

    def get_feedpasswords(self):
        passwords = self.col_auth.find({}, {'password': 1})
        return [x for x in passwords]

    def get_feeddownloads(self):
        query = self.col_downloads.find({}, {'url': 1})
        return [x for x in query]

    def get_feedip(self):
        iplist = self.col_sessions.find({}, {'src_ip': 1})
        return [x for x in iplist]
