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

import collections
import cProfile
import cStringIO
import os
import pstats
import subprocess
import tempfile

import bottle
import gprof2dot
import paste.urlmap


class ViewerApplication(object):
  def __init__(self, profile_map):
    self._profile_map = profile_map
    self._app = bottle.Bottle()
    self._app.get('/')(self._index_handler)
    self._app.get('/tree.png')(self._tree_handler)

  def __call__(self, environ, start_response):
    return self._app(environ, start_response)

  def _index_handler(self):
    request_path_prefix = bottle.request.query.get('request_path_prefix', '')
    sort_order = bottle.request.query.get('sort', 'cumtime')
    filtered_profiles = [
        profile for request_path, profile in self._profile_map.iteritems()
        if request_path.startswith(request_path_prefix)]
    if not filtered_profiles:
      stats_dump = 'No matching log.'
    else:
      output = cStringIO.StringIO()
      # pstats.Stats() hits recursion limit when many profiles are passed.
      stats = pstats.Stats(filtered_profiles[0], stream=output)
      for profile in filtered_profiles[1:]:
        stats.add(profile)
      stats.strip_dirs()
      stats.sort_stats(sort_order)
      stats.print_stats()
      stats_dump = output.getvalue()
    template_dict = {
        'query': bottle.request.query,
        'stats_dump': stats_dump,
    }
    return bottle.template(
        'profiler.html', template_dict,
        template_lookup=[os.path.dirname(__file__)])

  def _tree_handler(self):
    request_path_prefix = bottle.request.query.get('request_path_prefix', '')
    node_thres = float(bottle.request.query.get('node_thres', 0.5))
    edge_thres = float(bottle.request.query.get('edge_thres', 0.1))
    filtered_profiles = [
        profile for request_path, profile in self._profile_map.iteritems()
        if request_path.startswith(request_path_prefix)]
    if not filtered_profiles:
      return 'No matching log.'
    # pstats.Stats() hits recursion limit when many profiles are passed.
    parser = gprof2dot.PstatsParser(filtered_profiles[0])
    for profile in filtered_profiles[1:]:
      parser.stats.add(profile)
    parsed_profile = parser.parse()
    parsed_profile.prune(node_thres / 100.0, edge_thres / 100.0)
    output = cStringIO.StringIO()
    writer = gprof2dot.DotWriter(output)
    writer.graph(parsed_profile, gprof2dot.TEMPERATURE_COLORMAP)
    dot = output.getvalue()
    tmpfile = tempfile.NamedTemporaryFile()
    try:
      proc = subprocess.Popen(
          ['dot', '-Tpng', '-o', tmpfile.name],
          stdin=subprocess.PIPE)
      proc.communicate(dot)
    except Exception:
      tmpfile.close()
      return 'ERROR: Failed to execute "dot". Please install graphviz.'
    else:
      bottle.response.content_type = 'image/png'
      return bottle.WSGIFileWrapper(tmpfile)


class ProfileMiddleware(object):
  def __init__(self, app):
    self._base_app = app
    self._profile_map = collections.defaultdict(cProfile.Profile)
    self._viewer_app = ViewerApplication(self._profile_map)
    self._urlmap_app = paste.urlmap.URLMap(not_found_app=self._profiler_app)
    self._urlmap_app['/__profile__'] = self._viewer_app

  def __call__(self, environ, start_response):
    return self._urlmap_app(environ, start_response)

  def _profiler_app(self, environ, start_response):
    profile = self._profile_map[environ['PATH_INFO']]
    return profile.runcall(self._base_app, environ, start_response)
