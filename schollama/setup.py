"""Setup script for the filellama package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README for the long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Core dependencies
CORE_DEPENDENCIES = [
    'pydantic>=2.5.2',
    'PyPDF2>=3.0.0',
    'pytesseract>=0.3.10',
    'Pillow>=10.0.0',
    'requests>=2.31.0',
    'aiohttp>=3.9.1',
    'semanticscholar>=0.5.0',
    'click>=8.1.7',
    'PyYAML>=6.0.1',
    'rich>=13.7.0',
    'structlog>=23.2.0',
    'pdf2image>=1.16.3',
    'anthropic>=0.3.11',
    'anyio<4.0.0,>=3.5.0',
    # Additional document processing libraries
    'python-docx>=0.8.11',  # For .docx files
    'python-pptx>=0.6.21',  # For .pptx files
    'markdown>=3.3.7',      # For .md files
    'pdfplumber>=0.7.6',    # Better PDF text extraction
    'textract>=1.6.5',      # Unified text extraction from multiple formats
    'tika-python>=1.24.0',  # Apache Tika integration for better document parsing
    'pypdf>=3.7.0',         # Modern PDF processing
    'pdfminer.six>=20221105',  # Advanced PDF text extraction
]

# Development dependencies
DEV_DEPENDENCIES = [
    'pytest>=7.4.3',
    'black>=23.11.0',
    'isort>=5.12.0',
    'flake8>=6.1.0',
    'mypy>=1.7.1'
]

setup(
    name='filellama',
    version='0.1.0',
    description='Intelligent academic file management and organization tool',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Luke Steuber',
    author_email='luke@steuber.io',
    packages=find_packages(),
    install_requires=CORE_DEPENDENCIES,
    extras_require={
        'dev': DEV_DEPENDENCIES,
    },
    entry_points={
        'console_scripts': [
            'filellama=filellama.cli.main:main',
        ],
    },
    python_requires='>=3.9',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
) 