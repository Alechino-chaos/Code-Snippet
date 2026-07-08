from setuptools import setup

setup(
    name='Code-Snippet',
    version='1.1.0',
    description='A lightweight local CLI for managing code snippets.',
    py_modules=['main'],
    python_requires='>=3.8',
    install_requires=[
        'rich',
    ],
    entry_points={
        'console_scripts': [
            'snip = main:main', 
        ],
    },
)
