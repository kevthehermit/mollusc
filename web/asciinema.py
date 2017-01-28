# This is a modified version of the asciienam encoder from cowrie
# Origianal can be found at https://github.com/micheloosterhof/cowrie/blob/master/bin/asciinema

import json
import sys
import struct
import string

OP_OPEN, OP_CLOSE, OP_WRITE, OP_EXEC = 1, 2, 3, 4
TYPE_INPUT, TYPE_OUTPUT, TYPE_INTERACT = 1, 2, 3

COLOR_INTERACT = '\033[36m'
COLOR_INPUT = '\033[33m'
COLOR_RESET = '\033[0m'



def playlog(fd):

    settings = {
        'colorify': True,
        'output': ""
    }

    thelog = {}
    thelog['version'] = 1
    thelog['width'] = 80
    thelog['height'] = 24
    thelog['duration'] = 0.0
    thelog['command'] = "/bin/bash"
    thelog['title'] = "Cowrie Recording"
    theenv = {}
    theenv['TERM'] = "xterm256-color"
    theenv['SHELL'] = "/bin/bash"
    thelog["env"] = theenv
    stdout = []
    thelog["stdout"] = stdout

    ssize = struct.calcsize('<iLiiLL')

    currtty, prevtime, prefdir = 0, 0, 0
    sleeptime = 0.0

    color = None

    while 1:
        try:
            (op, tty, length, dir, sec, usec) = \
                struct.unpack('<iLiiLL', fd.read(ssize))
            data = fd.read(length)
        except struct.error:
            break

        if currtty == 0: currtty = tty

        if str(tty) == str(currtty) and op == OP_WRITE:
            # the first stream seen is considered 'output'
            if prefdir == 0:
                prefdir = dir
            if dir == TYPE_INTERACT:
                color = COLOR_INTERACT
            elif dir == TYPE_INPUT:
                color = COLOR_INPUT
            if dir == prefdir:
                curtime = float(sec) + float(usec) / 1000000
                if prevtime != 0:
                    sleeptime = curtime - prevtime
                prevtime = curtime
                if settings['colorify'] and color:
                    sys.stdout.write(color)

                # Handle Unicode
                try:
                    data = data.decode('unicode-escape')
                except:
                    for char in data:
                        if char not in string.printable:
                            data.replace(char, '.')

                # rtrox: While playback works properly
                #        with the asciinema client, upload
                #        causes mangling of the data due to
                #        newlines being misinterpreted without
                #        carriage returns.
                data = data.replace("\n", "\r\n")

                thedata = [sleeptime, data]
                thelog['duration'] = curtime
                stdout.append(thedata)

                if settings['colorify'] and color:
                    sys.stdout.write(COLOR_RESET)
                    color = None

        elif str(tty) == str(currtty) and op == OP_CLOSE:
            break

    return json.dumps(thelog, indent=4, ensure_ascii=True)
