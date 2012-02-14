#-*- coding: utf-8 -*-
import tools
from struct import *

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
            dtime = tools.get_dtime(fp)
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
            binary += tools.dtime2binary(event['dtime'])
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


