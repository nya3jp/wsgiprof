# Copyright 2015 Shuhei Takahashi All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import setuptools


def read_file(name):
  with open(os.path.join(os.path.dirname(__file__), name)) as f:
    return f.read().strip()


setuptools.setup(
    name='wsgiprof',
    version='1.0.0',
    author='Shuhei Takahashi',
    author_email='takahashi.shuhei@gmail.com',
    description='Lightweight WSGI Profiler with Call Graph Visualization',
    long_description=read_file('README.txt'),
    url='https://github.com/nya3jp/wsgiprof/',
    packages=['wsgiprof'],
    package_data={
        'wsgiprof': ['profiler.html'],
    },
    install_requires=read_file('requirements.txt').splitlines(),
    classifiers = [
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
