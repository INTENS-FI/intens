from setuptools import setup

setup(
    name='SimsvcClient',
    version='0.2.0',
    description='Python client for distributed simulation service',
    packages=['simclient'],
    author='Hannu Rummukainen',
    author_email='hannu.rummukainen@vtt.fi',
    keywords=['simulation'],
    python_requires=">= 3.6",
    install_requires=["requests", "python-socketio", "numpy"],
    extras_require={"bo": ["dragonfly", "pandas", "pyyaml"]}
)
