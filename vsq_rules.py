# -*- coding: utf-8 -*-
"""
とりあえずルール記述しておく領域
将来的にはDBにルールを格納するだろうけど
現時点の仕様
・各パラメータをディクショナリで定義
・クラス化したほうがいい気もするのだけど、
　メソッドが思いつかないので…

以下ディクショナリの要素について
rule_id:
    ルールID,重複しないように注意する必要がある。
    DBを使うようになれば問題ないのだが。

name:
    ルール名、重複あり

regexp:
    ルールを適用する際の適用対象判断のための、
    正規表現。適用する際のカーブをマッチする
    モーラ数分用意しなくてはならないので、
    *や?を使われると困る。

connect:
    正規表現にマッチした部分の音符が接続されていることを
    条件として考慮するかどうか。

relative_notes:
    相対音程を格納したリスト、regexpのモーラ数分用意
    する必要がある。つまり正規表現が「でしょ」等の場合
    は2つ分の相対音程を用意する。また、相対音程とは
    現在の音程と前の音の音程の差である。
    ノートが60,62,59と遷移する場合の相対音程は、
    0,2,-3となる。このパラメータを仕様する場合は、この
    相対音程もマッチするところにしかルールが適用されない。
    相対音程を考慮したくない場合はNoneを記述する。

dyn_curves:
pit_curves:
    マッチした部分にルールを適用する際の、適用後
    カーブを格納する。regexpのモーラ数分用意する
    必要がある。
"""

def curve(curvelist, stretch=None):
    return {"curve":curvelist,"stretch":stretch}

def linear(start, end=None, step=None, stretch=None):
    if not end: return curve([start])
    if not step: step = 1 if end > start else - 1
    return curve(range(start,end,step),stretch)

def lowpass(l_value, h_value, ratio, stretch=None):
    length = 1000;
    p = int(ratio*length)
    d = (h_value-l_value)/100.0
    c = [ h_value for v in range(p) ]
    c += [ int(h_value - d*i) for i in range(100)]
    c += [ l_value for v in range(1000-100-p)]
    return curve(c,stretch)


dyn_curves = [linear(0,100),
              curve(range(30,0,-1)+range(0,100)),
              linear(100,0)]

san_rule = {"rule_id":"R0",
        "name":"さんの前のdynを下げる",
        "regexp":u".さn",
        "connect":True,
        "relative_notes":[0,-2,0],
        "dyn_curves":dyn_curves,
        "pit_curves":[]}

zuii_dyn_curves = [lowpass(0,100,0.8)]
zuii_pit_curves = [lowpass(-10000,0,0.8)]


zuii_rule = {"rule_id":"R1",
        "name":"ずぃの最後お下げる",
        "connect":False,
        "regexp":u"ずぃ",
        "relative_notes":None,
        "dyn_curves":zuii_dyn_curves,
        "pit_curves":zuii_pit_curves}


