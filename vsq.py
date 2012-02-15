# -*- coding: utf-8 -*-
import re
from vsq_rules import *
from struct import *
import pprint

__author__ = "大野誠<makoto.pingpong1016@gmail.com>"
__status__ = "test"
__date__ = "2012/02/13"
__version__ = 0.02

def pp(obj):
    """オブジェクトを綺麗に表示する 
    """
    pp = pprint.PrettyPrinter(indent=4, width=180)
    str = pp.pformat(obj)
    print str

def pp_str(obj):
    """整形された obj のデータを返す
    """
    pp = pprint.PrettyPrinter(indent=4, width=180)
    return pp.pformat(obj)

def get_dtime(fp):
    """デルタタイムを取得する
    fp:vsqファイルポインタ or FakeFile インスタンス
    戻り値:デルタタイム
    ※fpはデルタタイムのところまでシークしておく必要がある
    """
    byte = ord(fp.read(1))
    dtime = byte & 0x7f
    while byte & 0x80:
        dtime <<= 7
        byte = ord(fp.read(1))
        dtime += byte & 0x7f
    return dtime


def dtime2binary(dtime):
    """デルタタイムをバイナリに変換する
    dtime:デルタタイム
    戻り値:デルタタイムのバイナリ
    """
    bins = []
    calc_1b = lambda b: (b & 0x7f) | 0x80 if bins else b & 0x7f 
    while dtime > 0x00:
        b = calc_1b(dtime)
        bins.insert(0,b)
        dtime >>= 7
    binary = pack(str(len(bins))+'B', *bins) if bins else '\x00'
    return binary


class FakeFile(object):
    """文字列アクセスをファイルアクセスのように動作させるクラス"""
    def __init__(self, string=''):
        self._string = string
        self._index = 0

    def read(self, byte):
        string = self._string[self._index:self._index+byte]
        self._index += byte
        return string

    def tell(self):
        return self._index


class Header(object):
    """MIDIヘッダを扱うクラス"""
    def __init__(self, fp):
        self.parse(fp)

    def parse(self, fp):
        """MIDIヘッダをパースする
        fp:vsqファイルポインタ or FakeFileインスタンス
        """
        data = {
            'MThd': unpack('>4s', fp.read(4))[0],
            'size': unpack('>i', fp.read(4))[0],
            'format': unpack('>h', fp.read(2))[0],
            'track_num': unpack('>h', fp.read(2))[0],
            'time_div': unpack('>h', fp.read(2))[0]}
        self.data = data

    def unparse(self):
        """MIDIヘッダをアンパースする
        戻り値:MIDIヘッダバイナリ
        """
        binary = pack(
            ">4si3h",
            self.data['MThd'],
            self.data['size'],
            self.data['format'],
            self.data['track_num'],
            self.data['time_div'])
        return binary


class MasterTrack(object):
    def __init__(self, fp):
        self.parse(fp)

    def parse(self, fp):
        """vsqファイルのマスタートラック部分をパースする
        fp:vsqファイルポインタ or FakeFile インスタンス
        ※fpはマスタートラック部分までシークしておく必要がある
        """
        #トラックチャンクヘッダの解析
        data = {
            "MTrk": unpack(">4s", fp.read(4))[0],
            "size": unpack('>i', fp.read(4))[0],
            "metaevents": []}
        
        #MIDIイベントの解析
        while True:
            dtime = get_dtime(fp)
            midi = unpack('3B', fp.read(3))
            mevent = {
                    'dtime': dtime,
                    'type': midi[1],
                    'len': midi[2],
                    'data': fp.read(midi[2])}
            data['metaevents'].append(mevent)
            t = mevent['type']
            if t == 0x2f:    #End of Trak
                break
            elif t == 0x51:  #Tempo
                self.tempo = unpack('>I', '\x00'+mevent['data'])[0]
            elif t == 0x03:  #Track Name
                self.name = mevent['data']
            elif t == 0x58:  #Beat
                self.beat = unpack('4b', mevent['data'])
        self.data = data

    def unparse(self):
        """マスタートラックをアンパースする
        戻り値:マスタートラックバイナリ
        """
        data = self.data
        binary = 'MTrk' + pack('>I', data['size'])
        for event in data['metaevents']:
            binary += dtime2binary(event['dtime'])
            binary += pack('cBB', '\xff', event['type'], event['len'])
            t =  event['type']
            if t == 0x2f:   #End of Track
                pass
            elif t == 0x51: #Tempo
                binary += pack('>I', self.tempo)[1:]
            elif t == 0x03: #Track Name
                binary += self.name
            elif t == 0x58: #Beat
                binary += pack('4b', *self.beat)
        return binary


class NormalTrack(object):
    """ノーマルトラック（マスタートラック以外）を扱うクラス"""
    def __init__(self, fp):
        # self.data
        # self.lyrics
        # self.anote_events の設定
        self.parse(fp)

    def __str__(self):
        return pp_str(self.data)

    def parse(self, fp):
        """vsqファイルのノーマルトラック部分をパースする
        fp:vsqファイルポインタ or FakeFileインスタンス
        ※fpはノーマルトラックのところまでシークしておく必要がある
        """
        #トラックチャンクヘッダの解析
        data = {
            "MTrk": unpack(">4s", fp.read(4))[0],
            "size": unpack('>i', fp.read(4))[0],
            "text": '',
            "cc_data": []
            }

        #MIDIイベントの解析
        while True:
            dtime = get_dtime(fp)
            mevent = unpack('3B', fp.read(3))
            if mevent[1] == 0x2f: 
                data['eot'] = dtime2binary(dtime) + '\xff\x2f\x00'
                break
            #Control Changeイベント
            if mevent[0] == 0xb0:
                data['cc_data'].append({'dtime':dtime, 'cc':mevent})
            else:
                #TrackNameイベント
                if mevent[1] == 0x03: 
                    data['name'] = fp.read(mevent[2])
                #Textイベント
                elif mevent[1] == 0x01:
                    fp.read(8) #skip "DM:xxxx:"
                    data['text'] += fp.read(mevent[2]-8)

        data.update(self.__parse_text(data['text']))
        anote_events = self.__create_anote_events(data)
        lyrics = [anote['lyrics'] for anote in anote_events]

        self.lyrics = unicode(''.join(lyrics), 'shift-jis')
        self.data = data
        self.anote_events = anote_events

    def unparse(self):
        """ノーマルトラックをアンパースする
        戻り値:ノーマルトラックバイナリ
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
        for i in range(0,len(text)-1,step):
            frame = min(step, len(text)-i)
            binary += pack("4B", 0x00, 0xff, 0x01, frame+8)
            binary += "DM:%04d:" % (i/step) + text[i:i+frame]
            
        #Control Change event
        for b in data['cc_data']:
            binary += dtime2binary(b['dtime'])
            binary += pack('3B', *b['cc'])

        #End of Track
        binary += data['eot']  
        return binary

    def __parse_text(self, text):
        data = {
            "Common": {},
            "Master": {},
            "Mixer": {},
            "EventList": [],    # [時間] = ID#xxxxのリスト
            "Events": {},       # ID#xxxxタグ
            "Details": {}}      # h#xxxxタグ

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
                    time, eventid  = line.split('=')
                    event = {'time': time, 'id': eventid}
                    data['EventList'].append(event)
                #各パラメータカーブタグ
                elif re.compile('.+BPList').match(current_tag):
                    if not data.get(current_tag):
                        data[current_tag] = []
                    key, value = line.split('=')
                    data[current_tag].append({'time': int(key),
                                               'value': int(value)})
                #ID#xxxxタグ
                elif re.compile('ID#[0-9]{4}').match(current_tag):
                    if not data['Events'].get(current_tag):
                        data['Events'][current_tag] = {}
                    key, value = line.split('=')
                    data['Events'][current_tag][key] = value
                #h#xxxxタグ
                elif re.compile('h#[0-9]{4}').match(current_tag):
                    if not data['Details'].get(current_tag):
                        data['Details'][current_tag] = {}
                    lines = len(line.split(','))
                    if lines == 1:
                        key, value = line.split('=')
                        data['Details'][current_tag][key] = value
                    #歌詞情報
                    else:
                        l0 = line.split('=')[1].split(',')
                        d = {}
                        #2パターンあった
                        if len(l0) == 5:
                            d = {
                                'lyrics': l0[0][1:-1],
                                'phonetic': l0[1][1:-1],
                                'unknown1': l0[2],
                                'unknown2': l0[3],
                                'protect': l0[4]}
                        else:
                            d = {
                                'lyrics': l0[0][1:-1],
                                'phonetic': l0[1][1:-1],
                                'unknown1': l0[2],
                                'unknown2': l0[3],
                                'unknown3': l0[4],
                                'protect': l0[5]}
                        data['Details'][current_tag] = d
        return data

    def __unparse_text(self):
        #テキスト情報
        data = self.data
        text = ''
        #Common,Master,Mixer
        for tag in ['Common','Master','Mixer']:
            text += '[%s]\n' % tag
            for item in data[tag].items():
                text += "%s=%s\n" % item
        #EventList        
        text += '[EventList]\n'
        for event in data['EventList']:
            text += "%(time)s=%(id)s\n" % event
        #Events
        for key, value in data['Events'].items():
            text += '[%s]\n' % key
            for item in value.items():
                text += "%s=%s\n" % item
        #Details
        for key, value in data['Details'].items():
            text += '[%s]\n' % key
            if value.keys().count('lyrics') == 0:
                for item in value.items():
                    text += "%s=%s\n" % item
            elif value.keys().count('unknown3') == 0:
                text += '''L0=\"%(lyrics)s\",\"%(phonetic)s\",%(unknown1)s,%(unknown2)s,%(protect)s\n''' % value
            else:
                text += '''L0=\"%(lyrics)s\",\"%(phonetic)s\",%(unknown1)s,%(unknown2)s,%(unknown3)s,%(protect)s\n''' % value
        #any BPList                         
        bprxp = re.compile('.+BPList')
        bptags = [tag for tag in data.keys() if bprxp.match(tag)]
        for tag in bptags:
            text += "[%s]\n" % tag 
            for item in data[tag]:
                text += "%(time)d=%(value)d\n" % item

        return text
    
    def __create_anote_events(self, data):
        """[ID,歌詞,発音,音高,開始時間,終了時間]
            でまとめられた音符イベントのリストが生成される
            ルール適用部分の参考素材になりそうな予定
        """
        anote_events = []
        for event in data['EventList'][:-1]:
            if data['Events'][event['id']]['Type'] == 'Anote': 
                e = data['Events'][event['id']] 
                d = data['Details'][e['LyricHandle']]
                es ={
                    'id': event['id'],
                    'start_time': int(event['time']),
                    'lyrics': d['lyrics'],
                    'phonetic': d['phonetic'],
                    'note': int(e['Note#']),
                    'end_time': int(event['time'])+int(e['Length'])}
                anote_events.append(es)
        return anote_events


class VSQEditor(object):

    def __init__(self, filename=None, binary=None):
        if filename: self.parse(filename=filename)
        elif binary: self.parse(binary=binary)
        

    def parse(self, filename=None, binary=None):
        """VSQファイルをパースする
        filename:VSQファイルのパス
        binary:VSQファイルのバイナリデータ
        引数はfilename,binaryのどちらかを指定
        """

        #各チャンクのパース
        self._fp = open(filename, 'r') if filename else FakeFile(binary)
        self.header = Header(self._fp)
        self.track_num = self.header.data['track_num']-1
        self.master_track = MasterTrack(self._fp)
        self.normal_tracks = [NormalTrack(self._fp) for i in range(self.track_num)]
            
        #トラックの先端時間（プリメジャータイムを除いた時間）を求める
        pre_measure = int(self.normal_tracks[0].data['Master']['PreMeasure'])
        nn, dd, _, _ = self.master_track.beat
        time_div = self.header.data['time_div']
        self.start_time = int(nn/float(2**dd)*4*pre_measure*time_div)

        #トラックの終端時間（最後のノートイベントの終端時間）を求める
        self.end_time = self.start_time
        for track in self.normal_tracks:
            et = track.anote_events[-1]['end_time']
            self.end_time = max(et, self.end_time)

        # self.current_track を 0 番目に設定
        self.select_track(0)
        
    def unparse(self, filename=None):
        """現在のオブジェクトのデータをアンパースして、
        VSQファイルとして書きこむ
        filename:書き込むVSQファイルのパス
        戻り値:filenameが指定されなかった場合にはバイナリを返す
        """
        #各チャンクのアンパース
        binary = self.header.unparse()
        binary += self.master_track.unparse()
        for track in self.normal_tracks:
            binary += track.unparse()
        
        #オプションに従って出力
        if filename:
            open(filename, 'w').write(binary)
        else:
            return binary
    
    def get_lyrics(self):
        """歌詞を取得する
        戻り値:歌詞(string)
        """
        return self.current_track.lyrics

    def get_anotes(self, s=None, e=None):
        """sからeまでの音符情報を取得する
        s:選択開始地点の時間
        e:選択終了地点の時間
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる
        戻り値:AnoteEventのリスト
        AnoteEvent:
            音符イベントの主な情報をまとめたディクショナリ
            構造は以下
            {
            "id":イベントID,
            "lyrics":歌詞,
            "phonetic":発音記号,
            "start_time":音符イベントの絶対開始時刻,
            "end_time":音符イベントの絶対終了時間,
            "note":音高（MIDIの規格に基づく）
            }
        """
        if s == None:
            s = self.start_time
        if e == None:
            e = self.end_time
        anotes = self.current_track.anote_events
        return [ev for ev in anotes
                if s <= ev['end_time'] and ev['start_time'] <= e]

    def get_anotes_f_lyric_i(self, s=None, e = None):
        lyrics = self.get_lyrics()
        if not s: s = 0
        if not e: e = len(lyrics)
        smallrxp = re.compile(u"[ぁぃぅぇぉゃゅょ]")

        s_index = s - len(smallrxp.findall(lyrics[:s]))
        e_index = e - len(smallrxp.findall(lyrics[:e]))
        return self.current_track.anote_events[s_index:e_index]
    
    def get_pitch_curve(self, s=None, e=None):
        """sからeまでのピッチ曲線を取得する
        s:選択開始地点の絶対時間
        e:選択終了地点の絶対時間
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる
        """
        return self.__get_param_curve('PitchBendBPList', s, e)

    def get_dynamics_curve(self, s=None, e=None):
        """sからeまでのダイナミクス曲線を取得する
        s:選択開始地点の絶対時間
        e:選択終了地点の絶対時間
        戻り値:曲線における
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる
        """
        return self.__get_param_curve('DynamicsBPList', s, e)

    def set_pitch_curve(self, curve, s=None, e=None, stretch=None):
        """sからeまでのピッチ曲線をcurveで置き換える
        curve:曲線を表すリスト
        s:選択開始地点の絶対時間
        e:選択終了地点の絶対時間
        stretch:曲線の伸縮オプション（未実装）
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる
        """
        return self.__set_param_curve('PitchBendBPList',
                                        curve,
                                        s,
                                        e,
                                        stretch)
        
    def set_dynamics_curve(self, curve, s=None, e=None, stretch=None):
        """sからeまでのダイナミクス曲線をcurveで置き換える
        curve:曲線を表すリスト
        s:選択開始地点の絶対時間
        e:選択終了地点の絶対時間
        stretch:曲線の伸縮オプション（未実装）
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる
        """
        return self.__set_param_curve('DynamicsBPList',
                                        curve,
                                        s,
                                        e,
                                        stretch)

    def set_anote_length(self, anotes, length):
        """音符の長さを変更する
        anotes:変更対象となる音符イベント（リスト）
        length:変更後の音符の長さ
        """
        events = self.current_track['Events']
        for anote in anotes:
            events[anote['id']]['length'] = length
            anote['end_time'] = anote['start_time'] + length
    
    def insert_note(self, note, index):
        """指定したインデックスの箇所に音符を挿入する
        === Args
        note: 挿入する音符イベント
        index: EventListのインデックス、おそらく歌詞の挿入としてはこっちのほうが自然
        === Returns
        0: 成功
        1: 失敗
        """
        
        def invalid_arguments(note, index):
            """引数のチェック"""
            i = False if 0 <= index <= len(self.current_track.data["EventList"]) else True
            j = False if note['lyric'] and note['event'] else True
            k = False if note else True
            return i and j and k

        def inc(handle_number_string):
            return "h#%04d" % (int(handle_number_string[2:]) + 1)

        if invalid_arguments(note, index):
            return 1
        
        # あとでIDとかhを振り直す
        event_list = [e['time'] for e in self.current_track.data['EventList']]
        handle_detail = [e[1] for e in sorted(self.current_track.data['Details'].items())]
        events_detail = [e[1] for e in sorted(self.current_track.data['Events'].items())]

        note['event']['LyricHandle'] = events_detail[index]['LyricHandle']
        handle_index = int(events_detail[index]['LyricHandle'][2:])
        for i in range(index, len(events_detail), 1):
            if 'LyricHandle' in events_detail[i]:
                events_detail[i]['LyricHandle'] = inc(events_detail[i]['LyricHandle'])
            if 'VibratoHandle' in events_detail[i]:
                events_detail[i]['VibratoHandle'] = inc(events_detail[i]['VibratoHandle'])
        # ♂
        events_detail.insert(index, note['event'])
        handle_detail.insert(handle_index, note['lyric'])
        event_list.insert(index, event_list[index])
        self.current_track.anote_events.insert(index - 2, {
                'id': 'ID#%04d' % (index - 1),
                'lyrics': note['lyric']['lyrics'],
                'note': int(note['event']['Note#']),
                'phonetic': note['lyric']['phonetic'],
                'start_time': self.current_track.anote_events[index-2]['start_time'],
                'end_time': self.current_track.anote_events[index-2]['start_time'] + int(note['event']['Length']),
                })

        # 追加するノートの長さ分、EventListの時間をずらす
        l = int(note['event']['Length'])
        for i in range(index-1, len(self.current_track.anote_events), 1):
            self.current_track.anote_events[i]['start_time'] += l
            self.current_track.anote_events[i]['end_time'] += l
            
        for i in range(index+1, len(event_list), 1):
            event_list[i] = int(event_list[i]) + int(note['event']['Length'])

        # 値の更新
        self.end_time += int(note['event']['Length'])
        self.current_track.data['EventList'] = (
            [{'id': 'ID#%04d' % (i), 'time': e} for i, e in enumerate(event_list)]
            )
        for i, h in enumerate(handle_detail):
            self.current_track.data['Details'].update({'h#%04d' % (i): h})
        for i, e in enumerate(events_detail):
            self.current_track.data['Events'].update({'ID#%04d' % (i): e})
        return 0
    
    def select_track(self, n):
        """操作対象トラックを変更する
        n: トラック番号
        """
        if n < self.track_num:
            self.current_track = self.normal_tracks[n]

    def apply_rule(self, rule_i):
        """ルールを適用する
        rule_i: get_rule_candsメソッドによって得られたルール適用候補
        """
        anotes = self.get_anotes_f_lyric_i(rule_i['s_index'],
                                      rule_i['e_index'])
        for i, curve in enumerate(rule_i['rule']['dyn_curves']):
            self.set_dynamics_curve(curve['curve'],
                                anotes[i]['start_time'],
                                anotes[i]['end_time'],
                                curve['stretch'])
        for i, curve in enumerate(rule_i['rule']['pit_curves']):
            self.set_pitch_curve(curve['curve'],
                                anotes[i]['start_time'],
                                anotes[i]['end_time'],
                                curve['stretch'])

    def unapply_rule(self, rule_i):
        """ルールの適用をもとに戻す
        rule_i: get_rule_candsメソッドによって得られたルール適用候補
        """
        anotes = self.get_anotes_f_lyric_i(rule_i['s_index'],rule_i['e_index'])
        start_time = anotes[0]['start_time']
        end_time = anotes[-1]['end_time']
        self.set_dynamics_curve(rule_i['undyn'], 
                                start_time,
                                end_time)

        self.set_pitch_curve(rule_i['unpit'], 
                                start_time,
                                end_time)

    def get_rule_cands(self, rule):
        """ルール適用候補を取得する
        rule:ディクショナリとして格納されたルール定義（vsq_rules.pyを参照）
        戻り値:ルール適用候補（ディクショナリ）
        ルール適用候補のキーには重複しないIDが振られている
        """
        rulerxp = re.compile(rule['regexp'])
        rule_dic = {}

        def is_connected(anotes):
            if len(anotes) <= 1: return True 
            for i, anote in enumerate(anotes[1:]):
                if anote['start_time'] - anotes[i]['end_time'] > 50:
                    return False
            return True

        def check_notes(notes, anotes):
            if notes is None:
                return True
            relative_notes = [0] + [anote['note'] - anotes[i]['note'] 
                                    for i, anote in enumerate(anotes[1:])]
            return relative_notes == notes

        match_len = lambda x, y: (not x or not y) or len(x)==len(y)
        lyrics = self.get_lyrics()
        for i, match in enumerate(rulerxp.finditer(lyrics)):
            s = match.start()
            e = match.end()
            match_anotes = self.get_anotes_f_lyric_i(s,e)
            #各ノートが接続されているか
            if rule['connect'] and not is_connected(match_anotes):
                continue
            #ノートの数と各ノートに割り当てられるカーブの数が一致するか
            if (not match_len(rule['dyn_curves'], match_anotes) or
                not match_len(rule['pit_curves'], match_anotes)):
                continue
            #音階の変化が一致するか
            if (rule['relative_notes'] and 
                not check_notes(rule['relative_notes'],match_anotes)):
                continue
            else:
                u_dyn_curve = self.get_dynamics_curve(
                        match_anotes[0]['start_time'],
                        match_anotes[-1]['end_time'])
                u_pit_curve = self.get_pitch_curve(
                        match_anotes[0]['start_time'],
                        match_anotes[-1]['end_time'])
                rule_i = {"instance_id":"I"+str(i),
                        "rule":rule,
                        "s_index":s,
                        "e_index":e,
                        "undyn":u_dyn_curve,
                        "unpit":u_pit_curve}
                rule_dic[rule['rule_id']+rule_i['instance_id']] = rule_i

        return rule_dic

    def __set_param_curve(self, ptype, curve, s, e, stretch):
        if s == None or s <= self.start_time:
            s = self.start_time + 1     
        if e == None or self.end_time <= e:
            e = self.end_time + 1     
        length = e - s
        if length < 0 or curve == None:
            return False
        len_ratio = float(length)/len(curve)

        #curveをスケールしながらパラメータを生成
        new_bp = []
        for i, v in enumerate(curve):
            if int(len_ratio*i) != int(len_ratio*(i-1)) or i == 0:
                new_bp.append({'time': s+int(len_ratio*i), 'value':v})
        select = self.__get_param_curve

        #元の波形の終端の値を新しい波形の終端に追加
        #選択範囲以外への影響を抑制する
        end_value = select(ptype, self.start_time, e)[-1]['value']
        new_bp.append({'time':e+1, 'value':end_value})

        param = self.current_track.data[ptype]
        for p in select(ptype, s, e):
            param.remove(p)  #選択範囲の元の波形の除去
        param.extend(new_bp)  #新しい波形の追加
        param.sort()
        return True

    def __get_param_curve(self, ptype, s, e):
        if s == None:
            s = self.start_time
        if e == None:
            e = self.end_time
        return [ev for ev in self.current_track.data[ptype] if s <= ev['time'] <= e]
    

'''
テストコード:
1.test.vsqを読み込んで、時間6800~7100に存在する音符イベント、
ダイナミクス、ピッチベンドのカーブを表示する
2.指定した時間の時間のダイナミクス、ピッチベンドのカーブを
任意のものに変更する
3.パース結果をアンパースし、outtest.vsqとして出力する
4.歌詞を表示する
5.音程の相対値を表示する
'''
if __name__ == '__main__':
    editor = VSQEditor(binary=open('out.vsq', 'r').read())
    enable = [7]

    #1.音符情報、dynamics,pitchbendカーブを表示
    if 1 in enable: 
        print "anotes:"
        anotes = editor.get_anotes(6800,7100)
        pp(anotes)
        
        print "\ndynamics:"
        pp(editor.get_dynamics_curve(6800,7100))
        print "\npitchbend:"
        pp(editor.get_pitch_curve(6800,7100))
    
    #2.範囲を選択してカーブを編集
    if 2 in enable:
        editor.set_pitch_curve(range(-5000,5000,1),850,6200)
        editor.set_dynamics_curve(range(1,100)+range(100,1,-1),20800,35200)
        editor.set_dynamics_curve([0],30800,35200)
        editor.set_dynamics_curve([128],32000,32000)
        
    #4.歌詞を表示
    if 4 in enable:
        print "\nlyrics:"
        print editor.get_lyrics()
    
    #5.相対音階を表示（前のノートとの差をとる）
    if 5 in enable:
        print "\nrelative_notes:"
        anotes = editor.get_anotes()
        relative_notes = [0] + [anote['note'] - anotes[i]['note'] 
                                    for i, anote in enumerate(anotes[1:])]
        print relative_notes
    
    #6.ルール適用テスト
    if 6 in enable:
        rule_cands = editor.get_rule_cands(zuii_rule)
        for rule_i in rule_cands.values():
            editor.apply_rule(rule_i)

    #3.編集結果をunparseして書きこむ
    if 3 in enable:
        editor.unparse('out.vsq')   

    # ノート挿入テスト
    if 7 in enable:
        i = 10
        note = {
            'lyric': {
                'lyrics': 'a',
                'phonetic': 'a',
                'protect': '0',
                'unknown1': '0.000000',
                'unknown2': '0'
                },
            'event': {
                "PMBendDepth": "8",
                "PMBendLength": "14",
                "PMbPortamentoUse": "0",
                "DEMdecGainRate": "50",
                "Type": "Anote",
                "Length": "120",
                "DEMaccent": "50",
                "Dynamics": "64"
                }
            }

        print "----before insert----"
        pp(editor.current_track.data['EventList'][i-3:i+3])
        for i in range(i-3, i+3, 1):
            s = "h#%04d" % i
            pp(editor.current_track.data['Details'][s])

        print "----after insert----"
        editor.insert_note(note, i)
        pp(editor.current_track.data['EventList'][i-3:i+3])
        for i in range(i-3, i+3, 1):
            s = "h#%04d" % i
            pp(editor.current_track.data['Details'][s])

