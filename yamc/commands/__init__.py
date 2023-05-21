# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import click

from .run import run
from .plugin import plugin

import yamc.config as yamc_config


@click.group()
@click.option("--no-ansi", "no_ansi", is_flag=True, default=False, help="Do not use ANSI colors")
@click.option("--debug", "debug", is_flag=True, default=False, help="Print debug information")
def yamc(no_ansi, debug):
    if no_ansi:
        yamc_config.ANSI_COLORS = False
    if debug:
        yamc_config.DEBUG = True


yamc.add_command(run)
yamc.add_command(plugin)
