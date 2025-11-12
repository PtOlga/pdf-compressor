#!/usr/bin/env python3
"""
Diagnostic script to test Mega credentials with rclone
Run this in GitHub Actions to troubleshoot connection issues
"""

import os
import subprocess
import sys

def test_credentials():
    """Test Mega credentials with rclone"""
    
    print("=" * 60)
    print("🔍 MEGA CREDENTIALS DIAGNOSTIC TEST")
    print("=" * 60)
    print()
    
    # Check environment variables
    print("1. Checking environment variables...")
    email = os.getenv('MEGA_EMAIL')
    password = os.getenv('MEGA_PASSWORD')
    
    if not email:
        print("   ❌ MEGA_EMAIL not set!")
        return False
    
    if not password:
        print("   ❌ MEGA_PASSWORD not set!")
        return False
    
    # Mask email and password for display
    masked_email = f"{email[:3]}***@{email.split('@')[1] if '@' in email else '***'}"
    masked_password = "[MASKED]"
    
    print(f"   ✅ MEGA_EMAIL: {masked_email}")
    print(f"   ✅ MEGA_PASSWORD: {masked_password} (length: {len(password)})")
    print()
    
    # Check rclone installation
    print("2. Checking rclone installation...")
    try:
        result = subprocess.run(
            ['rclone', 'version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"   ✅ {version}")
        else:
            print("   ❌ rclone not working properly")
            return False
    except FileNotFoundError:
        print("   ❌ rclone not installed!")
        return False
    except Exception as e:
        print(f"   ❌ Error checking rclone: {e}")
        return False
    print()
    
    # Test password obscuring
    print("3. Testing password obscuring...")
    try:
        result = subprocess.run(
            ['rclone', 'obscure', password],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            obscured = result.stdout.strip()
            print(f"   ✅ Password obscured successfully (length: {len(obscured)})")
        else:
            print(f"   ⚠️ Password obscuring returned no output")
            print(f"   stderr: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Error obscuring password: {e}")
    print()
    
    # Test connection with environment variables
    print("4. Testing direct connection with environment variables...")
    env = os.environ.copy()
    env['RCLONE_CONFIG_MEGA_TYPE'] = 'mega'
    env['RCLONE_CONFIG_MEGA_USER'] = email
    env['RCLONE_CONFIG_MEGA_PASS'] = password
    
    try:
        result = subprocess.run(
            ['rclone', 'lsd', 'mega:/'],
            capture_output=True,
            text=True,
            timeout=30,
            env=env
        )
        
        if result.returncode == 0:
            print("   ✅ Connection successful!")
            print("   Output:")
            for line in result.stdout.strip().split('\n')[:5]:
                print(f"      {line}")
            if len(result.stdout.strip().split('\n')) > 5:
                print(f"      ... and {len(result.stdout.strip().split('\n')) - 5} more items")
            return True
        else:
            print("   ❌ Connection failed!")
            print("   Error:")
            for line in result.stderr.strip().split('\n'):
                print(f"      {line}")
            
            # Analyze error
            error = result.stderr
            if 'Object (typically, node or user) not found' in error:
                print()
                print("   💡 This error usually means:")
                print("      • Email or password is incorrect")
                print("      • Mega account is not activated")
                print("      • Two-factor authentication is enabled (not supported)")
                print("      • Account is locked or suspended")
            elif 'couldn\'t login' in error:
                print()
                print("   💡 Login failed - verify your credentials")
            
            return False
            
    except subprocess.TimeoutExpired:
        print("   ❌ Connection timed out (30 seconds)")
        return False
    except Exception as e:
        print(f"   ❌ Error testing connection: {e}")
        return False

if __name__ == "__main__":
    print()
    success = test_credentials()
    print()
    print("=" * 60)
    
    if success:
        print("✅ ALL TESTS PASSED - Credentials are working!")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED - Please check your Mega credentials")
        print()
        print("Troubleshooting steps:")
        print("1. Verify MEGA_EMAIL and MEGA_PASSWORD in GitHub Secrets")
        print("2. Try logging into https://mega.nz with these credentials")
        print("3. Make sure two-factor authentication is disabled")
        print("4. Check if your account is verified and active")
        sys.exit(1)