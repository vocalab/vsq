#-*- coding: utf-8 -*-
import pprint
from struct import *

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


