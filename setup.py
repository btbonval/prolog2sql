from setuptools import setup

setup(name='prolog2sql',
      version='0.0.2',
      url='https://github.com/btbonval/',
      author='Bryan Bonvallet',
      author_email='btbonval@gmail.com',
      license='MIT',
      packages=['prolog2sql.py'],
      install_requires=[
        'parsimonious',
        'sqlalchemy>=1.3.0',
      ],
      zip_safe=False)
