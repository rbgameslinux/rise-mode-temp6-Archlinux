# Maintainer: rbgameslinux <rbgameslinux@users.noreply.github.com>

pkgname=rise-mode-temp6-archlinux
pkgver=1.0.1
pkgrel=2
pkgdesc="Driver experimental para display USB do air cooler Rise Mode Temp 6 Pro (Arch Linux)"
arch=('any')
url="https://github.com/rbgameslinux/rise-mode-temp6-Archlinux"
license=('MIT')
depends=('python' 'python-psutil' 'systemd')
makedepends=('git')
optdepends=(
    'yay: para instalar zenpower automaticamente'
    'paru: para instalar zenpower automaticamente'
    'zenpower: sensor de temperatura AMD (recomendado para CPUs AMD)'
)
backup=('etc/systemd/system/rise-temp6.service')
install=rise-temp6.install
source=("$pkgname::git+$url")
sha256sums=('SKIP')

pkgver() {
    cd "$pkgname"
    git describe --long --tags | sed 's/^v//;s/\([^-]*-g\)/r\1/;s/-/./g'
}

package() {
    cd "$pkgname"

    # Instalar script principal
    install -Dm755 rise_temp6.py "$pkgdir/usr/bin/rise_temp6.py"

    # Instalar servico systemd (ajustar caminho para /usr/bin/ no contexto do pacote)
    sed 's|/usr/local/bin/rise_temp6.py|/usr/bin/rise_temp6.py|' rise-temp6.service > "$pkgdir/etc/systemd/system/rise-temp6.service"
    chmod 644 "$pkgdir/etc/systemd/system/rise-temp6.service"

    # Instalar regras udev
    install -Dm644 99-rise-temp6.rules "$pkgdir/etc/udev/rules.d/99-rise-temp6.rules"

    # Instalar script de instalacao (para uso manual)
    install -Dm755 install.sh "$pkgdir/usr/share/$pkgname/install.sh"
    install -Dm755 uninstall.sh "$pkgdir/usr/share/$pkgname/uninstall.sh"

    # Instalar README
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
