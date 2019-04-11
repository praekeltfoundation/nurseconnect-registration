from setuptools import find_packages, setup

setup(
    name="nurseconnect-registration",
    version="0.0.1",
    url="http://github.com/praekeltfoundation/nurseconnect-registration",
    license="BSD",
    author="Praekelt.org",
    author_email="dev@praekelt.org",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django==2.1.7",
        "django-environ==0.4.5",
        "psycopg2==2.7.7",
        "phonenumberslite==8.10.7",
        "django-prometheus==1.0.15",
        "django-watchman==0.16.0",
        "hashids==1.2.0",
        "djangorestframework==3.9.2",
        "coreapi==2.3.3",
        "rapidpro-python==2.1.8",
        "wabclient==2.2.1",
        # wabclient depends on six, but doesn't specify it in dependancies
        "six==1.12.0",
        "celery==4.3.0",
        "raven==6.10.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Django",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
