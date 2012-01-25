# -*- coding: utf-8 -*-
import re
from struct import *
import sys
import codecs
#sys.stdout = codecs.EncodedFile(sys.stdout, 'utf_8')


__author__ = "大野誠<makoto.pingpong1016@gmail.com>"
__status__ = "test"
__date__ = "2012/01/22"
__version__ = 0.01


def stu(s):
	"""shift_jisの文字列をutf-8に変換する（表示の時以外は使わないでね！）
		vsqファイルの日本語（shift-jis）を自分の環境（utf-8）で表示できるようにする。
	"""
	return s.decode('shift_jis').encode('utf-8')


def pp(obj):
	"""オブジェクトを綺麗に表示する。
		現時点では、リストを改行して表示するのみ。
	"""
	if isinstance(obj, list):
		for o in obj:
			pp(o)
	else:
		print obj

class FakeFile(object):
	"""文字列アクセスをファイルアクセスのように
		動作させるクラス
	"""
	def __init__(self, string=''):
		self._string = string
		self._index = 0

	def read(self, byte):
		string = self._string[self._index:self._index+byte]
		self._index += byte
		return string


class VSQEditor(object):
	"""VSQファイルを扱うモジュール。
		超簡素かつ粗雑な作り。
		使い方は一番下のテストコードで察してください。
	"""
	def __init__(self, filename=None, string=None):
		if filename: self.parse(filename=filename)
		elif string: self.parse(string=string)
        
	def __get_dtime(self):
		dtime = 0
		byte = ord(self._f.read(1))
		dtime += (byte & 0x7f)
		while byte & 0x80:
			dtime  = dtime << 7
			byte = ord(self._f.read(1))
			dtime += (byte & 0x7f)
		return dtime
	
	def __dtime2binary(self, dtime):
		bins = []
		byte = dtime
		calc_1b = lambda b:(b & 0x7f) if bins else ((b & 0x7f) | 0x80)
		while byte >= 0x80:
			b = calc_1b(byte)
			bins.append(b)
			byte = byte >> 7
		b = calc_1b(byte)
		bins.append(b)
		bins.reverse()
		binary = ''
		for b in bins: binary += pack('B', b)
		return binary
		
	def __parse_header(self):
		if self._f.read(4) != "MThd":
			print "header not found."
			return {}
		header = {'size': unpack('>i', self._f.read(4))[0],
				  'format': unpack('>h', self._f.read(2))[0],
				  'trackNum': unpack('>h', self._f.read(2))[0],
				  'timeDiv': unpack('>h', self._f.read(2))[0]}
		return header

	def __unparse_header(self):
		binary = 'MThd' + pack('>ihhh',
							   self.header['size'],
							   self.header['format'],
							   self.header['trackNum'],
							   self.header['timeDiv'])
		return binary

	def __parse_master_track(self):
		#トラックチャンクヘッダの解析
		if self._f.read(4) != "MTrk":
			print "Master Track not found."
			return {}
		master_track = {}
		master_track['size'] = unpack('>i', self._f.read(4))[0]
		master_track['MetaEvents'] = []
		#MIDIイベントの解析
		dtime = self.__get_dtime()
		mevent = unpack('BBB', self._f.read(3))
		while mevent[1] != 0x2f:
			#テンポイベント
			if mevent[1] == 0x51:
				contents = unpack('>I', '\x00'+self._f.read(3))[0]
				metaevent = {'dtime': dtime,
							 'type': 'tempo',
							 'tb': mevent[1],
							 'len': 3,
							 'contents': contents}
				master_track['MetaEvents'].append(metaevent)	
			#トラックネームイベント
			elif mevent[1] == 0x03:
				metaevent = {'dtime': dtime,
							 'type': 'TrackName',
							 'tb': mevent[1],
							 'len': mevent[2],
							 'contents': self._f.read(mevent[2])}
				master_track['MetaEvents'].append(metaevent)
			#拍・拍子イベント
			elif mevent[1] == 0x58:
				metaevent =	{'dtime': dtime,
							 'type': 'beat',
							 'tb': mevent[1],
							 'len': 4,
							 'contents': unpack('bbbb', self._f.read(4))}
				master_track['MetaEvents'].append(metaevent)
				#プリメジャータイムを求める
				if dtime == 0:
					nn = metaevent['contents'][0]
					dd = 2 ** metaevent['contents'][1]
					premtime = nn/float(dd)*16*self.header['timeDiv']
					master_track['startTime'] = premtime
			dtime = self.__get_dtime()
			mevent = unpack('BBB', self._f.read(3))
		return master_track

	def __unparse_master_track(self):
		binary = 'MTrk' + pack('>I',self.master_track['size'])
		for event in self.master_track['MetaEvents']:
			binary += self.__dtime2binary(event['dtime'])
			binary += pack('cBB',
							'\xff',
							event['tb'],
							event['len'])
			if event['tb'] == 0x51:
				tempo = event['contents']
				binary += pack('>BBB',
								(tempo & 0x00ff0000) >> 16,
								(tempo & 0x0000ff00) >> 8,
								(tempo & 0x000000ff))
			elif event['tb'] == 0x03:
				binary += event['contents']
			elif event['tb'] == 0x58:
				for b in event['contents']: binary += pack('b', b)
		binary += '\x00\xff\x2f\x00'
		return binary

	def __parse_normal_track(self):
		#トラックチャンクヘッダの解析
		if self._f.read(4) != "MTrk":
			print "Normal Track not found."
			return {}
		track = {}
		track['size'] = unpack('>i', self._f.read(4))[0]
		track['metastring'] = ''
		track['CCdata'] = []
		#MIDIイベントの解析
		dtime = self.__get_dtime()
		mevent = unpack('BBB', self._f.read(3))
		while mevent[1] != 0x2f: 
			#コントロールチェンジイベント
			if mevent[0] == 0xb0:
				track['CCdata'].append({'dtime':dtime, 'cc':mevent})
			else:
				#トラックネームイベント
				if mevent[1] == 0x03: 
					track['name'] = self._f.read(mevent[2])
				#テキストイベント
				elif mevent[1] == 0x01:
					self._f.read(8) #skip "DM:xxxx:"
					track['metastring'] += self._f.read(mevent[2]-8)
			dtime = self.__get_dtime()
			mevent = unpack('BBB', self._f.read(3))
		#End of Trackイベント
		track['eot'] = self.__dtime2binary(dtime) + '\xff\x2f\x00'
		current_tag = ''
		track['Common'] = {}
		track['Master'] = {}
		track['Mixer'] = {}
		track['EventList'] = []
		track['Events'] = {}
		track['Details'] = {}
		#テキスト情報の解析
		for line in track['metastring'].split('\n'):
			if line == '': break
			if re.compile('\[.+\]').match(line):
				current_tag = line[1:-1]
			else:
				#Common,Master,Mixer情報
				if re.compile('Common|Master|Mixer').match(current_tag):
					key, value = line.split('=')
					track[current_tag][key] = value
				#イベントリスト
				elif current_tag == "EventList":
					time, eventid  = line.split('=')
					event = {'time': time, 'id': eventid}
					track['EventList'].append(event)
				#各パラメータカーブのリスト
				elif re.compile('.+BPList').match(current_tag):
					if not track.get(current_tag):
						track[current_tag] = []
					key, value = line.split('=')
					track[current_tag].append({'time': int(key),
											   'value': int(value)})
				#イベントの詳細
				elif re.compile('ID#[0-9]{4}').match(current_tag):
					if not track['Events'].get(current_tag):
						track['Events'][current_tag] = {}
					key, value = line.split('=')
					track['Events'][current_tag][key] = value
				#各種詳細(歌詞情報等もここに含まれる)
				elif re.compile('h#[0-9]{4}').match(current_tag):
					if not track['Details'].get(current_tag):
						track['Details'][current_tag] = {}
					lines = len(line.split(','))
					if lines == 1:
						key, value = line.split('=')
						track['Details'][current_tag][key] = value
					#歌詞情報
					else:
						l0 = line.split('=')[1].split(',')
						d = {}
						#2パターンあった
						if len(l0) == 5:
							d = {'lyrics': l0[0][1:-1],
								 'phonetic': l0[1][1:-1],
								 'unknown1': l0[2],
								 'unknown2': l0[3],
								 'protect': l0[4]}
						else:
							d = {'lyrics': l0[0][1:-1],
								 'phonetic': l0[1][1:-1],
								 'unknown1': l0[2],
								 'unknown2': l0[3],
								 'unknown3': l0[4],
								 'protect': l0[5]}
						track['Details'][current_tag] = d
		#音符イベントをまとめたリストを生成する 
		track['AnoteEvents'] = self.__create_anote_events(track)
		last_anote = track['AnoteEvents'][-1]
		self.master_track['endTime'] = (last_anote['end_time']+
										self.header['timeDiv']*4)
		return track

	def __unparse_normal_track(self, track): 
		#トラックチャンクヘッダ
		binary = 'MTrk' + pack('>I', track['size'])
		binary += pack('BBBB',
						0x00,
						0xff,
						0x03,
						len(track['name']))
		binary += track['name']
		#テキスト情報
		metastring = ''
		for tag in ['Common','Master','Mixer']:
			metastring += '[%s]\n' % tag
			for item in track[tag].items():
				metastring += "%s=%s\n" % item
		metastring += '[EventList]\n'
		for event in track['EventList']:
			metastring += "%(time)s=%(id)s\n" % event
		for key, value in track['Events'].items():
			metastring += '[%s]\n' % key
			for item in value.items():
				metastring += "%s=%s\n" % item
		for key, value in track['Details'].items():
			metastring += '[%s]\n' % key
			if value.keys().count('lyrics') == 0:
				for item in value.items():
					metastring += "%s=%s\n" % item
			elif value.keys().count('unknown3') == 0:
				metastring += '''L0=\"%(lyrics)s\",\
								 \"%(phonetic)s\",\
								 %(unknown1)s,\
								 %(unknown2)s,\
								 %(protect)s\n''' % value
			else:
				metastring += '''L0=\"%(lyrics)s\",\
								 \"%(phonetic)s\",\
								 %(unknown1)s,\
								 %(unknown2)s,\
								 %(unknown3)s,\
								 %(protect)s\n''' % value
		bprxp = re.compile('.+BPList')
		bptags = [tag for tag in track.keys() if bprxp.match(tag)]
		for tag in bptags:
			metastring += "[%s]" % tag + '\n'
			for item in track[tag]:
				metastring += "%(time)d=%(value)d" % item + '\n'
		#テキスト情報からSMFに変換する処理
		s=0
		e=119
		mslist = []
		while e < len(metastring):
			mslist.append(metastring[s:e])
			s+=119
			e+=119
		mslist.append(metastring[s:])
		dmcount = 0
		for tevent in mslist:
			binary += pack('BBBB',
							0x00,
							0xff,
							0x01,
							len(tevent)+8)
			binary += 'DM:%04d:' % dmcount + tevent
			dmcount += 1
		for b in track['CCdata']:
			binary += self.__dtime2binary(b['dtime'])
			binary += pack('BBB', b['cc'][0], b['cc'][1], b['cc'][2])
		#End of Track
		binary += track['eot']	
		return binary

	def __create_anote_events(self, track):
		"""[ID,歌詞,発音,音高,開始時間,終了時間]
			でまとめられた音符イベントのリストが生成される
			ルール適用部分の参考素材になりそうな予定
		"""
		anoteEvents = []
		for event in track['EventList']:
			if event['id'] == 'EOS':
				break
			if track['Events'][event['id']]['Type'] == 'Anote': 
				e = track['Events'][event['id']] 
				d = track['Details'][e['LyricHandle']]
				es ={'id': event['id'],
					 'start_time': int(event['time']),
					 'lyrics': d['lyrics'],
					 'phonetic': d['phonetic'],
					 'note': int(e['Note#']),
					 'end_time': int(event['time']+e['Length'])}
				anoteEvents.append(es)
		return anoteEvents

	def parse(self, filename=None, string=None):
		"""VSQファイルをパースする。"""
		if filename: self._f = open(filename, 'r')
		else: self._f = FakeFile(string)
		self.header = self.__parse_header()
		self.master_track = self.__parse_master_track()
		self.normal_tracks = []
		for i in range(self.header['trackNum']-1):
			track = self.__parse_normal_track()
			self.normal_tracks.append(track)       
		self.select_track(0)
		
	def unparse(self, filename=None):
		"""現在のオブジェクトのデータをアンパースして、
		   VSQファイルとして書きこむ。
		"""
		binary = self.__unparse_header()
		binary += self.__unparse_master_track()
		for track in self.normal_tracks:
			binary += self.__unparse_normal_track(track)
		if filename: 
			self._of = open(filename, 'w')
			self._of.write(binary)
		else:
			return binary
		
	def __set_param_curve(self, ptype, curve, s, e):
		start_time = self.master_track['startTime']
		end_time = self.master_track['endTime']
		if s is None or s <= start_time: s = start_time + 1 	
		if e is None or e >= end_time: e = end_time + 1 	
		length = e - s
		if length < 0:
			return False
		len_ratio = float(length)/len(curve)
		new_bp = []
		for i, v in enumerate(curve):
			if int(len_ratio*i) != int(len_ratio*(i-1)) or i == 0:
				new_bp.append({'time': s+int(len_ratio*i), 'value':v})
		param = self.current_track[ptype]
		select = self.__get_param_curve
		end_cands = select(ptype,start_time,s) + select(ptype,s,e)
		endvalue = end_cands[-1]['value']
		new_bp.append({'time':e+1, 'value':endvalue})
		for p in select(ptype,s,e): param.remove(p)
		param.extend(new_bp)
		param.sort()
		return True

	def get_anotes(self, s=None, e=None):
		"""sからeまでの音符情報を取得する。
			sやeを指定しなければ、トラックの先頭と末尾に置き換えられる。
		"""
		if s==None: s = self.master_track['startTime']
		if e==None: e = self.master_track['endTime']
		return [ev for ev in self.current_track['AnoteEvents']
					   if s <= ev['end_time'] and ev['start_time'] <= e]

	def __get_param_curve(self, ptype, s, e):
		if s==None: s = self.master_track['startTime']
		if e==None: e = self.master_track['endTime']
		return [ev for ev in self.current_track[ptype]
					   if s <= ev['start_time'] <= e]

	def get_pitch_curve(self, s=None, e=None):
		"""sからeまでのピッチ曲線を取得する。
			sやeを指定しなければ、トラックの先頭と末尾に置き換えられる。
		"""
		return self.__get_param_curve('PitchBendBPList', s, e)

	def get_dynamics_curve(self, s=None, e=None):
		"""sからeまでのダイナミクス曲線を取得する。
			sやeを指定しなければ、トラックの先頭と末尾に置き換えられる。
		"""
		return self.__get_param_curve('DynamicsBPList', s, e)

	def set_pitch_cureve(self, curve, s=None, e=None):
		"""sからeまでのピッチ曲線をcurveで置き換える。"""
		return self.__set_param_curve('PitchBendBPList', curve, s, e)
		
	def set_dynamics_curve(self, curve, s=None, e=None):
		"""sからeまでのダイナミクス曲線をcurveで置き換える。"""
		return self.__set_param_curve('DynamicsBPList', curve, s, e)
		
	def select_track(self, track_num):
		"""操作対象トラックを変更する。"""
		if track_num < self.header['trackNum']:
			self.current_track = self.normal_tracks[track_num]
			return True
		else:
			return False


'''
テストコード:
1.test.vsqを読み込んで、時間6800~7100に存在する音符イベント、
ダイナミクス、ピッチベンドのカーブを表示する。
2.指定した時間の時間のダイナミクス、ピッチベンドのカーブを
任意のものに変更する。
3.パース結果をアンパースし、outtest.vsqとして出力する。
4.歌詞を表示する。
'''
if __name__ == '__main__':
	editor = VSQEditor(string=open('test.vsq', 'r').read())
	enable = [3,4]
	boinrxp = re.compile("[a|i|M|e|o]")
	
	#1
	if 1 in enable: 
		pp("anotes:")
		pp(editor.get_anotes(s=6800))
		pp("\ndynamics:")
		pp(editor.get_dynamics_curve(6800,7100))
		pp("\npitchbend:")
		pp(editor.get_pitch_curve(6800,7100))
		pp('')
	
	#2
	if 2 in enable:
		editor.set_pitch_cureve(range(-5000,5000,1),850,6200)
		editor.set_dynamics_curve(range(1,100)+range(100,1,-1),20800,35200)
		editor.set_dynamics_curve([0],30800,35200)
		editor.set_dynamics_curve([128],32000,32000)
		
	#3
	if 3 in enable:
		print editor.unparse()
		
	#4
	if 4 in enable:
		pp('lyrics:')
		anotes = editor.get_anotes()
		lyrics = [anote['phonetic'] for anote in anotes]
		pp(''.join(lyrics))
		pp('phonetic:')
		plist = []
		for i, anote in enumerate(anotes):
			if (not boinrxp.match(anote['phonetic']) and
					not i is len(anotes)-1):
				first = anote	
				second = anotes[i+1]
				if(second['start_time'] - first['end_time'] < 20 and
						boinrxp.match(second['phonetic'])):
					plist.append(first['lyrics']+second['lyrics']+',')
		print ''.join(plist)


