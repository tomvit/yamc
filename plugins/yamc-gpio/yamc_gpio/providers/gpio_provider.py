# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

import time
import RPi.GPIO as GPIO

from yamc.providers import BaseProvider
from yamc import WorkerComponent


class GPIOPulseProvider(BaseProvider, WorkerComponent):
    """
    GPIO pulse provider that collects pulses from a GPIO channel.
    """

    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        self.gpio_channel = self.config.value_int("gpio_channel", min=1, max=40)
        self._pulses = 0
        self.timeout_rising_edge = 1000
        self.timeout_falling_edge = 5000

    def pulses(self, diff=True):
        self.updated_time = time.time()
        self.log.debug("pulses read: %d" % self._pulses)
        return self.diff("pulses", self._pulses) if diff else self._pulses

    def worker(self, exit_event):
        if not self.args.test:
            GPIO.setmode(GPIO.BCM)

            # this assumes that there is a pull down resistor installed
            # if there is no pull down resistor, the line should be as follows:
            # GPIO.setup(self.gpio_channel, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(self.gpio_channel, GPIO.IN)
            self.log.info("Initializing GPIO, channel=%d, GPIO.IN" % self.gpio_channel)
            try:
                while not exit_event.is_set():
                    if GPIO.wait_for_edge(
                        int(self.gpio_channel),
                        GPIO.RISING,
                        timeout=self.timeout_rising_edge,
                    ):
                        if GPIO.wait_for_edge(
                            int(self.gpio_channel),
                            GPIO.FALLING,
                            timeout=self.timeout_falling_edge,
                        ):
                            self._pulses += 1
                        else:
                            self.log.error("No falling edge detected after %d millseconds!" % self.timeout_falling_edge)
            finally:
                self.log.info("Cleaning up GPIO.")
                GPIO.cleanup()
        else:
            self.log.info("Running in test mode, will not collect any pulses.")
            while not exit_event.is_set():
                time.sleep(1)
