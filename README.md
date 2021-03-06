# S0PCM MQTT
MQTT client for s0pcm pulse readers. Written in Python 3.x

Includes Home Assistant MQTT Auto Discovery.
## Usage:
* Adapt path in `s0pcm-mqtt.service` to your install location (default: `/opt/iot/s0pcm`)
* Copy `config.rename.py` to `config.py` and adapt for your configuration (minimal: mqtt ip, username, password)
* `sudo systemctl enable s0pcm-mqtt`
* `sudo systemctl start s0pcm-mqtt`
* adapt `measurement.yaml` totals to current actuals (before starting script)

Use
http://mqtt-explorer.com/
to test & inspect MQTT messages

## Requirements
* paho-mqtt
* pyserial
* pyyaml
* python 3.x

Tested under Linux; there is no reason why it does not work under Windows.

## Licence
GPL v3

## Versions
1.1.7:
* Fix exit code (SUCCESS vs FAILURE)

1.1.6:
* Remove the unspecified Mx values from MQTT message

1.1.5:
* Fixed issue detecting power down of s0pcm module while s0pcm-mqtt parser is running

1.1.3:
* Initial version on github