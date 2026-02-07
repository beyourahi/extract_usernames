"""Setup configuration for Instagram Username Extractor."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="instagram-username-extractor",
    version="2.0.0",
    author="Rahi Khan",
    author_email="beyourahi@gmail.com",
    description="Extract Instagram usernames from screenshots with VLM+OCR dual-engine validation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/beyourahi/extract_usernames",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "extract-usernames=extract_usernames.cli:main",
        ],
    },
)
