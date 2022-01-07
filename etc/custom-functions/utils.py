# Common utility functions 

import datetime 

def epoch_time(datetime_str, format):
    epoch = datetime.datetime.utcfromtimestamp(0)
    return (datetime.datetime.strptime(datetime_str, format)-epoch).total_seconds()