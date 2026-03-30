"""
Redux Browser — Script de Build e Release
Automatiza: bump de versão → PyInstaller build → Inno Setup → hash SHA-256

Uso:
    python scripts/build_release.py                   # Build sem bump
    python scripts/build_release.py --bump patch      # 1.0.0 → 1.0.1
    python scripts/build_release.py --bump minor      # 1.0.0 → 1.1.0
    python scripts/build_release.py --bump major      # 1.0.0 → 2.0.0
    python scripts/build_release.py --skip-installer   # Pula Inno Setup
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# ---- Paths ----
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
VERSION_FILE = SRC / "browser" / "__version__.py"
SPEC_FILE = ROOT / "build.spec"
ISS_FILE = ROOT / "installer" / "redux_browser.iss"
DIST_DIR = ROOT / "dist"
INSTALLER_OUTPUT = DIST_DIR / "installer"


def read_version() -> str:
    """Lê a versão atual de __version__.py"""
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', content)
    if not match:
        print("❌ Não foi possível ler APP_VERSION de __version__.py")
        sys.exit(1)
    return match.group(1)


def bump_version(current: str, bump_type: str) -> str:
    """Incrementa a versão semântica."""
    parts = [int(x) for x in current.split(".")]
    while len(parts) < 3:
        parts.append(0)

    if bump_type == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == "minor":
        parts[1] += 1
        parts[2] = 0
    elif bump_type == "patch":
        parts[2] += 1
    else:
        print(f"❌ Tipo de bump inválido: {bump_type}")
        sys.exit(1)

    return ".".join(str(p) for p in parts)


def write_version(new_version: str):
    """Atualiza a versão em __version__.py e no .iss"""
    # __version__.py
    content = VERSION_FILE.read_text(encoding="utf-8")
    content = re.sub(
        r'APP_VERSION\s*=\s*"[^"]+"',
        f'APP_VERSION = "{new_version}"',
        content
    )
    VERSION_FILE.write_text(content, encoding="utf-8")

    # Inno Setup .iss
    if ISS_FILE.exists():
        iss = ISS_FILE.read_text(encoding="utf-8")
        iss = re.sub(
            r'#define MyAppVersion\s+"[^"]+"',
            f'#define MyAppVersion "{new_version}"',
            iss
        )
        ISS_FILE.write_text(iss, encoding="utf-8")

    print(f"✅ Versão atualizada para {new_version}")


def run_pyinstaller():
    """Executa o PyInstaller com o build.spec"""
    print("\n🔨 Executando PyInstaller...")
    print("=" * 60)

    # Limpar dist anterior
    dist_app = DIST_DIR / "ReduxBrowser"
    if dist_app.exists():
        shutil.rmtree(dist_app)

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--clean", "--noconfirm"],
        cwd=str(ROOT),
        capture_output=False,
    )

    if result.returncode != 0:
        print("❌ PyInstaller falhou!")
        sys.exit(1)

    exe_path = dist_app / "ReduxBrowser.exe"
    if not exe_path.exists():
        print(f"❌ Executável não encontrado em {exe_path}")
        sys.exit(1)

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✅ PyInstaller concluído: {exe_path}")
    print(f"   Tamanho do .exe: {size_mb:.1f} MB")

    # Tamanho total da pasta
    total = sum(f.stat().st_size for f in dist_app.rglob("*") if f.is_file())
    print(f"   Tamanho total da pasta: {total / (1024 * 1024):.0f} MB")


def run_inno_setup(version: str):
    """Compila o instalador com Inno Setup"""
    print("\n📦 Compilando instalador Inno Setup...")
    print("=" * 60)

    # Procura o ISCC.exe (Inno Setup Compiler)
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    ]

    iscc = None
    for p in iscc_paths:
        if os.path.exists(p):
            iscc = p
            break

    if iscc is None:
        # Tenta encontrar no PATH
        iscc = shutil.which("ISCC")

    if iscc is None:
        print("⚠️  Inno Setup (ISCC.exe) não encontrado!")
        print("   Instale de: https://jrsoftware.org/isdl.php")
        print("   Pule com: --skip-installer")
        return False

    os.makedirs(INSTALLER_OUTPUT, exist_ok=True)

    result = subprocess.run(
        [iscc, str(ISS_FILE)],
        cwd=str(ROOT / "installer"),
        capture_output=False,
    )

    if result.returncode != 0:
        print("❌ Inno Setup falhou!")
        return False

    installer_name = f"ReduxBrowser_Setup_{version}.exe"
    installer_path = INSTALLER_OUTPUT / installer_name

    if installer_path.exists():
        size_mb = installer_path.stat().st_size / (1024 * 1024)
        print(f"✅ Instalador criado: {installer_path}")
        print(f"   Tamanho: {size_mb:.1f} MB")
        return True
    else:
        print("⚠️  Instalador não encontrado no diretório de saída esperado.")
        return False


def generate_sha256(version: str):
    """Gera SHA-256 do instalador para verificação de integridade."""
    installer_name = f"ReduxBrowser_Setup_{version}.exe"
    installer_path = INSTALLER_OUTPUT / installer_name

    if not installer_path.exists():
        print("⚠️  Instalador não encontrado, pulando SHA-256.")
        return

    sha = hashlib.sha256()
    with open(installer_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 64), b""):
            sha.update(chunk)

    hash_value = sha.hexdigest()
    sha_file = INSTALLER_OUTPUT / "sha256.txt"
    sha_file.write_text(f"{hash_value}  {installer_name}\n", encoding="utf-8")

    print(f"\n🔐 SHA-256: {hash_value}")
    print(f"   Salvo em: {sha_file}")

    # Gera também latest.json para o auto-updater
    import json
    latest = {
        "version": version,
        "filename": installer_name,
        "sha256": hash_value,
    }
    latest_file = INSTALLER_OUTPUT / "latest.json"
    latest_file.write_text(json.dumps(latest, indent=2), encoding="utf-8")
    print(f"   latest.json: {latest_file}")


def main():
    parser = argparse.ArgumentParser(description="Redux Browser — Build & Release")
    parser.add_argument("--bump", choices=["major", "minor", "patch"],
                        help="Incrementa a versão antes do build")
    parser.add_argument("--skip-installer", action="store_true",
                        help="Pula a etapa do Inno Setup")
    args = parser.parse_args()

    print("🚀 Redux Browser — Build & Release")
    print("=" * 60)

    # 1. Versão
    version = read_version()
    print(f"📌 Versão atual: {version}")

    if args.bump:
        version = bump_version(version, args.bump)
        write_version(version)
        print(f"📌 Nova versão: {version}")

    # 2. PyInstaller
    run_pyinstaller()

    # 3. Inno Setup
    if not args.skip_installer:
        success = run_inno_setup(version)
        if success:
            generate_sha256(version)
    else:
        print("\n⏭️  Inno Setup pulado (--skip-installer)")

    # Resumo
    print("\n" + "=" * 60)
    print("🎉 Build concluído!")
    print(f"   Versão: {version}")
    print(f"   .exe:   dist/ReduxBrowser/ReduxBrowser.exe")
    if not args.skip_installer:
        print(f"   Setup:  dist/installer/ReduxBrowser_Setup_{version}.exe")
    print("\nPróximos passos:")
    print("  1. Teste o .exe: dist\\ReduxBrowser\\ReduxBrowser.exe")
    print("  2. Teste o instalador (se gerado)")
    print(f"  3. Crie uma release no GitHub com tag v{version}")
    print(f"  4. Faça upload do ReduxBrowser_Setup_{version}.exe como asset")


if __name__ == "__main__":
    main()
