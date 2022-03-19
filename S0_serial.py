"""
Read S0 Pulse Meter

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

Inspired by:
https://github.com/ualex73/docker-s0pcm-reader

Description
-----------
This small Python application reads the pulse counters of a S0PCM-2 or S0PCM-5 and send the total and
daily counters via MQTT to your favorite home automation like Home Assistant. The S0PCM-2 or 5 are the
S0 Pulse Counter Module sold by http://www.smartmeterdashboard.nl

Pulse vs liter vs m3
--------------------
I use the S0PCM-Reader to measure my water meter and normally in the Netherlands the water usage is
easurement in m3 and not in liters. Only this S0PCM-Reader isn't really aware of liters vs m3, be
cause it counts the pulses. So it is important for you to check how your e.g. water meter is counting
the usage, my Itron water meter send 1 pulse per liter of water. This then means the 'measurement.yaml' file,
which stores the total and daily counters, all should be in liters and not in m3.
The conversion from m3 to liter is easy, because you can just multiple it by 1000.
E.g. 770.123 m3 is 770123 liter.

S0PCM
-----
The following S0PCM (ascii) protocol is used by this S0PCM-Reader, a simple S0PCM telegram:

Header record (once, after start-up):
/a: S0 Pulse Counter V0.6 - 30/30/30/30/30ms

Data record (repeated every interval):
For S0PCM-5: ID:a:I:b:M1:c:d:M2:e:f:M3:g:h:M4:i:j:M5:k:l
For S0PCM-2: ID:a:I:b:M1:c:d:M2:e:f

Legenda:
a -> Unique ID of the S0PCM
b -> interval between two telegrams in seconds, this is set in the firmware at 10 seconds.
c/e/g/i/k -> number of pulses in the last interval of register 1/2/3/4/5
d/f/h/j/l/ -> number of pulses since the last start-up of register 1/2/3/4/5

Data example:
/8237:S0 Pulse Counter V0.6 - 30/30/30/30/30ms
ID:8237:I:10:M1:0:0:M2:0:0:M3:0:0:M4:0:0:M5:0:0


To test in bash :
stty raw -echo < /dev/ttyACM0; cat -vte /dev/ttyACM0
ID:21434:I:10:M1:0:24130:M2:0:0:M3:3:870:M4:0:3:M5:0:0^M$
ID:21434:I:10:M1:0:24130:M2:0:0:M3:1:871:M4:0:3:M5:0:0^M$

S1: Jacuzzi
S2:
S3: Water
S4:
S5:

Also the S0PCM-Reader uses the following default serialport configuration (used by S0PCM-2 and S0PCM-5):
Speed: 9600 baud
Parity: Even
Databits: 7
Stopbit: 1
Xon/Xoff: No
Rts/Cts: No
"""

import serial
import threading
import time
import re

import config as cfg

# Logging
import __main__
import logging
import os

script = os.path.basename(__main__.__file__)
script = os.path.splitext(script)[0]
logger = logging.getLogger(script + "." + __name__)


class TaskReadSerial(threading.Thread):

  def __init__(self, trigger, stopper, telegram):
    """

    Args:
      :param threading.Event() trigger: signals that new telegram is available
      :param threading.Event() stopper: stops thread
      :param list() telegram: dsmr telegram
    """

    logger.debug(">>")
    super().__init__()
    self.__trigger = trigger
    self.__stopper = stopper
    self.__telegram = telegram
    self.__counter = 0

    # [ Serial parameters ]
    if cfg.PRODUCTION:
      self.__tty = serial.Serial()
      self.__tty.port = cfg.ser_port
      self.__tty.baudrate = cfg.ser_baudrate
      self.__tty.bytesize = serial.SEVENBITS
      self.__tty.parity = serial.PARITY_EVEN
      self.__tty.stopbits = serial.STOPBITS_ONE
      self.__tty.xonxoff = 0
      self.__tty.rtscts = 0
      self.__tty.timeout = 20

    try:
      if cfg.PRODUCTION:
        self.__tty.open()
        logger.debug(f"serial {self.__tty.port} opened")
      else:
        self.__tty = open(cfg.SIMULATORFILE, 'rb')

    except Exception as e:
      logger.error(f"ReadSerial: {type(e).__name__}: {str(e)}")
      self.__stopper.set()
      raise ValueError('Cannot open P1 serial port', cfg.ser_port)

  def __del__(self):
    logger.debug(">>")

  def __read_serial(self):
    """
      Opens & Closes serial port
      Reads S0 telegrams; stores in global variable (self.__telegram)
      Sets threading event to signal other clients (parser) that
      new telegram is available.
      In non-production mode, reads telegrams from file

    Returns:
      None
    """
    logger.debug(">>")

    while not self.__stopper.is_set():

      # wait till parser has copied telegram content
      # ...we need the opposite of trigger.wait()...block when set; not available
      while self.__trigger.is_set():
        time.sleep(0.1)

      # add a counter as first field to the list
      self.__counter += 1
      self.__telegram.append(f"{self.__counter}")

      # Decode from binary to ascii
      # Remove CR LF
      line = self.__tty.readline().decode('utf-8').rstrip()
      logger.debug(f"Line read from s0pcm={line}")

      # Only in simulator mode; detect EOF in file
      if (not cfg.PRODUCTION) and line.startswith('EOF'):
        self.__stopper.set()
        logger.debug(f"EOF Detected in {cfg.SIMULATORFILE}")
        break

      # Basic input validation
      #ID:21434:I:10:M1:0:104647:M2:0:0:M3:0:1416:M4:0:56:M5:0:0^M$
      if not re.match(r"^ID:\d+:I:\d+:M1:\d+:\d+:M2:\d+:\d+:M3:\d+:\d+:M4:\d+:\d+:M5:\d+:\d+.*", line):
        logger.warning(f"Unexpected input received from s0pcm module = {line}")
        self.__telegram.clear()
        continue

      # append
      self.__telegram.append(f"{line}")

      # Trigger that new telegram is available for MQTT
      self.__trigger.set()

      # In simulation mode, insert a delay
      if not cfg.PRODUCTION:
        # 0.5sec delay mimics dsmr behaviour, but 2x as fast, which transmits every 1sec a telegram
        time.sleep(0.5)

    logger.debug("<<")

  def run(self):
    logger.debug(">>")
    try:
      # In production, ReadSerial has infinite loop
      # In simulation, ReadSerial will return @ EOF
      self.__read_serial()

    except Exception as e:
      logger.error(f"{e}")

    finally:
      self.__tty.close()
      self.__stopper.set()

    logger.debug("<<")
