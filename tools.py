#-*- coding: utf-8 -*-
import pprint
from struct import *

__author__ = "大野誠<makoto.pingpong1016@gmail.com>"
__status__ = "test"
__date__ = "2012/02/13"
__version__ = 0.02


def pp(obj):
    """オブジェクトを綺麗に表示する
    Args:
        obj: 任意のオブジェクト
    """
    pp = pprint.PrettyPrinter(indent=4, width=180)
    str = pp.pformat(obj)
    print str


def pp_str(obj):
    """整形したオブジェクトの文字列を返す
    Args:
        obj: 任意のオブジェクト

    Returns:
        整形された文字列
    """
    pp = pprint.PrettyPrinter(indent=4, width=180)
    return pp.pformat(obj)


def get_dtime(fp):
    """デルタタイムを取得する
    Args:
        fp: vsqファイルポインタ or FakeFile インスタンス
    fpはデルタタイムのところまでシークしておく必要がある

    Returns:
        デルタタイム
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
    Args:
        dtime:デルタタイム

    Returns:
        デルタタイムのバイナリ
    """
    bins = []
    calc_1b = lambda b: (b & 0x7f) | 0x80 if bins else b & 0x7f
    while dtime > 0x00:
        b = calc_1b(dtime)
        bins.insert(0, b)
        dtime >>= 7
    binary = pack(str(len(bins)) + "B", *bins) if bins else "\x00"
    return binary


#歌詞=>発音記号の変換テーブル
phonetic_table = {
        u"あ": u"a", u"い": u"i", u"う": u"M", u"え": u"e", u"お": u"o",
        u"か": u"k a", u"き": u"k i", u"く": u"k M", u"け": u"k e", u"こ": "k o",
        u"さ": u"s a", u"し": u"S i", u"す": u"s M", u"せ": u"s e", u"そ": "s o",
        u"た": u"t a", u"ち": u"tS i", u"つ": u"ts M", u"て": u"t e", u"と": "t o",
        u"な": u"n a", u"に": u"J i", u"ぬ": u"n M", u"ね": u"n e", u"の": u"n o",
        u"は": u"h a", u"ひ": u"C i", u"ふ": u"p\ M", u"へ": u"h e", u"ほ": u"h o",
        u"ま": u"m a", u"み": u"m' i", u"む": u"m M", u"め": u"m e", u"も": u"m o",
        u"や": u"j a", u"ゆ": u"j M", u"いぇ": u"j e", u"よ": u"j o",
        u"ら": u"4 a", u"り": u"4' i", u"る": u"4 M", u"れ": u"4 e", u"ろ": u"4 o",
        u"わ": u"w a", u"うぃ": u"w i", u"うぇ": u"w e", u"を": u"w o",
        u"ぁ": u"h\ a", u"ぃ": u"h\ i", u"ぅ": u"h\ M", u"ぇ": u"h\ e", u"ぉ": u"h\ o",
        u"きゃ": u"k' a", u"きゅ": u"k' M", u"きょ": u"k' o",
        u"しゃ": u"S a", u"すぃ": u"s i", u"しゅ": u"S M", u"しぇ": u"S e", u"しょ": u"S o",
        u"ちゃ": u"tS a", u"つぃ": u"ts i", u"ちゅ": u"tS M", u"ちぇ": u"tS e", u"ちょ": u"tS o",
        u"にゃ": u"J a", u"にゅ": u"J M", u"にぇ": u"J e", u"にょ": u"J o",
        u"ひゃ": u"C a", u"ひゅ": u"C M", u"ひぇ": u"C e", u"ひょ": u"C o",
        u"ふぁ": u"p\ a", u"ふぃ": u"p\' M", u"ふゅ": u"p\' M", u"ふぇ": u"p\ e", u"ふぉ": u"p\ o",
        u"みゃ": u"m' a", u"みゅ": u"m' M", u"みぇ": u"m' e", u"みょ": u"m' o",
        u"りゃ": u"4' a", u"りゅ": u"4' M", u"りょ": u"4' o",
        u"が": u"g a", u"ぎ": u"g' i", u"ぐ": u"g M", u"げ": u"g e", u"ご": u"g o",
        u"ざ": u"dZ a", u"じ": u"dZ i", u"ず": u"dz M", u"ぜ": u"dz e", u"ぞ": u"dz o",
        u"だ": u"d a", u"ぢ": u"d i", u"づ": u"d M", u"で": u"d e", u"ど": u"d o",
        u"ば": u"b a", u"び": u"b' i", u"ぶ": u"b M", u"べ": u"b e", u"ぼ": u"b o",
        u"ぱ": u"p a", u"ぴ": u"p' i", u"ぷ": u"p M", u"ぺ": u"p e", u"ぽ": u"p o",
        u"ん": u"n",
        u"ぎゃ": u"g' a", u"ぎゅ": u"g' M", u"ぎょ": u"g' o",
        u"じゃ": u"dZ a", u"ずぃ": u"dz i", u"じゅ": u"dZ M", u"じぇ": u"dZ e", u"じょ": "dZ o",
        u"でぃ": u"d' i", u"でゅ": u"d' M",
        u"びゃ": u"b' a", u"びゅ": u"b' M", u"びぇ": u"b' e", u"びょ": u"b' o",
        u"ぴゃ": u"p' a", u"ぴゅ": u"p' M", u"ぴぇ": u"p' e", u"ぴょ": u"p' o",

        u"てゃ": u"t' a", u"てぃ": u"t' i", u"てゅ": u"t' M", u"てぇ": u"t' e", u"てょ": u"t' o"
    }

#発音記号=>歌詞（ひらがな）の変換テーブル
lyric_table = dict(zip(phonetic_table.values(), phonetic_table.keys()))


#ローマ字の歌詞が入力されたとき用に更新
phonetic_table.update({
    u"a": u"a", u"i": u"i", u"u": u"M", u"e": u"e", u"o": u"o",  # あ行
    u"ka": u"k a", u"ca": u"k a", u"ki": u"k i", u"ku": u"k M", u"cu": u"k M", u"qu": u"k M", u"ke": u"k e", u"ko": u"k o", u"co": "k o",  # か行
    u"sa": u"s a", u"si": u"s i", u"shi": u"s i", u"ci": u"s i", u"su": u"s M", u"se": u"s e", u"ce": u"s e", u"so": u"s o",  # さ行
    u"ta": u"t a", u"ti": u"tS i", u"tu": u"ts M", u"te": u"t e", u"to": u"t o",  # た行
    u"na": u"n a", u"ni": u"J i", u"nu": u"n M", u"ne": u"n e", u"no": u"n o",  # な行
    u"ha": u"h a", u"hi": u"C i", u"hu": u"p\ M", u"he": u"h e", u"ho": "h o",  # は行
    u"ma": u"m a", u"mi": u"m' i", u"mu": u"m M", u"me": u"m e", u"mo": u"m o",   # ま行
    u"ya": u"j a", u"yu": u"j M", u"ye": u"j e", u"yo": u"j o",  # や行
    u"ra": u"4 a", u"ri": u"4' i", u"ru": u"4 M", u"re": u"4 e", u"ro": u"4 o",  # ら行
    u"wa": u"w a", u"wi": u"w i", u"we": u"w e", u"wo": u"w o",  # わ行
    u"la": "h\ a", u"xa": u"h\ a", u"li": u"h\ i", u"xi": u"h\ i", u"lu": u"h\ M", u"xu": u"h\ M", u"le": u"h\ e", u"xe": u"h\ e", u"lo": u"h\ o", u"xo": u"h\ o",  # ぁぃぅぇぉ
    u"kya": u"k' a", u"kyu": u"k' M", u"kyo": u"k' o",  # きゃきゅきょ
    u"sha": u"S a", u"sya": u"S a", u"shu": u"S M", u"syu": u"S M", u"she": u"tS e", u"sye": u"tS e", u"sho": u"S o", u"syo": u"S o",  # しゃしゅしぇしょ
    u"cha": u"tS a", u"cya": u"tS a", u"tya": u"tS a", u"tsi": u"ts i", u"chu": u"tS M", u"cyu": u"tS M", u"che": u"tS e", u"tye": u"tS e", u"tyo": u"tS o", u"cho": u"tS o",  # ちゃつぃちゅちぇちょ
    u"nya": u"J a", u"nyu": u"J M", u"nye": u"J e", u"nyo": u"J o",  # にゃにゅにぇにょ
    u"hya": u"C a", u"hyu": u"C M", u"hye": u"C e", u"hyo": u"C o",  # ひゃひゅひぇひょ
    u"fa": u"p\ a", u"fi": u"p\' i", u"fyu": u"p\' M", u"fe": u"p\ e", u"fo": u"p\ o",  # ふぁふぃふゅふぇふぉ
    u"mya": u"m' a", u"myu": u"m' M", u"mye": u"m' e", u"myo": u"m' o",  # みゃみゅみぇみょ
    u"rya": u"4' a", u"ryu": u"4' M", u"ryo": u"4' o",  # りゃりゅりょ
    u"ga": u"g a", u"gi": u"g' i", u"gu": u"g M", u"ge": u"g e", u"go": u"g o",  # がぎぐげご
    u"nga": u"N a", u"ngi": u"N' i", u"ngu": u"N M", u"nge": u"N e", u"ngo": u"N o",  # nがnぎnぐnげnご
    u"za": u"dZ a", u"zi": u"dZ i", u"ji": u"dZ i", u"zu": u"dZ M", u"ze": u"dz e", u"zo": u"dz o",  # ざじずぜぞ
    u"da": u"d a", u"di": u"d i", u"du": u"d M", u"de": u"d e", u"do": u"d o",  # だぢづでど
    u"ba": u"b a", u"bi": u"b' i", u"bu": u"b M", u"be": u"b e", u"bo": u"b o",  # ばびぶべぼ
    u"pa": u"p a", u"pi": u"p' i", u"pu": u"p M", u"pe": u"p e", u"po": u"p o",  # ぱぴぷぺぽ
    u"n": u"n",
    u"gya": u"g' a", u"gyu": u"g' M", u"gyo": u"g' o",  # ぎゃぎゅぎょ
    u"ja": u"dZ a", u"zya": u"dZ a", u"ju": u"dZ M", u"zyu": u"dZ M",  u"je": u"dZ e", u"zye": u"dZ e", u"jo": u"dZ o", u"zyo": u"dZ o",  # じゃじゅじぇじょ
    u"dhi": u"d' i", u"dhu": u"d' M",  # でぃでゅ
    u"bya": u"b' a", u"byu": u"b' M", u"bye": u"b' e", u"byo": u"b' o",  # びゃびゅびぇびょ
    u"pya": u"p' a", u"pyu": u"p' M", u"pye": u"p' e", u"pyo": u"p' o",  # ぴゃぴゅぴぇぴょ
    u"tha": u"t' a", u"thi": u"t' i", u"thu": u"t' M", u"the": u"t' e", u"tho": u"t' o", # てゃてぃてゅてぇてょ
    })

#その他の歌詞が挿入された場合
phonetic_table.update({
    u"-": u"a", u"ー": u"a", u"−": u"a",  # 伸ばし棒 
    u"s": u"s", u"m": u"m"
    })


def lyric2phonetic(lyric):
    """歌詞を発音記号に変換する
    Args:
        lyric: 歌詞（ひらがな or ローマ字）(unicode)

    Returns:
        発音記号(unicode)
    """
    try:
        phonetic = phonetic_table[lyric]
    except KeyError:
        phonetic = u"a"
    return phonetic


def phonetic2lyric(phonetic):
    """発音記号を歌詞に変換する
    Args:
        phonetic: 発音記号（unicode）

    Returns:
        歌詞（ひらがな）（unicode）
    """
    try:
        lyric = lyric_table[phonetic]
    except KeyError:
        lyric = u"あ"
    return lyric

class FakeFile(object):
    """文字列アクセスをファイルアクセスのように動作させるクラス"""
    def __init__(self, string=""):
        """
        Args:
            string: 対象文字列
        """
        self._string = string
        self._index = 0

    def read(self, byte):
        """文字列を読み出す
        Args:
            byte: 読み出すbyte数

        Returns:
            読み出した文字列
        """
        string = self._string[self._index:self._index + byte]
        self._index += byte
        return string

    def tell(self):
        """現在の読み出し開始インデックスを返す
        Returns:
            現在の読み出し開始インデックス
        """
        return self._index
