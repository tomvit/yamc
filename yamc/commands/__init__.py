# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import click

from .run import run
from .plugin import plugin

import yamc.config as config

@click.group()
@click.option(
    "--no-ansi", "no_ansi", is_flag=True, default=False, help="Do not use ANSI colors"
)
@click.option(
    "--debug", "debug", is_flag=True, default=False, help="Print debug information"
)
def yamc(no_ansi, debug):
    if no_ansi:
        config.ANSI_COLORS = False
    if debug:
        config.DEBUG = True


yamc.add_command(run)
yamc.add_command(plugin)
