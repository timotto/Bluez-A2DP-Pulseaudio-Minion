#!/usr/bin/python

# based on changes to monitor-bluetooth by Domen Puncer <domen@cba.si>
# 2013-06-02 Tim Otto <tim@ubergrund.de>

import gobject
import dbus
import dbus.mainloop.glib
import os
import subprocess

def paConnect(bt_addr):
	cmd = "pactl load-module module-loopback source=bluez_source.%s sink=%s" % (bt_addr,sink)
	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
	(out, err) = proc.communicate()
	if str(out).rstrip().isdigit():
		print "loaded module, nr = %s" % str(out).rstrip()
		bt_addr2 = ":".join(bt_addr.split("_"))
		set_last_addr(bt_addr2)
	else:
		print "failed to load module, stdout=[%s], stderr=[%s]" % (out,err)

def paUnload(modnr):
	cmd = "pactl unload-module %s" % modnr
	os.system(cmd)

def onAudioSourceState(path, state):
	bt_addr = "_".join(path.split('/')[-1].split('_')[1:])
	bt_addr2 = ":".join(bt_addr.split("_"))
	if state == "connecting":
		print "establishing connection with %s" % path
	elif state == "connected":
		print "connection established with %s" % path
	elif state == "playing":
		existing = getModuleIdFor(bt_addr)
		if existing != 0:
			print "loopback module already configured: %s" % existing
			return
		
		print "connection active with %s, configuring pulseaudio" % path
		paConnect(bt_addr)
		
	elif state == "disconnected":
		existing = getModuleIdFor(bt_addr)
		if existing == 0:
			print "no matching loopback-module found"
			return
			
		print "connection lost with %s, configuring pulseaudio" % path
		paUnload(existing)
		
	else:
		print "Unknown state [%s] for AudioSource [%s]" % (state, path)

def connectA2DP(path):
	aud = dbus.Interface (bus.get_object('org.bluez', path), 'org.bluez.AudioSource')
	try:
		print "calling connect on %s" % path
		aud.Connect()
		return
	except:
		print "failed to use %s for A2DP" % path

def onDeviceConnected(path, connected):
	if connected == "1":
		print "device [%s] connected" % path
		connectA2DP(path)
	else:
		print "device [%s] disconnected" % path

def onControlConnected(path, connected):
	if connected == "1":
		print "control [%s] connected" % path
	else:
		print "control [%s] disconnected" % path

def getModuleIdFor(bt_addr):
	wantedSource = "source=bluez_source.%s" % bt_addr
	proc = subprocess.Popen("pactl list short modules", stdout=subprocess.PIPE, shell=True)
	for line in proc.stdout:
		strLine = str(line).rstrip()
		parts = strLine.split()
		if parts[0].isdigit() and parts[1] == "module-loopback" and parts[2] == wantedSource:
			return parts[0]
	return 0

def property_changed(name, value, path, interface):
	iface = interface[interface.rfind(".") + 1:]
	val = str(value)
	#print "{%s.PropertyChanged} [%s] %s = %s" % (iface, path, name, val)

	if iface == "Device" and name == "Connected":
		onDeviceConnected(path, val)
	elif iface == "Control" and name == "Connected":
		onControlConnected(path, val)
	elif iface == "AudioSource" and name == "State":
		onAudioSourceState(path, val)

def object_signal(value, path, interface, member):
    iface = interface[interface.rfind(".") + 1:]
    val = str(value)
    print "{%s.%s} [%s] Path = %s" % (iface, member, path, val)

def set_last_addr(path):
    try:
        f = open('bluez-a2dp-connect.last', 'w')
        f.write(path)
        f.close()
    except:
        print "failed to store last used BT address"
        pass

def get_last_addr():
    try:
        f = open('bluez-a2dp-connect.last', 'r')
        path = f.readline().rstrip('\n')
        f.close()
        return path
    except:
        return ""

def connect_audio(bt_addr):
    list = adapter.ListDevices()
    candidates = []
    for i in list:
        dev = dbus.Interface(bus.get_object("org.bluez", i), "org.bluez.Device")
        prop = dev.GetProperties()
        if prop["Address"] == bt_addr:
            aud = dbus.Interface (bus.get_object('org.bluez', i), 'org.bluez.AudioSource')
            try:
                print "calling connect on %s" % i
                aud.Connect()
                return
            except:
                print "failed to use %s for A2DP" % i

def findPairedPath(bt_addr):
    list = adapter.ListDevices()
    candidates = []
    for i in list:
        dev = dbus.Interface(bus.get_object("org.bluez", i), "org.bluez.Device")
        prop = dev.GetProperties()
        if prop["Address"] == bt_addr:
            return i
    return ""

def getDefaultSink():
	# find default sink
	proc = subprocess.Popen("pactl list short sinks", stdout=subprocess.PIPE, shell=True)
	for line in proc.stdout:
		strLine = str(line).rstrip()
		parts = strLine.split()
		return parts[1]
	
	raise MyError("Failed to find default pulseaudio sink, cannot continue")

if __name__ == '__main__':
	
	sink = getDefaultSink()

	print "Using sink [%s] for A2DP output" % sink

	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

	bus = dbus.SystemBus()
	manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.bluez.Manager")
	adapter = dbus.Interface(bus.get_object("org.bluez", manager.DefaultAdapter()), "org.bluez.Adapter")

	bus.add_signal_receiver(property_changed, bus_name="org.bluez", signal_name = "PropertyChanged", path_keyword="path", interface_keyword="interface")

	last = get_last_addr()
	if last != "":
		path = findPairedPath(last)
		if path != "":
			print "Connecting to last connected device [%s]" % last
			connectA2DP(path)

	mainloop = gobject.MainLoop()
	mainloop.run()

class MyError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)
