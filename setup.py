# Tupan Water Maker - Setup
import os
from setuptools import setup

REPO = os.path.dirname(os.path.abspath(__file__))

setup(
    name="tupan-machina-de-chuva",
    version="0.1.0",
    author="Túlio Ferreira Horta",
    author_email="tulio.horta@pucmg.edu.br",
    description="Portable atmospheric water generator - academic project",
    long_description=open(os.path.join(REPO, "README.md"), encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tuliofh/tupan-machina-de-chuva",
    packages=[],
    install_requires=[
        "python-docx>=0.8.11",
        "matplotlib>=3.5.0",
        "python-pptx>=0.6.23",
        "Pillow>=9.0.0",
        "networkx>=2.8.0",
        "graphviz>=0.20.1",
        "flask>=3.0",
        "numpy>=1.24",
        "scikit-learn>=1.3",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.14",
        "Operating System :: OS Independent",
    ],
)