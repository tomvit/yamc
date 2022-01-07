# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import time
import socket
import sys
import signal
import logging
import traceback

from yamc.config import Config
from threading import Event 

exit_event = Event()

# gets a lock using domain sockets to prevent this script from running more than once
def get_lock():
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        get_lock._lock_socket.bind('\0yamc-magic-5djwjrfkxsweocosw_')
        return True
    except socket.error:
        return False
 
def signal_quit(signal, frame):
    log.info("Received signal %d"%signal) 
    exit_event.set()

# if not(get_lock()): 
#     print("Already running!", file=sys.stderr)
#     sys.exit(1)

for sig in ('TERM', 'HUP', 'INT'):
    signal.signal(getattr(signal, 'SIG'+sig), signal_quit);
  
# input arguments
parser = argparse.ArgumentParser(description='Yet another metric collector', add_help=True)
required = parser.add_argument_group('required arguments')
required.add_argument('--config', required=True, help='Configuration file', metavar='<file>')

logarg = parser.add_mutually_exclusive_group()
logarg.add_argument('--debug', required=False, default=False, action='store_true', help='Print debug details in the log')
logarg.add_argument('--trace', required=False, default=False, action='store_true', help='Print fine grained details in the log')

optional = parser.add_argument_group('optional arguments')
optional.add_argument('--test', required=False, default=False, action='store_true', help='Run in the test mode with disabled writing activities')

args=parser.parse_args()
log = None

try:
    config = Config(args.config, args)

    from yamc import __version__, init_scope, start_components, join_components

    log = logging.getLogger('main')
    log.info("Yet another metric collector, yamc v%s"%__version__)
    log.info("The configuration loaded from %s"%config.config_file)    
    log.info("Initializing...")
    init_scope(config)
    
    log.info("Starting the components.")
    start_components(exit_event)

    log.info("Running the main loop")
    while not exit_event.is_set():
        time.sleep(0.5)

    log.info("Exiting, waiting for the components to end.")
    join_components()

except Exception  as e:
    if not log:
        sys.stderr.write("ERROR: %s\n"%str(e))
    else:
        log.error(str(e))
    if args.debug:
        traceback.print_exc(file=sys.stderr)   
finally:
    log.info("Done.")     



