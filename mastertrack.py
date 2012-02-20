#-*- coding: utf-8 -*-
import tools
from struct import *


class MasterTrack(object):
    """vsqファイル中のマスタートラック部分を扱うクラス
    Attributes:
        data: トラック情報を表すディクショナリ
            {"MTrk": トラックチャンクを表す文字列"MTrk",
             "size": トラックチャンクのサイズ（byte）,
             "metaevents": SMFメタイベントのリスト,
                [{"dtime": デルタタイム（前のイベントとの相対時間）
                  "size": コンテンツのサイズ（byte）,
                  "type": 種類（SMFの企画に基づく）,
                  "data": メタイベントのコンテンツ部分]}
        name: トラックネーム（Master Trackで固定？）
        tempo: トラックの始端時におけるBPM
        beat: トラックの始端時における拍・拍子を表すリスト
            [nn,dd,cc,bb]
            nn: 拍子記号の分子
            dd: 2のdd乗で表される分母
            cc: メトロノーム1カウントあたりのMIDIクロック数
            bb: 4分音符中の32分音符数
    """
    def __init__(self, fp):
        self.parse(fp)

    def parse(self, fp):
        """vsqファイルのマスタートラック部分をパースする
        Args:
            fp: vsqファイルポインタ or FakeFile インスタンス
        fpはマスタートラック部分までシークしておく必要がある
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
            if t == 0x2f:    # End of Trak
                break
            elif t == 0x51:  # Tempo
                self.tempo = unpack('>I', '\x00' + mevent['data'])[0]
            elif t == 0x03:  # Track Name
                self.name = mevent['data']
            elif t == 0x58:  # Beat
                self.beat = unpack('4b', mevent['data'])
        self.data = data

    def unparse(self):
        """マスタートラックをアンパースする
        Returns:
            マスタートラックバイナリ
        """
        data = self.data
        binary = 'MTrk' + pack('>I', data['size'])
        for event in data['metaevents']:
            binary += tools.dtime2binary(event['dtime'])
            binary += pack('cBB', '\xff', event['type'], event['len'])
            t = event['type']
            if t == 0x2f:    # End of Track
                pass
            elif t == 0x51:  # Tempo
                binary += pack('>I', self.tempo)[1:]
            elif t == 0x03:  # Track Name
                binary += self.name
            elif t == 0x58:  # Beat
                binary += pack('4b', *self.beat)
        return binary
