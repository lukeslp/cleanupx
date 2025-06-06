#!/usr/bin/env python3
"""
cleanupx - Comprehensive File Processing Tool
Setup script for PyPI distribution

MIT License by Luke Steuber
Website: lukesteuber.com, assisted.site
Email: luke@lukesteuber.com
LinkedIn: https://www.linkedin.com/in/lukesteuber/
"""

from setuptools import setup, find_packages
import os
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read version from cleanupx_core/__init__.py
def get_version():
    """Extract version from __init__.py"""
    with open('cleanupx_core/__init__.py', 'r') as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip('"').strip("'")
    return "2.0.0"

# Core dependencies that are always required
REQUIRED = [
    'requests>=2.31.0',
    'python-dotenv>=0.15.0',
    'rich>=13.7.0',
    'inquirer>=3.4.0',
    'pillow>=10.0.0',
    'backoff>=2.2.0',
]

# Optional dependencies for extended functionality
EXTRAS = {
    'ai': [
        'openai>=1.0.0',
    ],
    'documents': [
        'PyPDF2>=3.0.1',
        'python-docx>=1.1.2',
    ],
    'images': [
        'pyheif>=0.7.1',
    ],
    'archives': [
        'rarfile>=4.0',
    ],
    'dev': [
        'pytest>=7.0.0',
        'black>=22.0.0',
        'flake8>=4.0.0',
        'build>=0.8.0',
        'twine>=4.0.0',
    ]
}

# All optional dependencies combined
EXTRAS['all'] = [dep for deps in EXTRAS.values() for dep in deps]

setup(
    name="cleanupx",
    version=get_version(),
    author="Luke Steuber",
    author_email="luke@lukesteuber.com",
    description="Comprehensive AI-powered file processing and organization tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lukeslp/cleanupx",
    project_urls={
        "Homepage": "https://lukesteuber.com",
        "Documentation": "https://github.com/lukeslp/cleanupx#readme",
        "Repository": "https://github.com/lukeslp/cleanupx",
        "Bug Tracker": "https://github.com/lukeslp/cleanupx/issues",
        "Changelog": "https://github.com/lukeslp/cleanupx/blob/main/CHANGELOG.md",
        "Author Website": "https://lukesteuber.com",
        "Assistant Platform": "https://assisted.site",
        "Newsletter": "https://lukesteuber.substack.com/",
        "Support": "https://usefulai.lemonsqueezy.com/buy/bf6ce1bd-85f5-4a09-ba10-191a670f74af",
    },
    packages=find_packages(),
    py_modules=['cleanupx'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "Topic :: System :: Archiving",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Text Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Natural Language :: English",
    ],
    python_requires=">=3.8",
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    entry_points={
        'console_scripts': [
            'cleanupx=cleanupx:main',
            'cleanupx-status=cleanupx_core:print_status',
        ],
    },
    include_package_data=True,
    package_data={
        'cleanupx_core': ['*.md', '*.txt', '*.json'],
    },
    keywords=[
        'file-processing', 'ai', 'deduplication', 'organization', 
        'cleanup', 'images', 'accessibility', 'privacy', 'automation',
        'cli', 'productivity', 'utilities', 'xai', 'machine-learning'
    ],
    license="MIT",
    zip_safe=False,
) 