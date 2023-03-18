# Common utility functions

import datetime
import socket
import logging
import platform
import hashlib

DEV_SERVER='brenta.local'

log = logging.getLogger('utils')

def platform():
    return platform.platform().spli("-")[0]

def epoch_time(datetime_str, format):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime.datetime.strptime(datetime_str, format)-epoch).total_seconds()

def check_hostname(hostname):
    return socket.gethostname() in [hostname, DEV_SERVER]

def format(msg, **kwargs):
    return msg.format(**kwargs)

def handle_error(expr, default):
    try:
        return eval(expr)
    except:
        return default
