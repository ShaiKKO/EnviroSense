"""
EnviroSense - TeraFlux Studios
Environmental Monitoring and Health Alert System
"""
from setuptools import setup, find_packages

setup(
    name="envirosense",
    version="0.0.1",
    description="Environmental Monitoring and Health Alert System",
    author="TeraFlux Studios",
    author_email="info@terafluxstudios.com",
    packages=find_packages(),
    install_requires=[
        # Core dependencies
        "numpy>=1.22.0",
        "pandas>=1.4.0",
        "scipy>=1.8.0",
        
        # API and web dependencies
        "fastapi>=0.78.0",
        "uvicorn>=0.17.6",
        "websockets>=10.3",
        
        # Visualization dependencies
        "streamlit>=1.10.0",
        "plotly>=5.8.0",
        
        # Utility dependencies
        "pydantic>=1.9.1",
    ],
    entry_points={
        "console_scripts": [
            "envirosense-state=envirosense.state.cli:main",
        ],
    },
    python_requires=">=3.8",
)
