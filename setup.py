import setuptools

long_description = open('README.md').read()

setuptools.setup(
    name="pykuna",
    version="0.7.1",
    author="Mark Coombes",
    author_email="mark@markcoombes.ca",
    description="Python3 async library for interacting with the Kuna camera mobile API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kevin-david/pykuna",
    packages=['pykuna'],
    # aiohttp is an extra, not a requirement: Home Assistant installs custom
    # requirements into a separate target directory, where a required aiohttp
    # would be installed again (with newer dependencies) over the one it ships.
    extras_require={'aiohttp': ['aiohttp']},
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ],
)
