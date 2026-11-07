#!/usr/bin/env python3
# Wiring self-test. Lights each driver channel in turn so a wrong wire is obvious.
# If it prints IN1..IN4 but no LEDs light, the driver has no power
# (check + on physical pin 2, - on physical pin 6).
from gpiozero import OutputDevice
from time import sleep

pins = [OutputDevice(p) for p in (17, 18, 27, 22)]
for i, p in enumerate(pins):
    print("IN%d on" % (i + 1)); p.on(); sleep(1); p.off()
