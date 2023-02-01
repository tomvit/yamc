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
import json

from yamc.config import Config, read_raw_config
from threading import Event

exit_event = Event()


# gets a lock using domain sockets to prevent this script from running more than once
def get_lock():
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        get_lock._lock_socket.bind("\0yamc-magic-5djwjrfkxsweocosw_")
        return True
    except socket.error:
        return False


def signal_quit(signal, frame):
    log.info("Received signal %d" % signal)
    exit_event.set()


# if not(get_lock()):
#     print("Already running!", file=sys.stderr)
#     sys.exit(1)

for sig in ("TERM", "HUP", "INT"):
    signal.signal(getattr(signal, "SIG" + sig), signal_quit)

# input arguments
parser = argparse.ArgumentParser(
    prog="yamc", description="Yet another metric collector", add_help=True
)

required = parser.add_argument_group("required arguments")
required.add_argument(
    "--config", required=True, help="Configuration file", metavar="<file>"
)

optional = parser.add_argument_group("other optional arguments")
optional.add_argument(
    "--env",
    required=False,
    default=None,
    help="Environment variables file",
    metavar="<file>",
)
optional.add_argument(
    "--test",
    required=False,
    default=False,
    action="store_true",
    help="Run in the test mode with disabled writing activities",
)
optional.add_argument(
    "--show-config",
    required=False,
    default=False,
    help="Show consolidated configurarion before validation",
    action="store_true",
)

logarg = optional.add_mutually_exclusive_group()
logarg.add_argument(
    "--debug",
    required=False,
    default=False,
    action="store_true",
    help="Print debug details in the log",
)
logarg.add_argument(
    "--trace",
    required=False,
    default=False,
    action="store_true",
    help="Print even more details in the log",
)

args = parser.parse_args()
log = None

try:
    if args.show_config:
        config, _, _ = read_raw_config(args.config, args.env)
        print(json.dumps(config, default=lambda x: str(x), indent=4))
        sys.exit(0)

    from yamc import __version__

    config = Config(args.config, args)
    log = logging.getLogger("main")
    log.info("Yet another metric collector, yamc v%s" % __version__)

    from yamc import init_scope, start_components, join_components, destroy_components

    config.init_config()
    log.info("The configuration loaded from %s" % config.config_file)
    log.info("Initializing...")
    init_scope(config)

    log.info("Starting the components.")
    start_components(exit_event)
    try:
        log.info("Running the main loop")
        while not exit_event.is_set():
            time.sleep(0.5)
    finally:
        log.info("Waiting for components' workers to end.")
        join_components()
        log.info("Destroying components.")
        destroy_components()
        log.info("Done.")

except Exception as e:
    if not log:
        sys.stderr.write("ERROR: %s\n" % str(e))
    else:
        log.error(str(e), exc_info=args.debug or args.trace)
