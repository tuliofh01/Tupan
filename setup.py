# Tupan Water Maker - Setup
from setuptools import setup, find_packages

setup(
    name="tupan-water-maker",
    version="0.1.0",
    author="Túlio Ferreira Horta",
    author_email="tulio.horta@pucmg.edu.br",
    description="Portable atmospheric water generator - academic project",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/tuliofh/tupan-water-maker",
    packages=find_packages(),
    install_requires=[
        "python-docx>=0.8.11",
        "matplotlib>=3.5.0",
        "python-pptx>=0.6.23",
        "Pillow>=9.0.0",
        "networkx>=2.8.0",
        "graphviz>=0.20.1",
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