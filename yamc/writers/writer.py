# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import os
import sys
import time
import threading
import logging
import re
import ast
import pickle

from queue import Queue
from yamc.utils import Map, randomString
from yamc.component import WorkerComponent


class HealthCheckException(Exception):
    pass


class Writer(WorkerComponent):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.config = config.writer(component_id)

        self.write_interval = self.config.value_int("write_interval", default=10)
        self.healthcheck_interval = self.config.value_int(
            "healthcheck_interval", default=20
        )
        self.batch_size = self.config.value_int("batch_size", default=100)
        self._is_healthy = False
        self.last_healthcheck = 0
        self.queue = Queue()
        self.backlog = Backlog(self, config)
        self.thread = None
        self.write_event = threading.Event()

    def healthcheck(self):
        pass

    def is_healthy(self):
        if (
            not self._is_healthy
            and time.time() - self.last_healthcheck > self.healthcheck_interval
        ):
            try:
                self.last_healthcheck = time.time()
                self.healthcheck()
                self._is_healthy = True
                self.log.info("The healthcheck succeeded.")
            except Exception as e:
                self.log.error("The healthcheck failed on %s" % (str(e)))
                self.log.info("The backlog size is %d." % (self.backlog.size()))
                self._is_healthy = False
        return self._is_healthy

    def write(self, collector_id, data, writer_config):
        """
        Non-blocking write operation. This method is called from a collector and must be non-blocking
        so that the collector can process collecting of measurements
        """
        _data = Map(collector_id=collector_id, data=data, writer_config=writer_config)
        if self.is_healthy():
            self.queue.put(_data)
            if self.write_interval == 0:
                self.write_event.set()
        else:
            self.backlog.put([_data])

    def do_write(self, data):
        """
        Abstract method to write data to a desintation writer
        """
        pass

    def worker(self, exit_event):
        """
        Thread worker method
        """

        def _process_qeue():
            if self.is_healthy() and self.queue.qsize() > 0:
                # create the batch
                batch = []
                while self.queue.qsize() > 0 and len(batch) < self.batch_size:
                    batch.append(self.queue.get())
                    self.queue.task_done()

                # write the batch
                try:
                    self.log.info(
                        "Writing the batch, batch-size=%d, queue-size=%d."
                        % (len(batch), self.queue.qsize())
                    )
                    if not self.base_config.test:
                        self.do_write(batch)
                    else:
                        self.log.info(
                            "Running in test mode, the writing operation is disabled."
                        )
                except HealthCheckException as e:
                    self.log.error(
                        "Cannot write the batch due to writer's problem: %s. The batch will be stored in the backlog."
                        % (str(e)),
                        exc_info=self.base_config.debug,
                    )
                    self._is_healthy = False
                    self.backlog.put(batch)
                except Exception as e:
                    self.log.error(
                        "Cannot write the batch. It will be discarded due to the following error: %s"
                        % (str(e)),
                        exc_info=self.base_config.debug,
                    )

        while not exit_event.is_set():
            _process_qeue()
            if self.is_healthy():
                self.backlog.process()
            exit_event.wait(self.write_interval)

        # process all remaining items in the queue if possible
        self.log.info("Ending the writer thread .")
        _process_qeue()

        # write unprocessed items to the backlog
        if self.queue.qsize() > 0:
            self.log.info(
                "There are %d unprocessed items in the queue of the writer. Writing them all to the backlog."
                % (self.queue.qsize())
            )
            batch = []
            while self.queue.qsize() > 0:
                batch.append(self.queue.get())
                self.queue.task_done()
            self.backlog.put(batch)

        self.log.info("The writer thread ended.")


class Backlog:
    def __init__(self, writer, config):
        self.writer = writer
        self.config = config
        self.log = writer.log
        self.backlog_dir = config.get_dir_path(
            config.data_dir + "/backlog/" + self.writer.component_id
        )
        os.makedirs(self.backlog_dir, exist_ok=True)
        self.refresh()

    def refresh(self):
        files = filter(
            lambda x: os.path.isfile(os.path.join(self.backlog_dir, x))
            and re.match("items_[a-zA-Z0-9]+.data$", x),
            os.listdir(self.backlog_dir),
        )
        files = [f for f in files]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.backlog_dir, x)))
        self.all_files = files

    def put(self, items):
        if self.writer.base_config.test:
            self.log.info("Running in test mode, the backlog item will not be created")
        else:
            file = "items_%s.data" % randomString()
            with open(os.path.join(self.backlog_dir, file), "wb") as f:
                pickle.dump(items, f, protocol=pickle.HIGHEST_PROTOCOL)
            self.all_files.append(file)
            self.log.debug(
                "Writing data to the writer's backlog. The backlog size is %d."
                % (self.size())
            )

    def peek(self, size):
        files = self.all_files[: min(size, len(self.all_files))]
        data = []
        for file in files:
            with open(os.path.join(self.backlog_dir, file), "rb") as f:
                data += pickle.load(f)
        return files, data

    def remove(self, files):
        if not self.writer.base_config.test:
            for file in files:
                os.remove(os.path.join(self.backlog_dir, file))
        else:
            self.log.info(
                "Running in test mode, removing of backlog files is disabled."
            )
        self.all_files = [x for x in self.all_files if x not in files]
        self.log.debug(
            "Removing data from the writer's backlog. The backlog size is %s."
            % (self.size())
        )

    def size(self):
        return len(self.all_files)

    def process(self):
        if self.size() > 0:
            self.log.info(
                "There are %d items in the backlog. Writing items in batches of %d..."
                % (self.size(), self.writer.batch_size)
            )
            while self.size() > 0:
                batch_files, batch = self.peek(self.writer.batch_size)
                try:
                    if not self.writer.base_config.test:
                        self.writer.do_write(batch)
                    else:
                        self.log.info(
                            "Running in test mode, writing of backlog files is disabled (the backlog will be removed from memory only)."
                        )
                    self.remove(batch_files)
                except Exception as e:
                    self.log.error(
                        "Cannot write item from the writer's backlog due to: %s"
                        % (str(e)),
                        exc_info=self.writer.base_config.debug,
                    )
                    self.writer._is_healthy = False
                    break
            self.log.info(
                "The processing of the backlog finished. The backlog size is %s."
                % self.size()
            )
