from setuptools import setup, find_packages

setup(
    name="refcocos_annotator",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "refcocos_annotator": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
        ],
    },
    install_requires=[
        "flask>=2.0.0",
        "pillow>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "refcocos-annotator=refcocos_annotator.app:run_app",
        ],
    },
    author="Kuo Yang",
    author_email="kuoyang1999@gmail.com",
    description="Reference Expression Annotation Tool for COCO Dataset",
    keywords="coco, dataset, annotation, computer vision",
    url="https://github.com/kuoyang1999/refcocos-annotator",
    python_requires=">=3.6",
)