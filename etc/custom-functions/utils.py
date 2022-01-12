# Common utility functions 

import datetime 
import socket 

DEV_SERVER='brenta.local'

def epoch_time(datetime_str, format):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime.datetime.strptime(datetime_str, format)-epoch).total_seconds()
    
def check_hostname(hostname):
    return socket.gethostname() in [hostname, DEV_SERVER]
    
def echo(v):
    return v