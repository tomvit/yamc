# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import threading
import time

from .utils import merge_dicts


class BaseComponent:
    """
    Base class for all components.
    """
    def __init__(self, config, component_id):
        self.base_config = config
        self.component_id = component_id
        self.log = logging.getLogger("%s" % (component_id))
        self.enabled = True

    def base_scope(self, custom_scope=None):
        """
        Return the base scope for the component by merging the scope from the main
        configuration, custon functions and `custom_scope` provided as a parameter.
        """
        return merge_dicts(
            self.base_config.scope, self.base_config.custom_functions, custom_scope
        )

    # TODO: the destroy method should be replaced by a standard __del__ method
    def destroy(self):
        pass


class WorkerComponent(BaseComponent):
    """
    The base class for all worker components, that is components that run
    worker threads.
    """
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.thread = None
        self.start_time = None

    def worker(self, exit_event):
        """
        The main method to run work. This should be run in the component's worker thread.
        """
        pass

    def start(self, exit_event):
        """
        Start the worker thread.
        """
        self.log.info(f"Starting the worker thread '{self.component_id}'.")
        self.start_time = time.time()
        self.thread = threading.Thread(
            target=self.worker, args=(exit_event,), daemon=True
        )
        self.thread.start()

    def running(self):
        """
        Return `True` is the worker thread is running and is alive.
        """
        return self.thread is not None and self.thread.is_alive()

    def join(self):
        """
        Call `join` on the worker thread if the worker thread is running. 
        """
        if self.running():
            self.thread.join()
