from setuptools import setup, find_packages
setup(
    name="Simsvc",
    version="0.1",
    packages=["simsvc"],
    scripts=["run-server.py", "sio-test.py"],
    python_requires=">= 3.6",
    install_requires=["Flask", "Flask-SocketIO", "ZODB", "eventlet", 
                      "dask", "distributed", "socketIO-client"])
