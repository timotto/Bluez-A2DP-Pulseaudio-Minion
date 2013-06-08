#!/bin/bash

PIN=31337

cd /home/debian/

case "$1" in
	init)
		while [ ! -L /sys/class/bluetooth/hci0 ]; do
			echo "Waiting for bluetooth device..."
			sleep 1
		done
		sleep 1
		/usr/sbin/hciconfig hci0 piscan
		su -c "/home/debian/start.sh daemon" debian
		;;
	daemon)
		# to start pulseaudio
		pactl list sinks short

		( while [ ! -f /tmp/a2dp.stop ] ; do bluetooth-agent "$PIN" ; done ; ) &
		./a2dp.py | logger -t a2dp &
		echo started
		wait
		;;
	*)
		screen -d -m $0 daemon
		;;
esac

exit 0
