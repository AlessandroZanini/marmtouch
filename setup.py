from setuptools import setup, find_packages

setup(
    name="marmtouch",
    packages=find_packages(),
    use_scm_version= {
        'write_to': 'marmtouch/_version.py'
    },
    setup_requires=['setuptools_scm'],
    description="Experiment control software for marmoset touch screen apparatus",
    author='Janahan Selvanayagam',
    author_email='seljanahan@hotmail.com',
    keywords=['touchscreen','experiment'],
    install_requires=[
        "netifaces",
        "pyyaml",
        "pygame",
        "click",
        "RPi.GPIO",
        "picamera",
        "tqdm"
    ],
    entry_points='''
        [console_scripts]
        marmtouch=marmtouch.scripts:marmtouch
    ''',
    zip_safe=False
)
