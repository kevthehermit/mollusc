from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseServerError, StreamingHttpResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from database import Database
from common import parse_config, convert_date
import logging
from base64 import b64encode
import asciinema
from django.conf import settings
import StringIO
import io
import json
from wordcloud import WordCloud
import geoip2.database
import os
import shodan
import datetime

logger = logging.getLogger(__name__)
config = parse_config()
db = Database()

##
# Page Views
##
# Login Page
def login_page(request):
    try:
        user_name = request.POST['username']
        password = request.POST['password']
        if user_name and password:
            user = authenticate(username=user_name, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('/')
                else:
                    message = "This account is currently disabled. Please check with your admin."
                    return main_page(request, error_line=message)
            else:
                message = "User does not exist or incorrect password."
                return main_page(request, error_line=message)
        else:
            message = "You need to specify a UserName and Password"
            return main_page(request, error_line=message)

    except Exception as error:
        logger.error(error)
        message = "Unable to login to the Web Panel"
        return main_page(request, error_line=message)


# Logout Page
def logout_page(request):
    logout(request)
    return redirect('/')


def main_page(request, error_line=None):
    """
    Returns the main vol page
    :param request:
    :param error_line:
    :return:
    """

    # Add warning for debug mode

    errors = []

    if error_line:
        errors.append(error_line)

    if settings.DEBUG:
        errors.append("You have debug set to TRUE, this can leak sensitive information if exposed on a public IP.")

    # Check for auth
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return render(request, 'index.html', {'reqauth': True,
                                                  'errors': errors
                                                  })
    sensor_list = db.get_sensors()
    endtime = datetime.datetime.now()

    session_list = db.get_pagequery('sessions', 0, 25, None, 'starttime', 1)
    resultcount = db.count_sessions()

    starttime = endtime - datetime.timedelta(days=7)

    timelines = db.get_timeline(starttime.isoformat(), endtime.isoformat())


    #ToDo: There are too many dates here.
    # To mkae it usable just grab the last weeks worth and display this.
    # Then on the sensor page allow a variable time entry

    # Get all dates per sensor for the timeline.
    timeline_string = ''

    for sensor, dates in timelines.iteritems():
        sensor_string = '{{ name: "{0}", data: ['.format(sensor)
        for date in dates:
            sensor_string += 'new Date(\'{0}\'),'.format(date['starttime'])

        sensor_string += '], color: "{0}"}},\n'.format('blue')
        timeline_string += sensor_string

    # Main Table is populated with ajax
    return render(request, 'index.html', {'reqauth': False,
                                          'sensor_list': sensor_list,
                                          'errors': errors,
                                          'timeline': timeline_string,
                                          'session_list': session_list,
                                          'resultcount': resultcount
                                          })

def session_page(request, session_id):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    # These are all the things i need for the session page.

    session_details = db.get_session({'session': session_id})
    auth_list = db.search_auth({'session': session_id})
    input_list = db.search_input({'session': session_id})
    tty_log = db.get_ttylog({'session': session_id})
    download_list = db.search_downloads({'session': session_id})

    # Modify some values

    if 'telnet' in session_details['system']:
        honey_type = 'Telnet'
    elif 'ssh' in session_details['system']:
        honey_type = 'SSH'
    else:
        honey_type = 'Unknown'

    session_details['system'] = honey_type

    if tty_log:
        tty_log['ttylog'] = b64encode(tty_log['ttylog'].decode('hex'))

    return render(request, 'session.html', {'session_details': session_details,
                                            'auth_list': auth_list,
                                            'input_list': input_list,
                                            'tty_log': tty_log,
                                            'download_list': download_list})

def get_ttylog(request, session_id):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    tty_log = db.get_ttylog({'session': session_id})

    if tty_log:
        tty_stream = tty_log['ttylog'].decode('hex')
        logfd = StringIO.StringIO(tty_stream)
        # Now to convert it to asciinema

        json_data = asciinema.playlog(logfd)
    else:
        json_data = {}

    return HttpResponse(json_data)

def ipaddress_page(request, ipadd):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    errors = []
    ip_details = {}
    ip_details['IP'] = ipadd

    # Get the database from
    # https://dev.maxmind.com/geoip/geoip2/geolite2/


    maxmind_city_db = '/usr/share/GeoIP/GeoLite2-City.mmdb'
    if not os.path.exists(maxmind_city_db):
        raise IOError("Unable to locate GeoLite2-City.mmdb")

    reader = geoip2.database.Reader(maxmind_city_db)
    try:
        record = reader.city(ipadd)

        if not record.country.name:
            ip_details['country_name'] = 'Unknown'
        else:
            ip_details['country_name'] = record.country.name

        ip_details['timezone'] = record.location.time_zone

        ip_details['long'] = record.location.longitude
        ip_details['lat'] = record.location.latitude

    except Exception as e:
        errors.append("Geo Lookup Failed: {0}".format(e))
        ip_details['country_name'] = "Unknown"
        ip_details['timezone'] = "Unknown"
        ip_details['lat'] = "Unknown"
        ip_details['long'] = "Unknown"


    # we also need a maps api key

    api_key = config['maps']['api_key']
    if api_key == 'enter key here':
        errors.append('Missing Maps API Key')

    return render(request, 'ipaddress.html', {'ip_details': ip_details, 'errors': errors})


def feeds(request, datatype, format):
    """
    Returns a machine readble list of source IP's
    :param request:
    :param format:
    :return:
    """
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    if format.lower() not in ['csv', 'json', 'list']:
        return main_page(request, error_line='Invalid Feed Format requested')

    # Get data

    data_list = []

    if datatype == 'passwords':
        count = db.count_passwords()
        for row in count:
            data_list.append('{0},{1}'.format(row['_id'], row['count']))
        download_name = 'passwords.csv'

    elif datatype == 'usernames':
        count = db.count_usernames()
        for row in count:
            data_list.append('{0},{1}'.format(row['_id'], row['count']))
        download_name = 'usernames.csv'

    elif datatype == 'commands':
        count = db.count_commands()
        for row in count:
            data_list.append('{0},{1}'.format(row['_id'], row['count']))
        download_name = 'commands.csv'

    elif datatype == 'downloads':
        count = db.count_downloads()
        for row in count:
            data_list.append('{0},{1}'.format(row['_id'], row['count']))
        download_name = 'downloads.csv'

    elif datatype == 'ip':
        ip_list = db.get_feedip()
        data_list = []
        for ip in ip_list:
            data_list.append(ip['src_ip'])
        download_name = "ip_list.txt"

    else:
        return HttpResponseServerError


    if format == 'list':
        # create a basic list
        file_data = '\n'.join(set(data_list))
        # Create the reponse object
        response = HttpResponse(file_data, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="{0}"'.format(download_name)
        return response

    elif format == 'json':
        pass

    elif format == 'csv':
        # create a csv string
        file_data = ','.join(set(data_list))
        # Create the reponse object
        response = HttpResponse(file_data, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="{0}.csv"'.format(download_name[:-3])
        return response


def passwords(request):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')
    count = db.count_passwords()

    word_list = []
    for c in count[:100]:
        size = c['count']
        word_list.append((c['_id'], size))
        #word_list.append({'text': count['_id'], 'size': size})

    word_cloud = WordCloud(background_color="white", width=800, height=300).generate_from_frequencies(word_list)

    image = word_cloud.to_image()

    imgBytes = io.BytesIO()
    image.save(imgBytes, format='PNG')

    b64_image = b64encode(imgBytes.getvalue())

    seq = [x['_id'] for x in count]
    longest = max(seq, key=len)
    shortest = min(seq, key=len)

    return render(request, 'passwords.html', {'count': count[:25],
                                              'count_total': len(count),
                                              'longest': longest,
                                              'shortest': shortest,
                                              'b64_image': b64_image
                                              })

def usernames(request):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    count = db.count_usernames()

    word_list = []
    for c in count[:100]:
        size = c['count']
        word_list.append((c['_id'], size))
        #word_list.append({'text': count['_id'], 'size': size})

    word_cloud = WordCloud(background_color="white", width=800, height=300).generate_from_frequencies(word_list)

    image = word_cloud.to_image()

    imgBytes = io.BytesIO()
    image.save(imgBytes, format='PNG')

    b64_image = b64encode(imgBytes.getvalue())

    seq = [x['_id'] for x in count]
    longest = max(seq, key=len)
    shortest = min(seq, key=len)

    return render(request, 'usernames.html', {'count': count[:25],
                                              'count_total': len(count),
                                              'longest': longest,
                                              'shortest': shortest,
                                              'b64_image': b64_image
                                              })

def commands_page(request):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    count = db.count_commands()
    seq = [x['_id'] for x in count]
    longest = max(seq, key=len)
    shortest = min(seq, key=len)

    return render(request, 'commands.html', {'count': count[:25],
                                              'count_total': len(count),
                                              'longest': longest,
                                              'shortest': shortest,
                                              })

def downloads_page(request):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    count = db.count_downloads()
    seq = [x['_id'] for x in count]
    longest = max(seq, key=len)
    shortest = min(seq, key=len)

    return render(request, 'downloads.html', {'count': count[:25],
                                              'count_total': len(count),
                                              'longest': longest,
                                              'shortest': shortest
                                              })

def sourceip_page(request):
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    errors = []

    # get list of IP's
    ip_list = db.count_sourceip()

    # GeoIP table
    geo_list = db.get_geoip()


    # Lookup table
    lookup = []
    for row in geo_list:
        lookup.append(row['src_ip'])


    # Geo Database
    maxmind_city_db = '/usr/share/GeoIP/GeoLite2-City.mmdb'
    if not os.path.exists(maxmind_city_db):
        raise IOError("Unable to locate GeoLite2-City.mmdb")
    reader = geoip2.database.Reader(maxmind_city_db)


    for ip_dict in ip_list:
        ipadd = ip_dict['_id']
        #if not any(d['src_ip'] == ipadd for d in geo_list):
        if not ipadd in lookup:
            # Create the new entry
            geo_entry = {'src_ip': ipadd}
            try:
                record = reader.city(ipadd)
                if not record.country.name:
                    geo_entry['country_name'] = 'Unknown'
                else:
                    geo_entry['country_name'] = record.country.name
                    geo_entry['timezone'] = record.location.time_zone
                    geo_entry['long'] = record.location.longitude
                    geo_entry['lat'] = record.location.latitude

            except Exception as e:
                geo_entry['country_name'] = "Unknown"
                geo_entry['timezone'] = "Unknown"
                geo_entry['lat'] = "Unknown"
                geo_entry['long'] = "Unknown"

            # add to database
            db.add_geoip(geo_entry)
            # add to geo_list to save a final query
            geo_list.append(geo_entry)

    # we also need a maps api key

    api_key = config['maps']['api_key']
    if api_key == 'enter key here':
        errors.append('Missing Maps API Key')

    # return results
    return render(request, 'sourceip.html', {'geo_list': geo_list, 'api_key': api_key})


@csrf_exempt
def ajax_handler(request, command):
    """
    return data requested by the ajax handler in mollusc.js
    :param request:
    :param command:
    :return:
    """
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return HttpResponse('Auth Required.')

    if command == 'shodan':
        ipadd = request.POST['ipadd']
        if config['shodan']['enabled'].lower() == 'true':
            shodan_key = config['shodan']['api_key']
            shodan_api = shodan.Shodan(shodan_key)
            try:
                host = shodan_api.host(ipadd)
                print host
            except shodan.APIError as e:
                print e

    if command in ['sessions', 'password', 'username', 'command', 'download']:
        dataset = command

        total_sessions = db.count_sessions()
        filtered_sessions = db.count_sessions()

        # Filter before we query
        # If we are paging with datatables
        if 'pagination' in request.POST:
            if 'start' in request.POST:
                start = int(request.POST['start'])
            else:
                start = 0
            if 'length' in request.POST:
                length = int(request.POST['length'])
            else:
                length = 25

            # Searching
            searching = False
            if 'search[value]' in request.POST:
                search_term = request.POST['search[value]']
                if search_term not in ['']:
                    searching = True

            # Sorting
            # Because we dont have a column index we need to create one
            index_table = ['session', 'src_ip', 'dst_port', 'starttime', 'endtime', 'duration', 'success', 'sensor']
            # Column Sort
            col_index = int(request.POST['order[0][column]'])
            col_name = index_table[col_index]
            if request.POST['order[0][dir]'] == 'asc':
                order = 1
            else:
                order = -1

            output = db.get_pagequery(dataset, start, length, search_term, col_name, order)

            if searching:
                filtered_sessions = len(output)

            # Format Data for Tables
            datatables = {
                "draw": int(request.POST['draw']),
                "recordsTotal": total_sessions,
                "recordsFiltered": filtered_sessions,
                "data": output
            }

            return_data = datatables

        # Else return standard 25 rows
        else:
            output = db.get_pagequery('sessions', 0, 25, None, 'starttime', 1)

            rendered_data = render(request, 'session_list.html', {'session_list': output,
                                                                  'resultcount': total_sessions})
            if rendered_data.status_code == 200:
                return_data = rendered_data.content
            else:
                return_data = str(rendered_data.status_code)
        final_javascript = ''
        json_response = {'data': return_data, 'javascript': final_javascript}
        return JsonResponse(json_response, safe=False)
