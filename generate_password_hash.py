#!/usr/bin/env python3
"""
Password Hash Generator for BMC Dashboard
Use this script to generate secure password hashes
"""

import hashlib
import getpass

def generate_hash(password):
    """Generate SHA-256 hash of a password"""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    print("="*70)
    print("BMC DASHBOARD - PASSWORD HASH GENERATOR")
    print("="*70)
    print()
    print("This tool generates a SHA-256 hash for your password.")
    print("The hash can be safely stored in your code without exposing the password.")
    print()
    
    # Option 1: Interactive password entry
    print("Enter a new password (or press Enter to skip):")
    password = getpass.getpass("Password: ")
    
    if password:
        hash_value = generate_hash(password)
        print()
        print("="*70)
        print("YOUR PASSWORD HASH:")
        print("="*70)
        print(hash_value)
        print()
        print("Copy this hash and update the PASSWORD_HASH variable in app_improved.py:")
        print(f'PASSWORD_HASH = "{hash_value}"')
        print()
        
        # Verify
        print("Verify by entering the password again:")
        verify_password = getpass.getpass("Verify password: ")
        if generate_hash(verify_password) == hash_value:
            print("✅ Verification successful!")
        else:
            print("❌ Passwords don't match!")
    
    print()
    print("="*70)
    print("CURRENT PASSWORD HASH (for reference):")
    print("="*70)
    print("Current password: Aguacate78)")
    print("Current hash: 8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918")
    print()
    print("="*70)
    print("HOW TO UPDATE PASSWORD IN DASHBOARD:")
    print("="*70)
    print("1. Run this script to generate a new hash")
    print("2. Open app_improved.py")
    print("3. Find the line: PASSWORD_HASH = \"...\"")
    print("4. Replace with your new hash")
    print("5. Save the file")
    print("6. Restart the dashboard")
    print()
    print("SECURITY NOTES:")
    print("- Never commit the actual password to GitHub")
    print("- Only commit the hash (it's safe)")
    print("- Keep the actual password in a password manager")
    print("- Share the password securely with authorized users only")
    print()

if __name__ == "__main__":
    main()
