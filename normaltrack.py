# -*- coding: utf-8 -*-
import tools
import re
from anote import *
from singer import *
from struct import *



class NormalTrack(object):
    """ノーマルトラック（マスタートラック以外）を扱うクラス
    Attributes:
        data: データ
        anotes: 音符イベントのリスト
        singers: 歌手変更イベントのリスト
        phonetics: 各音符イベントの発音記号を連結したもの
        lyrics: 各音符イベントの歌詞を連結したもの
    """
    def __init__(self, fp):
        self.parse(fp)

    def parse(self, fp):
        """vsqファイルのノーマルトラック部分をパースする
        Args:
            fp: vsqファイルポインタ or FakeFileインスタンス
        fpはノーマルトラックのところまでシークしておく必要がある
        """
        #トラックチャンクヘッダの解析
        data = {
            "MTrk": unpack(">4s", fp.read(4))[0],
            "size": unpack('>i', fp.read(4))[0],
            "text": '',
            "cc_data": []}

        #MIDIイベントの解析
        while True:
            dtime = tools.get_dtime(fp)
            mevent = unpack('3B', fp.read(3))
            if mevent[1] == 0x2f:
                data['eot'] = tools.dtime2binary(dtime) + '\xff\x2f\x00'
                break
            #Control Changeイベント
            if mevent[0] == 0xb0:
                data['cc_data'].append({'dtime': dtime, 'cc': mevent})
            else:
                #TrackNameイベント
                if mevent[1] == 0x03:
                    data['name'] = fp.read(mevent[2])
                #Textイベント
                elif mevent[1] == 0x01:
                    fp.read(8)  # skip "DM:xxxx:"
                    data['text'] += fp.read(mevent[2] - 8)

        data.update(self.__parse_text(data['text']))
        anotes, singers = self.__pack_events(data['Events'], data['Details'])

        self.data = data
        self.anotes = anotes
        self.singers = singers

    def unparse(self):
        """ノーマルトラックをアンパースする
        Returns:
            ノーマルトラックバイナリ
        """
        # 変数宣言
        data = self.data
        track_header = ''
        binary = ''

        # トラック名の変換
        binary += pack('4B', 0x00, 0xff, 0x03, len(data['name'])) + data['name']

        # テキストデータの変換
        text = self.__unparse_text()
        #step = 119
        step = 127 - len("DM:....:")
        for i in range(0, len(text) - 1, step):
            frame = min(step, len(text) - i)
            binary += pack("4B", 0x00, 0xff, 0x01, frame + 8)
            binary += "DM:%04d:" % (i / step) + text[i:i + frame]

        # コントロールチェンジイベントの変換
        for b in data['cc_data']:
            binary += tools.dtime2binary(b['dtime'])
            binary += pack('3B', *b['cc'])

        # End of Track
        binary += data['eot']

        # MTrk と トラックサイズの再計算
        track_header = pack(
            '>4sI',
            data['MTrk'],
            len(binary)
            )
        return track_header + binary

    def __parse_text(self, text):
        data = {
            "Common": {},
            "Master": {},
            "Mixer": {},
            "Events": {},
            "Details": {}
            }

        #テキスト情報の解析
        current_tag = ''
        for line in text.split('\n')[:-1]:
            #操作タグの変更時
            if re.compile('\[.+\]').match(line):
                current_tag = line[1:-1]
            else:
                #Common,Master,Mixerタグ
                if re.compile('Common|Master|Mixer').match(current_tag):
                    key, value = line.split('=')
                    data[current_tag][key] = value
                #EventListタグ
                elif current_tag == "EventList":
                    time, eventid = line.split('=')
                    data['Events'][eventid] = {'time': time}
                #各パラメータカーブタグ
                elif re.compile('.+BPList').match(current_tag):
                    if not current_tag in data:
                        data[current_tag] = []
                    key, value = line.split('=')
                    data[current_tag].append({'time': int(key),
                                               'value': int(value)})
                #ID#xxxxタグ
                elif re.compile('ID#[0-9]{4}').match(current_tag):
                    key, value = line.split('=')
                    data['Events'][current_tag][key] = value
                #h#xxxxタグ
                elif re.compile('h#[0-9]{4}').match(current_tag):
                    if not current_tag in data['Details']:
                        data['Details'][current_tag] = {}
                    lines = len(line.split(','))
                    #ビブラート情報、歌手情報
                    if lines == 1:
                        key, value = line.split('=')
                        data['Details'][current_tag][key] = value
                    #歌詞情報
                    else:
                        l0 = line.split('=')[1].split(',')
                        #lyricとprotectがあれば他は自動的に決まる？
                        data['Details'][current_tag] = {
                                'lyric': unicode(l0[0][1:-1], "shift-jis"),
                                'protect': unicode(l0[-1], "shift-jis")}
        if not 'PitchBendBPList' in data:
            data['PitchBendBPlist'] = {'time': 0, 'value': 0}
        if not 'DynamicsBPList' in data:
            data['DynamicsBPList'] = {'time': 0, 'value': 0}

        data['EOS'] = data['Events'].pop('EOS')['time']
        return data

    def __unparse_text(self):
        #テキスト情報
        data = self.data
        text = ''
        #Common,Master,Mixer
        for tag in ['Common', 'Master', 'Mixer']:
            text += '[%s]\n' % tag
            for item in data[tag].items():
                text += "%s=%s\n" % item

        #Event関連
        events, details = self.__unpack_events(self.anotes, self.singers)
        event_text = ''
        detail_text = ''
        eventlist_text = '[EventList]\n'
        for i, e in enumerate(events):
            event_id = "ID#%04d" % i
            eventlist_text += "%s=%s\n" % (e.pop('time'), event_id)
            event_text += "[%s]\n" % event_id
            for item in e.items():
                event_text += "%s=%s\n" % item
        eventlist_text += "%s=%s\n" % (self.data['EOS'], 'EOS')

        for i, d in enumerate(details):
            detail_id = "h#%04d" % i
            detail_text += "[%s]\n" % detail_id
            if d.keys().count('lyric') == 0:
                for item in d.items():
                    detail_text += "%s=%s\n" % item
            elif d.keys().count('ca1') == 0:
                detail_text += '''L0=\"%(lyric)s\",\"%(phonetic)s\",%(lyric_delta)s,%(ca0)s,%(protect)s\n''' % d
            else:
                detail_text += '''L0=\"%(lyric)s\",\"%(phonetic)s\",%(lyric_delta)s,%(ca0)s,%(ca1)s,%(protect)s\n''' % d

        text += eventlist_text + event_text + detail_text

        #any BPList
        bprxp = re.compile('.+BPList')
        bptags = [tag for tag in data.keys() if bprxp.match(tag)]
        for tag in bptags:
            text += "[%s]\n" % tag
            for item in data[tag]:
                text += "%(time)d=%(value)d\n" % item

        return text

    def __pack_events(self, events, details):
        """イベントを扱いやすいようにpackする
        Args:
            events: イベント情報（ID#xxxxタグ以下の情報）のリスト
            details: 詳細イベント情報（h#xxxxタグ以下の徐放）のリスト
        Returns:
            anotes: events、detailsから生成されたAnoteインスタンスのリスト
            singers: events, detailsから生成されたSingerインスタンスのリスト
        """
        anotes = AnoteList()
        singers = []
        for e in events.values():
            time = e.pop('time')
            t = e.pop('Type')
            if t == 'Anote':
                lyric = details[e.pop('LyricHandle')]
                vibrato = details.pop(e.pop('VibratoHandle', None), None)
                for key, value in e.items():
                    e[key] = int(value)
                params = {
                    'time': int(time),
                    'note': e.pop('Note#'),
                    'lyric': lyric['lyric'],
                    'length': e.pop('Length'),
                    'vibrato': vibrato,
                    'prop': e}
                anotes.append(Anote(**params))
            elif t == 'Singer':
                icon = details[e.pop('IconHandle')]
                singers.append(Singer(time, icon))
        anotes.sort(key=lambda x: x.start)
        singers.sort(key=lambda x: x.start)
        return anotes, singers

    def __unpack_events(self, anotes, singers):
        """unpackする
        Args:
            anotes: 音符イベントのリスト
            singers: 歌手変更イベントのリスト
        Returns:
            events: イベント情報（ID#xxxxタグ以下の情報）のリスト
            details: イベント詳細情報（h#xxxxタグ以下の情報）のリスト
        """
        packed = anotes + singers
        packed.sort(key=lambda x: int(x.start))

        details = []
        events = []
        for p in packed:
            e = p.event
            if e['Type'] == 'Anote':
                e.update({'LyricHandle': 'h#%04d' % len(details)})
                details.append(p.lyric_event)
                vibrato = p.vibrato_event
                if vibrato:
                    e.update({'VibratoHandle': 'h#%04d' % len(details)})
                    details.append(vibrato)
            elif e['Type'] == 'Singer':
                e.update({'IconHandle': 'h#%04d' % len(details)})
                details.append(p.singer_event)
            events.append(e)
        return events, details
