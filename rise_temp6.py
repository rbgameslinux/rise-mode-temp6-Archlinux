#!/usr/bin/env python3
"""Experimental Linux driver for Rise Mode Temp 6 / Semico HID LCD panels."""

from __future__ import annotations

import argparse
import array
import fcntl
import re
import time
from dataclasses import dataclass
from pathlib import Path


DEFAULT_VENDOR_ID = 0x1A2C
DEFAULT_PRODUCT_ID = 0x4984
DEFAULT_INTERFACE = 1
DEFAULT_REPORT_ID = 0x07
DEFAULT_REPORT_LENGTH = 64


IOC_NRBITS = 8
IOC_TYPEBITS = 8
IOC_SIZEBITS = 14
IOC_DIRBITS = 2

IOC_NRSHIFT = 0
IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS

IOC_WRITE = 1
IOC_READ = 2


def _ioc(direction: int, type_: int, nr: int, size: int) -> int:
    return (
        (direction << IOC_DIRSHIFT)
        | (type_ << IOC_TYPESHIFT)
        | (nr << IOC_NRSHIFT)
        | (size << IOC_SIZESHIFT)
    )


def hid_set_feature(length: int) -> int:
    return _ioc(IOC_READ | IOC_WRITE, ord("H"), 0x06, length)


@dataclass(frozen=True)
class HidrawDevice:
    path: Path
    vendor_id: int
    product_id: int
    interface: int | None
    name: str
    phys: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def _device_properties(hidraw_name: str) -> dict[str, str]:
    uevent = Path("/sys/class/hidraw") / hidraw_name / "device" / "uevent"
    props: dict[str, str] = {}
    for line in _read_text(uevent).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            props[key] = value
    return props


def _interface_number(hidraw_name: str) -> int | None:
    device_link = (Path("/sys/class/hidraw") / hidraw_name / "device").resolve()
    match = re.search(r":1\.(\d+)(?:/|$)", str(device_link))
    if match:
        return int(match.group(1))
    return None


def enumerate_hidraw() -> list[HidrawDevice]:
    devices: list[HidrawDevice] = []
    for path in sorted(Path("/dev").glob("hidraw*")):
        props = _device_properties(path.name)
        hid_id = props.get("HID_ID", "")
        match = re.match(r"^[0-9A-Fa-f]+:([0-9A-Fa-f]+):([0-9A-Fa-f]+)$", hid_id)
        if not match:
            continue
        vendor_id = int(match.group(1), 16)
        product_id = int(match.group(2), 16)
        devices.append(
            HidrawDevice(
                path=path,
                vendor_id=vendor_id,
                product_id=product_id,
                interface=_interface_number(path.name),
                name=props.get("HID_NAME", ""),
                phys=props.get("HID_PHYS", ""),
            )
        )
    return devices


def find_device(vendor_id: int, product_id: int, interface: int | None) -> HidrawDevice:
    candidates = [
        dev
        for dev in enumerate_hidraw()
        if dev.vendor_id == vendor_id
        and dev.product_id == product_id
        and (interface is None or dev.interface == interface)
    ]
    if not candidates:
        wanted = f"{vendor_id:04x}:{product_id:04x}"
        iface = "any" if interface is None else str(interface)
        raise SystemExit(f"Nenhum hidraw encontrado para {wanted}, interface {iface}.")
    if len(candidates) > 1:
        paths = ", ".join(str(dev.path) for dev in candidates)
        raise SystemExit(f"Mais de um candidato encontrado: {paths}. Informe --path.")
    return candidates[0]


def cpu_temperature(sensor: str | None = None) -> float:
    try:
        import psutil
    except ImportError as exc:
        raise SystemExit("psutil nao esta instalado; instale python3-psutil ou use --temp.") from exc

    sensors = psutil.sensors_temperatures()
    if not sensors:
        raise SystemExit("Nenhum sensor de temperatura foi exposto pelo sistema.")

    if sensor:
        needle = sensor.lower()
        for sensor_name, entries in sensors.items():
            if needle in sensor_name.lower() and entries:
                return float(entries[0].current)
        raise SystemExit(f"Nenhum sensor contendo {sensor!r} foi encontrado.")

    for preferred in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
        entries = sensors.get(preferred)
        if entries:
            return float(entries[0].current)

    first_entries = next(iter(sensors.values()))
    return float(first_entries[0].current)


def cpu_usage(interval: float = 0.15) -> int:
    try:
        import psutil
    except ImportError:
        return 0
    return max(0, min(100, int(round(psutil.cpu_percent(interval=interval)))))


def split_digits(value: float | int) -> tuple[int, int, int]:
    number = max(0, min(999, int(round(value))))
    return number // 100, (number // 10) % 10, number % 10


def find_rapl_package() -> Path | None:
    for name_file in Path("/sys/class/powercap").glob("intel-rapl*/name"):
        if _read_text(name_file).strip() == "package-0":
            energy_file = name_file.with_name("energy_uj")
            if energy_file.exists():
                return energy_file
    return None


class PowerReader:
    def __init__(self) -> None:
        self.energy_file = find_rapl_package()
        self.last_energy_uj: int | None = None
        self.last_time: float | None = None

    def read(self) -> float | None:
        if not self.energy_file:
            return None

        try:
            energy_uj = int(_read_text(self.energy_file).strip())
        except ValueError:
            return None

        now = time.monotonic()
        if self.last_energy_uj is None or self.last_time is None:
            self.last_energy_uj = energy_uj
            self.last_time = now
            return None

        delta_energy = energy_uj - self.last_energy_uj
        delta_time = now - self.last_time
        self.last_energy_uj = energy_uj
        self.last_time = now

        if delta_energy < 0 or delta_time <= 0:
            return None
        return (delta_energy / 1_000_000.0) / delta_time


def build_report(temp_celsius: float, power_watts: float = 0, unit: str = "c") -> bytes:
    display_temp = temp_celsius
    unit_flag = 0
    if unit.lower() == "f":
        display_temp = temp_celsius * 9 / 5 + 32
        unit_flag = 1

    report = bytearray(DEFAULT_REPORT_LENGTH)
    report[0] = DEFAULT_REPORT_ID
    report[1], report[2], report[3] = split_digits(display_temp)
    report[4] = unit_flag
    report[5], report[6], report[7] = split_digits(power_watts)
    return bytes(report)


def send_report(path: Path, report: bytes, method: str) -> None:
    with path.open("r+b", buffering=0) as dev:
        if method in ("feature", "both"):
            buf = array.array("B", report)
            fcntl.ioctl(dev.fileno(), hid_set_feature(len(buf)), buf, True)
        if method in ("write", "both"):
            dev.write(report)


def print_devices() -> None:
    devices = enumerate_hidraw()
    if not devices:
        print("Nenhum /dev/hidraw encontrado.")
        return
    for dev in devices:
        interface = "-" if dev.interface is None else dev.interface
        marker = ""
        if (
            dev.vendor_id == DEFAULT_VENDOR_ID
            and dev.product_id == DEFAULT_PRODUCT_ID
            and dev.interface == DEFAULT_INTERFACE
        ):
            marker = "  <-- candidato Rise Temp 6"
        print(
            f"{dev.path} {dev.vendor_id:04x}:{dev.product_id:04x} "
            f"if={interface} name={dev.name!r} phys={dev.phys!r}{marker}"
        )


def resolve_path(args: argparse.Namespace) -> Path:
    if args.path:
        return Path(args.path)
    return find_device(args.vid, args.pid, args.interface).path


def command_send(args: argparse.Namespace) -> None:
    path = resolve_path(args)
    temp = args.temp if args.temp is not None else cpu_temperature(args.sensor)
    power = args.power if args.power is not None else 0
    report = build_report(temp, power, args.unit)
    send_report(path, report, args.method)
    print(
        f"Enviado para {path}: temp={temp:.1f}C power={power:.1f}W "
        f"unit={args.unit.upper()} method={args.method} report={report.hex(' ')}"
    )


def command_watch(args: argparse.Namespace) -> None:
    path = resolve_path(args)
    power_reader = PowerReader()
    print(f"Atualizando {path} a cada {args.interval:.1f}s. Ctrl+C para parar.")
    while True:
        temp = cpu_temperature(args.sensor)
        power = args.power if args.power is not None else power_reader.read()
        if power is None:
            power = 0
        report = build_report(temp, power, args.unit)
        send_report(path, report, args.method)
        print(f"\rtemp={temp:.1f}C power={power:5.1f}W unit={args.unit.upper()}   ", end="", flush=True)
        time.sleep(args.interval)


def add_device_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--vid", type=lambda value: int(value, 16), default=DEFAULT_VENDOR_ID)
    parser.add_argument("--pid", type=lambda value: int(value, 16), default=DEFAULT_PRODUCT_ID)
    parser.add_argument("--interface", type=int, default=DEFAULT_INTERFACE)
    parser.add_argument("--path", help="Caminho hidraw explicito, ex.: /dev/hidraw1")


def add_payload_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--temp", type=float, help="Temperatura Celsius fixa para teste.")
    parser.add_argument("--power", type=float, help="Potencia fixa em watts para teste.")
    parser.add_argument("--sensor", help="Substring do sensor psutil, ex.: coretemp.")
    parser.add_argument("--unit", choices=("c", "f"), default="c")
    parser.add_argument("--method", choices=("feature", "write", "both"), default="feature")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Driver experimental Rise Mode Temp 6 HID.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Lista dispositivos hidraw.")
    list_parser.set_defaults(func=lambda _args: print_devices())

    send_parser = subparsers.add_parser("send", help="Envia uma atualizacao unica ao display.")
    add_device_args(send_parser)
    add_payload_args(send_parser)
    send_parser.set_defaults(func=command_send)

    watch_parser = subparsers.add_parser("watch", help="Atualiza continuamente com temperatura/uso da CPU.")
    add_device_args(watch_parser)
    add_payload_args(watch_parser)
    watch_parser.add_argument("--interval", type=float, default=1.0)
    watch_parser.set_defaults(func=command_watch)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        raise SystemExit(130)
