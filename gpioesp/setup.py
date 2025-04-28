from setuptools import setup, find_packages

setup(
    name='gpioctrl',
    version='0.3',
    description='Python interface for controlling ESP32 GPIO with servo and stepper support',
    author='Your Name',
    packages=find_packages(),
    install_requires=['pyserial'],
    python_requires='>=3.6',
)
