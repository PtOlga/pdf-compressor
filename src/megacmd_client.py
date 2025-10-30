#!/usr/bin/env python3
"""
Client for working with MEGA Incoming Shares via MEGAcmd + WebDAV

FIXED VERSION - Correct WebDAV URL handling

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
        """Serve root (/) via WebDAV and capture served URL printed by MEGAcmd.
        MEGAcmd typically prints a URL with a session token.
        """
        self.logger.info("🌐 Starting MEGA WebDAV for root '/'")
        # First, try to list existing served locations to avoid duplicates (best-effort)
        subprocess.run(['mega-webdav'], capture_output=True, text=True)

        # Serve root
        proc = subprocess.run(['mega-webdav', '/'], capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            # If already served, 'mega-webdav' without args will list them
            listing = subprocess.run(['mega-webdav'], capture_output=True, text=True, timeout=10)
            output = (listing.stdout or '') + (proc.stdout or '') + (proc.stderr or '')
        else:
            output = proc.stdout or ''

        # Extract base URL (without trailing path components)
        # MEGAcmd outputs something like: 
        #   http://127.0.0.1:4443/TOKEN
        #   http://127.0.0.1:4443/TOKEN/Cloud%20Drive
        # We want ONLY the base: http://127.0.0.1:4443/TOKEN
        
        # First, try to match the full URL including any path
        m = re.search(r"(https?://127\.0\.0\.1:\d+/\S+)", output)
        if not m:
            # Last attempt: call 'mega-webdav' (list) and parse
            listing2 = subprocess.run(['mega-webdav'], capture_output=True, text=True, timeout=10)
            m = re.search(r"(https?://127\.0\.0\.1:\d+/\S+)", listing2.stdout or '')
        
        if not m:
            raise Exception(f"Could not determine MEGAcmd WebDAV URL from output:\n{output}")

        # Extract the full matched URL
        full_url = m.group(1).rstrip('/')
        
        # Now extract ONLY the base (protocol://host:port/token)
        # Split by '/' and keep only first 4 parts
        # Example: ['http:', '', '127.0.0.1:4443', 'iVlkWbDZ', 'Cloud%20Drive']
        #       -> ['http:', '', '127.0.0.1:4443', 'iVlkWbDZ']
        parts = full_url.split('/')
        
        if len(parts) >= 4:
            # Keep only protocol://host:port/token (first 4 parts)
            base_url = '/'.join(parts[:4])
        else:
            # Fallback to full URL if unexpected format
            base_url = full_url
        
        self._served_url = base_url
        self.logger.info(f"🔗 MEGA WebDAV base URL: {self._served_url}")
        if len(parts) > 4:
            self.logger.debug(f"   (Stripped trailing path: /{'/'.join(parts[4:])})")
        
        # Give the server a moment to be ready
        time.sleep(1)

    def _setup_rclone_webdav(self):
        """FIXED: Configure rclone to use base WebDAV URL without path assumptions"""
        assert self._served_url, "WebDAV URL not set"
        self.logger.info("🔧 Configuring rclone WebDAV remote for MEGA...")

        # Use the base URL without any path modifications
        # MEGAcmd serves root (/) which includes both Cloud Drive and Incoming Shares
        url_for_remote = self._served_url
        
        self.logger.debug(f"Using WebDAV URL: {url_for_remote}")
        
        # Best-effort: remove existing remote to avoid stale URL
        subprocess.run(['rclone', 'config', 'delete', self.remote_name], capture_output=True, text=True)

        # Create rclone remote pointing to the MEGA root
        create = subprocess.run(
            ['rclone', 'config', 'create', self.remote_name, 'webdav', 
             f'url={url_for_remote}', 'vendor=other'],
            capture_output=True, text=True, timeout=30
        )
        
        if create.returncode != 0:
            self.logger.warning(f"rclone config create output: {create.stdout or create.stderr}")

        # Test connection (list root - should show Cloud Drive and Incoming Shares)
        self.logger.info("🧪 Testing WebDAV connection...")
        test = subprocess.run(
            ['rclone', 'lsd', f'{self.remote_name}:'], 
            capture_output=True, text=True, timeout=30
        )
        
        if test.returncode == 0:
            self.logger.info("✅ rclone WebDAV remote is ready")
            self.logger.debug(f"Root contents:\n{test.stdout}")
            
            # Log what folders are available
            if test.stdout:
                folders = [line.strip() for line in test.stdout.split('\n') if line.strip()]
                self.logger.info(f"📁 Available root folders: {len(folders)}")
                for folder_line in folders[:5]:  # Show first 5
                    self.logger.debug(f"  {folder_line}")
        else:
            error_msg = test.stderr or test.stdout
            self.logger.error(f"❌ WebDAV test failed: {error_msg}")
            raise Exception(f"rclone WebDAV remote test failed: {error_msg}")

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
        """Normalize path to use proper case for Incoming Shares folder"""
        if not path:
            return path
        
        # Remove leading/trailing slashes for easier processing
        p = path.strip().strip('/')
        
        # Split into parts
        parts = p.split('/')
        
        if not parts:
            return path
        
        # Check if first part is a variant of "Incoming shares"
        first = parts[0].lower()
        
        if first in ['incoming shares', 'incoming_shares', 'incomingshares']:
            # Replace with canonical name
            parts[0] = 'Incoming Shares'
        elif len(parts) > 1:
            # Check for two-part name
            if first == 'incoming' and parts[1].lower() in ['shares', 'share']:
                parts[0] = 'Incoming'
                parts[1] = 'Shares'
                # Rejoin as single part
                parts = ['Incoming Shares'] + parts[2:]
        
        # Rebuild path with leading slash
        return '/' + '/'.join(parts)

    def _rel_path(self, path: str) -> str:
        """Convert an absolute MEGA path into a relative path for WebDAV.
        
        WebDAV serves MEGA root, so we just need to remove the leading slash
        and ensure proper path format.
        """
        if not path:
            return ''
        
        # Normalize the path first
        p = self._normalize_incoming_shares_path(path).strip()
        
        # Remove leading slash for WebDAV (it expects relative paths)
        if p.startswith('/'):
            p = p[1:]
        
        return p

    def list_pdf_files(self, folder_path: str) -> List[Dict[str, Any]]:
        from utils import format_file_size  # local import to avoid cycles
        import json
        import fnmatch

        self._ensure_connected()
        folder_path = self._normalize_incoming_shares_path(folder_path).strip().rstrip('/')
        rel_path = self._rel_path(folder_path).rstrip('/')
        
        self.logger.info(f"🔍 (WebDAV) Scanning folder: {folder_path}")
        self.logger.debug(f"   Relative path for rclone: {rel_path}")
        
        res = self._run_rclone_command(['lsjson', '--recursive', '--files-only', f'{self.remote_name}:{rel_path}'])
        
        if not res['success']:
            self.logger.error(f"❌ Error listing files: {res.get('error', 'Unknown error')}")
            return []
        
        try:
            files_data = json.loads(res['stdout']) if res['stdout'] else []
        except Exception as e:
            self.logger.error(f"❌ Error parsing file list: {e}")
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
            pdf_files.append({
                'name': name, 
                'path': full_path, 
                'size': size, 
                'modified': fi.get('ModTime', '')
            })
        
        self.logger.info(f"📋 (WebDAV) Found {len(pdf_files)} PDF files for processing")
        pdf_files.sort(key=lambda x: x['size'])
        return pdf_files

    def download_file(self, remote_path: str, local_path: str) -> bool:
        self._ensure_connected()
        rel_remote = self._rel_path(remote_path)
        local = Path(local_path)
        local.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"Downloading: {remote_path} -> {local_path}")
        self.logger.debug(f"  WebDAV path: {rel_remote}")
        
        res = self._run_rclone_command([
            'copyto', 
            f'{self.remote_name}:{rel_remote}', 
            str(local), 
            '--progress'
        ])
        return res['success'] and local.exists()

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        self._ensure_connected()
        rel_remote = self._rel_path(remote_path)
        local = Path(local_path)
        
        if not local.exists():
            self.logger.error(f"❌ Local file not found: {local_path}")
            return False
        
        # Ensure parent dir
        parent = str(Path(rel_remote).parent)
        if parent and parent != '.':
            self._run_rclone_command(['mkdir', f'{self.remote_name}:{parent}'])
        
        res = self._run_rclone_command([
            'copyto', 
            str(local), 
            f'{self.remote_name}:{rel_remote}', 
            '--progress'
        ])
        return bool(res['success'])

    def delete_file(self, remote_path: str) -> bool:
        self._ensure_connected()
        rel_remote = self._rel_path(remote_path)
        res = self._run_rclone_command(['deletefile', f'{self.remote_name}:{rel_remote}'])
        return bool(res['success'])

    def move_file(self, source_path: str, target_path: str) -> bool:
        self._ensure_connected()
        rel_source = self._rel_path(source_path)
        rel_target = self._rel_path(target_path)
        
        parent = str(Path(rel_target).parent)
        if parent and parent != '.':
            self._run_rclone_command(['mkdir', f'{self.remote_name}:{parent}'])
        
        res = self._run_rclone_command([
            'moveto', 
            f'{self.remote_name}:{rel_source}', 
            f'{self.remote_name}:{rel_target}'
        ])
        return bool(res['success'])

    def copy_file(self, source_path: str, target_path: str) -> bool:
        self._ensure_connected()
        rel_source = self._rel_path(source_path)
        rel_target = self._rel_path(target_path)
        
        parent = str(Path(rel_target).parent)
        if parent and parent != '.':
            self._run_rclone_command(['mkdir', f'{self.remote_name}:{parent}'])
        
        res = self._run_rclone_command([
            'copyto', 
            f'{self.remote_name}:{rel_source}', 
            f'{self.remote_name}:{rel_target}'
        ])
        return bool(res['success'])

    def get_folder_info(self, folder_path: str) -> Dict[str, Any]:
        pdfs = self.list_pdf_files(folder_path)
        total_size = sum(f['size'] for f in pdfs)
        return {
            'path': folder_path, 
            'total_files': len(pdfs), 
            'total_size': total_size, 
            'files': pdfs
        }

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