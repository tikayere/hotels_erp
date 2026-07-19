from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

setup(
    name="hotel_erp",
    version="1.0.0",
    description="Hotel ERP / PMS — Service A of the hotel booking ecosystem",
    author="Hotel ERP Team",
    author_email="pourou.2000@gmail.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
