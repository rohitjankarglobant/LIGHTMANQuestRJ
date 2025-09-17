from setuptools import setup, find_packages

setup(
    name="minitel_lite_client",
    version="0.1.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'minitel-lite=minitel_lite_client.cli:main'
        ]
    },
    install_requires=[
        # No external dependencies - using standard libraries
    ],
    python_requires='>=3.8',
)
