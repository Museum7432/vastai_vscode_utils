pkgname=vastai-utils
pkgver=1.0.0
pkgrel=1
pkgdesc="utils for adding instances' ssh terminals and sftp config to vscode"
arch=('x86_64')
license=('MIT')
makedepends=('python')

source=("vast_vscode_utils.py")

sha256sums=('SKIP')

options=('!debug')

build() {
  python -m venv venv
  
  venv/bin/python -m pip install pyinstaller==6.12.0 pyparsing==3.2.1 requests==2.32.3
  venv/bin/python -m pip install vastai-sdk==0.1.16 --no-deps
  
  venv/bin/python -m PyInstaller --onefile vast_vscode_utils.py
}

package() {
  install -Dm755 "dist/vast_vscode_utils" "${pkgdir}/usr/bin/vast_vscode_utils"
}
