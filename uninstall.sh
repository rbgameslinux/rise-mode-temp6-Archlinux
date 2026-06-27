#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root: sudo ./uninstall.sh" >&2
    exit 1
fi

systemctl disable --now rise-temp6.service 2>/dev/null || true
rm -f /etc/systemd/system/rise-temp6.service
rm -f /etc/udev/rules.d/99-rise-temp6.rules
rm -f /usr/local/bin/rise_temp6.py

systemctl daemon-reload
udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw || true

echo "rise-temp6 removido."
