wsgiprof
========

wsgiprof is a lightweight WSGI profiler with call graph visualization.

|PyPI version|

Screenshot
----------

|Screenshot|

Usage
-----

.. code:: python

    import wsgiprof

    application = wsgiprof.ProfileMiddleware(application)

Access to the application several times, and visit URL /\_\_profile\_\_
.

Please note that graphviz is required to render call graph.

Changelog
---------

1.0.0 (2015-09-02)

-  First release.

Author
------

Shuhei Takahashi

-  Website: https://nya3.jp/
-  Twitter: https://twitter.com/nya3jp/

License
-------

Copyright 2015 Shuhei Takahashi All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may
not use this file except in compliance with the License. You may obtain
a copy of the License at

::

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

.. |PyPI version| image:: https://badge.fury.io/py/wsgiprof.svg
   :target: http://badge.fury.io/py/wsgiprof
.. |Screenshot| image:: https://raw.githubusercontent.com/nya3jp/wsgiprof/master/docs/screenshot1.png
   :target: https://raw.githubusercontent.com/nya3jp/wsgiprof/master/docs/screenshot1.png
