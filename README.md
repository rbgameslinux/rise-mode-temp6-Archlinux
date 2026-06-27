# Rise Mode Temp 6 Linux Driver

Driver experimental para Linux do display USB do air cooler **Rise Mode Temp 6 Pro**.

O dispositivo usa um controlador HID da Semico/Ocypus e aparece no Linux como:

```text
1a2c:4984 SEMICO USB Gaming Keyboard
```

O driver atualiza o display com:

- temperatura da CPU, via `psutil`
- potencia aproximada do pacote CPU em watts, via Intel RAPL quando disponivel

## Status

Testado em Ubuntu com kernel Linux e dispositivo:

```text
VID: 1a2c
PID: 4984
Interface HID: 1
Report ID: 0x07
```

O protocolo foi inferido do software Windows oficial (`DeviceDriver.exe`), que usa `HidD_SetFeature`.

## Protocolo HID

O report enviado tem 64 bytes:

```text
byte 0     report ID: 0x07
bytes 1-3  temperatura em centenas/dezenas/unidades
byte 4     unidade: 0 = Celsius, 1 = Fahrenheit
bytes 5-7  potencia em watts em centenas/dezenas/unidades
bytes 8-63 zero
```

Exemplo para `29 C` e `15 W`:

```text
07 00 02 09 00 00 01 05 ...
```

## Requisitos

Ubuntu/Debian:

```bash
sudo apt install python3 python3-psutil
```

Para leitura de potencia, o sistema precisa expor Intel RAPL em:

```text
/sys/class/powercap/intel-rapl*
```

Se RAPL nao estiver disponivel, o driver mostra `0 W`, mas a temperatura continua funcionando.

## Instalacao

Clone o projeto e execute:

```bash
sudo ./install.sh
```

O instalador copia:

- `rise_temp6.py` para `/usr/local/bin/rise_temp6.py`
- `rise-temp6.service` para `/etc/systemd/system/rise-temp6.service`
- `99-rise-temp6.rules` para `/etc/udev/rules.d/99-rise-temp6.rules`

Depois habilita e inicia o servico:

```bash
sudo systemctl enable --now rise-temp6.service
```

## Uso manual

Listar dispositivos HID:

```bash
sudo ./rise_temp6.py list
```

Enviar um valor fixo:

```bash
sudo ./rise_temp6.py send --temp 55 --power 42
```

Atualizar continuamente:

```bash
sudo ./rise_temp6.py watch --sensor coretemp --interval 1
```

## Servico

Ver status:

```bash
systemctl status rise-temp6.service
```

Ver logs:

```bash
journalctl -u rise-temp6.service -f
```

Reiniciar:

```bash
sudo systemctl restart rise-temp6.service
```

Parar:

```bash
sudo systemctl stop rise-temp6.service
```

## Desinstalacao

```bash
sudo ./uninstall.sh
```

## Notas

- O dispositivo se identifica como teclado HID, mas a interface usada pelo display e a interface `1`.
- O script usa `HidD_SetFeature` equivalente via `ioctl(HIDIOCSFEATURE)` em `/dev/hidraw`.
- Este projeto nao e oficial da Rise Mode, Semico ou Ocypus.
