# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import time
import json

import paho.mqtt.client as mqtt

from yamc.providers import EventProvider, Event
from yamc import WorkerComponent
from yamc.utils import Map

class MQTTProvider(EventProvider, WorkerComponent):
    '''
    MQTT provider to read events from MQTT broker.
    '''

    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.address = self.config.value_str("address")
        self.name = self.config.value_str("name")
        self.log.info(f"Creating MQTT client with name '{self.name}' and address '{self.address}'")
        self.client = mqtt.Client(self.name)
        self.client.connect(self.address)
        self.client.on_message = self.on_message
        for event_id in self.events:
            self.log.info(f"Subscribing to the topic {event_id}")
            self.client.subscribe(event_id)

    def on_message(self, client, userdata, message):
        try:
            topic = message._topic.decode("utf-8")
            self.log.info(f"Received on_message for topic {topic}")
            events = self.select(topic)
            if events is not None and len(events)>0:
                data = Map(json.loads(str(message.payload.decode("utf-8"))))
                self.log.debug("The data is: " + str(data))
                events[0].update(data)
        except Exception as e:
            self.log.error(str(e))

    def worker(self, exit_event):
        self.client.loop_start()
        try:
            while not exit_event.is_set():
                time.sleep(1)
        finally:
            pass #self.client.loop_end()
