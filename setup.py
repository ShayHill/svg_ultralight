import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='svg_writer',
    version='0.1',
    author="Shay Hill",
    author_email="shay_public@hotmail.com",
    description="Write SVG files with Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ShayHill/svg_writer",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)



