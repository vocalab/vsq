# -*- coding: utf-8 -*-
import re
from tools import *
from vsq_rules import *
from normaltrack import *
from mastertrack import *
from header import *
from struct import *


class VSQEditor(object):
    """VSQファイルを操作するクラス
    Attributes:
        header: headerインスタンス（header.pyを参照）
        master_track: mastertrackインスタンス（mastertrack.pyを参照）
        track_num: ノーマルトラック数
        normaltracks: normaltrackインスタンスのリスト（normaltrack.pyを参照）
        current_track: 操作対象トラック
        start_time: シーケンスの先端時間（各トラックにおける実質先端時間）
        end_time: シーケンスの終端時間
    """

    def __init__(self, filename=None, binary=None):
        if filename:
            self.parse(filename=filename)
        elif binary:
            self.parse(binary=binary)

    def parse(self, filename=None, binary=None):
        """VSQファイルをパースする
        Args:
            filename: VSQファイルのパス
            binary: VSQファイルのバイナリデータ
        引数はfilename,binaryのどちらかを指定
        両方書いた場合filenameが優先される
        """
        #各チャンクのパース
        self._fp = open(filename, 'r') if filename else tools.FakeFile(binary)
        self.header = Header(self._fp)
        self.master_track = MasterTrack(self._fp)
        track_num = self.header.data['track_num'] - 1
        self.normal_tracks = [NormalTrack(self._fp) for i in range(track_num)]

        self.unapply_dict = {}

        #トラックの先端時間（プリメジャータイムを除いた時間）を求める
        pre_measure = int(self.normal_tracks[0].data['Master']['PreMeasure'])
        nn, dd, _, _ = self.master_track.beat
        time_div = self.header.data['time_div']
        self.start_time = int(nn / float(2 ** dd) * 4 * pre_measure * time_div)

        #トラックの終端時間（最後のノートイベントの終端時間）を求める
        self.end_time = self.start_time
        for track in self.normal_tracks:
            et = track.anotes[-1].end
            self.end_time = max(et, self.end_time)

        # self.current_track を 0 番目に設定
        self.select_track(0)

    def unparse(self, filename=None):
        """現在のオブジェクトのデータをアンパースして、
        VSQファイルとして書きこむ
        Args:
            filename: 書き込むVSQファイルのパス
        Returns:
            filenameが指定されなかった場合はバイナリ
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
        Returns:
            歌詞(string)
        """
        return self.current_track.lyrics

    def get_anotes(self, s=None, e=None):
        """sからeまでの音符情報を取得する
        Args:
            s: 選択開始地点の時間
            e: 選択終了地点の時間
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる

        Returns:
            Anoteインスタンスのリスト
            Anoteクラスについては、normaltrack.pyを参照
        """
        if s is None:
            s = self.start_time
        if e is None:
            e = self.end_time
        anotes = self.current_track.anotes
        return [a for a in anotes if s <= a.end and a.start <= e]

    def get_anotes_f_lyric_i(self, s=None, e=None):
        lyrics = self.get_lyrics()
        if not s:
            s = 0
        if not e:
            e = len(lyrics)
        smallrxp = re.compile(u"[ぁぃぅぇぉゃゅょ]")

        s_index = s - len(smallrxp.findall(lyrics[:s]))
        e_index = e - len(smallrxp.findall(lyrics[:e]))
        return self.current_track.anotes[s_index:e_index]

    def get_pitch_curve(self, s=None, e=None):
        """sからeまでのピッチ曲線を取得する
        Args:
            s: 選択開始地点の絶対時間
            e: 選択終了地点の絶対時間
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる

        Returns:
            ピッチ曲線（時間と値で構成されるディクショナリのリスト）
            example:
            [{"time": 100, "value": -10},
             {"time": 200, "value": 0},
             {"time": 300, "value": 30}]

        """
        return self.__get_param_curve('PitchBendBPList', s, e)

    def get_dynamics_curve(self, s=None, e=None):
        """sからeまでのダイナミクス曲線を取得する
        Args:
            s: 選択開始地点の絶対時間
            e: 選択終了地点の絶対時間
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる

        Returns:
            ダイナミクス曲線（時間と値で構成されるディクショナリのリスト）
            example:
            [{"time": 100, "value": 10},
             {"time": 200, "value": 20},
             {"time": 300, "value": 30}]
        """
        return self.__get_param_curve('DynamicsBPList', s, e)

    def set_pitch_curve(self, curve, s=None, e=None, stretch=None):
        """sからeまでのピッチ曲線をcurveで置き換える
        Args:
            curve: 曲線を表すリスト
            s: 選択開始地点の絶対時間
            e: 選択終了地点の絶対時間
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
        Args:
            curve:曲線を表すリスト
            s: 選択開始地点の絶対時間
            e: 選択終了地点の絶対時間
            stretch: 曲線の伸縮オプション（未実装）
        sやeを指定しなければ、トラックの先頭と末尾の時間に置き換えられる
        """
        return self.__set_param_curve('DynamicsBPList',
                                        curve,
                                        s,
                                        e,
                                        stretch)

    def set_anote_length(self, anotes, length):
        """音符の長さを変更する
        Args:
            anotes: 変更対象となる音符イベント（リスト）
            length: 変更後の音符の長さ
        """
        for a in anotes:
            a.length = length

    def select_track(self, n):
        """操作対象トラックを変更する
        Args:
            n: トラック番号
        """
        if n < len(self.normal_tracks):
            self.current_track = self.normal_tracks[n]

    def apply_rule(self, rule_i):
        """ルールを適用する
        Args:
            rule_i: get_rule_candsメソッドによって得られたルール適用候補
        """
        anotes = self.get_anotes_f_lyric_i(rule_i['s_index'],
                                      rule_i['e_index'])
        for i, curve in enumerate(rule_i['rule']['dyn_curves']):
            self.set_dynamics_curve(curve['curve'],
                                anotes[i].start,
                                anotes[i].end,
                                curve['stretch'])
        for i, curve in enumerate(rule_i['rule']['pit_curves']):
            self.set_pitch_curve(curve['curve'],
                                anotes[i].start,
                                anotes[i].end,
                                curve['stretch'])

    def unapply_rule(self, rule_i):
        """ルールの適用をもとに戻す
        Args:
            rule_i: get_rule_candsメソッドによって得られたルール適用候補
        """
        rule_i = self.unapply_dict[rule_i['id']]
        anotes = self.get_anotes_f_lyric_i(rule_i['s_index'], rule_i['e_index'])
        start_time = anotes[0].start
        end_time = anotes[-1].end

        dynamics_list = self.current_track.data['DynamicsBPList']
        pitch_list = self.current_track.data['PitchBendBPList']
        for p in self.get_dynamics_curve(start_time, end_time):
            self.current_track.data['DynamicsBPList'].remove(p)
        for p in self.get_pitch_curve(start_time, end_time):
            self.current_track.data['PitchBendBPList'].remove(p)
        dynamics_list.extend(rule_i['undyn'])
        pitch_list.extend(rule_i['unpit'])
        dynamics_list.sort()
        pitch_list.sort()

    def get_rule_cands(self, rule):
        """ルール適用候補を取得する
        Arge:
            rule: ディクショナリとして格納されたルール定義（vsq_rules.pyを参照）

        Returns:
            ルール適用候補（リスト）
        ルール適用候補のキーには重複しないIDが振られている
        """
        rulerxp = re.compile(rule['regexp'])
        rules = []

        def is_connected(anotes):
            if len(anotes) <= 1:
                return True
            for i, a in enumerate(anotes[1:]):
                if a.start - anotes[i].end > 50:
                    return False
            return True

        def check_notes(notes, anotes):
            if notes is None:
                return True
            relative_notes = [0] + [anote['note'] - anotes[i]['note']
                for i, anote in enumerate(anotes[1:])]
            return relative_notes == notes

        match_len = lambda x, y: (not x or not y) or len(x) == len(y)
        lyrics = self.get_lyrics()
        for i, match in enumerate(rulerxp.finditer(lyrics)):
            s = match.start()
            e = match.end()
            match_anotes = self.get_anotes_f_lyric_i(s, e)
            #各ノートが接続されているか
            if rule['connect'] and not is_connected(match_anotes):
                continue
            #ノートの数と各ノートに割り当てられるカーブの数が一致するか
            if (not match_len(rule['dyn_curves'], match_anotes) or
                not match_len(rule['pit_curves'], match_anotes)):
                continue
            #音階の変化が一致するか
            if (rule['relative_notes'] and
                not check_notes(rule['relative_notes'], match_anotes)):
                continue
            else:
                rule_i = {"id": rule['rule_id'] + 'I' + str(i),
                        "rule": rule,
                        "s_index": s,
                        "e_index": e}
                u_dyn = self.get_dynamics_curve(
                        match_anotes[0].start,
                        match_anotes[-1].end)
                u_pit = self.get_pitch_curve(
                        match_anotes[0].start,
                        match_anotes[-1].end + match_anotes[-1].length)
                un_rule_i = {"s_index": s,
                        "e_index": e,
                        "undyn": u_dyn,
                        "unpit": u_pit}
                if not rule_i['id'] in self.unapply_dict:
                    self.unapply_dict[rule_i['id']] = un_rule_i
                rules.append(rule_i)

        return rules

    def __set_param_curve(self, ptype, curve, s, e, stretch):
        if s == None or s <= self.start_time:
            s = self.start_time + 1
        if e == None or self.end_time <= e:
            e = self.end_time + 1
        length = e - s
        if length < 0 or not curve:
            return False
        len_ratio = float(length) / len(curve)

        #curveをスケールしながらパラメータを生成
        new_bp = []
        for i, v in enumerate(curve):
            if int(len_ratio * i) != int(len_ratio * (i - 1)) or i == 0:
                new_bp.append({'time': s + int(len_ratio * i), 'value': v})
        select = self.__get_param_curve

        #元の波形の終端の値を新しい波形の終端に追加
        #選択範囲以外への影響を抑制する
        end_value = select(ptype, self.start_time, e)[-1]['value']
        new_bp.append({'time': e + 1, 'value': end_value})

        param = self.current_track.data[ptype]
        for p in select(ptype, s, e):
            param.remove(p)  # 選択範囲の元の波形の除去
        param.extend(new_bp)  # 新しい波形の追加
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
6.zuii_ruleを適用する
8.新しいノートを挿入する
'''
if __name__ == '__main__':
    editor = VSQEditor(binary=open('test.vsq', 'r').read())
    enable = [6]

    #1.音符情報、dynamics,pitchbendカーブを表示
    if 1 in enable:
        print "anotes:"
        anotes = editor.get_anotes(6800, 7100)
        pp(anotes)
        print "\ndynamics:"
        pp(editor.get_dynamics_curve(6800, 7100))
        print "\npitchbend:"
        pp(editor.get_pitch_curve(6800, 7100))

    #2.範囲を選択してカーブを編集
    if 2 in enable:
        editor.set_pitch_curve(range(-5000, 5000, 1), 850, 6200)
        editor.set_dynamics_curve(range(1, 100) + range(100, 1, -1), 20800, 35200)
        editor.set_dynamics_curve([0], 30800, 35200)
        editor.set_dynamics_curve([128], 32000, 32000)

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
        print "\nbefore"
        print editor.get_dynamics_curve(6740, 6820)
        for rule_i in rule_cands:
            editor.apply_rule(rule_i)
        print "\napplyied"
        print editor.get_dynamics_curve(6740, 6820)
        for rule_i in rule_cands:
            editor.unapply_rule(rule_i)
        print "\nunapplyed"
        print editor.get_dynamics_curve(6740, 6820)

    #ノート挿入テスト(Anoteクラス実装後版)
    if 8 in enable:
        note = {
            "time": 3200,
            "note": 64,
            "lyric": u"byo",
            "length": 120,
            "vibrato": None,
            }
        pp([l.get_phonetic() for l in editor.current_track.anotes])
        editor.current_track.anotes.append(Anote(**note))
        pp([l.get_phonetic() for l in editor.current_track.anotes])

    #3.編集結果をunparseして書きこむ
    if 3 in enable:
        editor.unparse('out.vsq')
