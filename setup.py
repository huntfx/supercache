import os
from setuptools import setup, find_packages


# Get the README.md text
with open(os.path.join(os.path.dirname(__file__), 'README.md'), 'r') as f:
    readme = f.read()

# Parse supercache/__init__.py for a version
with open(os.path.join(os.path.dirname(__file__), 'supercache/__init__.py'), 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = eval(line.split('=')[1].strip())
            break
    else:
        raise RuntimeError('no version found')

setup(
    name = 'supercache',
    packages = find_packages(),
    version = version,
    license='MIT',
    description = 'Easy to use and intuitive caching for functions.',
    long_description=readme,
    long_description_content_type='text/markdown',
    author = 'Peter Hunt',
    author_email='peter@huntfx.uk',
    url = 'https://github.com/Peter92/supercache',
    download_url = 'https://github.com/Peter92/supercache/archive/{}.tar.gz'.format(version),
    project_urls={
        #'Documentation': 'https://github.com/Peter92/supercache/wiki',
        'Source': 'https://github.com/Peter92/supercache',
        'Issues': 'https://github.com/Peter92/supercache/issues',
    },
    keywords = [
        'cache', 'caching', 'memoise', 'memoize', 'store',
    ],
    install_requires=[],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    python_requires=('>=2.7, !=3.0.*, !=3.1.*, !=3.2.*')
)
