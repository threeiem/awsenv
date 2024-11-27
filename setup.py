from setuptools import setup, find_packages

setup(
    name="aws-environment-setup",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.28.44",
        "python-dotenv>=1.0.0",
        "pydantic>=2.3.0",
        "typer>=0.9.0",
    ],
)