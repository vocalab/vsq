import os
import cgi
from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from vsq import VSQEditor

class MainPage(webapp.RequestHandler):
    def get(self):
        template_values = {
                'greeting': 'Hello World'
                }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class ParserPage(webapp.RequestHandler):
    def post(self):
        data = self.request.get('file')
        file_name = self.request.body_file.vars['file'].filename
        editor = VSQEditor(string = data)
        anotes = editor.get_anotes()
        lyrics = [anote['lyrics'] for anote in anotes]
        memcache.set_multi({ "data": data,
            "name": file_name },
            key_prefix="vsq_", time=3600)
        template_values = {
                'lyrics': ''.join(lyrics).decode('shift_jis').encode('utf-8')
                }
        path = os.path.join(os.path.dirname(__file__), 'parse.html')
        self.response.out.write(template.render(path, template_values))
        #lyric = editor.get_anotes(s=6800)[0]['lyrics']
        #self.response.out.write('<pre>' + lyric + '</pre>')

class DownloadPage(webapp.RequestHandler):
    def post(self):
        data = memcache.get("vsq_data")
        file_name = memcache.get("vsq_name")
        self.response.headers['Content-Type'] = "application/x-vsq; charset=Shift_JIS"
        self.response.headers['Content-disposition'] = "filename=" + file_name.encode("utf-8")
        editor = VSQEditor(string = data)
        self.response.out.write(editor.unparse())

application = webapp.WSGIApplication(
                                        [('/', MainPage),
                                         ('/parse', ParserPage),
                                         ('/download', DownloadPage)],
                                        debug=True)

def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
