from setuptools import setup

import webproj

with open("README.md") as f:
    readme = f.read()

setup(
    name="webproj",
    version=webproj.__version__,
    description="REST API for PROJ Transformations",
    license="MIT",
    keywords="PROJ transformations geodesy projections",
    author="Kristian Evers",
    author_email="kreve@sdfe.dk",
    url="https://github.com/Kortforsyningen/WEBPROJ",
    long_description=readme,
    packages=["webproj", "tests", "app"],
    install_requires=["flask", "flask-restx", "flask-cors", "pyproj"],
    test_suite="tests/test_api.py",
    data_files=["webproj/data.json"],
    include_package_data=True,
    zip_safe=False,
    entry_points="""
        [console_scripts]
        webproj=app.main:run
      """,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering :: GIS",
    ],
)
