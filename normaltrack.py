# -*- coding: utf-8 -*-
import tools
import re
from struct import *


class NormalTrack(object):
    """ノーマルトラック（マスタートラック以外）を扱うクラス"""
    def __init__(self, fp):
        self.parse(fp)

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
            "EventList": [],
            "Events": {}, #ID#xxxxタグ
            "Details": {}} #h#xxxxタグ

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


