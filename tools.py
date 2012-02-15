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
    binary = pack(str(len(bins))+"B", *bins) if bins else "\x00"
    return binary

phonetic_table = {
        u"あ":u"a", u"い":u"i", u"う":u"M", u"え":u"e", u"お":u"o",
        u"か":u"k a", u"き":u"k i", u"く":u"k M", u"け":u"k e", u"こ": "k o",
        u"さ":u"s a", u"し":u"S i", u"す":u"s M", u"せ":u"s e", u"そ": "s o",
        u"た":u"t a", u"ち":u"tS i", u"つ":u"ts M", u"て":u"t e", u"と": "t o",
        u"な":u"n a", u"に":u"J i", u"ぬ":u"n M", u"ね":u"n e", u"の":u"n o",
        u"は":u"h a", u"ひ":u"C i", u"ふ":u"p\ M", u"へ":u"h e", u"ほ":u"h o",
        u"ま":u"m a", u"み":u"m' i", u"む":u"m M", u"め":u"m e", u"も":u"m o",
        u"や":u"j a", u"ゆ":u"j M", u"いぇ":u"j e", u"よ":u"j o",
        u"ら":u"4 a", u"り":u"4' i",u"る":u"4 M", u"れ":u"4 e", u"ろ":u"4 o",
        u"わ":u"w a", u"うぃ":u"w i",u"うぇ":u"w e", u"を":u"w o",
        u"ぁ":u"h\ a",u"ぃ":u"h\ i",u"ぅ":u"h\ M", u"ぇ":u"h\ e", u"ぉ":u"h\ o",
        u"きゃ":u"k' a", u"きゅ":u"k' M",u"きょ":u"k' o",
        u"しゃ":u"S a",u"すぃ":u"s i",u"しゅ":u"S M",u"しぇ":u"S e",u"しょ":u"S o",
        u"ちゃ":u"tS a",u"つぃ":u"ts i",u"ちゅ":u"tS M",u"ちぇ":u"tS e", u"ちょ":u"tS o",
        u"にゃ":u"J a", u"にゅ":u"J M",u"にぇ":u"J e",u"にょ":u"J o",
        u"ひゃ":u"C a",u"ひゅ":u"C M",u"ひぇ":u"C e",u"ひょ":u"C o",
        u"ふぁ":u"p\ a",u"ふぃ":u"p\' M",u"ふゅ":u"p\' M",u"ふぇ":u"p\ e",u"ふぉ":u"p\ o",
        u"みゃ":u"m' a",u"みゅ":u"m' M",u"みぇ":u"m' e",u"みょ":u"m' o",
        u"りゃ":u"4' a",u"りゅ":u"4' M",u"りょ":u"4' o",
        u"が":u"g a",u"ぎ":u"g' i",u"ぐ":u"g M",u"げ":u"g e",u"ご":u"g o",
        u"ざ":u"dZ a",u"じ":u"dZ i",u"ず":u"dz M",u"ぜ":u"dz e",u"ぞ":u"dz o",
        u"だ":u"d a", u"ぢ":u"d i",u"づ":u"d M",u"で":u"d e",u"ど":u"d o",
        u"ば":u"b a",u"び":u"b' i",u"ぶ":u"b M",u"べ":u"b e",u"ぼ":u"b o",
        u"ぱ":u"p a",u"ぴ":u"p' i",u"ぷ":u"p M",u"ぺ":u"p e",u"ぽ":u"p o",
        u"ん":u"n",
        u"ぎゃ":u"g' a",u"ぎゅ":u"g' M", u"ぎょ":u"g' o",
        u"じゃ":u"dZ a",u"ずぃ":u"dz i",u"じゅ":u"dZ M",u"じぇ":u"dZ e",u"じょ":"dZ o",
        u"でぃ":u"d' i",u"でゅ":u"d' M",
        u"びゃ":u"b' a",u"びゅ":u"b' M",u"びぇ":u"b' e", u"びょ":u"b' e",
        u"ぴゃ":u"p' a",u"ぴゅ":u"p' M",u"ぴぇ":u"p' e",u"ぴょ":u"p' o"
    }

lyric_table = dict(zip(phonetic_table.values(),phonetic_table.keys()))

#ローマ字の歌詞が入力されたとき用
phonetic_table.update({
    u"a":u"a",u"i":u"i",u"u":u"M",u"e":u"e",u"o":u"o",
    u"n":u"n"
    })

def lyric2phonetic(lyric):
    return phonetic_table[lyric]

def phonetic2lyric(phonetic):
    return lyric_table[phonetic]

class FakeFile(object):
    """文字列アクセスをファイルアクセスのように動作させるクラス"""
    def __init__(self, string=""):
        self._string = string
        self._index = 0

    def read(self, byte):
        string = self._string[self._index:self._index+byte]
        self._index += byte
        return string

    def tell(self):
        return self._index

