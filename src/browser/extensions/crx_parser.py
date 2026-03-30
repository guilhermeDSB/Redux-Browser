"""
Redux Browser — Parser de arquivos .crx (Chrome Extension Package)
Formato CRX3: magic(4) + version(4) + header_size(4) + header + zip
"""

import struct
import zipfile
from pathlib import Path
import tempfile
import shutil

class CRXParser:
    CRX_MAGIC = b'Cr24'
    
    def extract(self, crx_path: Path, dest_dir: Path = None) -> Path:
        """
        Extrai um arquivo .crx para uma pasta.
        Retorna o caminho da pasta com a extensão descompactada.
        """
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp(prefix="ext_"))
        
        # Garantir que o diretório destino existe
        dest_dir.mkdir(parents=True, exist_ok=True)
            
        with open(crx_path, 'rb') as f:
            data = f.read()
            
        if data[:4] == self.CRX_MAGIC:
            version = struct.unpack('<I', data[4:8])[0]
            if version == 3:
                zip_offset = self._parse_crx3_header(data)
            elif version == 2:
                zip_offset = self._parse_crx2_header(data)
            else:
                raise ValueError(f"Versão CRX não suportada: {version}")
        else:
            # Pode ser já um ZIP puro (uma extensão empacotada normal renomeada pra .crx, o que é comum)
            zip_offset = 0
            
        # Extrair ZIP começando do zip_offset:
        zip_data = data[zip_offset:]
        
        if len(zip_data) < 4:
            raise ValueError("Arquivo .crx vazio ou corrompido.")
        
        if zip_data[:2] != b'PK':
            raise ValueError("Arquivo .crx não contém um ZIP válido.")
        
        zip_path = dest_dir / "temp.zip"
        with open(zip_path, 'wb') as f:
            f.write(zip_data)
            
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
        except zipfile.BadZipFile:
            raise ValueError("Arquivo .crx corrompido ou ZIP inválido.")
        finally:
            if zip_path.exists():
                zip_path.unlink()
                
        return dest_dir
    
    def _parse_crx3_header(self, data: bytes) -> int:
        """Retorna o offset onde o ZIP começa no CRX3."""
        # CRX3 Header: magic(4) + version(4) + header_size(4) + header_data(header_size) + ZIP
        header_size = struct.unpack('<I', data[8:12])[0]
        return 12 + header_size
    
    def _parse_crx2_header(self, data: bytes) -> int:
        """Retorna o offset onde o ZIP começa no CRX2."""
        # CRX2 Header: magic(4) + version(4) + pub_key_len(4) + sig_len(4) + pub_key(pub_key_len) + sig(sig_len) + ZIP
        pub_key_len = struct.unpack('<I', data[8:12])[0]
        sig_len = struct.unpack('<I', data[12:16])[0]
        return 16 + pub_key_len + sig_len
    
    def is_valid_crx(self, path: Path) -> bool:
        """Verifica se o arquivo é um CRX válido."""
        try:
            with open(path, 'rb') as f:
                magic = f.read(4)
                if magic == self.CRX_MAGIC:
                    return True
                
            # Verifica se é só um ZIP
            with zipfile.ZipFile(path, 'r') as z:
                return z.testzip() is None
        except Exception:
            return False
