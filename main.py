import time
import ubinascii
import machine
from machine import Pin,PWM
from umqtt.simple import MQTTClient

# Many ESP8266 boards have active-low "flash" button on GPIO0.
button = Pin(0, Pin.IN)
dat = machine.Pin(12)

# Set pins connected to MOSFETS
pin_blue = PWM(Pin(2), freq=500, duty=0)
pin_red = PWM(Pin(15), freq=500, duty=0)
pin_green = PWM(Pin(13), freq=500, duty=0)

# Default MQTT server to connect to
SERVER = "[Home Assistant Server IP]"
CLIENT_ID = ubinascii.hexlify(machine.unique_id())
USER = b"[Home Assistant Username]"
PASSWORD = b"[Home Assistant Password]"
PORT = 1883

# Light ID and type
LIGHT_ID = b"1" # ID of light 
NAME = b"hackyleds" + LIGHT_ID
TYPE = "flood" # string "strip", "flood"

# Define initial state and empty message queue for sending of messages in mainline loop
MSGQ = [] # Status message queue 
STATE = 0 # int 0,1

# Define coefficients for white balance over different lighting types
if TYPE == "flood":
	RED_COEF = 0.71  # 182,255,200 = cool white.
	GREEN_COEF = 1
	BLUE_COEF = 0.78 # 0.78
if TYPE == "strip":
	RED_COEF = 0.71  # 182,255,200 = cool white.
	GREEN_COEF = 1
	BLUE_COEF = 0.78 # 0.78

# White start state as initial previous state
PREV_STATE = [int(255 * RED_COEF * 4), int(255 * GREEN_COEF * 4), int(255 * BLUE_COEF * 4)] 

# Define command and state topics
STATE_TOPIC_PWR = b"stat/" + NAME + b"/POWER" # b ON, OFF
COMMAND_TOPIC_PWR = b"cmnd/" + NAME + b"/POWER" # b ON, OFF

STATE_TOPIC_DIM = b"stat/" + NAME + b"/DIMMER" # int 0 - 100
COMMAND_TOPIC_DIM = b"cmnd/" + NAME + b"/DIMMER" # int 0 - 100

STATE_TOPIC_EFFECT = b"stat/" + NAME + b"/EFFECT" # int 0-1
COMMAND_TOPIC_EFFECT = b"cmnd/" + NAME + b"/EFFECT" # int 0-1

STATE_TOPIC_RGB = b"stat/" + NAME + b"/RESULT" # b JSON {"ITEM" : "STATE"}
COMMAND_TOPIC_RGB = b"cmnd/" + NAME + b"/COLOR" # b"255,255,255"

# Pause for network
time.sleep_ms(1000)

# Callback for received message
def sub_cb(topic, msg):
	global MSGQ
	global PREV_STATE
	global STATE
	global DIM_LEVEL
	endTopic = topic.split(b'/')[-1] # truncate all but last topic
	
	if endTopic == b'COLOR':
		rgb = msg.split(b',')
		pin_red.duty((int(int(rgb[0]) * RED_COEF * 4) / 100 ) * DIM_LEVEL)
		pin_green.duty((int(int(rgb[1]) * GREEN_COEF * 4) / 100 ) * DIM_LEVEL)
		pin_blue.duty((int(int(rgb[2]) * BLUE_COEF * 4) / 100 ) * DIM_LEVEL)
		MSGQ.append([STATE_TOPIC_RGB, b'{"RED":"' + rgb[0] + b'","GREEN": "' + rgb[1] + b'","BLUE":"' + rgb[2] + b'"}'])
		MSGQ.append([STATE_TOPIC_RGB, rgb[0] + b',' + rgb[1] + b',' + rgb[2]])
		
	if endTopic == b'DIMMER':
		if int(msg) in range(1,100):
			DIM_LEVEL = int(msg)
			pin_red.duty(int(pin_blue.duty()/100) * DIM_LEVEL)
			pin_green.duty(int(pin_green.duty()/100) * DIM_LEVEL)
			pin_blue.duty(int(pin_blue.duty()/100) * DIM_LEVEL)
			MSGQ.append([STATE_TOPIC_DIM, b'{"DIMMER":"' + msg + '"}'])
			MSGQ.append([STATE_TOPIC_DIM, msg])
		
	if endTopic == b'EFFECT':
		# TBA
		MSGQ.append([STATE_TOPIC_EFFECT, b'{"EFFECT":"' + msg + '"}'])
		MSGQ.append([STATE_TOPIC_EFFECT, msg])
		
	if endTopic == b'POWER':
		if msg == b'OFF' and STATE == 1:
			PREV_STATE[0] = pin_red.duty()
			pin_red.duty(0)
			PREV_STATE[1] = pin_green.duty()
			pin_green.duty(0)
			PREV_STATE[2] = pin_blue.duty()
			pin_blue.duty(0)
			MSGQ.append([STATE_TOPIC_PWR, b'{"POWER":"OFF"}'])
			MSGQ.append([STATE_TOPIC_PWR, b'OFF'])
			STATE = 0	
      
		if msg == b'ON' and STATE == 0:
			pin_red.duty(PREV_STATE[0]) 
			pin_green.duty(PREV_STATE[1])
			pin_blue.duty(PREV_STATE[2])
			MSGQ.append([STATE_TOPIC_PWR, b'{"POWER":"ON"}'])
			MSGQ.append([STATE_TOPIC_PWR, b'ON'])
			STATE = 1
      
# main loop
def main(server=SERVER, port=PORT, user=USER, password=PASSWORD):
	global MSGQ
	print("Connecting")
	c = MQTTClient(CLIENT_ID, server, port, user, password)
	try:
		c.connect()
	except OSError as exc:
		machine.reset()

	print("Connected to %s" % server) 
	c.set_callback(sub_cb)
	c.subscribe(COMMAND_TOPIC_PWR)
	c.subscribe(COMMAND_TOPIC_DIMMER)
	c.subscribe(COMMAND_TOPIC_EFFECT)
	c.subscribe(COMMAND_TOPIC_RGB)
	
	# set to off on connect
	pin_red.duty(0)
	pin_green.duty(0)
	pin_blue.duty(0)

	while True:
			c.check_msg()
			if MSGQ != []:
				currItem = MSGQ.pop()
				c.publish(currItem[0], currItem[1])
	c.disconnect()
main()
