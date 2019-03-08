# This file is executed on every boot (including wake-boot from deepsleep)

import esp
esp.osdebug(None)
import gc
import webrepl
webrepl.start()
gc.collect()

def do_connect():
    import network
    SSID = '[SSID]'
    PASSWORD = '[KEY]'
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    if ap_if.active():
        ap_if.active(False)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(SSID, PASSWORD)
        while not sta_if.isconnected():
            pass
    print('Network configuration:', sta_if.ifconfig())

do_connect()
