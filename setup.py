from setuptools import setup


def readme():
    with open('README.rst', encoding="utf8") as f:
        return f.read()


setup(name='htp-client',
      version='0.4.3',
      description='Make a Hecks engine using the HTP protocol play on the hecks.space website',
      long_description=readme(),
      url='http://github.com/unc0mm0n/htp-client.git',
      author='Yuval Wyborski',
      author_email='yvw.bor@gmail.com',
      packages=['htpclient'],
      license='WTFPL',
      zip_safe=False,
      include_package_data=True,

      install_requires=['selenium'],

      entry_points={
        'console_scripts': ['htpplay = htpclient.main:cli_main']
      })
