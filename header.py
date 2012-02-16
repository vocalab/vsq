#-*- coding: utf-8 -*-
from struct import *


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


