from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="open-webui-mcp-connector",
    version="0.1.0",
    author="ivanuser",
    author_email="ivan@example.com",  # Replace with your email
    description="MCP Connector for Open WebUI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ivanuser/open-webui-mcp-connector",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.1",
        "aiohttp>=3.7.4",
        "pydantic>=1.8.2",
    ],
)