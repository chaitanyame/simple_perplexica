#!/usr/bin/env python3
"""
Verify that all dependencies are at the latest stable versions.

This script checks installed versions against requirements files and reports
any discrepancies or potential issues.
"""

import subprocess
import sys
from pathlib import Path


def parse_requirements(file_path: Path) -> dict[str, str]:
    """Parse requirements file and return dict of package: version."""
    requirements = {}

    with open(file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Handle different formats: package==version, package[extra]==version
                if "==" in line:
                    # Remove comments
                    line = line.split("#")[0].strip()
                    # Handle extras like redis[hiredis]==5.2.0
                    if "[" in line:
                        package = line.split("[")[0]
                        version = line.split("==")[1].strip()
                    else:
                        package, version = line.split("==")
                    requirements[package.strip()] = version.strip()

    return requirements


def get_installed_versions() -> dict[str, str]:
    """Get currently installed package versions."""
    result = subprocess.run(["pip", "list", "--format=json"], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running pip list: {result.stderr}")
        sys.exit(1)

    import json

    packages = json.loads(result.stdout)
    return {pkg["name"].lower(): pkg["version"] for pkg in packages}


def compare_versions(
    required: dict[str, str], installed: dict[str, str]
) -> tuple[list[str], list[str], list[str]]:
    """
    Compare required and installed versions.

    Returns:
        Tuple of (matching, missing, mismatched)
    """
    matching = []
    missing = []
    mismatched = []

    for package, required_version in required.items():
        package_lower = package.lower()

        if package_lower not in installed:
            missing.append(f"{package}=={required_version}")
        elif installed[package_lower] != required_version:
            mismatched.append(
                f"{package}: required {required_version}, installed {installed[package_lower]}"
            )
        else:
            matching.append(package)

    return matching, missing, mismatched


def main():
    """Main verification function."""
    print("🔍 Verifying dependency versions...\n")

    # Get paths
    base_dir = Path(__file__).parent
    requirements_txt = base_dir / "requirements.txt"
    requirements_dev_txt = base_dir / "requirements-dev.txt"

    if not requirements_txt.exists():
        print(f"❌ {requirements_txt} not found")
        sys.exit(1)

    # Parse requirements
    print("📄 Parsing requirements files...")
    prod_requirements = parse_requirements(requirements_txt)
    dev_requirements = (
        parse_requirements(requirements_dev_txt) if requirements_dev_txt.exists() else {}
    )

    print(f"   Production packages: {len(prod_requirements)}")
    print(f"   Development packages: {len(dev_requirements)}")

    # Get installed versions
    print("\n📦 Checking installed packages...")
    installed = get_installed_versions()
    print(f"   Total installed: {len(installed)}")

    # Compare production dependencies
    print("\n✅ Production Dependencies:")
    matching, missing, mismatched = compare_versions(prod_requirements, installed)

    if matching:
        print(f"   ✓ {len(matching)} packages up to date")

    if missing:
        print(f"\n   ⚠️  {len(missing)} packages missing:")
        for pkg in missing:
            print(f"      - {pkg}")

    if mismatched:
        print(f"\n   ❌ {len(mismatched)} version mismatches:")
        for mismatch in mismatched:
            print(f"      - {mismatch}")

    # Compare development dependencies
    if dev_requirements:
        print("\n🧪 Development Dependencies:")
        matching_dev, missing_dev, mismatched_dev = compare_versions(dev_requirements, installed)

        if matching_dev:
            print(f"   ✓ {len(matching_dev)} packages up to date")

        if missing_dev:
            print(f"\n   ⚠️  {len(missing_dev)} packages missing:")
            for pkg in missing_dev:
                print(f"      - {pkg}")

        if mismatched_dev:
            print(f"\n   ❌ {len(mismatched_dev)} version mismatches:")
            for mismatch in mismatched_dev:
                print(f"      - {mismatch}")

    # Summary
    print("\n" + "=" * 60)
    total_missing = len(missing) + len(missing_dev)
    total_mismatched = len(mismatched) + len(mismatched_dev)

    if total_missing == 0 and total_mismatched == 0:
        print("✅ All dependencies are correctly installed!")
        print("\n💡 You can now proceed with development.")
        return 0
    else:
        print("⚠️  Issues found:")
        if total_missing > 0:
            print(f"   - {total_missing} packages need to be installed")
        if total_mismatched > 0:
            print(f"   - {total_mismatched} packages have wrong versions")

        print("\n💡 To fix, run:")
        if total_missing > 0 or total_mismatched > 0:
            print("   pip install -r requirements.txt")
            if dev_requirements and (missing_dev or mismatched_dev):
                print("   pip install -r requirements-dev.txt")

        return 1


if __name__ == "__main__":
    sys.exit(main())
