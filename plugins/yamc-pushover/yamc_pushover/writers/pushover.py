# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import logging
import requests
import socket

from yamc.writers import Writer, HealthCheckException
from yamc.utils import Map, deep_eval


class PushoverWriter(Writer):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.app_token = self.config.value_str("app_token")
        self.user_token = self.config.value_str("user_token")
        self.pushover_host = self.config.value_str(
            "pushover_host", default="api.pushover.net"
        )
        self.pushover_url = self.config.value_str(
            "pushover_url", default="/1/messages.json"
        )
        if self.config.value("write_interval", None) is None:
            self.write_interval = 0
        self._prev_hash = None

    def healthcheck(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.pushover_host, 443))
        except Exception as e:
            raise HealthCheckException(
                f"Cannot connect to the pushover host {self.pushover_host}!", e
            )
        finally:
            sock.close()

    def items_per_collector(self, items):
        collectors = Map()
        for item in items:
            if not item.collector_id in collectors.keys():
                collectors[item.collector_id] = []
            collectors[item.collector_id].append(
                Map(data=item.data, writer_config=item.writer_config)
            )
        return collectors.items()

    def do_write(self, items):
        for collector, _items in self.items_per_collector(items):
            if len(_items) > 0:
                self.log.debug(
                    f"{collector}: there are more than 1 item, will use the last one."
                )
            item = _items[-1]
            self.log.debug(
                f"{collector}: using the following data to prepare a message: "
                + str(item)
            )

            if not item.writer_config.do_push:
                self.log.debug(
                    f"{collector}: the message will not be sent, do_push was evaluated to False."
                )
                continue

            self.log.info(
                f"{collector}: sending pushover message '{item.writer_config.message}'"
            )
            try:
                r = requests.post(
                    f"https://{self.pushover_host}{self.pushover_url}",
                    data={
                        "token": self.app_token,
                        "user": self.user_token,
                        "message": item.writer_config.message,
                    },
                )
                r.raise_for_status()
                self._prev_hash = item.writer_config.hash
            except requests.exceptions.HTTPError as e:
                raise Exception("Sending message to pushover failed!", e)
            except requests.exceptions.RequestException as e:
                raise HealthCheckException("Sending message to pushover failed!", e)
