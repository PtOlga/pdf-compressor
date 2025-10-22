#!/usr/bin/env python3
"""
Client for working with Mega cloud storage using rclone
This module replaces mega.py library with stable rclone CLI tool
"""

import logging
import subprocess
import json
import tempfile
import shutil
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import fnmatch

from config import get_config
from utils import format_file_size, validate_file_path


class RcloneClient:
    """Client for working with Mega cloud storage via rclone"""
    
    def __init__(self):
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self._authenticated = False
        
        # Retry settings
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # rclone remote name (configured in workflow)
        self.remote_name = "mega"
        
        # Check rclone availability and setup
        self._check_rclone()
        self._setup_rclone_config()
    
    def _check_rclone(self):
        """Check if rclone is installed"""
        try:
            result = subprocess.run(
                ['rclone', 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                self.logger.info(f"✅ rclone found: {version}")
            else:
                raise Exception("rclone not working properly")
                
        except FileNotFoundError:
            raise Exception(
                "rclone not installed. "
                "Install it: curl https://rclone.org/install.sh | sudo bash"
            )
        except Exception as e:
            raise Exception(f"Error checking rclone: {e}")
    
    def _setup_rclone_config(self):
        """Setup rclone configuration for Mega"""
        email = self.config.mega_email
        password = self.config.mega_password
        
        if not email or not password:
            raise ValueError(
                "Mega credentials not configured. "
                "Set MEGA_EMAIL and MEGA_PASSWORD environment variables"
            )
        
        try:
            self.logger.info("🔐 Configuring rclone for Mega...")
            self.logger.debug(f"   Email: {email[:3]}***@{email.split('@')[1] if '@' in email else '***'}")
            
            # Method 1: Try using rclone config create with environment variables
            # This is the most reliable method
            self.logger.debug("🔧 Method 1: Using rclone config create...")
            
            # Set environment variables for rclone
            env = os.environ.copy()
            env['RCLONE_CONFIG_MEGA_TYPE'] = 'mega'
            env['RCLONE_CONFIG_MEGA_USER'] = email
            env['RCLONE_CONFIG_MEGA_PASS'] = password
            
            # Try direct connection test with env vars (no config file needed)
            result = subprocess.run(
                ['rclone', 'lsd', f'{self.remote_name}:/'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            if result.returncode == 0:
                self.logger.info("✅ Connected using environment variables")
                self._authenticated = True
                
                # Save to config file for persistence
                config_dir = Path.home() / '.config' / 'rclone'
                config_dir.mkdir(parents=True, exist_ok=True)
                config_file = config_dir / 'rclone.conf'
                
                # Create config using rclone config create
                create_result = subprocess.run(
                    ['rclone', 'config', 'create', self.remote_name, 'mega',
                     f'user={email}', f'pass={password}'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if create_result.returncode == 0:
                    self.logger.debug("✅ Config file created")
                else:
                    self.logger.debug(f"⚠️ Config create warning: {create_result.stderr}")
                
                self._check_quota()
                return
            
            # Method 2: Try manual config file creation with obscured password
            self.logger.debug("🔧 Method 2: Trying manual config file...")
            
            config_dir = Path.home() / '.config' / 'rclone'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / 'rclone.conf'
            
            # Obscure password
            self.logger.debug("🔐 Obscuring password...")
            obscured_password = self._obscure_password(password)
            
            if obscured_password:
                # Create config with obscured password
                config_content = f"""[{self.remote_name}]
type = mega
user = {email}
pass = {obscured_password}
"""
                
                with open(config_file, 'w') as f:
                    f.write(config_content)
                
                config_file.chmod(0o600)
                self.logger.debug(f"✅ Config file created: {config_file}")
                
                # Test connection
                self.logger.info("🔍 Testing Mega connection...")
                result = self._run_rclone_command(['lsd', f'{self.remote_name}:/'], timeout=30)
                
                if result['success']:
                    self._authenticated = True
                    self.logger.info("✅ Successfully connected to Mega")
                    self._check_quota()
                    return
            
            # If we got here, neither method worked
            if 'result' in locals():
                if isinstance(result, dict):
                    error_msg = result.get('error', 'Connection failed')
                else:
                    error_msg = result.stderr if hasattr(result, 'stderr') else 'Connection failed'
            else:
                error_msg = "All connection methods failed"
            
            # Check for specific errors
            if 'Object (typically, node or user) not found' in str(error_msg):
                self.logger.error("❌ Authentication failed - check your credentials")
                self.logger.error("   Possible causes:")
                self.logger.error("   1. Incorrect email or password in GitHub Secrets")
                self.logger.error("   2. Mega account locked or suspended")
                self.logger.error("   3. Two-factor authentication enabled (not supported)")
                self.logger.error("   4. Account email not verified")
            
            raise Exception(f"Failed to connect to Mega: {error_msg}")
                
        except Exception as e:
            self.logger.error(f"❌ Error setting up rclone: {e}")
            raise
    
    def _obscure_password(self, password: str) -> str:
        """Obscure password for rclone config"""
        try:
            self.logger.debug("Running rclone obscure...")
            result = subprocess.run(
                ['rclone', 'obscure', password],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                obscured = result.stdout.strip()
                self.logger.debug(f"✅ Password obscured successfully (length: {len(obscured)})")
                return obscured
            else:
                self.logger.warning(f"⚠️ rclone obscure failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.warning("⚠️ rclone obscure timed out")
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Error obscuring password: {e}")
            return None
    
    def _run_rclone_command(self, args: List[str], timeout: int = 300) -> Dict[str, Any]:
        """
        Run rclone command with retry logic
        
        Args:
            args: rclone command arguments
            timeout: command timeout in seconds
            
        Returns:
            Dictionary with command result
        """
        for attempt in range(self.max_retries):
            try:
                # Build full command
                cmd = ['rclone'] + args
                
                self.logger.debug(f"Running: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                if result.returncode == 0:
                    return {
                        'success': True,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                else:
                    error_msg = result.stderr or result.stdout or 'Unknown error'
                    
                    if attempt < self.max_retries - 1:
                        self.logger.warning(
                            f"⚠️ Attempt {attempt + 1} failed: {error_msg}. Retrying..."
                        )
                        time.sleep(self.retry_delay)
                        continue
                    
                    return {
                        'success': False,
                        'error': error_msg,
                        'returncode': result.returncode
                    }
                    
            except subprocess.TimeoutExpired:
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"⚠️ Timeout on attempt {attempt + 1}. Retrying...")
                    time.sleep(self.retry_delay)
                    continue
                
                return {
                    'success': False,
                    'error': f'Command timeout after {timeout} seconds'
                }
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(f"⚠️ Error on attempt {attempt + 1}: {e}. Retrying...")
                    time.sleep(self.retry_delay)
                    continue
                
                return {
                    'success': False,
                    'error': str(e)
                }
        
        return {
            'success': False,
            'error': 'Max retries exceeded'
        }
    
    def _check_quota(self):
        """Check Mega account quota"""
        try:
            # rclone about command shows quota information
            result = self._run_rclone_command(
                ['about', f'{self.remote_name}:', '--json'],
                timeout=30
            )
            
            if result['success'] and result['stdout']:
                try:
                    quota_info = json.loads(result['stdout'])
                    
                    total = quota_info.get('total', 0)
                    used = quota_info.get('used', 0)
                    free = quota_info.get('free', total - used)
                    
                    self.logger.info(f"💾 Mega quota:")
                    self.logger.info(f"   📊 Total: {format_file_size(total)}")
                    self.logger.info(f"   📊 Used: {format_file_size(used)}")
                    self.logger.info(f"   📊 Free: {format_file_size(free)}")
                    
                    # Warning if low space
                    if free < 100 * 1024 * 1024:  # < 100 MB
                        self.logger.warning(f"⚠️ Low free space in Mega: {format_file_size(free)}")
                        
                except json.JSONDecodeError:
                    self.logger.warning("⚠️ Could not parse quota information")
                    
        except Exception as e:
            self.logger.warning(f"⚠️ Could not get quota information: {e}")
    
    def _ensure_connected(self):
        """Check connection to Mega"""
        if not self._authenticated:
            raise ConnectionError("Not connected to Mega")
    
    def list_pdf_files(self, folder_path: str) -> List[Dict[str, Any]]:
        """
        Get list of PDF files in specified folder
        
        Args:
            folder_path: path to folder in Mega
            
        Returns:
            list of dictionaries with file information
        """
        self._ensure_connected()
        
        try:
            self.logger.info(f"🔍 Scanning folder: {folder_path}")
            
            # Clean folder path
            folder_path = folder_path.strip().rstrip('/')
            
            # Use rclone lsjson to get file list with details
            result = self._run_rclone_command([
                'lsjson',
                '--recursive',
                '--files-only',
                f'{self.remote_name}:{folder_path}'
            ])
            
            if not result['success']:
                self.logger.error(f"❌ Error listing files: {result.get('error', 'Unknown error')}")
                return []
            
            # Parse JSON output
            try:
                files_data = json.loads(result['stdout']) if result['stdout'] else []
            except json.JSONDecodeError:
                self.logger.error("❌ Error parsing file list")
                return []
            
            self.logger.debug(f"📊 Total objects found: {len(files_data)}")
            
            pdf_files = []
            skip_patterns = self.config.skip_patterns
            
            for file_info in files_data:
                file_name = file_info.get('Name', '')
                file_size = file_info.get('Size', 0)
                file_path_relative = file_info.get('Path', '')
                
                # Check extension
                if not file_name.lower().endswith(('.pdf', '.PDF')):
                    continue
                
                # Check skip patterns
                should_skip = False
                for pattern in skip_patterns:
                    if fnmatch.fnmatch(file_name.lower(), pattern.lower()):
                        self.logger.debug(f"⏭️ Skipping {file_name} (matches pattern: {pattern})")
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Check file size limits
                min_size = self.config.min_file_size_kb * 1024
                max_size = self.config.max_file_size_mb * 1024 * 1024
                
                if file_size < min_size:
                    self.logger.debug(f"⏭️ Skipping {file_name} (too small: {format_file_size(file_size)})")
                    continue
                
                if file_size > max_size:
                    self.logger.debug(f"⏭️ Skipping {file_name} (too large: {format_file_size(file_size)})")
                    continue
                
                # Build full path
                full_path = f"{folder_path}/{file_path_relative}" if file_path_relative else f"{folder_path}/{file_name}"
                
                pdf_files.append({
                    'name': file_name,
                    'path': full_path,
                    'size': file_size,
                    'modified': file_info.get('ModTime', '')
                })
                
                self.logger.debug(f"✅ Found PDF: {file_name} ({format_file_size(file_size)})")
            
            self.logger.info(f"📋 Found {len(pdf_files)} PDF files for processing")
            
            # Sort by size (process smaller files first)
            pdf_files.sort(key=lambda x: x['size'])
            
            return pdf_files
            
        except Exception as e:
            self.logger.error(f"❌ Error scanning folder {folder_path}: {e}")
            return []
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Download file from Mega
        
        Args:
            remote_path: path in Mega
            local_path: local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connected()
        
        local_file = Path(local_path)
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            self.logger.debug(f"📥 Downloading {remote_path} -> {local_path}")
            
            # Clean remote path
            remote_path = remote_path.strip()
            
            result = self._run_rclone_command([
                'copyto',
                f'{self.remote_name}:{remote_path}',
                str(local_file),
                '--progress'
            ])
            
            if not result['success']:
                self.logger.error(f"❌ Download failed: {result.get('error', 'Unknown error')}")
                return False
            
            # Verify file was downloaded
            if not local_file.exists():
                self.logger.error(f"❌ File not found after download: {local_path}")
                return False
            
            file_size = local_file.stat().st_size
            self.logger.debug(f"✅ Downloaded: {local_file.name} ({format_file_size(file_size)})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error downloading {remote_path}: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Upload file to Mega
        
        Args:
            local_path: local file path
            remote_path: path in Mega to save
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connected()
        
        local_file = Path(local_path)
        if not local_file.exists():
            self.logger.error(f"❌ Local file not found: {local_path}")
            return False
        
        try:
            file_size = local_file.stat().st_size
            self.logger.debug(f"📤 Uploading {local_path} -> {remote_path} ({format_file_size(file_size)})")
            
            # Clean remote path
            remote_path = remote_path.strip()
            
            # Ensure parent directory exists
            remote_dir = str(Path(remote_path).parent)
            if remote_dir and remote_dir != '.':
                self._ensure_folder_exists(remote_dir)
            
            result = self._run_rclone_command([
                'copyto',
                str(local_file),
                f'{self.remote_name}:{remote_path}',
                '--progress'
            ])
            
            if not result['success']:
                self.logger.error(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                return False
            
            self.logger.debug(f"✅ Uploaded: {local_file.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error uploading {local_path}: {e}")
            return False
    
    def _ensure_folder_exists(self, folder_path: str):
        """Create folder in Mega if it doesn't exist"""
        if not folder_path or folder_path == '/':
            return
        
        try:
            # rclone mkdir creates folder if it doesn't exist
            result = self._run_rclone_command([
                'mkdir',
                f'{self.remote_name}:{folder_path}'
            ])
            
            if result['success']:
                self.logger.debug(f"📁 Folder ensured: {folder_path}")
            else:
                # Folder might already exist, which is fine
                self.logger.debug(f"📁 Folder operation: {folder_path}")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Could not ensure folder {folder_path}: {e}")
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete file from Mega
        
        Args:
            remote_path: path to file in Mega
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connected()
        
        try:
            self.logger.debug(f"🗑️ Deleting file: {remote_path}")
            
            # Clean remote path
            remote_path = remote_path.strip()
            
            result = self._run_rclone_command([
                'deletefile',
                f'{self.remote_name}:{remote_path}'
            ])
            
            if result['success']:
                self.logger.debug(f"✅ File deleted: {Path(remote_path).name}")
                return True
            else:
                self.logger.warning(f"⚠️ Could not delete file: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error deleting {remote_path}: {e}")
            return False
    
    def move_file(self, source_path: str, target_path: str) -> bool:
        """
        Move file in Mega
        
        Args:
            source_path: source path
            target_path: target path
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connected()
        
        try:
            self.logger.debug(f"📋 Moving {source_path} -> {target_path}")
            
            # Clean paths
            source_path = source_path.strip()
            target_path = target_path.strip()
            
            # Ensure target directory exists
            target_dir = str(Path(target_path).parent)
            if target_dir and target_dir != '.':
                self._ensure_folder_exists(target_dir)
            
            result = self._run_rclone_command([
                'moveto',
                f'{self.remote_name}:{source_path}',
                f'{self.remote_name}:{target_path}'
            ])
            
            if result['success']:
                return True
            else:
                self.logger.error(f"❌ Move failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error moving {source_path}: {e}")
            return False
    
    def copy_file(self, source_path: str, target_path: str) -> bool:
        """
        Copy file in Mega
        
        Args:
            source_path: source path
            target_path: target path
            
        Returns:
            True if successful, False otherwise
        """
        self._ensure_connected()
        
        try:
            self.logger.debug(f"📋 Copying {source_path} -> {target_path}")
            
            # Clean paths
            source_path = source_path.strip()
            target_path = target_path.strip()
            
            # Ensure target directory exists
            target_dir = str(Path(target_path).parent)
            if target_dir and target_dir != '.':
                self._ensure_folder_exists(target_dir)
            
            result = self._run_rclone_command([
                'copyto',
                f'{self.remote_name}:{source_path}',
                f'{self.remote_name}:{target_path}'
            ])
            
            if result['success']:
                return True
            else:
                self.logger.error(f"❌ Copy failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error copying {source_path}: {e}")
            return False
    
    def get_folder_info(self, folder_path: str) -> Dict[str, Any]:
        """
        Get folder information
        
        Args:
            folder_path: path to folder
            
        Returns:
            dictionary with folder information
        """
        self._ensure_connected()
        
        try:
            pdf_files = self.list_pdf_files(folder_path)
            
            total_size = sum(f['size'] for f in pdf_files)
            
            return {
                'path': folder_path,
                'total_files': len(pdf_files),
                'total_size': total_size,
                'files': pdf_files
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting folder info for {folder_path}: {e}")
            return {'path': folder_path, 'total_files': 0, 'total_size': 0, 'files': []}


def test_rclone_client():
    """Test rclone client"""
    try:
        client = RcloneClient()
        
        # Test getting file list
        input_folder = client.config.input_folder
        print(f"🧪 Testing folder: {input_folder}")
        
        folder_info = client.get_folder_info(input_folder)
        print(f"📊 Files in folder: {folder_info['total_files']}")
        print(f"📊 Total size: {format_file_size(folder_info['total_size'])}")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_rclone_client()