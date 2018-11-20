from setuptools import setup, find_packages
setup(
    name="Simsvc",
    version="0.1",
    author="Timo Korvola",
    author_email="Timo.Korvola@vtt.fi",
    description="A distributed simulation service",
    packages=["simsvc"],
    scripts=["run-server.py"],
    python_requires=">= 3.6",
    install_requires=["Flask", "Flask-SocketIO", "ZODB", "eventlet", 
                      "dask", "distributed >= 1.24.1", "tornado >= 5.1.1"],
)
