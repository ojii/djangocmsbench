import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "djangocmsbench",
    version = "0.1",
    description = "A harness and a set of benchmarks for measuring django CMS's performance over time.",
    long_description = read('README.rst'),
    url = 'http://github.com/ojii/djangocmsbench',
    license = 'BSD',
    author = 'Jonas Obrist',
    author_email = 'jonas.obrist@divio.ch',
    packages = find_packages(),
    include_package_data = True,
    zip_safe=False,
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Benchmark'
    ],
    install_requires = ['argparse==1.1', 'Unipath==0.2.1', 'simplejson==2.1.1', 'virtualenv==1.6.4'],
        
    entry_points = {
        'console_scripts': ['djangocmsbench = djangocmsbench.main:main']
    }
)
