"""
  Rename to config.py

  Configure:
  - MQTT client
  - Home Assistant Discovery
  - USB P1 serial port
  - Debug level
"""

# [ LOGLEVELS ]
# DEBUG, INFO, WARNING, ERROR, CRITICAL
loglevel = "INFO"

# [ PRODUCTION ]
# True if run in production
# False when running in simulation
PRODUCTION = True

# File below is used when PRODUCTION is set to False
# Simulation file can be created in bash/Linux:
# tail -f /dev/ttyUSB0 > dsmr.raw (wait 10-15sec and hit ctrl-C)
# (assuming that P1 USB is connected as ttyUSB0)
# Add string "EOF" (without quotes) as last line
SIMULATORFILE = "test/s0pcm.raw"

# File where measurement data is stored
# S0PCM module does not have a persistent memory
MEASUREMENTFILE = "measurement.yaml"

# All named inputs will be included in the MQTT message
# All "None" inputs will be excluded from the MQTT message
S0_DEFINITION = {
  "M1" : "jacuzzi",
  "M2" : None,
  "M3" : "water",
  "M4" : None,
  "M5" : None
}

# [ MQTT Parameters ]
# Using local dns names was not always reliable with PAHO
MQTT_BROKER = "192.168.1.1"
MQTT_PORT = 1883
MQTT_CLIENT_UNIQ = 'mqtt-s0pcm'
MQTT_QOS = 1
MQTT_USERNAME = "username"
MQTT_PASSWORD = "password"

# Max nrof MQTT messages per second
# Set to 0 for unlimited rate
MQTT_RATE = 100

if PRODUCTION:
  MQTT_TOPIC_PREFIX = "s0pcm"
else:
  MQTT_TOPIC_PREFIX = "test_s0pcm"


# [ P1 USB serial ]
ser_port = "/dev/ttyACM0"
ser_baudrate = 9600

# [ InfluxDB ]
# Add a influxdb database tag, for Telegraf processing (database:INFLUXDB)
# This is not required for core functionality of this parser
# Set to None if Telegraf is not used
INFLUXDB = "s0pcm"
#INFLUXDB = None

# [ Home Assistant ]
HA_DISCOVERY = True

# only supports one level of hierarchy
HA_MQTT_DISCOVERY_TOPIC_PREFIX = MQTT_TOPIC_PREFIX

# Default is False, removes the auto config message when this program exits
HA_DELETECONFIG = False

# Discovery messages per hour
# At start-up, always a discovery message is send
# Default is 12 ==> 1 message every 5 minutes. If the MQTT broker is restarted
# it can take up to 5 minutes before the dsmr device re-appears in HA
HA_INTERVAL = 12