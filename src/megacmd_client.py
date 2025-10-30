#!/usr/bin/env python3
"""
Client for working with MEGA Incoming Shares via MEGAcmd + WebDAV

Approach:
- Log in to MEGA using MEGAcmd (mega-login)
- Serve the MEGA root via MEGAcmd WebDAV (mega-webdav /)
- Create an rclone WebDAV remote pointed to the served URL
- Reuse the same rclone-based operations as in RcloneClient

This allows accessing "Incoming shares" which the rclone mega backend
cannot list directly.
"""

import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

from config import get_config


class MegaWebDAVClient:
    """Client that exposes MEGA via MEGAcmd WebDAV and uses rclone(WebDAV)"""

    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self._authenticated = False
        self.max_retries = 3
        self.retry_delay = 5

        # rclone remote name for WebDAV
        self.remote_name = "megaweb"
        self._served_url: str | None = None

        # Checks and setup
        self._check_rclone()
        self._check_megacmd()
        self._megacmd_login()
        self._start_webdav()
        self._setup_rclone_webdav()
        self._authenticated = True

    # ---- Basic checks ----
    def _check_rclone(self):
        try:
            result = subprocess.run(['rclone', 'version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(result.stderr or result.stdout)
            self.logger.info(f"✅ rclone found: {result.stdout.splitlines()[0]}")
        except FileNotFoundError:
            raise Exception("rclone not installed. Install it: curl https://rclone.org/install.sh | sudo bash")

    def _check_megacmd(self):
        try:
            result = subprocess.run(['mega-version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info(f"✅ MEGAcmd found: {result.stdout.strip()}")
                return
        except FileNotFoundError:
            pass
        # Fallback check
        try:
            result = subprocess.run(['mega-help'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info("✅ MEGAcmd found (mega-help)")
                return
        except FileNotFoundError:
            pass
        raise Exception("MEGAcmd not installed. Install it via 'apt-get install -y megacmd'.")

    # ---- MEGAcmd auth & webdav ----
    def _megacmd_login(self):
        email = self.config.mega_email
        password = self.config.mega_password
        if not email or not password:
            raise ValueError("Mega credentials not configured (MEGA_EMAIL/MEGA_PASSWORD)")

        # Ensure clean session
        subprocess.run(['mega-logout'], capture_output=True, text=True)

        self.logger.info("🔐 Logging into MEGA via MEGAcmd...")
        result = subprocess.run(['mega-login', email, password], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            err = result.stderr or result.stdout
            raise Exception(f"MEGAcmd login failed: {err}")

        who = subprocess.run(['mega-whoami'], capture_output=True, text=True, timeout=20)
        if who.returncode == 0:
            self.logger.info(f"👤 Logged in as: {who.stdout.strip()}")
        else:
            self.logger.warning("⚠️ Could not verify login with mega-whoami")

    def _start_webdav(self):
        """Serve root (/) via WebDAV and capture served URL.
        We use 'mega-webdav /' which prints the served URL.
        """
        self.logger.info("🌐 Starting MEGA WebDAV for root '/'")
        # First, try to list existing served locations to avoid duplicates
        subprocess.run(['mega-webdav'], capture_output=True, text=True)

        # Serve root
        proc = subprocess.run(['mega-webdav', '/'], capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            # If already served, 'mega-webdav' without args will list them
            listing = subprocess.run(['mega-webdav'], capture_output=True, text=True, timeout=10)
            output = listing.stdout + proc.stdout + proc.stderr
        else:
            output = proc.stdout

        # Extract URL (http://127.0.0.1:4443/XXXX...)
        m = re.search(r"http://127\.0\.0\.1:\d+/(?:[A-Za-z0-9_-]+)/?", output)
        if not m:
            # Try another common pattern: show both path and url
            m = re.search(r"(http://127\.0\.0\.1:\d+/[^\s]+)", output)
        if not m:
            # last attempt: call 'mega-webdav' (list) and parse
            listing2 = subprocess.run(['mega-webdav'], capture_output=True, text=True, timeout=10)
            m = re.search(r"(http://127\.0\.0\.1:\d+/[^\s]+)", listing2.stdout)
        if not m:
            raise Exception(f"Could not determine MEGAcmd WebDAV URL from output:\n{output}")

        # Use the entire match as URL (works for both patterns)
        self._served_url = m.group(0).rstrip('/')
        self.logger.info(f"🔗 MEGA WebDAV URL: {self._served_url}")
        # Give the server a moment to be ready
        time.sleep(1)

    def _setup_rclone_webdav(self):
        assert self._served_url, "WebDAV URL not set"
        self.logger.info("🔧 Configuring rclone WebDAV remote for MEGA...")

        # Create/update rclone remote
        create = subprocess.run(
            ['rclone', 'config', 'create', self.remote_name, 'webdav', f'url={self._served_url}', 'vendor=other'],
            capture_output=True, text=True, timeout=30
        )
        if create.returncode != 0:
            # Ignore errors if it already exists; we will test it anyway
            self.logger.debug(f"rclone config create output: {create.stdout or create.stderr}")

        # Test connection (list root)
        test = subprocess.run(['rclone', 'lsd', f'{self.remote_name}:'], capture_output=True, text=True, timeout=30)
        if test.returncode == 0:
            self.logger.info("✅ rclone WebDAV remote is ready")
        else:
            raise Exception(f"rclone WebDAV remote test failed: {test.stderr or test.stdout}")

    # ---- Utilities ----
    def _run_rclone_command(self, args: List[str], timeout: int = 300) -> Dict[str, Any]:
        for attempt in range(self.max_retries):
            try:
                cmd = ['rclone'] + args
                self.logger.debug("Running: %s", ' '.join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if result.returncode == 0:
                    return {'success': True, 'stdout': result.stdout, 'stderr': result.stderr}
                if attempt < self.max_retries - 1:
                    self.logger.warning("⚠️ Attempt %d failed: %s. Retrying...", attempt + 1, result.stderr or result.stdout)
                    time.sleep(self.retry_delay)
                    continue
                return {'success': False, 'error': result.stderr or result.stdout, 'returncode': result.returncode}
            except subprocess.TimeoutExpired:
                if attempt < self.max_retries - 1:
                    self.logger.warning("⚠️ Timeout on attempt %d. Retrying...", attempt + 1)
                    time.sleep(self.retry_delay)
                    continue
                return {'success': False, 'error': f'Command timeout after {timeout} seconds'}
            except Exception as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning("⚠️ Error on attempt %d: %s. Retrying...", attempt + 1, e)
                    time.sleep(self.retry_delay)
                    continue
                return {'success': False, 'error': str(e)}
        return {'success': False, 'error': 'Max retries exceeded'}

    # ---- Public API (compatible with RcloneClient) ----
    def _ensure_connected(self):
        if not self._authenticated:
            raise ConnectionError("Not connected to MEGA (WebDAV)")

    @staticmethod
    def _normalize_incoming_shares_path(path: str) -> str:
        # Normalize the first segment to the canonical name used by MEGAcmd WebDAV
        # Common variants: 
        #   /Incoming shares/...  -> /Incoming Shares/...
        #   /incoming Shares/...  -> /Incoming Shares/...
        if not path:
            return path
        parts = path.strip().split('/')
        if len(parts) > 1 and parts[1].lower() == 'incoming' and len(parts) > 2 and parts[2].lower().startswith('shares'):
            parts[1] = 'Incoming'
            parts[2] = 'Shares'
            return '/'.join(parts)
        if len(parts) > 1 and parts[1].lower().startswith('incoming'):
            # Single-word variant
            parts[1] = 'Incoming Shares'
            return '/'.join(parts)
        # Also normalize exact known lowercase variant
        if path.lower().startswith('/incoming shares/'):
            return '/Incoming Shares/' + path[len('/incoming shares/'):]
        return path

    def list_pdf_files(self, folder_path: str) -> List[Dict[str, Any]]:
        from utils import format_file_size  # local import to avoid cycles
        import json
        import fnmatch

        self._ensure_connected()
        folder_path = self._normalize_incoming_shares_path(folder_path).strip().rstrip('/')
        self.logger.info(f"🔍 (WebDAV) Scanning folder: {folder_path}")
        res = self._run_rclone_command(['lsjson', '--recursive', '--files-only', f'{self.remote_name}:{folder_path}'])
        if not res['success']:
            self.logger.error(f"❌ Error listing files: {res.get('error', 'Unknown error')}")
            return []
        try:
            files_data = json.loads(res['stdout']) if res['stdout'] else []
        except Exception:
            self.logger.error("❌ Error parsing file list")
            return []
        pdf_files: List[Dict[str, Any]] = []
        skip_patterns = self.config.skip_patterns
        for fi in files_data:
            name = fi.get('Name', '')
            size = fi.get('Size', 0)
            rel = fi.get('Path', '')
            if not name.lower().endswith(('.pdf', '.PDF')):
                continue
            # Skip patterns
            if any(fnmatch.fnmatch(name.lower(), p.lower()) for p in skip_patterns):
                continue
            # Size filters
            if size < self.config.min_file_size_kb * 1024:
                continue
            if size > self.config.max_file_size_mb * 1024 * 1024:
                continue
            full_path = f"{folder_path}/{rel}" if rel else f"{folder_path}/{name}"
            pdf_files.append({'name': name, 'path': full_path, 'size': size, 'modified': fi.get('ModTime', '')})
        self.logger.info(f"📋 (WebDAV) Found {len(pdf_files)} PDF files for processing")
        pdf_files.sort(key=lambda x: x['size'])
        return pdf_files

    def download_file(self, remote_path: str, local_path: str) -> bool:
        self._ensure_connected()
        remote_path = self._normalize_incoming_shares_path(remote_path).strip()
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        res = self._run_rclone_command(['copyto', f'{self.remote_name}:{remote_path}', str(local), '--progress'])
        return res['success'] and local.exists()

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        self._ensure_connected()
        remote_path = self._normalize_incoming_shares_path(remote_path).strip()
        local = Path(local_path)
        if not local.exists():
            self.logger.error(f"❌ Local file not found: {local_path}")
            return False
        # Ensure parent dir
        parent = str(Path(remote_path).parent)
        if parent and parent != '.':
            self._run_rclone_command(['mkdir', f'{self.remote_name}:{parent}'])
        res = self._run_rclone_command(['copyto', str(local), f'{self.remote_name}:{remote_path}', '--progress'])
        return bool(res['success'])

    def delete_file(self, remote_path: str) -> bool:
        self._ensure_connected()
        remote_path = self._normalize_incoming_shares_path(remote_path).strip()
        res = self._run_rclone_command(['deletefile', f'{self.remote_name}:{remote_path}'])
        return bool(res['success'])

    def move_file(self, source_path: str, target_path: str) -> bool:
        self._ensure_connected()
        source_path = self._normalize_incoming_shares_path(source_path).strip()
        target_path = self._normalize_incoming_shares_path(target_path).strip()
        parent = str(Path(target_path).parent)
        if parent and parent != '.':
            self._run_rclone_command(['mkdir', f'{self.remote_name}:{parent}'])
        res = self._run_rclone_command(['moveto', f'{self.remote_name}:{source_path}', f'{self.remote_name}:{target_path}'])
        return bool(res['success'])

    def copy_file(self, source_path: str, target_path: str) -> bool:
        self._ensure_connected()
        source_path = self._normalize_incoming_shares_path(source_path).strip()
        target_path = self._normalize_incoming_shares_path(target_path).strip()
        parent = str(Path(target_path).parent)
        if parent and parent != '.':
            self._run_rclone_command(['mkdir', f'{self.remote_name}:{parent}'])
        res = self._run_rclone_command(['copyto', f'{self.remote_name}:{source_path}', f'{self.remote_name}:{target_path}'])
        return bool(res['success'])

    def get_folder_info(self, folder_path: str) -> Dict[str, Any]:
        pdfs = self.list_pdf_files(folder_path)
        total_size = sum(f['size'] for f in pdfs)
        return {'path': folder_path, 'total_files': len(pdfs), 'total_size': total_size, 'files': pdfs}

    def close(self):
        """Stop serving WebDAV (best-effort)."""
        try:
            # Try to un-serve root; ignore errors
            subprocess.run(['mega-webdav', '-d', '/'], capture_output=True, text=True)
        except Exception:
            pass
        # Logout to drop session (best-effort)
        try:
            subprocess.run(['mega-logout'], capture_output=True, text=True)
        except Exception:
            pass

