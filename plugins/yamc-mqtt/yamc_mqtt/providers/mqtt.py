# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import json

import paho.mqtt.client as mqtt

from yamc.providers import EventProvider, Event
from yamc.component import WorkerComponent
from yamc.utils import Map


class MQTTProvider(EventProvider, WorkerComponent):
    """
    MQTT provider reads events from MQTT broker and uses abstract `yamc.providers.EventProvider`
    and `yamc.providers.Event` interfaces. When an event occurs in MQTT, the `MQTTProvider.on_message` method is
    called which in turn updates the yamc event with the sensor data. The yamc event than pushes the data to all its subscribers.
    The subscribers must be of type `yamc.collectors.EventCollector`.
    """

    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.name = self.config.value_str("name")
        self.address = self.config.value_str("address")
        self.port = self.config.value_int("port", default=1883)
        self.keepalive = self.config.value_int("keepalive", default=60)
        self.reconnect_after = self.config.value_int("reconnect_after", default=30)
        self.loop_timeout = self.config.value_int("loop_timeout", default=1)
        self.client = None
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        self.log.info(f"Connected to the MQTT broker at {self.address}:{self.port}")
        for event_id in self.events:
            self.log.info(f"Subscribing to the topic {event_id}")
            self.client.subscribe(event_id)

    def on_disconnect(self, client, userdata, rc):
        self.log.info(f"Disconnected from the MQTT broker.")
        if rc != 0:
            self.log.error("The client was disconnected unexpectedly.")
        self.connected = False

    def on_message(self, client, userdata, message):
        try:
            topic = message._topic.decode("utf-8")
            self.log.info(f"Received on_message for topic {topic}")
            event = self.select_one(topic)
            if event:
                data = Map(json.loads(str(message.payload.decode("utf-8"))))
                self.log.debug("The data is: " + str(data))
                event.update(data)
        except Exception as e:
            self.log.error(str(e))

    def wait_for_connection(self, exit_event, reconnect=False):
        if reconnect or self.client is None or not self.connected:
            if self.client is not None:
                self.client.disconnect()
                self.connected = False
            self.client = mqtt.Client(self.name)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            while not exit_event.is_set():
                try:
                    self.client.connect(
                        self.address, port=self.port, keepalive=self.keepalive
                    )
                    break
                except Exception as e:
                    self.log.error(
                        f"Cannot connect to the MQTT broker at {self.address}:{self.port}. {str(e)}. "
                        + f"Will attemmpt to reconnect after {self.reconnect_after} seconds."
                    )
                    exit_event.wait(self.reconnect_after)

    def worker(self, exit_event):
        self.wait_for_connection(exit_event)
        try:
            while not exit_event.is_set():
                try:
                    self.client.loop(timeout=self.loop_timeout, max_packets=1)
                    if not self.connected:
                        self.wait_for_connection(exit_event)
                except Exception as e:
                    self.log.error(f"Error occurred in the MQTT loop. {str(e)}")
                    self.wait_for_connection(exit_event, reconnect=True)
        finally:
            if self.connected:
                self.client.disconnect()
