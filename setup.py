from setuptools import find_packages, setup
from coderush_cli import __version__

setup(
  name="coderush-cli",
  version=__version__,
  packages=find_packages(),
  include_package_data=True,
  install_requires=[
    "PyGithub",
    "slackclient",
    "python-dotenv",
    "pandas",
    "anthropic",
    "slack_sdk",
    "splitio_client",
    "setuptools",
    "colorama",
    "rich-click>=1.6.1",
    "rich>=13.3.5",
    "plotly",
    "markdown",
  ],
  entry_points={
    "console_scripts": [
      "coderush-cli=coderush_cli.main:main",
    ],
  },
  author="Coderush",
  author_email="prashant@coderush.ai",
  description="Engineering Team Metrics Script",
  long_description=open("README.md").read(),
  long_description_content_type="text/markdown",
  url="https://github.com/coderush/coderush-cli",
  classifiers=[
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
  ],
  python_requires=">=3.7",
)
