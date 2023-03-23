# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import sys
import traceback
import json
import logging

import yamc.config as config

from yamc.commands import yamc

try:
    log = logging.getLogger("main")
    yamc(prog_name="yamc")
except Exception as e:
    log.error(f"ERROR: {str(e)}")
    if config.DEBUG:
        print("---")
        traceback.print_exc()
        print("---")
