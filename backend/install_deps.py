#!/usr/bin/env python3
"""
Install dependencies for RStudio AI Backend
"""

import subprocess
import sys

def install_package(package):
    """Install a Python package"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}")
        return False

def main():
    """Install all required dependencies"""
    print("🔧 Installing RStudio AI Backend Dependencies")
    print("=" * 50)
    
    # Core dependencies
    core_packages = [
        "fastapi",
        "uvicorn",
        "httpx",
        "pydantic"
    ]
    
    # Admin dashboard dependencies
    admin_packages = [
        "requests",
        "tabulate"
    ]
    
    print("Installing core dependencies...")
    for package in core_packages:
        install_package(package)
    
    print("\nInstalling admin dashboard dependencies...")
    for package in admin_packages:
        install_package(package)
    
    print("\n🎉 Installation complete!")
    print("\nTo start the backend:")
    print("  cd backend")
    print("  source venv/bin/activate")
    print("  uvicorn main:app --host 127.0.0.1 --port 8001")
    print("\nTo use the admin dashboard:")
    print("  cd backend")
    print("  python admin_dashboard.py")

if __name__ == "__main__":
    main() 