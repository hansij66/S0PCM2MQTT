"""
  Parses S0 telegrams to MQTT messages
  Queue MQTT messages

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

import threading
import copy
import time
import json
import yaml
import config as cfg

# Logging
import __main__
import logging
import os
script = os.path.basename(__main__.__file__)
script = os.path.splitext(script)[0]
logger = logging.getLogger(script + "." + __name__)


class ParseTelegrams(threading.Thread):
  """
  """

  def __init__(self, trigger, stopper, mqtt, telegram):
    """
    Args:
      :param threading.Event() trigger: signals that new telegram is available
      :param threading.Event() stopper: stops thread
      :param mqtt.mqttclient() mqtt: reference to mqtt worker
      :param list() telegram: dsmr telegram
    """
    logger.debug(">>")
    super().__init__()
    self.__trigger = trigger
    self.__stopper = stopper
    self.__telegram = telegram
    self.__all_values = []
    self.__prev_all_values = []
    self.__measurements = {1: {'total': 0}, 2: {'total': 0}, 3: {'total': 0}, 4: {'total': 0}, 5: {'total': 0}, 'date': 0}
    self.__mqtt = mqtt
    self.__measurements_file_name = ""
    self.__safe_counter = 0

    # Todo fix
    BASEPATH = os.path.dirname(os.path.realpath(__file__))
    self.__measurements_file_name = BASEPATH + "/" + cfg.MEASUREMENTFILE

  def __del__(self):
    logger.debug(">>")

  def __read_measurements(self):
    logger.debug(">>")
    # measurement['date'] = datetime.date.today()

    try:
      with open(self.__measurements_file_name, 'r') as f:
        self.__measurements = yaml.safe_load(f)
    except Exception as e:
      logger.warning(f"File {self.__measurements_file_name} exception {e}")
      return

    logger.debug(f"YAML = {self.__measurements_file_name}")

    logger.debug("<<")

  def __write_measurements(self, throttle=False):
    logger.debug(">>")

    # reduce nrof writes to disk
    if throttle:
      self.__safe_counter += 1
      if self.__safe_counter < 2:
        return
      else:
        self.__safe_counter = 0
        logger.debug("SAVE")

    try:
      with open(self.__measurements_file_name, 'w') as f:
        yaml.dump(self.__measurements, f, default_flow_style=False)
    except Exception as e:
      logger.error(f"File {self.__measurements_file_name} exception {e}")
      return

  def __publish_telegram(self, json_dict):
    # publish the dictionaries per topic

    # make resilient against double forward slashes in topic
    topic = cfg.MQTT_TOPIC_PREFIX
    topic = topic.replace('//', '/')
    message = json.dumps(json_dict, sort_keys=True, separators=(',', ':'))
    self.__mqtt.do_publish(topic, message, retain=False)

  def __decode_telegram_element(self, element, jsonvalues):
    # Split data into an array
    s0array = element.split(':')

    # Capture serial and remove from array (and "I:digit") - ID:21434:I:10:
    s0array.pop(0)
    jsonvalues["serial"] = str(s0array[0])
    s0array.pop(0)
    s0array.pop(0)
    s0array.pop(0)

    # Loop through 5 s0pcm data inputs
    # M1:0:104647:M2:0:0:M3:2:1418:M4:0:56:M5:0:0
    for count in range(5):

      # channel is eg M1
      channel = s0array[0]

      # 2nd element is total since power-on of S0PCM device
      pulsecounter = int(s0array[2])
      jsonvalues[channel] = pulsecounter

      # Remove M1, delta counter and total counter
      s0array.pop(0)
      s0array.pop(0)
      s0array.pop(0)

  def __decode_telegrams(self, telegram):
    """
    Args:
      :param list telegram:

    Returns:
      :rtype: bool
      True: if change detected wrt previous read value
      False: no change detected wrt previous read value

    """
    logger.debug(f">>")
    json_values = dict()

    # epoch, mqtt timestamp
    ts = int(time.time())

    # get counter and remove from telegram list
    counter = telegram[0]
    telegram.pop(0)

    # Build a dict of key:value, for MQTT JSON
    json_values["timestamp"] = ts
    json_values["counter"] = counter

    if cfg.INFLUXDB:
      json_values["database"] = cfg.INFLUXDB

    self.__all_values.clear()

    for element in telegram:
      self.__decode_telegram_element(element, json_values)

    # store all M1..M5 values as list
    for i in range(1, 6):
      self.__all_values.append(json_values["M" + str(i)])

    # One time initialization
    if len(self.__prev_all_values) == 0:
      self.__prev_all_values = copy.deepcopy(self.__all_values)

    # Compare list with M1..M5 values with previous one
    # Skip if there are no changes
    if self.__all_values != self.__prev_all_values:
      for i in range(5):
        # Calculate difference between current and previous measurement
        delta = self.__all_values[i] - self.__prev_all_values[i]

        # Update total
        try:
          self.__measurements[(i + 1)]["total"] += delta
        except IndexError:
          self.__measurements[(i + 1)]["total"] = self.__all_values[i]

      for i in range(1, 6):
        json_values["M" + str(i)] = self.__measurements[i]["total"]

      # replace Mx labels with named labels (see config.py)
      # eg M1 --> jacuzzi
      for i in range(1, 6):
        jsonkey = cfg.S0_DEFINITION["M" + str(i)]
        if jsonkey is not None:
          json_values[jsonkey] = json_values.pop("M" + str(i))

      self.__publish_telegram(json_values)
      self.__measurements["date"] = ts
      self.__write_measurements(True)
      self.__prev_all_values = copy.deepcopy(self.__all_values)

  def run(self):
    logger.debug(">>")

    self.__read_measurements()
    logger.debug(f"YAML = {self.__measurements}")

    while not self.__stopper.is_set():
      # block till event is set, but implement timeout to allow stopper
      self.__trigger.wait(timeout=1)
      if self.__trigger.is_set():
        # Make copy of the telegram, for further parsing
        telegram = copy.deepcopy(self.__telegram)

        # Clear telegram list for next capture by ReadSerial class
        self.__telegram.clear()

        # Clear trigger, serial reader can continue
        self.__trigger.clear()

        self.__decode_telegrams(telegram)

    # write measurements when closing
    self.__write_measurements()
    logger.debug("<<")
