from setuptools import setup
import re

requirements = []
with open('requirements.txt') as f:
  requirements = f.read().splitlines()

version = ''
with open('discordanalytics/__init__.py') as f:
  version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', f.read(), re.MULTILINE).group(1)

if not version:
  raise RuntimeError('version is not set')

if version.endswith(('a', 'b', 'rc')):
  try:
    import subprocess
    p = subprocess.Popen(['git', 'rev-list', '--count', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if out:
      version += out.decode('utf-8').strip()
    p = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if out:
      version += '+g' + out.decode('utf-8').strip()
  except Exception:
    pass

readme = ''
with open('README.md') as f:
  readme = f.read()

packages = [
  'discordanalytics'
]

setup(
  name='discordanalytics',
  author='ValDesign',
  url='https://github.com/DiscordAnalytics/python-package',
  project_urls={
    'Documentation': 'https://docs.discordanalytics.xyz',
    'Issue tracker': 'https://github.com/DiscordAnalytics/python-package/issues'
  },
  version=version,
  packages=packages,
  license='MIT',
  description='A Python package for interacting with Discord Analytics API',
  long_description=readme,
  long_description_content_type='text/markdown',
  include_package_data=True,
  install_requires=requirements,
  python_requires='>=3.8.0'
)