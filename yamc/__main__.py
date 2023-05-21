# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import traceback
import logging
import signal

import yamc.config as yamc_config

from yamc.commands import yamc


def signal_quit(signal, frame):
    """
    Function called when process ends when any signal is received. The function
    sets the `exit_event` so that all worker threads using the event can gracefully end.
    """
    log.info("Received signal %d" % signal)
    yamc_config.exit_event.set()


# register `signal_quit` function for all signals.
for sig in ("TERM", "HUP", "INT"):
    signal.signal(getattr(signal, "SIG" + sig), signal_quit)

try:
    log = logging.getLogger("main")
    yamc(prog_name="yamc")
except Exception as e:
    log.error(f"ERROR: {str(e)}")
    if yamc_config.DEBUG:
        print("---")
        traceback.print_exc()
        print("---")
