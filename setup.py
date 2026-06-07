from setuptools import setup, find_packages

setup(
    name="teach-skill-claude",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "click",
        "claude-agent-sdk",
    ],
    extras_require={
        "recorder": [
            "pywin32",
            "pynput",
            "Pillow",
            "pystray",
            "psutil",
            "uiautomation",
        ],
        "ui": [
            "PySide6",
        ],
        "dev": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "teach-skill=teach_skill.cli:main",
        ],
    },
)
