# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import threading 
import time 

class BaseComponent():
    def __init__(self, config, component_id):
        self.component_id = component_id
        self.log = logging.getLogger("%s"%(component_id))
        self.args = config.args
    
class WorkerComponent(BaseComponent):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.thread = None
        self.start_time = None        
        
    def worker(self, exit_event):
        pass
    
    def start(self, exit_event):
        self.log.info("Starting the worker thread.")
        self.start_time = time.time()
        self.thread = threading.Thread(target=self.worker, args=(exit_event,), daemon=True)
        self.thread.start()

    def running(self):
        return self.thread is not None and self.thread.is_alive()
    
    def join(self):
        if self.running():
            self.thread.join()

class PythonExpression():
    def __init__(self, expr):
        self.expr_str = expr
        self.expr = self.compile()
        
    def compile(self):
        return compile(self.expr_str, "<string>", "eval")    
        
    def eval(self, scope):
        return eval(self.expr, {}, scope)
        
    def __getstate__(self):
        return (self.expr_str, None)
    
    def __setstate__(self, state):
        self.expr_str,_ = state
        self.expr=self.compile()
        
