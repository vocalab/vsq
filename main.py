# -*- coding: utf-8 -*-

import os
import logging
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
import simplejson as json
from vsq import *

class MainPage(webapp.RequestHandler):
    def get(self):
        template_values = {
                'greeting': 'VSQファイルを解析し、加工するプログラムです<br>画像はwin内のデータを使っているので、完成次第差し替えてください。',
                
                }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class ParserPage(webapp.RequestHandler):
    def post(self):
        data = self.request.get('file')
        file_name = self.request.body_file.vars['file'].filename
        editor = VSQEditor(binary = data)
        rules = [zuii_rule, san_rule, port_rule, n_accent_rule]

        cand_ids = [c['id'] for c in editor.get_rule_cands(*rules)]
        memcache.set_multi(
                {"editor": editor, "name": file_name},
                key_prefix="vsq_",
                time=3600
                )
        template_values = {
                'cand_ids': cand_ids,
                'rules': rules,
                'vsq_length': editor.end_time - editor.start_time
                }
        path = os.path.join(os.path.dirname(__file__), 'parse.html')
        self.response.out.write(template.render(path, template_values))

class AppliedLyricJSON(webapp.RequestHandler):
    def get(self):
        editor = memcache.get("vsq_editor")
        rules = [zuii_rule, san_rule, port_rule, n_accent_rule]
        candidates = editor.get_rule_cands(*rules)

        anote_list = []
        for a in editor.anotes:
            rules_for_json = [{"name": c["rule"]["name"], "id": c["id"]}
                        for c in candidates if a in c["anotes"]]
            anote_for_json = {"lyric": a.lyric.encode('utf-8'),
                              "start_time": a.start,
                              "length": a.length,
                              "rules": rules_for_json}
            anote_list.append(anote_for_json)

        self.response.content_type = "application/json"
        self.response.out.write(json.dumps(anote_list))

class AppliedVsqJSON(webapp.RequestHandler):
    def post(self):
        editor = memcache.get("vsq_editor")
        file_name = memcache.get("vsq_name")
        rules = [zuii_rule, san_rule, port_rule, n_accent_rule]
        cands = editor.get_rule_cands(*rules)
        select_ids = self.request.get_all("rule")

        for c in cands:
            if c['id'] in select_ids:
                editor.apply_rule(c)
            else:
                editor.unapply_rule(c)

        memcache.replace_multi(
                { "editor": editor,"name": file_name },
                time=3600,
                key_prefix="vsq_"
                )

        dyn_list = [[p['time'],p['value']] for p in editor.get_dynamics_curve()]
        pit_list = [[p['time'],p['value']] for p in editor.get_pitch_curve()]
        self.response.content_type = "application/json"
        self.response.out.write(json.dumps({"dyn":dyn_list,"pit":pit_list}))

class DownloadPage(webapp.RequestHandler):
    def post(self):
        editor = memcache.get("vsq_editor")
        file_name = memcache.get("vsq_name")
        if editor is None or file_name is None:
            print 'Content-Type: text/plain'
            print ''
            print '<p>セッション切れです。<a href="/">トップ</a>へ戻ってもう一度作業してください。</p>'
        else:
            self.response.headers['Content-Type'] = "application/x-vsq; charset=Shift_JIS"
            self.response.headers['Content-disposition'] = "filename=" + file_name.encode("utf-8")
            self.response.out.write(editor.unparse())

application = webapp.WSGIApplication(
                                        [('/', MainPage),
                                         ('/parse', ParserPage),
                                         ('/appliedvsq', AppliedVsqJSON),
                                         ('/appliedlyric', AppliedLyricJSON),
                                         ('/download', DownloadPage)],
                                        debug=True)

def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
