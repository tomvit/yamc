# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

from yamc.config import Config, read_raw_config
from threading import Event
import logging
import signal
import time

import yamc.config as _config

from yamc import __version__ as version
from yamc import init_scope, start_components, join_components, destroy_components

import click


### common options


@click.command("run", help="Run command.")
@click.option(
    "--config",
    "config",
    metavar="<file>",
    is_flag=False,
    required=True,
    help="Configuration file",
)
@click.option(
    "--env",
    "env",
    metavar="<file>",
    is_flag=False,
    required=False,
    help="Environment variable file",
)
def run(config, env):
    exit_event = Event()

    def signal_quit(signal, frame):
        log.info("Received signal %d" % signal)
        exit_event.set()

    for sig in ("TERM", "HUP", "INT"):
        signal.signal(getattr(signal, "SIG" + sig), signal_quit)

    config = Config(config, env, False, "DEBUG" if _config.DEBUG else "INFO")
    log = logging.getLogger("main")
    log.info(f"Yet another metric collector, yamc v{version}")

    config.init_config()
    log.info(f"The configuration loaded from {config.config_file}")
    log.info("Initializing...")
    init_scope(config)

    log.info("Starting the components.")
    start_components(exit_event)
    try:
        log.info("Running the main loop")
        exit_event.wait()
    finally:
        log.info("Waiting for components' workers to end.")
        join_components()
        log.info("Destroying components.")
        destroy_components()
        log.info("Done.")
