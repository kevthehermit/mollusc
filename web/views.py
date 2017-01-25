from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseServerError, StreamingHttpResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from database import Database
from common import parse_config, convert_date
import logging
from base64 import b64encode
import asciinema

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

    # Check for auth
    if 'auth' in config:
        if config['auth']['enable'].lower() == 'true' and not request.user.is_authenticated:
            return render(request, 'index.html', {'reqauth': True,
                                                  'error_line': error_line
                                                  })
    sensor_list = db.get_sensors()
    # Main Table is populated with ajax
    return render(request, 'index.html', {'reqauth': False,
                                          'sensor_list': sensor_list,
                                          'error_line': error_line
                                          })

def session_page(request, session_id):
    # These are all the things i need for the session page.

    print 1
    session_details = db.get_session({'session': session_id})
    print 2
    auth_list = db.find_auth({'session': session_id})
    print 3
    input_list = db.get_input({'session': session_id})
    print 4
    tty_log = db.get_ttylog({'session': session_id})
    print 5

    if tty_log:
        tty_log['ttylog'] = b64encode(tty_log['ttylog'].decode('hex'))

    return render(request, 'session.html', {'session_details': session_details,
                                            'auth_list': auth_list,
                                            'input_list': input_list,
                                            'tty_log': tty_log})

def get_ttylog(request, session_id):
    tty_log = db.get_ttylog({'session': session_id})

    if tty_log:
        tty_stream = tty_log['ttylog'].decode('hex')
        with open('/tmp/ttylog.tty', 'wb') as out:
            out.write(tty_stream)
        # Now to convert it to asciinema
        logfd = open('/tmp/ttylog.tty', 'rb')
        json_data = asciinema.playlog(logfd)
    else:
        json_data = {}

    return HttpResponse(json_data)


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

    if command == 'sessions':

        print 10

        total_sessions = db.count_sessions()
        print 11
        filtered_sessions = db.count_sessions()

        print 12
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

            print 13

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

            print 14

            # Get matching Rows
            output = db.get_allsessions(start=start, length=length, search_term=search_term, col_name=col_name, order=order)

            if searching:
                filtered_sessions = len(output)



            print 15

            # Format Data
            rows = []
            for row in output:
                success = False
                auth_rows = db.find_auth({'session': row['session']})
                for auth in auth_rows:
                    if auth['message'].endswith('succeeded'):
                        success = True

                # Time Stuffs
                starttime = convert_date(row['starttime'])
                endtime = convert_date(row['endtime'])

                time_delta = endtime - starttime

                rows.append([
                    row['session'],
                    row['src_ip'],
                    row['dst_port'],
                    starttime.strftime('%Y-%m-%d %H:%M:%S.%f'), #row['starttime'],
                    endtime.strftime('%Y-%m-%d %H:%M:%S.%f'), #row['endtime'],
                    str(time_delta), #'abc Seconds',
                    success,
                    row['sensor']
                ])

            print 16
            datatables = {
                "draw": int(request.POST['draw']),
                "recordsTotal": total_sessions,
                "recordsFiltered": filtered_sessions,
                "data": rows
            }

            return_data = datatables

        # Else return standard 25 rows
        else:

            print 21

            output = db.get_allsessions(start=0, length=25)

            rows = []

            print 22

            # Check if a session had a valid auth

            # This is SLOW

            for row in output:
                success = 'N/A'

                #auth_rows = db.find_auth({'session': row['session']})
                #for auth in auth_rows:
                #    if auth['message'].endswith('succeeded'):
                #        success = True
                row['success'] = success


                print 23
                # Time formatting
                starttime = convert_date(row['starttime'])
                endtime = convert_date(row['endtime'])
                time_delta = endtime - starttime

                row['starttime'] = starttime.strftime('%Y-%m-%d %H:%M:%S.%f')
                row['endtime'] = endtime.strftime('%Y-%m-%d %H:%M:%S.%f')
                row['duration'] = str(time_delta)
                rows.append(row)

            rendered_data = render(request, 'session_list.html', {'session_list': rows,
                                                                   'resultcount': total_sessions})
            if rendered_data.status_code == 200:
                return_data = rendered_data.content
            else:
                return_data = str(rendered_data.status_code)

        final_javascript = ''

        json_response = {'data': return_data, 'javascript': final_javascript}

        return JsonResponse(json_response, safe=False)
