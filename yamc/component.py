# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import threading
import time

from .utils import merge_dicts


class BaseComponent:
    def __init__(self, config, component_id):
        self.base_config = config
        self.component_id = component_id
        self.log = logging.getLogger("%s" % (component_id))
        self.args = config.args
        self.enabled = True

    def base_scope(self, custom_scope=None):
        from yamc import yamc_scope

        return merge_dicts(yamc_scope, self.base_config.custom_functions, custom_scope)

    def destroy(self):
        pass


class WorkerComponent(BaseComponent):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.thread = None
        self.start_time = None

    def worker(self, exit_event):
        pass

    def start(self, exit_event):
        self.log.info(f"Starting the worker thread '{self.component_id}'.")
        self.start_time = time.time()
        self.thread = threading.Thread(
            target=self.worker, args=(exit_event,), daemon=True
        )
        self.thread.start()

    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def join(self):
        if self.running():
            self.thread.join()
