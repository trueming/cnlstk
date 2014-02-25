#!/usr/bin/env python
# -*- coding: utf-8 *-*
"""
Created by TRuEmInG (2008 fall) at NTU ESOE
Updated by TRuEmInG (2010~11 winter) at NTU ESOE for CNLSTK, Web API
Updated by TRuEmInG (2014 winter) at NTU ESOE for CNLSTK and CBETA output by Ray
"""

import codecs, os, re, cPickle
import xml.parsers.expat
from struct import *
from time import time, strftime, gmtime
from utility import *


class CBETAParser:
	'''
	將 CBETA XML檔案轉成欲建 Suffix Array 的連續文字及 offset 地副索引
	以果睿 2014 輸出的CBETA電子佛典(量化分析版) 為標準 'Dropbox/cbeta-simple-xml'
	一律輸出成 utf32 編碼檔案
	'''
	def __init__(self, location):
		'''
		location: parse 後的全文與索引存放位置
		'''
		if location[-1] == '/': location = location[:-1]	# 去資料夾尾記號
		if not os.path.exists(location): os.mkdir(location)	# 建資料夾（parse 後的全文與索引存放位置）
		self.location = location							# 資料夾設為全域變數
		self.offset = 0										# 處理中當前的 offset 位置是全域變數
		self.flag = 'off'									# 儲存文檔開關
		
		###########################
		# register the 3 expat handler functions above
		###########################
		self.p = xml.parsers.expat.ParserCreate()
		self.p.StartElementHandler = self.start_element
		self.p.EndElementHandler = self.end_element
		self.p.CharacterDataHandler = self.char_data

		############################################
		# 記錄所有不重複的 tag names, attrs and values
		# self.tags = { name1:{attr1:[value1,value2,...]}, name2:{...}, ...}
		############################################
		self.tags = {}
		
		####################################
		# 記錄 parsing 中目前所在的 tags 的層級
		####################################
		self.currentLevel = []
		self.lb = ''
		self.lb2 = ''
	
	###########################
	# 3 expat handler functions
	###########################
	def start_element(self, name, attrs):
		'''
		name = tage name
		attrs = {attr1:value1, attr2:value2, ...}
		'''
#		print 'Start element:', name, attrs
		
		# 記錄 self.currentLevel
		self.currentLevel.append(name)
#		print self.currentLevel
		
		# 處理 tags 並記錄 self.tags
		# 1. <lb n="0001a01" ed="T"/> 不記錄在 self.tags 中
		if name == 'lb':
			if len(attrs['n']) == 7: tmp = self.lb+'_p'+attrs['n']	# 標準的 lb 頁編號
			else: tmp = self.lb+'p'+attrs['n']						# 超過七碼的頁編號
			self.lb2 = tmp											# 記錄 current lb
			self.fwl.write( pack('17sI', str(tmp), self.offset) )	# 記錄每個行號及對應的起始 offset
#			print tmp, self.offset
#			raw_input()
		# 2. <pb n="0001a" ed="T" id="T01.0001.0001a"/> 不記錄在 self.tags 中
		elif name == 'pb':
			tmp = attrs['id'].split('.')
			self.lb = tmp[0]+'n'+tmp[1]								# self.lb = 'T01n0001'
		# 3. 除了 lb, pb 之外，其他的 tag 都記錄
		elif name not in self.tags:
			if name == 'body': self.flag = 'on'						# 寫入模式開啟
			
			# 寫入模式開啟 + 遇到要加換行符號的標記 + 前一個字元不是換行符號
			if self.flag == 'on' and \
				name in ('div', 'ab', 'byline', 'head') and \
				self.pre != '\n':
				self.w = '\n'
				self.f_tmp.write(self.w)
				self.fwf.write(self.w)
				self.offset += 4
				self.pre = '\n'
				
#				print 0, self.currentLevel, repr(self.w), self.w, self.offset
#				raw_input()
			
			self.tags[name] = {}
			for k in attrs.keys():
				if k not in self.tags[name]: self.tags[name][k] = [attrs[k]]
		else:
			for k in attrs.keys():
				if k not in self.tags[name]: self.tags[name][k] = [attrs[k]]
				else: self.tags[name][k].append(attrs[k])
#		raw_input()

	def end_element(self, name):
#		print 'End element:', name

		# 檢查tags
		if name != self.currentLevel[-1]:
			print self.lb
			raw_input()
		
		if name == 'body': self.flag = 'off'						# 寫入模式關閉
		
		# 寫入模式開啟 + 遇到要加換行符號的標記 + 前一個字元不是換行符號
		if self.flag == 'on' and \
			name in ('div', 'ab', 'byline', 'head') and \
			self.pre != '\n':
			self.w = '\n'
			self.f_tmp.write(self.w)
			self.fwf.write(self.w)
			self.offset += 4
			self.pre = '\n'
			
#			print 1, self.currentLevel, repr(self.w), self.w, self.offset
#			raw_input()

		# 結束清 current tag
		self.currentLevel.pop()
#		print self.currentLevel
#		raw_input()

	def char_data(self, data):
		'''
		self.p.Parse(text.encode('utf8'), 1) and unicode data out
		'''
#		print 'Character data:', data	#repr(data)
		
		if self.flag == 'on':		# after start tag 'body'
			extb_chk = 0
			for k in data:
				self.w = k
				if self.w == '\n' and self.pre == '\n': continue
			
				if ord(self.w) >= 0xD800 and ord(self.w) <= 0xDBFF:
					self.pre = self.w
					extb_chk += 1
					continue
				elif ord(self.w) >= 0xDC00 and ord(self.w) <= 0xDFFF:
					self.w = self.pre+self.w
					
					if extb_chk != 1:			# 遇到五碼 unicode 的字尾，字頭卻不對
						print self.lb2
						raw_input()
					
					extb_chk = extb_chk-1

#					print self.lb2, self.w
#					raw_input()

				self.f_tmp.write(self.w)
				self.fwf.write(self.w)
				self.offset += 4
				self.pre = self.w
			
#				print self.currentLevel,
#				print repr(self.w), self.w, self.offset
#				raw_input()
				

	def run(self, fL, in_code, out_code='utf32', pun=0):
		'''
		合併原始文件群，輸出正反兩全文檔案（純文字＋換行）。
		記錄所有 tage 開始與結束的 offset
		texts = list of files
		in_code = coding of input files
		out_code = coding of the main file
		pun = 0 keep punctuations, else erase punctuations.
		'''
		texts = []
		for fs in fL:
			l = getFiles(fs)
			texts.extend(l)
		texts.sort()
		print 'total %d files' % len(texts)
		
		self.fwf = codecs.open(self.location+'/Text_f', 'w', out_code)	#純文字檔
		self.fwl = open(self.location+'/Text_f_lb', 'wb')				#行號索引 lb
		if os.path.exists(self.location+'/bktmpf'):
			os.system('rm '+self.location+'/bktmpf/*.*')				#for linux OS only
			os.removedirs(self.location+'/bktmpf')
		os.mkdir( self.location+'/bktmpf' )								#反向檔暫存區

		# 因為用 codecs 開檔（主文字檔），所以有 BOM，一開始就要加一個單位的 offset
		# 因為內定用 utf32 寫檔，所以一個單位的 offset = 4
		# 如果用 utf16 寫檔，一個單位的 offset = 2
		# 如果用其他如 long, int 等寫檔，offset 長度亦需跟著改
		# 不管長度怎麼改（跟著檔案編碼），offset 長度必須固定，所以 utf8 不適用
		self.offset = 4
		
		#parse 每個檔案，文字累加存檔
		fct = 0
		for k in texts:
			fct += 1
			if fct%100 == 0: print '\r', fct, '/', len(texts), 'parsed.',
			
			bkn = os.path.split(k)
			self.f_tmp = codecs.open(self.location+'/bktmpf/'+bkn[1], 'w', out_code)		#全文暫存，給反向檔 reverse()
			
			self.w = '\n'							#宣告正要輸出的字元
			self.f_tmp.write(self.w)
			self.fwf.write(self.w)
			self.offset += 4
			self.pre = '\n'							#記錄正要處理字元的前一個（已寫出）字元
			
#			print 's', self.w, self.offset
#			raw_input()
		
			f = codecs.open(k, 'r', in_code)
			l = f.read()
			l = l.replace('\n', '')
			l = l.replace('\r', '')
			l = l.replace('\t', '')
			f.close()
			
			if pun != 0: l = tackoutPunctuation(l)
			self.p.Parse(l.encode('utf8'), 1)
			
			self.w = '\n'
			self.f_tmp.write(self.w)				#每個檔案頭尾都個加一個換行符號
			self.fwf.write(self.w)
			self.offset += 4
			self.pre = '\n'
			
#			print 'e', self.w, self.offset
#			raw_input()

			self.f_tmp.close()
		print fct, '/', len(texts), 'parsed.'
		
		self.fwf.close()
		self.fwl.close()
		
		f = open(self.location+'/cbeta_tags.pickle', 'wb')
		cPickle.dump(self.tags, f)
		
		print 'The foward fulltext file, Text_f, created!'
		print 'Creating backword fulltext ...'
		print self.__getBackwardFulltext__(self.location+'/bktmpf', 'Text_b', out_code)

		print 'Updating all subindex ...'
		print self.__completeLBIndex__(self.location+'/Text_f_lb', self.offset, 'sub_lb')
#		print self.__completeLBIndex__(self.location+'/Text_f_lb2', self.offset, 'sub_lb_sutra')

		#回傳 ( 正檔名, 反檔名, 檔案大小（offset 大小） ) 
		return self.location+'/Text_f', self.location+'/Text_b', self.offset

	
	def __modBackwardExtB__(self, L):
		'''
		檢查反過來的字串陣列，被分開的五碼以上的 unicode 合成一個，另一個為空。
		[u'\u6c0d', u'\udb82', u'\ude61', ...]
		=> [u'\u6c0d', u'\udb82'+u'\ude61', u'\ude61'-u'\ude61',...]
		=> [u'\u6c0d', u'\U000f0a61', u'', ...]
		'''
		c = 0
		while c < len(L):
			if ord(L[c]) >= 0xD800 and ord(L[c]) <= 0xDBFF:
				L[c] = L[c]+L[c+1]
			elif ord(L[c]) >= 0xDC00 and ord(L[c]) <= 0xDFFF:
				L[c] = ''
			c += 1
		return L
	

	def __getBackwardFulltext__(self, folder, fn, out_code):
		'''
		合併所有暫存反向檔
		folder = 反向檔暫存資料夾
		fn = 產生新檔案的名稱
		'''
		L = getFiles(folder)
		L.sort()
		L.reverse()
#		for k in L:
#			print k
		
		fwb = codecs.open(self.location+'/'+fn, 'w', out_code)	#反向檔
		for k in L:
			f_tmp = codecs.open(k, 'r', out_code)
			l_tmp = f_tmp.read()
			f_tmp.close()
			os.remove(k)
			
			tmp_bk = list( l_tmp )						#檔案字串轉陣列
			tmp_bk = self.__modBackwardExtB__(tmp_bk)	#處理陣列中被分開的五碼的 unicode
			tmp_bk.reverse()							#reverse 陣列
			tmp_bk = ''.join(tmp_bk)					#合併陣列為字串
			fwb.write( tmp_bk )

		fwb.close()
		os.rmdir(folder)
		return 'The backward fulltext file, %s, created!' % fn
		
		
	def __completeLBIndex__( self, FWsubindex, totalofst, fn ):
		'''
		用正向檔行號 subindex 算反向的行號位置
		產生完整行號索引檔
		FWsubindex = 正向檔行號索引檔
		totalofst = 正向檔總 offset 值
		fn = 產生新檔案的名稱
		'''
		flb = open(self.location+'/'+fn, 'wb')
		f = open(FWsubindex, 'rb')
		while f.tell() < os.stat( FWsubindex )[6]:
			tmplb = unpack( '17sI', f.read( calcsize('17sI') ) )
			bkofst = totalofst - tmplb[1]
			flb.write( pack('17sII', tmplb[0], tmplb[1], bkofst) )
		f.close()
		flb.close()
		os.remove(FWsubindex)
		return 'subindex %s ok.' % fn


	def __completeRangeIndex__( self, FWsubindex, totalofst, fn ):
		'''
		用正向檔行號 subindex 算反向的行號位置
		產生完整行號索引檔
		FWsubindex = 正向檔行號索引檔
		totalofst = 正向檔總 offset 值
		fn = 產生新檔案的名稱
		
		* 單純記錄範圍的如 lg, dharani 一致為正反檔各兩個 offset，可用同一 def 處理。
		'''
		flb = open(self.location+'/'+fn, 'wb')
		f = open(FWsubindex, 'rb')
		while f.tell() < os.stat( FWsubindex )[6]:
			tmplb = unpack( 'II', f.read( calcsize('II') ) )
			L = [tmplb[0], tmplb[1]]
			L.append( totalofst - tmplb[0] )
			L.append( totalofst - tmplb[1] )
			flb.write( pack('IIII', L[0], L[1], L[2], L[3]) )
		f.close()
		flb.close()
		os.remove(FWsubindex)
		return 'subindex %s ok.' % fn


def readLBpack(ff, fb, fn):
	'''
	給正反檔及行號檔
	測試行號索引是否正確
	'''
	ff = open(ff, 'rb')
	fb = open(fb, 'rb')
	f = open(fn, 'rb')
	i = 0
	while f.tell() < os.stat( fn )[6]:
		i += 1
		tmp = unpack( "17sII", f.read(28) )
		if tmp[0] == 'T57n2209_p0652a02' or tmp[0] == 'T46n1915_p0470a13':
		
			ff.seek(tmp[1]-2)
			n1 = ff.read(6).decode('utf16')
			fb.seek(tmp[2]-2)
			n2 = fb.read(6).decode('utf16')
			print i, tmp[0]
			print n1.replace('\n', u"\u204B "), tmp[1]
			print n2.replace('\n', u"\u204B "), tmp[2]
			raw_input()
	f.close()
	fb.close()
	ff.close()


if __name__ == "__main__":
	
#	print CBETAParser.__doc__
#	print CBETAParser.getSuffixArray.__doc__
#	print CBETAParser.doSearch.__doc__

#	測試正反檔及行號索引
#	readLBpack('./SuffixArray/cbetat2/Text_f','./SuffixArray/cbetat2/Text_b','./SuffixArray/cbetat2/Text_lb')
#	raw_input()

#	建正反擋及副索引（行號、缺字、版本）
	sourcefolders = ['../cnlstk_cbeta_test/corpus']
#	sourcefolders = ['../../../Dropbox/cbeta-simple-xml/output/T']
	ifolder = '../cnlstk_cbeta_test/index'
	
#	parse dataset create 2 main files and sub offset files.
	Ts = time()
	obj = CBETAParser(ifolder)			#ifolder: index 存放的資料夾
	n = obj.run(sourcefolders, 'utf8', 'utf32', 0)
	print n								#回傳 ( 正檔名, 反檔名, 檔案大小（offset 大小）, 行號索引檔名, 正向 g, anchor 索引檔名 )  
	Te = time()
	print strftime('%H:%M:%S', gmtime(Te-Ts))
		
	'''
#	建正反檔的 Suffix Array
		Tsa1 = time()
#		n = ('./SuffixArray/d054_nopun/Text_f', './SuffixArray/d054_nopun/Text_b')
	
		SA = SATools(n[1], 'index')
		SA.index(500000)
		indexSA(n[0], 1000000)
	
		Tsa2 = time()
		print 296, strftime('%H:%M:%S', gmtime(Tsa2-Tsa1))
	'''
	