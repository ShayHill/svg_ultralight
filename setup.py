import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='svg_writer',
    version='0.5',
    author="Shay Hill",
    author_email="shay_public@hotmail.com",
    description="Write SVG files with Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ShayHill/svg_writer",
    py_modules=["svg_writer"],
    install_requires=['lxml'],
    tests_require=['pytest'],
    python_requires='>=3.4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)



