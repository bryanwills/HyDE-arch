import os
import sys
import subprocess
import shutil
import argparse
import importlib

lib_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, lib_dir)

import xdg_base_dirs  # noqa: E402
import wrapper.libnotify as notify  # noqa: E402
import logger  # noqa: E402


if lib_dir is None:
    raise FileNotFoundError("None of the specified lib directories exist.")
    sys.exit(1)


def get_venv_path():
    """Set up the virtual environment path and modify sys.path."""
    venv_path = os.path.join(xdg_base_dirs.xdg_state_home(), "hyde", "pip_env")
    if not os.path.exists(venv_path):
        venv_path = os.path.expanduser("~/.local/state/hyde/pip_env")
    site_packages_path = os.path.join(
        venv_path,
        "lib",
        f"python{sys.version_info.major}.{sys.version_info.minor}",
        "site-packages",
    )
    sys.path.insert(0, site_packages_path)
    return venv_path


def create_venv(venv_path, requirements_file=None):
    """Create a virtual environment and optionally install dependencies."""
    if not os.path.exists(os.path.join(venv_path, "bin", "pip")):
        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
        # logger.debug(f"Virtual environment created at {venv_path}")
        pip_executable = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_executable, "install", "--upgrade", "pip"], check=True)
        # logger.debug("pip upgraded to the latest version")
        if requirements_file and os.path.exists(requirements_file):
            result = subprocess.run(
                [pip_executable, "install", "-r", requirements_file],
                capture_output=True,
                text=True,
            )
            logger.debug(f"Command output: {result.stdout}")
            logger.debug(f"Command error: {result.stderr}")
            result.check_returncode()
            # logger.debug(f"Dependencies installed from {requirements_file}")
    else:
        logger.debug(f"Virtual environment already exists at {venv_path}")
        pass


def destroy_venv(venv_path):
    """Destroy the virtual environment while retaining the requirements.txt file."""
    if os.path.exists(venv_path):
        shutil.rmtree(venv_path)
        # logger.debug(f"Virtual environment destroyed at {venv_path}")
    # else:
    # logger.debug(f"No virtual environment found at {venv_path}")


def install_dependencies(venv_path, requirements_file):
    """Install dependencies in the virtual environment."""
    if not os.path.exists(venv_path):
        create_venv(venv_path, requirements_file)
    else:
        pip_executable = os.path.join(venv_path, "bin", "pip")
        command = [pip_executable, "install", "-r", requirements_file]
        # logger.debug(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True)
        # logger.debug(f"Command output: {result.stdout}")
        # logger.debug(f"Command error: {result.stderr}")
        result.check_returncode()
        # logger.debug(f"Dependencies installed from {requirements_file}")


def install_package(venv_path, package):
    """Install a single package in the virtual environment."""
    if not os.path.exists(venv_path):
        create_venv(venv_path)
    pip_executable = os.path.join(venv_path, "bin", "pip")
    result = subprocess.run(
        [pip_executable, "install", package],
        capture_output=True,
        text=True,
    )
    # logger.debug(f"Command output: {result.stdout}")
    # logger.debug(f"Command error: {result.stderr}")
    result.check_returncode()
    # logger.debug(f"Package {package} installed")


def uninstall_package(venv_path, package):
    """Uninstall a single package from the virtual environment."""
    pip_executable = os.path.join(venv_path, "bin", "pip")
    result = subprocess.run(
        [pip_executable, "uninstall", "-y", package],
        capture_output=True,
        text=True,
    )
    # logger.debug(f"Command output: {result.stdout}")
    # logger.debug(f"Command error: {result.stderr}")
    result.check_returncode()
    # logger.debug(f"Package {package} uninstalled")


def v_import(module_name):
    """Dynamically import a module, installing it if necessary."""
    venv_path = get_venv_path()
    sys.path.insert(0, venv_path)  # Ensure sys.path is updated before import
    try:
        module = importlib.import_module(module_name)
        return module
    except ImportError:
        notify.send("HyDE Waybar", f"Installing {module_name} module...")
        install_package(venv_path, module_name)

        # Reload sys.path to include the new module
        importlib.invalidate_caches()
        sys.path.insert(0, venv_path)
        sys.path.insert(
            0,
            os.path.join(
                venv_path,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            ),
        )

        try:
            module = importlib.import_module(module_name)
            notify.send("HyDE Waybar", f"Successfully installed {module_name}.")
            return module
        except ImportError as e:
            notify.send(
                "HyDE Error",
                f"Failed to import module {module_name} after installation: {e}",
                urgency="critical",
            )
            raise


def v_install(module_name, force_reinstall=False):
    """Install a module in the virtual environment without importing it.
    Args:
        module_name (str): Name of module to install
        force_reinstall (bool): If True, reinstall even if module exists
    """
    venv_path = get_venv_path()
    if not os.path.exists(os.path.join(venv_path, "bin", "pip")):
        create_venv(venv_path)
    pip_executable = os.path.join(venv_path, "bin", "pip")
    # Check if module is already installed
    result = subprocess.run(
        [pip_executable, "show", module_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or force_reinstall:
        notify.send("HyDE Waybar", f"Installing {module_name} module...")
        install_package(venv_path, module_name)
        notify.send("HyDE Waybar", f"Successfully installed {module_name}.")
    sys.path.insert(0, venv_path)
    sys.path.insert(
        0,
        os.path.join(
            venv_path,
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        ),
    )


def main(args):
    parser = argparse.ArgumentParser(description="Python environment manager for HyDE")
    subparsers = parser.add_subparsers(dest="command")

    create_parser = subparsers.add_parser(
        "create", help="Create the virtual environment"
    )
    create_parser.set_defaults(func=create_venv)

    install_parser = subparsers.add_parser(
        "install", help="Install dependencies or a single package"
    )
    install_parser.add_argument("packages", nargs="*", help="Packages to install")
    install_parser.add_argument(
        "-f",
        "--requirements",
        type=str,
        help="The requirements file to use for installation",
    )
    install_parser.set_defaults(func=install_dependencies)

    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Uninstall a single package"
    )
    uninstall_parser.add_argument("package", help="Package to uninstall")
    uninstall_parser.set_defaults(func=uninstall_package)

    destroy_parser = subparsers.add_parser(
        "destroy", help="Destroy the virtual environment"
    )
    destroy_parser.set_defaults(func=destroy_venv)

    args = parser.parse_args(args)

    venv_path = get_venv_path()
    requirements_file = os.path.join(
        os.path.expanduser("~/.local/lib/hyde/pyutils"), "requirements.txt"
    )

    if args.command == "create":
        args.func(venv_path, requirements_file)
    elif args.command == "install":
        if args.packages:
            for package in args.packages:
                install_package(venv_path, package)
        else:
            args.func(venv_path, args.requirements or requirements_file)
    elif args.command == "uninstall":
        args.func(venv_path, args.package)
    elif args.command == "destroy":
        args.func(venv_path)
    else:
        parser.print_help()


def hyde(args):
    """Python environment manager for HyDE.

    Args:
        args (string): options
    """
    main(args)


if __name__ == "__main__":
    hyde(sys.argv[1:])

# Call get_venv_path() to set up the virtual environment path
sys.path.insert(0, get_venv_path())
