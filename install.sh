#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root: sudo ./install.sh" >&2
    exit 1
fi

python3 - <<'PY' || {
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("psutil") else 1)
PY
    echo "Dependencia ausente: instale python3-psutil." >&2
    echo "Ubuntu/Debian: sudo apt install python3-psutil" >&2
    exit 1
}

install -m 0755 rise_temp6.py /usr/local/bin/rise_temp6.py
install -m 0644 rise-temp6.service /etc/systemd/system/rise-temp6.service
install -m 0644 99-rise-temp6.rules /etc/udev/rules.d/99-rise-temp6.rules

udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw || true
systemctl daemon-reload
systemctl enable rise-temp6.service
systemctl restart rise-temp6.service

systemctl --no-pager --full status rise-temp6.service
