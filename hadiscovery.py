#!/usr/bin/python3

"""
  Send Home Assistant Auto Discovery MQTT messages


        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
import copy
import time
import threading
import json

# Local imports
import config as cfg

# Logging
import __main__
import logging
import os
script = os.path.basename(__main__.__file__)
script = os.path.splitext(script)[0]
logger = logging.getLogger(script + "." + __name__)


class Discovery(threading.Thread):

  def __init__(self, stopper, mqtt, version):
    """
    class init

    Keyword arguments:
    :param threading.Event()    stopper:
    :param mqtt.mqttclient()    mqtt: reference to mqtt client
    :param str                  version: version of the program
    """

    logger.debug(">>")
    super().__init__()
    self.__stopper = stopper
    self.__mqtt = mqtt
    self.__version = version
    self.__interval = 3600/cfg.HA_INTERVAL
    self.__lastmqtt = 0
    self.__listofjsondicts = list()

  def __del__(self):
    logger.debug(">>")

  def __create_discovery_JSON(self):
    """
      Create the HA/MQTT Autodiscovery messages

      https://www.home-assistant.io/docs/mqtt/discovery/
      https://www.home-assistant.io/integrations/sensor/
      https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics

    Returns:
      None
    """
    d = {}

    # create device JSON
    d["name"] = "s0pcm"
    d["unique_id"] = "s0pcm-device"
    d["state_topic"] = cfg.MQTT_TOPIC_PREFIX + "/status"
    d["icon"] = "mdi:home-automation"
    d["device"] = {"name": "s0pcm",
                   "sw_version": self.__version,
                   "model": "s0pcm/s0pcm-mqtt",
                   "manufacturer": "hansij66 @github.com",
                   "identifiers": ["s0pcm"]
                   }
    self.__listofjsondicts.append( copy.deepcopy(d) )

    # Create entries
    d.clear()
    d["unique_id"] = "jacuzzi"
    d["state_topic"] = cfg.MQTT_TOPIC_PREFIX
    d["name"] = "Jacuzzi E consumed"
    d["unit_of_measurement"] = "Wh"
    d["state_class"] = "total"
    d["value_template"] = "{{value_json.jacuzzi}}"
    d["device_class"] = "energy"
    d["icon"] = "mdi:counter"
    d["device"] = {"identifiers": ["s0pcm"]}
    self.__listofjsondicts.append( copy.deepcopy(d))

    d.clear()
    d["unique_id"] = "water"
    d["state_topic"] = cfg.MQTT_TOPIC_PREFIX
    d["name"] = "Water consumed"
    d["unit_of_measurement"] = "L"
    d["value_template"] = "{{value_json.water}}"
    d["device_class"] = "energy"  # Should be none, but generates error in HA
    d["state_class"] = "total"
    d["icon"] = "mdi:counter"
    d["device"] = {"identifiers": ["s0pcm"]}
    self.__listofjsondicts.append(copy.deepcopy(d))

  def run(self):
    """

    Returns:
      None
    """
    logger.debug(">>")

    self.__create_discovery_JSON()

    # infinite loop
    if cfg.HA_DISCOVERY:
      while not self.__stopper.is_set():
        # calculate time elapsed since last MQTT
        t_elapsed = int(time.time()) - self.__lastmqtt

        if t_elapsed > self.__interval:
          for dict in self.__listofjsondicts:
            topic = "homeassistant/sensor/" + cfg.HA_MQTT_DISCOVERY_TOPIC_PREFIX + "/" + dict["unique_id"] + "/config"
            self.__mqtt.do_publish(topic, json.dumps(dict, separators=(',', ':')), retain=True)
            self.__lastmqtt = int(time.time())
        else:
          # wait...
          time.sleep(0.5)

    # If configured, remove MQTT Auto Discovery configuration
    if cfg.HA_DELETECONFIG:
      for dict in self.__listofjsondicts:
        topic = "homeassistant/sensor/" + cfg.MQTT_TOPIC_PREFIX + "/" + dict["unique_id"] + "/config"
        self.__mqtt.do_publish(topic, "")
