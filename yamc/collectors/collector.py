# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import threading
import croniter
import sys
import copy

from datetime import datetime
from yamc import WorkerComponent
from yamc.utils import Map, deep_eval, merge_dicts


class BaseCollector(WorkerComponent):
    def __init__(self, config, component_id):
        from yamc import yamc_scope

        if yamc_scope.writers is None:
            raise Exception(
                "CRITICAL: There are no writers! Have you loaded writers before collectors?"
            )

        super().__init__(config, component_id)
        self.config = config.collector(component_id)
        self.enabled = self.config.value_bool("enabled", default=True)
        self.writers = {}

        # read writer configurations for this this collector
        # the writer objects will be later provided in set_writers method
        for w in self.config.value("writers", default=[]):
            self.writers[w["writer_id"]] = {
                k: v for k, v in w.items() if k != "writer_id"
            }
            self.writers[w["writer_id"]]["__writer"] = None

        for w in yamc_scope.writers.values():
            if w.component_id in self.writers.keys():
                self.writers[w.component_id]["__writer"] = w

        if not self.enabled:
            self.log.debug(f"The collector {component_id} is disabled")

        self.data_def = self.config.value("data", required=False, no_eval=True)
        if self.data_def is None:
            self.data_def = Map(__nod=0)
        if not isinstance(self.data_def, dict) and not callable(
            getattr(self.data_def, "eval", None)
        ):
            raise Exception(
                "The value of data property must be dict or a Python expression!"
            )
        self.max_history = self.config.value_int("max_history", default=120)
        self.history = []

    def add_time(self, data):
        if data.get("time") is None:
            data["time"] = int(time.time())
        return data

    def prepare_data(self, scope=None):
        _data, data = [], None
        if isinstance(self.data_def, dict):
            data = deep_eval(
                Map(self.data_def),
                scope=self.base_scope(custom_scope=scope),
                log=self.log,
                raise_ex=False,
            )
        elif callable(getattr(self.data_def, "eval", None)):
            data = self.data_def.eval(self.base_scope(custom_scope=scope))
        else:
            # this should not really happen
            raise Exception("CRITICAL: Invalid structure of data definition!")
        if isinstance(data, list):
            for d in data:
                _data.append(self.add_time(d))
        elif isinstance(data, dict):
            _data.append(self.add_time(data))
        else:
            raise Exception("The data must be dict or list!")
        if self.max_history > 0:
            self.history += _data
            self.history = self.history[-min(self.max_history, len(self.history)) :]
        return _data

    def write(self, data, scope=None):
        _scope = Map() if scope is None else scope
        _scope.data = data
        for w in self.writers.values():
            if w["__writer"] is not None:
                writer_config = Map({k: v for k, v in w.items() if k != "__writer"})
                w["__writer"].write(
                    self.component_id,
                    data,
                    deep_eval(
                        writer_config,
                        self.base_scope(_scope),
                        log=self.log,
                        raise_ex=False,
                    ),
                )


class CronCollector(BaseCollector):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.schedule = self.config.value_str("schedule", required=True)
        if not croniter.croniter.is_valid(self.schedule):
            raise Exception(
                "The value of schedule property '%s' is not valid!" % self.schedule
            )
        self.log.info("The cron schedule is %s" % (self.schedule))

    def get_time_to_sleep(self, itr):
        while True:
            next_run = itr.get_next(datetime)
            seconds = (next_run - datetime.now()).total_seconds()
            if seconds > 0:
                break
            else:
                self.log.warning(
                    f"The next run of the job {self.component_id} already passed by {seconds} seconds. Trying the next iteration."
                )
        self.log.debug(
            f"The next job of '{self.component_id}' will run at {next_run} (in {seconds} seconds)."
        )
        return seconds

    def worker(self, exit_event):
        itr = croniter.croniter(self.schedule, datetime.now())
        time2sleep = self.get_time_to_sleep(itr)
        while not exit_event.is_set():
            exit_event.wait(time2sleep)
            if not exit_event.is_set():
                self.log.info("Running job '%s'." % self.component_id)
                try:
                    self.write(self.prepare_data())
                except Exception as e:
                    self.log.error(
                        "The job failed due to %s" % (str(e)),
                        exc_info=self.args.debug or self.args.trace,
                    )
                time2sleep = self.get_time_to_sleep(itr)


class EventCollector(BaseCollector):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.source = self.config.value("source", required=True)
        self.log.info(
            "The event sources are: %s" % (", ".join([x.id for x in self.source]))
        )

    def worker(self, exit_event):
        for s in self.source:
            self.log.info(f"Subscribing to events from '{s.id}'")
            s.subscribe(
                lambda x: self.write(
                    self.prepare_data(scope=Map(event=x)), scope=Map(event=x)
                )
            )
        while not exit_event.is_set():
            exit_event.wait(1)
