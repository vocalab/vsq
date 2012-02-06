# -*- coding: utf-8 -*-

import os
import cgi
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
import simplejson as json
from vsq import *

class MainPage(webapp.RequestHandler):
    def get(self):
        template_values = {
                'greeting': 'VSQファイルを解析し、加工するプログラムです'
                }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class ParserPage(webapp.RequestHandler):
    def post(self):
        data = self.request.get('file')
        file_name = self.request.body_file.vars['file'].filename
        editor = VSQEditor(string = data)
        lyrics = editor.get_lyrics()
        rules = [zuii_rule, san_rule]
        #candidates = editor.get_rule_cands(zuii_rule)
        #candidates.update(editor.get_rule_cands(san_rule))

        output_lyrics = []
        candidates_keys = []
        for i, r in enumerate(rules):
            before_index = 0
            candidate_keys = []
            candidates = editor.get_rule_cands(r)
            output_lyrics.append("")
            for key, value in sorted(candidates.items(), key=lambda x:x[1]["s_index"]):
                s_index = value["s_index"]
                e_index = value["e_index"]
                output_lyrics[i] += lyrics[before_index:s_index].encode('utf-8') if (s_index > before_index) else ""
                output_lyrics[i] += "<span id=\"range"+key+"\" class=\"chooseable\">"+ lyrics[s_index:e_index].encode('utf-8') + "</span>"
                before_index = e_index
                candidate_keys.append(key)
            output_lyrics[i] += lyrics[before_index:].encode('utf-8') if (before_index != len(lyrics)) else ""
            candidates_keys.append(candidate_keys)

        memcache.set_multi({ "data": data,
            "name": file_name },
            key_prefix="vsq_", time=3600)
        template_values = {
                'lyrics': zip(candidates_keys, output_lyrics)
                }
        path = os.path.join(os.path.dirname(__file__), 'parse.html')
        self.response.out.write(template.render(path, template_values))

class AppliedVsqJSON(webapp.RequestHandler):
    def post(self):
        data = memcache.get("vsq_data")
        editor = VSQEditor(string = data)
        candidates = editor.get_rule_cands(zuii_rule)
        candidates.update(editor.get_rule_cands(san_rule))
        keys = self.request.get_all("rule")

        for key in keys:
            editor.apply_rule(candidates[key])
        dyn_list = [[p['time'],p['value']] for p in editor.get_dynamics_curve()]
        self.response.content_type = "application/json"
        self.response.out.write(json.dumps(dyn_list))

class DownloadPage(webapp.RequestHandler):
    def post(self):
        data = memcache.get("vsq_data")
        file_name = memcache.get("vsq_name")
        editor = VSQEditor(string = data)
        candidates = editor.get_rule_cands(zuii_rule)
        candidates.update(editor.get_rule_cands(san_rule))
        keys = self.request.get_all("rule")

        for key in keys:
            editor.apply_rule(candidates[key])
        self.response.headers['Content-Type'] = "application/x-vsq; charset=Shift_JIS"
        self.response.headers['Content-disposition'] = "filename=" + file_name.encode("utf-8")
        self.response.out.write(editor.unparse())

application = webapp.WSGIApplication(
                                        [('/', MainPage),
                                         ('/parse', ParserPage),
                                         ('/appliedvsq', AppliedVsqJSON),
                                         ('/download', DownloadPage)],
                                        debug=True)

def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
