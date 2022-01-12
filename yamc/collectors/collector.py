# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import threading
import croniter
import sys

from datetime import datetime
from yamc import WorkerComponent
from yamc.utils import Map

class BaseCollector(WorkerComponent):
    def __init__(self, config, component_id):
        from yamc import yamc_scope
        if yamc_scope.writers is None:
            raise Exception("CRITICAL: There are no writers! Have you loaded writers before collectors?") 

        super().__init__(config, component_id)       
        self.config = config.collector(component_id)  
        self.enabled = self.config.value_bool("enabled", default=True)
        self.writers = {} 
        
        # read writer configurations for this this collector 
        # the writer objects will be later provided in set_writers method
        for w in self.config.value("writers",default=[]):
            self.writers[w["writer_id"]] = {k:v for k,v in w.items() if k!="writer_id"}
            self.writers[w["writer_id"]]["__writer"] = None

        for w in yamc_scope.writers.values():
            if w.component_id in self.writers.keys():
                self.writers[w.component_id]["__writer"] = w
                
        if not self.enabled:
            self.log.debug(f"The collector {component_id} is disabled")
    
    def write(self, data):
        for w in self.writers.values():
            if w["__writer"] is not None:
                w["__writer"].write(self.component_id, data, {k:v for k,v in w.items() if k!="__writer"})
    

class CronCollector(BaseCollector):
    
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.schedule = self.config.value_str("schedule", required=True)
        if not croniter.croniter.is_valid(self.schedule):
            raise Exception("The value of schedule property '%s' is not valid!"%self.schedule)
        self.log.info("The cron schedule is %s"%(self.schedule))
        self.data_def = self.config.value("data", required=True, no_eval=True)
        if not isinstance(self.data_def, dict) and not callable(getattr(self.data_def,"eval",None)):
            raise Exception("The value of data property must be dict or a Python expression!")
        
    def job(self, exit_event):
        
        def _eval_expression(data_def, key):
            v = None
            try: 
                if callable(getattr(data_def[key],"eval",None)):
                    v = data_def[key].eval(self.base_scope())
                else:
                    v = data_def[key]
                if v is None:
                    self.log.warning("A value of field '%s' is None!"%key)
            except Exception as e:
                self.log.error("The python expression evaluation for field '%s' failed due to %s. Setting the value to None"%(key,str(e)))
                v = None
            return v

        def _write_data_point(data_def, data_point):
            if len([v for v in data_point.values() if v is not None])>0:   
                if isinstance(data_def, dict) and data_def.get("time") is not None:
                    data_point["time"] = _eval_expression(data_def, "time")
                if data_point.get("time") is None:
                    data_point["time"] = int(time.time())
                self.log.trace("Dumping data %s"%(str(data_point)))      
                self.write(data_point)
            else:
                self.log.debug("There are no fields to write!")
        
        if not isinstance(self.data_def, dict):
            data = self.data_def.eval(self.base_scope())
            if isinstance(data,list):
                for d in data:
                    _write_data_point(None, d)
            elif isinstance(data, dict):
                _write_data_point(None, data)
            else:
                raise Exception("The data must be list or dict!")
        else:
            # preparare the data
            data_point = {}
            for k,v in self.data_def.items():
                if k == "time":
                    continue
                data_point[k] = _eval_expression(self.data_def, k)
            _write_data_point(self.data_def, data_point)
        
    def get_time_to_sleep(self, itr): 
        while True:
            next_run = itr.get_next(datetime)
            seconds = (next_run-datetime.now()).total_seconds()
            if seconds > 0:
                break
            else:
                self.log.warning(f"The next run of the job {self.component_id} already passed by {seconds} seconds. Trying the next iteration.")
        self.log.debug(f"The next job of '{self.component_id}' will run at {next_run} (in {seconds} seconds).")
        return seconds
        
    def worker(self, exit_event):
        itr = croniter.croniter(self.schedule, datetime.now())
        time2sleep = self.get_time_to_sleep(itr)
        while not exit_event.is_set():
            exit_event.wait(time2sleep)
            if not exit_event.is_set():
                self.log.info("Running job '%s'."%self.component_id)
                try:
                    self.job(exit_event)
                except Exception as e:
                    self.log.error("The job failed due to %s"%(str(e)), exc_info=self.args.debug or self.args.trace)
                time2sleep = self.get_time_to_sleep(itr)
