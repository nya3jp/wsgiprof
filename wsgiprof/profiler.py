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

import cgi
import copy
import cProfile
import io
import itertools
import os
import pstats
import re
import subprocess
import time

import gprof2dot
import six
from six.moves.urllib import parse as urlparse


_VIEWER_TEMPLATE = """<!doctype html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>WSGI Profiler</title>
  </head>
  <body>
    <div style="float: right; border: 1px solid #444; margin: 8px; padding: 4px">
      <a href="/__profile__/tree.png?request_id={{ params.get('request_id', '') }}&amp;request_path_prefix={{ params.get('request_path_prefix', '') }}"><img src="/__profile__/tree.png?request_id={{ params.get('request_id', '') }}&amp;request_path_prefix={{ params.get('request_path_prefix', '') }}" style="width: 300px"></a>
    </div>
    <form method="GET" action="/__profile__/">
      <table>
        <tbody>
          <tr>
            <td>Request ID:</td>
            <td><input type="text" name="request_id" value="{{ params.get('request_id', '') }}" placeholder=""></td>
          </tr>
          <tr>
            <td>Request path prefix:</td>
            <td><input type="text" name="request_path_prefix" value="{{ params.get('request_path_prefix', '') }}" placeholder="/"></td>
          </tr>
          <tr>
            <td>Sort order:</td>
            <td>
              <select name="sort">
                <option value="cumtime" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'cumtime' else ''}}>cumulative time</option>
                <option value="filename" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'filename' else '' }}>file name</option>
                <option value="ncalls" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'ncalls' else '' }}>call count</option>
                <option value="pcalls" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'pcalls' else '' }}>primitive call count</option>
                <option value="line" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'line' else '' }}>line number</option>
                <option value="name" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'name' else '' }}>function name</option>
                <option value="nfl" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'nfl' else '' }}>name/file/line</option>
                <option value="stdname" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'stdname' else '' }}>standard name</option>
                <option value="tottime" {{ 'selected=selected' if params.get('sort', 'cumtime') == 'tottime' else '' }}>internal time</option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>
      <input type="submit" value="Refresh">
    </form>
    <pre>{{ stats_dump }}</pre>
  </body>
</html>
"""


def _render_template(template_html, template_dict):
    def replace_placeholder(m):
        value = eval(m.group(1), template_dict)
        return cgi.escape(value, quote=True)
    rendered_html = re.sub(r'\{\{(.*?)\}\}', replace_placeholder, template_html)
    return rendered_html.encode('utf-8')


def _parse_params(environ):
    params = dict(urlparse.parse_qsl(environ.get('QUERY_STRING', '')))
    if six.PY2:
        params = {key: value.decode('utf-8') for key, value in params.iteritems()}
    return params


class PersistentProfileResult(object):
    def __init__(self, profile):
        profile.create_stats()
        self._stats = profile.stats

    def create_stats(self):
        pass

    @property
    def stats(self):
        return copy.deepcopy(self._stats)

    @stats.setter
    def stats(self, value):
        pass  # ignore


class StartResponseHook(object):
    def __init__(self, start_response):
        self._start_response = start_response
        self.html_output = None

    def __call__(self, status, response_headers, exc_info=None):
        content_type, _ = self._find_header(response_headers, 'Content-Type')
        if (content_type and (
                'text/html' in content_type.lower() or
                'application/xhtml+xml' in content_type.lower())):
            self.html_output = True
            _, i = self._find_header(response_headers, 'Content-Length')
            if i is not None:
                del response_headers[i]
        else:
            self.html_output = False
        return self._start_response(status, response_headers, exc_info)

    @staticmethod
    def _find_header(response_headers, name, default=None):
        for i, (entry_name, entry_value) in enumerate(response_headers):
            if entry_name.lower() == name.lower():
                return entry_value, i
        return default, None


class ProfileMiddleware(object):
    def __init__(self, app):
        self._base_app = app
        self._results_by_path = {}
        self._result_by_id = {}

    def __call__(self, environ, start_response):
        if environ['REQUEST_METHOD'] == 'GET':
            path = environ['PATH_INFO'].strip('/')
            if path == '__profile__':
                return self._viewer_handler(environ, start_response)
            elif path == '__profile__/tree.png':
                return self._tree_handler(environ, start_response)
        return self._record_handler(environ, start_response)

    def _record_handler(self, environ, start_response):
        profile = cProfile.Profile()
        path = environ['PATH_INFO']
        id = '%.0f' % (time.time() * 1000000)
        try:
            start_response_hook = StartResponseHook(start_response)
            start_time = time.time()
            response = profile.runcall(self._base_app, environ, start_response_hook)
            end_time = time.time()
            if start_response_hook.html_output:
                profile_link = (
                    '[ Profiler: %.3fs. '
                    '<a href="/__profile__/?request_id=%s">Details</a> ]' %
                    (end_time - start_time, id)).encode('utf-8')
                if isinstance(response, tuple):
                    response = list(response) + [profile_link]
                elif isinstance(response, list):
                    response.append(profile_link)
                else:
                    response = itertools.chain(response, [profile_link])
            return response
        finally:
            result = PersistentProfileResult(profile)
            self._result_by_id[id] = result
            self._results_by_path.setdefault(path, []).append(result)

    def _get_results_by_request(self, params):
        request_id = params.get('request_id', '')
        if request_id:
            results = [self._result_by_id[request_id]]
        else:
            request_path_prefix = params.get('request_path_prefix', '')
            results = []
            for request_path, subresults in self._results_by_path.items():
                if request_path.startswith(request_path_prefix):
                    results.extend(subresults)
        return results

    def _viewer_handler(self, environ, start_response):
        params = _parse_params(environ)
        sort_order = params.get('sort', 'cumtime')
        results = self._get_results_by_request(params)
        if not results:
            stats_dump = 'No matching log.'
        else:
            output = io.StringIO() if six.PY3 else io.BytesIO()
            # pstats.Stats() hits recursion limit when many profiles are passed.
            stats = pstats.Stats(results[0], stream=output)
            for result in results[1:]:
                stats.add(result)
            stats.strip_dirs()
            stats.sort_stats(sort_order)
            stats.print_stats()
            stats_dump = output.getvalue()
            if six.PY2:
                stats_dump = stats_dump.decode('utf-8')
        html = _render_template(
            _VIEWER_TEMPLATE,
            {'params': params, 'stats_dump': stats_dump})
        start_response('200 OK', [('Content-Type', 'text/html')])
        return [html]

    def _tree_handler(self, environ, start_response):
        params = _parse_params(environ)
        node_thres = float(params.get('node_thres', 0.5))
        edge_thres = float(params.get('edge_thres', 0.1))
        results = self._get_results_by_request(params)
        if not results:
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [b'No matching log.']

        # pstats.Stats() hits recursion limit when many profiles are passed.
        parser = gprof2dot.PstatsParser(results[0])
        for result in results[1:]:
            parser.stats.add(result)
        parsed_profile = parser.parse()
        parsed_profile.prune(node_thres / 100.0, edge_thres / 100.0)

        output = io.StringIO() if six.PY3 else io.BytesIO()
        writer = gprof2dot.DotWriter(output)
        writer.graph(parsed_profile, gprof2dot.TEMPERATURE_COLORMAP)
        dot_data = output.getvalue()
        if six.PY3:
            dot_data = dot_data.encode('utf-8')

        try:
            proc = subprocess.Popen(
                ['dot', '-Tpng'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
            png_data, _ = proc.communicate(dot_data)
        except Exception:
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [b'ERROR: Failed to execute "dot". Please install graphviz.']
        else:
            start_response('200 OK', [('Content-Type', 'image/png')])
            return [png_data]
