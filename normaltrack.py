# -*- coding: utf-8 -*-
import tools
import re
from struct import *


class Singer(object):
    """歌手変更イベントを扱うクラス
    Attributes:
        start: イベント発生時間
        params: 各パラメータ
        歌手変更イベントは詳しく扱う必要がない気がするのでスルー
    """
    def __init__(self, time, params):
        self.start = time
        self.params = params

    def get_event(self):
        return {'Type': 'Singer', 'time': str(self.start)}

    def get_singer_event(self):
        return self.params


class Anote(object):
    """音符イベントを扱うクラス
    Attributes:
        start: イベント始端時間
        end: イベント終端時間
        length: イベントの長さ
        lyric: 歌詞
        phonetic: 発音記号
        dynamics: ベロシティ（VEL）
        vibrato: ビブラート情報（ディクショナリ）
            {"IconID": ビブラートの形式を識別するID,
             "IDS": ビブラートの形式名,
             "Caption": 不明,
             "Original": 不明,
             "Length": ビブラートの長さ,
             "StartDepth": 振幅の開始位置,
             "DepthBPNum": 振幅カーブのデータ点数,
             "DepthBPX": 振幅カーブのデータ点（時間軸）(csv),
             "DepthBPY": 振幅カーブのデータ点(csv),
             "StartRate": 周期の開始位置,
             "RateBPNum": 周期カーブのデータ点数,
             "RateBPX": 周期カーブのデータ点（時間軸）（csv),
             "RateBPY": 周期カーブのデータ点（csv)}
        prop: 音符のプロパティ（ディクショナリ）
            {"PMBendDepth": ベンドの深さ,
             "PMBendLength": ベンドの長さ,
             "PMbPortamentoUse":
                「〜形でポルタメントを付加」の指定内容。
                「上行形で〜」が指定されていれば+1
                「下行形で〜」が指定されていれば+2,
             "DEMdecGainRate" ディケイ,
             "DEMaccend": アクセント}
    ビブラート周りを除いて数値になるべきところは数値として扱う
    """
    #デフォルトプロパティ
    d_prop = {
            'PMBendDepth': 8,
            'PMBendLength': 0,
            'PMbPortamentoUse': 0,
            'DEMdecGainRate': 50,
            'DEMaccent': 50}
    _lyric = ''
    _phonetic = ''
    _length = 0
    _end = 0

    def __init__(self, time, note, lyric=u"a", length=120,
            dynamics=64, vibrato=None, prop=d_prop):
        self.start = time
        self.note = note
        self.length = length
        self.lyric = lyric
        self.dynamics = dynamics
        self.vibrato = vibrato
        self.prop = prop

    def set_lyric(self, lyric):
        self._lyric = lyric
        self._phonetic = tools.lyric2phonetic(lyric)

    def get_lyric(self):
        return self._lyric

    def set_phonetic(self, phonetic):
        self._phonetic = phonetic
        self._lyric = tools.phonetic2lyric(phonetic)

    def get_phonetic(self):
        return self._phonetic

    def set_length(self, length):
        self._length = length
        self._end = self.start + length

    def get_length(self):
        return self._length

    def set_end(self, end):
        self._end = end
        self._length = end - self._start

    def get_end(self):
        return self._end

    lyric = property(get_lyric, set_lyric)
    phonetic = property(get_phonetic, set_phonetic)
    length = property(get_length, set_length)
    end = property(get_end, set_end)

    def get_event(self):
        """音符イベント形式の音符データを取得する
        Returns:
            音符イベント形式の音符データ
            数値も文字列として格納される
        """
        event = {
            'Type': 'Anote',
            'time': str(self.start),
            'Length': str(self.length),
            'Note#': str(self.note)
            }
        for key, value in self.options.items():
            self.options[key] = str(value)
        event.update(self.options)
        if self.vibrato:
            vd = int((1 - int(self.vibrato['Length']) / 100.0) *
                    self.length / 5) * 5
            event['VibratoDelay'] = str(vd)
        return event

    def get_lyric_event(self):
        """詳細イベント形式の歌詞データを取得する
        Returns:
            詳細イベント形式の歌詞データ
            数値も文字列として格納される
        """
        lyric_event = {
            'lyric': self._lyric.encode('shift-jis'),
            'phonetic': self._phonetic.encode('shift-jis'),
            'lyric_delta': "%8.6f" % 0.000000,
            'protect': "0"
            }
        #ConsonantAdjustmentを追加
        phonetics = self._phonetic.split(' ')
        boinrxp = re.compile('aiMeo')
        for i, p in enumerate(phonetics):
            lyric_event['ca' + str(i)] = 0 if boinrxp.match(p) else 64
        return lyric_event

    def get_vibrato_event(self):
        """詳細イベント形式のビブラートデータを取得する
        Returns:
            詳細イベント形式の歌詞データ
        """
        return self.vibrato


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
        self.phonetics = ''.join([a.phonetic for a in self.anotes])
        self.lyrics = ''.join([a.lyric for a in self.anotes])

    def unparse(self):
        """ノーマルトラックをアンパースする
        Returns:
            ノーマルトラックバイナリ
        """
        #トラックチャンクヘッダ
        data = self.data
        binary = pack(
            '>4sI4B',
            data['MTrk'],
            data['size'],
            0x00, 0xff, 0x03, len(data['name']))
        binary += data['name']

        #convert text to textevents
        text = self.__unparse_text()
        step = 119
        for i in range(0, len(text) - 1, step):
            frame = min(step, len(text) - i)
            binary += pack("4B", 0x00, 0xff, 0x01, frame + 8)
            binary += "DM:%04d:" % (i / step) + text[i:i + frame]

        #Control Change event
        for b in data['cc_data']:
            binary += tools.dtime2binary(b['dtime'])
            binary += pack('3B', *b['cc'])

        #End of Track
        binary += data['eot']
        return binary

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
        anotes = []
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
            e = p.get_event()
            if e['Type'] == 'Anote':
                e.update({'LyricHandle': 'h#%04d' % len(details)})
                details.append(p.get_lyric_event())
                vibrato = p.get_vibrato_event()
                if vibrato:
                    e.update({'VibratoHandle': 'h#%04d' % len(details)})
                    details.append(vibrato)
            elif e['Type'] == 'Singer':
                e.update({'IconHandle': 'h#%04d' % len(details)})
                details.append(p.get_singer_event())
            events.append(e)
        return events, details
