from setuptools import setup, find_packages
setup(
    name="Simsvc",
    version="0.5.1",
    author="Timo Korvola",
    author_email="Timo.Korvola@vtt.fi",
    description="A distributed simulation service",
    packages=["simsvc"],
    include_package_data=True,
    python_requires=">= 3.6",
    install_requires=["Flask", "Flask-SocketIO", "ZODB", "zodburi",
                      "dask", "distributed >= 1.25.0", "tornado >= 5.1.1",
                      "eventlet", "flask_httpauth", "passlib >= 1.7",
                      "pyyaml"],
)
