#!/usr/bin/env python3
"""
Cross-platform installer for aicheckin.

This script installs the aicheckin tool system-wide and sets up
the required configuration file. It works on Windows, Linux, and macOS.

Usage:
    python install.py
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    
    # Check if we're on Windows and if ANSI is supported
    WINDOWS = platform.system() == "Windows"
    
    if WINDOWS:
        # Enable ANSI colors on Windows 10+
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            ENABLED = True
        except Exception:
            ENABLED = False
    else:
        ENABLED = True
    
    if ENABLED:
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        BOLD = '\033[1m'
        RESET = '\033[0m'
    else:
        GREEN = YELLOW = RED = BLUE = BOLD = RESET = ''


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def get_system_info() -> Tuple[str, str]:
    """Get system information.
    
    Returns:
        Tuple of (os_name, architecture)
    """
    os_name = platform.system()
    architecture = platform.machine()
    return os_name, architecture


def check_python_version() -> bool:
    """Check if Python version is 3.10 or higher.
    
    Returns:
        True if version is acceptable, False otherwise.
    """
    version = sys.version_info
    if version < (3, 10):
        print_error(f"Python 3.10 or higher is required.")
        print_error(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    
    print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def get_pip_command() -> list:
    """Get the appropriate pip command for the current system.
    
    Returns:
        List containing the pip command components.
    """
    return [sys.executable, "-m", "pip"]


def install_package() -> Tuple[bool, bool]:
    """Install the package using pip in editable mode.
    
    Returns:
        Tuple of (success, path_warning) where:
        - success: True if installation succeeded
        - path_warning: True if there was a PATH warning
    """
    print_info("Installing aicheckin package in editable mode...")
    
    project_dir = Path(__file__).parent
    pip_cmd = get_pip_command()
    
    try:
        # Install in editable mode
        result = subprocess.run(
            pip_cmd + ["install", "-e", "."],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        print_success("Package installed successfully")
        
        # Check if there's a PATH warning
        output = result.stdout + result.stderr
        has_path_warning = "is not on PATH" in output
        
        if has_path_warning:
            print_warning("Scripts directory is not on PATH (will be fixed)")
        
        return True, has_path_warning
        
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install package")
        if e.stderr:
            print(f"\nError details:\n{e.stderr}")
        if e.stdout:
            print(f"\nOutput:\n{e.stdout}")
        return False, False


def find_scripts_directory() -> Optional[Path]:
    """Find the Python Scripts directory where aicheckin was installed.
    
    Returns:
        Path to Scripts directory or None if not found.
    """
    print_info("Locating Scripts directory...")
    
    # Try to find where pip installed the script
    pip_cmd = get_pip_command()
    
    try:
        result = subprocess.run(
            pip_cmd + ["show", "-f", "vc-commit-helper"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output to find the location
        for line in result.stdout.splitlines():
            if line.startswith("Location:"):
                location = Path(line.split(":", 1)[1].strip())
                
                # Scripts directory is typically a sibling of site-packages
                if platform.system() == "Windows":
                    scripts_dir = location.parent / "Scripts"
                else:
                    scripts_dir = location.parent / "bin"
                
                if scripts_dir.exists():
                    print_info(f"Found Scripts directory: {scripts_dir}")
                    return scripts_dir
                
    except subprocess.CalledProcessError:
        pass
    
    # Fallback: check common locations
    print_info("Checking common installation locations...")
    
    if platform.system() == "Windows":
        # Windows Store Python
        user_base = Path.home() / "AppData" / "Local" / "Packages"
        if user_base.exists():
            for python_dir in user_base.glob("PythonSoftwareFoundation.Python.*"):
                scripts_dir = python_dir / "LocalCache" / "local-packages" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts"
                if scripts_dir.exists():
                    print_info(f"Found Scripts directory: {scripts_dir}")
                    return scripts_dir
        
        # Regular Python installation
        scripts_dir = Path(sys.prefix) / "Scripts"
        if scripts_dir.exists():
            print_info(f"Found Scripts directory: {scripts_dir}")
            return scripts_dir
    else:
        # Linux/Mac
        scripts_dir = Path(sys.prefix) / "bin"
        if scripts_dir.exists():
            print_info(f"Found Scripts directory: {scripts_dir}")
            return scripts_dir
        
        # User installation
        try:
            user_base = subprocess.run(
                [sys.executable, "-m", "site", "--user-base"],
                capture_output=True,
                text=True
            ).stdout.strip()
            scripts_dir = Path(user_base) / "bin"
            if scripts_dir.exists():
                print_info(f"Found Scripts directory: {scripts_dir}")
                return scripts_dir
        except Exception:
            pass
    
    print_warning("Could not locate Scripts directory automatically")
    return None


def add_to_path_windows(scripts_dir: Path) -> bool:
    """Add Scripts directory to Windows PATH.
    
    Args:
        scripts_dir: Path to the Scripts directory.
        
    Returns:
        True if successful, False otherwise.
    """
    try:
        import winreg
        
        print_info("Updating Windows PATH...")
        
        # Open the user environment variables key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        
        try:
            # Get current PATH
            current_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            current_path = ""
        
        # Check if already in PATH
        scripts_dir_str = str(scripts_dir)
        path_entries = [p.strip() for p in current_path.split(';') if p.strip()]
        
        # Case-insensitive check
        if any(scripts_dir_str.lower() == entry.lower() for entry in path_entries):
            print_success(f"Scripts directory already in PATH")
            winreg.CloseKey(key)
            return True
        
        # Add to PATH
        new_path = f"{current_path};{scripts_dir_str}" if current_path else scripts_dir_str
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)
        
        # Broadcast WM_SETTINGCHANGE to notify other applications
        try:
            import ctypes
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x1A
            SMTO_ABORTIFHUNG = 0x0002
            result = ctypes.c_long()
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST,
                WM_SETTINGCHANGE,
                0,
                "Environment",
                SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result)
            )
        except Exception:
            pass  # Not critical if broadcast fails
        
        print_success(f"Added to PATH: {scripts_dir}")
        return True
        
    except Exception as e:
        print_error(f"Failed to add to PATH: {e}")
        return False


def add_to_path_unix(scripts_dir: Path) -> bool:
    """Add Scripts directory to Unix PATH (Linux/Mac).
    
    Args:
        scripts_dir: Path to the bin directory.
        
    Returns:
        True if successful, False otherwise.
    """
    shell = os.environ.get("SHELL", "")
    home = Path.home()
    
    # Determine which shell config file to use
    if "zsh" in shell:
        rc_file = home / ".zshrc"
    elif "bash" in shell:
        rc_file = home / ".bashrc"
    else:
        rc_file = home / ".profile"
    
    export_line = f'export PATH="$PATH:{scripts_dir}"\n'
    
    try:
        print_info(f"Updating {rc_file.name}...")
        
        # Check if already in the file
        if rc_file.exists():
            content = rc_file.read_text()
            if str(scripts_dir) in content:
                print_success(f"Scripts directory already in {rc_file.name}")
                return True
        
        # Append to the file
        with open(rc_file, "a") as f:
            f.write(f"\n# Added by aicheckin installer\n")
            f.write(export_line)
        
        print_success(f"Added to PATH in {rc_file}")
        return True
        
    except Exception as e:
        print_error(f"Failed to add to PATH: {e}")
        return False


def setup_path(has_path_warning: bool) -> bool:
    """Set up PATH to include the Scripts directory.
    
    Args:
        has_path_warning: Whether pip warned about PATH.
        
    Returns:
        True if successful or not needed, False otherwise.
    """
    if not has_path_warning:
        print_success("Scripts directory is already on PATH")
        return False  # No update needed
    
    scripts_dir = find_scripts_directory()
    
    if not scripts_dir:
        print_warning("Could not locate Scripts directory")
        print_info("You may need to add it to PATH manually")
        return False
    
    os_name = platform.system()
    
    if os_name == "Windows":
        return add_to_path_windows(scripts_dir)
    else:
        return add_to_path_unix(scripts_dir)


def setup_config() -> bool:
    """Set up the Ollama configuration file in the user's home directory.
    
    Returns:
        True if successful, False otherwise.
    """
    config_dir = Path.home() / ".ollama_server"
    config_path = config_dir / ".ollama_config.json"
    
    if config_path.exists():
        print_success(f"Configuration file already exists")
        
        # Validate existing config
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            required_keys = ["base_url", "port", "model"]
            if all(key in config for key in required_keys):
                print_success("Configuration is valid")
                print_info(f"Config location: {config_path}")
                return True
            else:
                print_warning("Configuration is missing required keys")
        except Exception as e:
            print_warning(f"Configuration file is invalid: {e}")
    
    print_info("\nSetting up Ollama configuration...")
    print("Please provide the following information (press Enter for defaults):\n")
    
    try:
        base_url = input(f"  Ollama base URL [{Colors.BLUE}http://localhost{Colors.RESET}]: ").strip()
        base_url = base_url or "http://localhost"
        
        port = input(f"  Ollama port [{Colors.BLUE}11434{Colors.RESET}]: ").strip()
        port = port or "11434"
        
        model = input(f"  Ollama model [{Colors.BLUE}llama3{Colors.RESET}]: ").strip()
        model = model or "llama3"
        
        timeout = input(f"  Request timeout in seconds [{Colors.BLUE}60{Colors.RESET}]: ").strip()
        timeout = timeout or "60"
        
        max_tokens = input(f"  Max tokens (leave empty for default): ").strip()
        
        config = {
            "base_url": base_url,
            "port": int(port),
            "model": model,
            "request_timeout": float(timeout)
        }
        
        if max_tokens:
            config["max_tokens"] = int(max_tokens)
        
        # Create directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Write config file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        
        print_success(f"Configuration saved")
        print_info(f"Config location: {config_path}")
        return True
        
    except KeyboardInterrupt:
        print("\n")
        print_warning("Configuration setup cancelled")
        return False
    except Exception as e:
        print_error(f"Failed to save configuration: {e}")
        return False


def verify_installation() -> bool:
    """Verify that the installation was successful.
    
    Returns:
        True if aicheckin command is available, False otherwise.
    """
    print_info("Verifying installation...")
    
    try:
        # Try to run aicheckin --help
        result = subprocess.run(
            ["aicheckin", "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print_success("aicheckin command is available")
            return True
        else:
            print_warning("aicheckin command found but returned an error")
            return False
            
    except FileNotFoundError:
        print_warning("aicheckin command not found in current PATH")
        
        # Try with python -m
        try:
            result = subprocess.run(
                [sys.executable, "-m", "vc_commit_helper.cli", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                print_success("Module can be run with: python -m vc_commit_helper.cli")
                return True
        except Exception:
            pass
        
        return False
        
    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False


def print_usage_instructions(path_updated: bool, installation_verified: bool) -> None:
    """Print usage instructions after installation.
    
    Args:
        path_updated: Whether PATH was updated during installation.
        installation_verified: Whether the installation was verified successfully.
    """
    print_header("Installation Summary")
    
    os_name = platform.system()
    
    if path_updated:
        print_warning("PATH was updated - please restart your terminal!")
        if os_name == "Windows":
            print_info("Close this terminal and open a new one")
        else:
            print_info("Or run: source ~/.bashrc (or ~/.zshrc)")
        print()
    
    print(Colors.BOLD + "Usage:" + Colors.RESET)
    
    if installation_verified and not path_updated:
        print("  aicheckin              # Interactive mode")
        print("  aicheckin --yes        # Auto-accept all commits")
        print("  aicheckin --vcs git    # Force Git mode")
        print("  aicheckin --vcs svn    # Force SVN mode")
        print("  aicheckin --verbose    # Enable debug output")
    else:
        print(f"  {sys.executable} -m vc_commit_helper.cli              # Interactive mode")
        print(f"  {sys.executable} -m vc_commit_helper.cli --yes        # Auto-accept all commits")
        print(f"  {sys.executable} -m vc_commit_helper.cli --vcs git    # Force Git mode")
        print(f"  {sys.executable} -m vc_commit_helper.cli --verbose    # Enable debug output")
        
        if path_updated:
            print(f"\n  {Colors.YELLOW}After restarting terminal, you can use: aicheckin{Colors.RESET}")
    
    print("\n" + Colors.BOLD + "Next Steps:" + Colors.RESET)
    print("  1. Navigate to a Git or SVN repository")
    print("  2. Make some changes to files")
    if installation_verified and not path_updated:
        print("  3. Run 'aicheckin' to generate commit messages")
    else:
        print(f"  3. Run '{sys.executable} -m vc_commit_helper.cli' to generate commit messages")
    
    print()


def main() -> int:
    """Main installation routine.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print_header("aicheckin Installer")
    
    # Get system info
    os_name, arch = get_system_info()
    print_info(f"Operating System: {os_name} ({arch})")
    
    # Check Python version
    if not check_python_version():
        return 1
    
    # Install package
    print()
    package_installed, has_path_warning = install_package()
    
    if not package_installed:
        return 1
    
    # Set up PATH if needed
    print()
    path_updated = setup_path(has_path_warning)
    
    # Set up configuration
    print()
    config_ok = setup_config()
    
    if not config_ok:
        print_warning("Configuration setup incomplete")
        print_info("You can create .ollama_config.json manually later")
    
    # Verify installation
    print()
    installation_verified = verify_installation()
    
    # Print summary
    print()
    if installation_verified or package_installed:
        print_success("Installation completed successfully!")
        print_usage_instructions(path_updated, installation_verified)
        return 0
    else:
        print_error("Installation failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n")
        print_warning("Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)