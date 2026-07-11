# Rise Mode Temp 6 Linux Driver (Arch Linux)

Driver experimental para Linux do display USB do air cooler **Rise Mode Temp 6 Pro**.

Adaptado para **Arch Linux** e derivados (Manjaro, EndeavourOS, CachyOS, etc).

O dispositivo usa um controlador HID da Semico/Ocypus e aparece no Linux como:

```text
1a2c:4984 SEMICO USB Gaming Keyboard
```

O driver atualiza o display com:

- temperatura da CPU, via `psutil`
- potencia aproximada do pacote CPU em watts, via Intel RAPL quando disponivel

## Status

Testado em Arch Linux com kernel Linux e dispositivo:

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

### Arch Linux / Manjaro / EndeavourOS

```bash
sudo pacman -S python-psutil
```

### AUR (alternativa)

```bash
yay -S python-psutil
# ou
paru -S python-psutil
```

Para leitura de potencia, o sistema precisa expor Intel RAPL em:

```text
/sys/class/powercap/intel-rapl*
```

Se RAPL nao estiver disponivel, o driver mostra `0 W`, mas a temperatura continua funcionando.

## Instalacao

Clone o projeto e execute:

```bash
git clone https://github.com/rbgameslinux/rise-mode-temp6-Archlinux.git
cd rise-mode-temp6-Archlinux
sudo ./install.sh
```

O instalador:

- Detecta automaticamente a distro (Arch, Manjaro, EndeavourOS)
- Detecta o sensor de temperatura (zenpower para AMD, coretemp para Intel)
- Instala o script em `/usr/local/bin/`
- Configura o servico systemd
- Configura as regras udev

### Suporte a sensores

O driver suporta automaticamente:

| Sensor | Uso |
|--------|-----|
| `zenpower` | AMD Ryzen (preferencial) |
| `k10temp` | AMD (alternativo) |
| `coretemp` | Intel |
| `cpu_thermal` | Genérico (ARM, etc) |

## Uso manual

Listar dispositivos HID:

```bash
sudo ./rise_temp6.py list
```

Listar sensores de temperatura disponiveis:

```bash
sudo ./rise_temp6.py sensors
```

Enviar um valor fixo:

```bash
sudo ./rise_temp6.py send --temp 55 --power 42
```

Atualizar continuamente (sensor automatico):

```bash
sudo ./rise_temp6.py watch --interval 1
```

Atualizar com sensor especifico:

```bash
sudo ./rise_temp6.py watch --sensor zenpower --interval 1
```

### Opcoes

- `--sensor`: Nome do sensor (zenpower, k10temp, coretemp, cpu_thermal)
- `--temp`: Temperatura fixa em Celsius
- `--power`: Potencia fixa em Watts
- `--unit`: Unidade (c para Celsius, f para Fahrenheit)
- `--method`: Metodo de envio (feature, write, both)
- `--interval`: Intervalo em segundos (padrao: 1.0)

## Servico

O servico systemd e configurado automaticamente pelo instalador.

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

Desabilitar no boot:

```bash
sudo systemctl disable rise-temp6.service
```

## Desinstalacao

```bash
sudo ./uninstall.sh
```

## Personalizacao

### Mudar o sensor

Edite o servico:

```bash
sudo systemctl edit rise-temp6.service
```

Ou edite diretamente:

```bash
sudo nano /etc/systemd/system/rise-temp6.service
```

Altere a linha:

```ini
ExecStart=/usr/local/bin/rise_temp6.py watch --sensor zenpower --interval 1 --method feature
```

Para o sensor desejado (zenpower, k10temp, coretemp, cpu_thermal).

### Mudar o intervalo

Altere `--interval 1` para o desejado (em segundos).

## Compatibilidade

- [x] Arch Linux
- [x] Manjaro
- [x] EndeavourOS
- [x] CachyOS
- [x] Garuda Linux
- [x] ArcoLinux
- [x] Qualquer derivado do Arch

## Notas

- O dispositivo se identifica como teclado HID, mas a interface usada pelo display e a interface `1`.
- O script usa `HidD_SetFeature` equivalente via `ioctl(HIDIOCSFEATURE)` em `/dev/hidraw`.
- Este projeto nao e oficial da Rise Mode, Semico ou Ocypus.
- Contribuicoes sao bem-vindas!

## Links

- Repositorio original: https://github.com/daniSoares08/rise-mode-temp6-linux
- Repositorio Arch: https://github.com/rbgameslinux/rise-mode-temp6-Archlinux
- Rise Mode: https://risemode.com
