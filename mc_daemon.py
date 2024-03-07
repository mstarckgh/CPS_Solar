"""
author: Matthias Starck
file:   mc_daemon.py
desc:   Skript zum Senden des Signal zum Laden über mqtt.
"""


import paho.mqtt.client as paho
from classes import DB
import datetime as dt
from time import sleep
from random import randint


BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "Ladesaeule/toggle"
CLIENTID = f"ec2-cps-{randint(0, 1000)}"



def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to {BROKER}")
        else:
            print("Failed to connect")

    client = paho.Client(paho.CallbackAPIVersion.VERSION2, clean_session=False, client_id=CLIENTID)
    client.connect(BROKER, PORT)
    return client



def main():
    last_message = ''

    client = connect_mqtt()
    client.loop_start()

    while True:
        current_time = dt.datetime.now()
        last_entry = DB.getVorhersagewert(start=current_time-dt.timedelta(hours=-1, minutes=5), end=current_time-dt.timedelta(hours=-1), ascending=True)[0]
        if last_entry.laden is not None:
            if last_message != last_entry.laden:
                last_message = last_entry.laden
                client.publish(TOPIC, str(last_entry.laden), qos=1)
                print('laden:', last_entry.__dict__)
        elif last_message is not None:
            client.publish(TOPIC, '0', qos=1)
            last_message = None
            print("laden: 0 (None)")

        sleep(1)


if __name__ == '__main__':
    main()
