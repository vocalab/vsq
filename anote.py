# -*- coding: utf-8 -*-
import copy
import re
import tools


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
                「〜形でポルタメントを付加」の指定内容
                「上行形で〜」が指定されていれば+1
                「下行形で〜」が指定されていれば+2,
             "DEMdecGainRate" ディケイ,
             "DEMaccend": アクセント}
        is_prolong: 歌詞が伸ばし棒かどうか
        event: テキストベントの形式にフォーマットされたディクショナリ
        lyric_event: 同上。歌詞イベントを扱う
        vibrato_event: 同上。ビブラートイベントを扱う
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
    _start = 0
    _is_prolong = False  # 伸ばし棒かどうか
    def __init__(self, time, note, lyric=u"a", length=120,
            dynamics=64, vibrato=None, prop=d_prop):
        self.start = time
        self.note = note
        self.length = length
        self.lyric = lyric
        self.dynamics = dynamics
        self.vibrato = vibrato
        self.prop = prop

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return tools.pp_str({
                "start": self.start,
                "end": self._end,
                "note": self.note,
                "length": self._length,
                "lyric": self._lyric,
                "dynamics": self.dynamics,
                "properties": self.prop
                })

    def set_lyric(self, lyric):
        self._lyric = lyric
        self._is_prolong = bool(re.match(u"[-ー−]", self._lyric))
        self._phonetic = tools.lyric2phonetic(lyric)

    def get_lyric(self):
        return self._lyric

    def set_phonetic(self, phonetic):
        self._phonetic = phonetic
        #歌詞が伸ばし棒の時は発音記号の同期をしない
        if not self._is_prolong:
            self._lyric = tools.phonetic2lyric(phonetic)

    def get_phonetic(self):
        return self._phonetic

    def set_length(self, length):
        self._length = length
        self._end = self.start + length

    def get_length(self):
        return self._length

    def set_start(self, start):
        self._start = start
        self._end = self.start + self.length

    def get_start(self):
        return self._start

    def set_end(self, end):
        self._end = end
        self._length = end - self._start

    def get_end(self):
        return self._end

    lyric = property(get_lyric, set_lyric)
    phonetic = property(get_phonetic, set_phonetic)
    length = property(get_length, set_length)
    start = property(get_start, set_start)
    end = property(get_end, set_end)

    @property
    def is_prolong(self):
        return self._is_prolong

    @property
    def event(self):
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
        for key, value in self.prop.items():
            self.prop[key] = str(value)
        event.update(self.prop)
        if self.vibrato:
            vd = int((1 - int(self.vibrato['Length']) / 100.0) *
                    self.length / 5) * 5
            event['VibratoDelay'] = str(vd)
        return event

    @property
    def lyric_event(self):
        """詳細イベント形式の歌詞データを取得する
        Returns:
            詳細イベント形式の歌詞データ
            数値も文字列として格納される
        """
        lyric_event = {
            'lyric': self._lyric.encode('shift-jis'),
            'phonetic': self._phonetic.encode('shift-jis'),
            'lyric_delta': "%.6f" % 0,
            'protect': "0"
            }
        #ConsonantAdjustmentを追加
        phonetics = self._phonetic.split(' ')
        boinrxp = re.compile('aiMeo')
        for i, p in enumerate(phonetics):
            lyric_event['ca' + str(i)] = 0 if boinrxp.match(p) else 64
        return lyric_event

    @property
    def vibrato_event(self):
        """詳細イベント形式のビブラートデータを取得する
        Returns:
            詳細イベント形式の歌詞データ
        """
        return self.vibrato


class AnoteList(list):
    """Anoteインスタンスを格納するリスト
    ルール適用の際に、正規表現を使うので、
    歌詞上のインデックス <=> AnoteList上のインデックス
    みたいな処理がある

    Inherits:
        list

    Attributes:
        lyrics: 格納されているAnoteインスタンス間の歌詞を連結したもの
        phonetic: 格納されているAnoteインスタンス間の発音記号を連結したもの
        relative_notes: 格納されているAnoteインスタンス間の相対音階

    Exaples:
        anotes = AnoteList()
        antoes.append(Anote(1000, 64, u"あ"))
        anotes.append(Anote(100, 62, u"が"))   # ソートされて先頭にくる
        anotes.lyrics => "があ"
        anotes.phonetics => "g aa"
        anotes.relative_notes => [0, 2]
    """
    def __init__(self, other_list=[]):
        """コンストラクタ
        Args:
            other_list: 他のAnoteインスタンスが入ったリスト、またはAnoteList
        """
        super(AnoteList, self).__init__()
        self.extend(other_list)

    def append(self, anote):
        """Anoteインスタンスを追加する
        リストのappend()と同じ挙動。追加時に、
            ・型のチェック（Anoteインスタンスであるか）
            ・時間順ソート
            ・歌詞が伸ばし棒関連の場合の処理
        を行う

        Args:
            anote: 追加するAnoteインスタンス
        """
        if not anote.__class__.__name__ is 'Anote':
            raise TypeError("AnoteList support only Anote class for contents")

        #共通の参照のAnoteインスタンスを格納しない
        _anote = copy.deepcopy(anote) if anote in self else anote
        super(AnoteList, self).append(_anote)
        self.sort(key=lambda x: x.start)

        #歌詞が伸ばし棒だった場合
        if _anote.is_prolong:
            prev = self.index(_anote) - 1
            if prev >= 0:
                _anote.phonetic = self[prev].phonetic[-1]

        #挿入したAnoteの次の歌詞が伸ばし棒だった場合
        if self[-1] != _anote:
            next = self.index(_anote) + 1
            if self[next].is_prolong:
                self[next].phonetic = _anote.phonetic[-1]
            
    def extend(self, other_list):
        """他のAnoteインスタンスのリスト、AnoteListを連結する
        Args:
            other_list: 他のAnoteインスタンスのリスト、またはAnoteList
        """
        for anote in other_list:
            self.append(anote)

    def filter(self, start=None, end=None,
            lyric_start=None, lyric_end=None):
        """フィルタリングを行う
        Args:
            start: 選択始端時間
            end: 選択終端時間
            lyric_start: lyrics上の選択始端インデックス
            lyric_end: lyrics上の選択終端インデックス
            etc... 今後なにか追加できれば

        Returns:
            フィルタリングされたAnoteList
            戻り値のAnoteListは呼び出し元のものとは独立しているが、
            中身のAnoteインスタンスは共有される
        """
        s = start if start else 0
        e = end if end else self[-1].end
        lyric_s = lyric_start if lyric_start else 0
        lyric_e = lyric_end if lyric_end else len(self.lyrics)

        l2i = self.__lyric_index2index

        temp = self[l2i(lyric_s):l2i(lyric_e)]
        temp = [a for a in temp if s <= a.end and a.start <= e]

        return AnoteList(temp)

    def lyric_index(self, anote):
        """歌詞文字列上のインデックスを取得する
        Args:
            anote: 対象となるanote

        Returns:
            歌詞文字列上のインデックス

        Examples:
            anotes = AnoteList([
                            Anote(10, 50, u"ちゃ"),
                            Anote(20, 50, u"ちゅ"),
                            Anote(30, 50, u"ちょ")
                        ])
            anote = Anote(40, 50, u"あ")
            anotes.index(anote) => 3
            anotes.lyric_index(anote) => 6
        """
        i = self.index(anote)
        string = u''.join([a.lyric for a in self[:i]])
        return i + len(re.findall(u"[ぁぃぅぇぉゃゅょ]", string))

    def __lyric_index2index(self, i):
        return i - len(re.findall(u"[ぁぃぅぇぉゃゅょ]", self.lyrics[:i]))

    def __getslice__(self, i, j):
        return AnoteList(super(AnoteList, self).__getslice__(i, j))

    def split(self, distance=50):
        """distance時間以上離れているAnoteで区切る
        Args:
            distance: 区切る場所となる音符間の時間間隔

        Returns:
            区切られたAnoteList（AnoteListのList）
        """
        anote_lists = []
        buf = 0
        for i, a in enumerate(self[1:]):
            if a.start - self[i].end > distance:
                anote_lists.append(self[buf:i + 1])
                buf = i + 1
        anote_lists.append(self[buf:])
        return anote_lists

    @property
    def lyrics(self):
        return u''.join([a.lyric for a in self])

    @property
    def phonetics(self):
        return u''.join([a.phonetic for a in self])

    @property
    def relative_notes(self):
        return [0] + [a.note - self[i].note for i, a in enumerate(self[1:])]


if __name__ == '__main__':
    anotes = AnoteList()
    anote1 = Anote(100, 64, u"ひゃ")
    anote2 = Anote(260, 53, u"ー")
    anote3 = Anote(2000, 100, u"や")
    anote4 = Anote(5000, 100, u"お")
    anote5 = Anote(120, 90, u"い")
    anotes.extend([anote1, anote1, anote2, anote3])
    anotes.append(anote4)
    anotes.append(anote5)
    print anotes.phonetics
    print anotes.lyrics
    i = anotes.lyric_index(anote2)
    print i, anotes.lyrics[i]
    print anotes.split()[0].split()
    print anotes.filter(lyric_end=5)
    print anotes
