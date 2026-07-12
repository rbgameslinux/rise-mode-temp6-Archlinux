#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Execute como root: sudo ./install.sh" >&2
    exit 1
fi

# Detect distro family
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "${ID_LIKE:-$ID}" in
            *arch*|*manjaro*|*endeavouros*) echo "arch" ;;
            *debian*|*ubuntu*) echo "debian" ;;
            *fedora*|*rhel*) echo "fedora" ;;
            *) echo "unknown" ;;
        esac
    else
        echo "unknown"
    fi
}

# Detect CPU vendor
detect_cpu_vendor() {
    if grep -qi "AuthenticAMD" /proc/cpuinfo 2>/dev/null; then
        echo "amd"
    elif grep -qi "GenuineIntel" /proc/cpuinfo 2>/dev/null; then
        echo "intel"
    else
        echo "unknown"
    fi
}

# Find AUR helper
find_aur_helper() {
    for helper in yay paru trizen yaourt; do
        if command -v "$helper" >/dev/null 2>&1; then
            echo "$helper"
            return
        fi
    done
    echo ""
}

DISTRO=$(detect_distro)
CPU_VENDOR=$(detect_cpu_vendor)
AUR_HELPER=$(find_aur_helper)

echo "Distro detectada: $DISTRO"
echo "CPU detectada: $CPU_VENDOR"

# --- Instalar python-psutil ---
install_psutil() {
    case "$DISTRO" in
        arch)
            if pacman -Qi python-psutil >/dev/null 2>&1; then
                echo "python-psutil ja instalado."
                return
            fi
            echo "Instalando python-psutil..."
            if [ -n "$AUR_HELPER" ]; then
                sudo -u "$SUDO_USER" $AUR_HELPER -S python-psutil --needed --noconfirm
            else
                pacman -S --noconfirm python-psutil
            fi
            ;;
        debian)
            apt-get install -y python3-psutil
            ;;
        fedora)
            dnf install -y python3-psutil
            ;;
        *)
            echo "Instale python-psutil manualmente." >&2
            return 1
            ;;
    esac
}

install_psutil

# --- Instalar zenpower para AMD ---
install_zenpower() {
    if [ "$CPU_VENDOR" != "amd" ]; then
        echo "CPU nao e AMD, pulando zenpower."
        return
    fi

    # Verificar se zenpower ja esta disponivel
    if [ -d /sys/module/zenpower ]; then
        echo "zenpower ja esta carregado."
        return
    fi

    # Verificar se zenpower esta instalado mas nao carregado
    if modinfo zenpower >/dev/null 2>&1; then
        echo "zenpower ja instalado, carregando modulo..."
        modprobe zenpower 2>/dev/null || true
        return
    fi

    # Zenpower nao esta instalado, tentar instalar do AUR
    if [ "$DISTRO" != "arch" ]; then
        echo "zenpower so esta disponivel no AUR (Arch Linux)."
        echo "Instale manualmente: yay -S zenpower"
        return
    fi

    if [ -z "$AUR_HELPER" ]; then
        echo "Nenhum AUR helper encontrado (yay, paru, trizen)."
        echo "Instale zenpower manualmente:"
        echo "  1. Instale um AUR helper: sudo pacman -S --needed git base-devel && git clone https://aur.archlinux.org/yay-bin.git && cd yay-bin && makepkg -si"
        echo "  2. Instale zenpower: yay -S zenpower"
        return
    fi

    echo "Instalando zenpower via $AUR_HELPER (como usuario $SUDO_USER)..."
    sudo -u "$SUDO_USER" $AUR_HELPER -S zenpower --needed --noconfirm

    # Recarregar modulos
    echo "Recarregando modulos..."
    modprobe -r k10temp 2>/dev/null || true
    modprobe zenpower 2>/dev/null || true

    if [ -d /sys/module/zenpower ]; then
        echo "zenpower instalado e carregado com sucesso!"
        # Blacklist k10temp SO DEPOIS de confirmar que zenpower carregou
        if [ ! -f /etc/modprobe.d/zenpower.conf ]; then
            echo "Blacklistando k10temp para evitar conflito..."
            echo "blacklist k10temp" > /etc/modprobe.d/zenpower.conf
        fi
    else
        echo "Aviso: zenpower instalado mas nao conseguiu carregar."
        echo "k10temp permanecera ativo como fallback."
        echo "Reinicie o sistema para tentar novamente."
    fi
}

echo ""
echo "=== Configurando sensor de temperatura ==="
install_zenpower

# --- Detectar sensor disponivel ---
detect_sensor() {
    if [ -d /sys/module/zenpower ]; then
        echo "zenpower"
    elif [ -d /sys/module/k10temp ]; then
        echo "k10temp"
    elif [ -d /sys/module/coretemp ]; then
        echo "coretemp"
    else
        echo ""
    fi
}

SENSOR=$(detect_sensor)
echo ""
if [ -n "$SENSOR" ]; then
    echo "Sensor ativo: $SENSOR"
else
    echo "Sensor: auto-detect (nct6687/amdgpu ou outro disponivel)"
fi

# --- Instalar arquivos ---
echo ""
echo "=== Instalando rise-temp6 ==="

install -m 0755 rise_temp6.py /usr/local/bin/rise_temp6.py
install -m 0644 rise-temp6.service /etc/systemd/system/rise-temp6.service
install -m 0644 99-rise-temp6.rules /etc/udev/rules.d/99-rise-temp6.rules

# Update service file with detected sensor (if any)
if [ -n "$SENSOR" ]; then
    sed -i "s/--interval 1/--sensor $SENSOR --interval 1/" /etc/systemd/system/rise-temp6.service
fi

udevadm control --reload-rules
udevadm trigger --subsystem-match=hidraw || true
systemctl daemon-reload
systemctl enable rise-temp6.service
systemctl restart rise-temp6.service

echo ""
echo "========================================="
echo " Instalado com sucesso!"
if [ -n "$SENSOR" ]; then
    echo " Sensor configurado: $SENSOR"
else
    echo " Sensor: auto-detect (amdgpu ou outro)"
fi
echo "========================================="
echo ""
systemctl --no-pager --full status rise-temp6.service
