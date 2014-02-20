#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
Updated by TRuEmInG (2011 spring) at NTU ESOE for CNLSTK
"""

import os, re
from struct import *
from time import time, strftime, gmtime

import CBTextParser, GenTextParser
from SuffixArray import *
from utility import *


### Index Class ###
class Index:
	'''
	build index
	'''
	def __init__(self):
		pass
	
	def runCorpus(self, orgfolders, org_code, newfolder, new_code, opt=0, sub='off'):
		'''
		orgfolders: 檔案來源資料夾陣列
		newfolder: 新檔案儲存位置
		org_code: 原始檔案編碼
		new_code: 新檔案編碼
		opt: 改變索引距離
		'''
		Ts = time()
		rst = GenTextParser.preparseCorpus(orgfolders, org_code, newfolder, new_code)
#		rst = ( 正檔名, 反檔名, 檔案大小（offset 大小）, 行號索引檔名 )
		if rst == 1:
			return
		Tm = time()
		print 'Texts parsed,', strftime('%H:%M:%S', gmtime(Tm-Ts))
		
		#想自訂索引距離者用 opt
		if opt != 0:
			print 'created suffix array with length:', opt
			rst[-1] = opt
		
		for k in rst[:2]:
			self.makeSuffixArray(k, new_code, rst[-1])
		Tn = time()
		print 'Suffix Arraies created,', strftime('%H:%M:%S', gmtime(Tn-Tm))
		
		# 耗費資源較大可另外 call makeNextWordIndex() 執行
		if sub == 'on':
			gram = (1,2,3,4)	#依需要修改
			ext = 2				#依需要修改
			self.makeNextWordIndex(rst[0], 'sch', rst[-1], new_code, rst[0]+'_SA', gram, ext)
			self.makeNextWordIndex(rst[1], 'schbk', rst[-1], new_code, rst[1]+'_SA', gram, ext)
			Te = time()
			print 'Next index created,', strftime('%H:%M:%S', gmtime(Te-Tn))
		
		print 'Down!'
		
	def runCBETA(self, L, ifolder, opt=0, pun=0, next=''):
		'''
		L: 所有要建索引檔案的陣列（L 中所有檔案的編碼須一致）
		ifolder: 新正反檔案存放的資料夾
		opt: 換行符號是否要建索引（內定不建，但抽詞用的索引需建。）
		pun: 0 保留標點； 1 去標點
		next: [延伸長度, 建索引頻率下限, [n-gram 陣列] ] ex.( 5,20,(1,2,3,4) )
		'''
		Ts = time()
		n = self.parseCBETA(L, ifolder, pun)
		Tm = time()
		print 'CBETA texts parsed,', strftime('%H:%M:%S', gmtime(Tm-Ts))
		
		for k in n[:2]: self.makeSuffixArray(k, 'utf32', 4, opt)
#		Text_f_SA, Text_b_SA
		Tn = time()
		print 'Suffix Arraies created,', strftime('%H:%M:%S', gmtime(Tn-Tm))
		
		if next != '':
			#gram = (1,2,3,4)
			#ext = 3
			#limit = 1000
			ext = next[0]
			limit = next[1]
			gram = next[2]
			self.makeNextWordIndex(n[0], 'sch', 4, 'utf32', n[0]+'_SA', gram, ext, limit)
			self.makeNextWordIndex(n[1], 'schbk', 4, 'utf32', n[1]+'_SA', gram, ext, limit)
			Te = time()
			print 'Next index created,', strftime('%H:%M:%S', gmtime(Te-Tn))
		print 'CBETA OK!'

	def parseCBETA(self, src, save_pth, pun=0):
		obj = CBTextParser.TextParser(save_pth)
		rst = obj.run(src, 'utf8', pun)
#		path = ifolder+'/'
#		n = ( path+'Text_f', path+'Text_b' )
		return rst
	
	def makeSuffixArray(self, fn, coding, size, opt, cache=1000000):
		'''
		fn: 欲建 suffix array 的檔案
		coding: fn 的檔案編碼（'ascii', 'utf16', 'utf32'）
		size: suffix array 的索引長度（'ascii':any, 'utf16':2, 'utf32':4）
		opt: 換行符號是否建索引（0:否；1:是）
		cache: 建索引時每次排序的 tmp 容量（內定每一百萬個字排序一次）
		'''
		SA = SATools(fn, 'index', size, coding)
		SA.index(opt, cache)
		print 'The Suffix Array of %s has been made!' % fn
		return

	def makeNextWordIndex(self, fn, opt, size, coding, fsa, gram, ext, freq=1000):
		'''
		fn: Text_f
		opt: sch
		size: 4
		coding: utf32
		fsa: Text_f_SA
		gram: (1,2,3,4)
		ext: 5
		'''
		Nobj = SATools(fn, opt, size, coding, fsa)
#		測試用，範圍縮小
#		gram = (1,2,3)
#		ext = 3
#		Nobj.innext(gram, ext, 50)	#freq 超過 50 就建，內定是 1000，見 innext() 
		Nobj.innext(gram, ext, freq)
		return
		
	def makeLongOffsetList(self):
		pass


### Search Class ###
class Search:
	'''
	search functions
	'''
	def __init__(self, path):
		if path[-1] != '/':
			path += '/'
		self.path = path
		
		#取得主檔的編碼和索引長度
		f = open(path+'encode', 'r')
		l = f.read()
		f.close()
		code = l.split(',')
		self.calen = int(code[1])

		#取得 lb index 檔名
		lb = ''
		L = os.listdir(path)
		if 'sub_lb' in L:
			lb = path+'sub_lb'

		#檢查並取得 offset list index 資訊
		oL = []
		chkp = 0
		for k in L:
			if re.match(r'ofst\-\d+$', k):
				tmp = k.split('-')
				oL = [ path+k, int(tmp[1]) ]
				self.ofstlimit = int(tmp[1])	#多少 freq. 以上的字串才有 ofst index
			elif k == 'Text_f': chkp = os.stat(path+k)[6]
		if oL == []: self.ofstlimit = chkp
		
		#檢查並取得 next index 資訊
		nLf = []
		nLb = []				#建 obj 用
#		self.ntlimit_f = 		#如何設計以達到有或沒有索引的最佳效果（設計中...)
#		self.ntlimit_b = 
		#資料夾名稱所含資訊： f-5-1_2_3_4-20 (正反向-extlen-n_gram-freq.)
		if os.path.exists(path+'next'):
			L = os.listdir(path+'next')
			for k in L:
				if os.path.isdir(path+'next/'+k):
					tmp = k.split('-')
					if tmp[0] == 'b':
						nLb.append(path+'next/'+k)
						for ks in range(int(tmp[1])):
							nLb.append( path+'next/b_ext-'+str(ks+1) )
					else:
						nLf.append(path+'next/'+k)
						for ks in range(int(tmp[1])):
							nLf.append( path+'next/f_ext-'+str(ks+1) )
		
#		print oL, self.ofstlimit
#		print nLf
#		print nLb
#		raw_input()
		
		self.Tobj_f = SATools( path+'Text_f', 'sch', self.calen, code[0], path+'Text_f_SA', lb, nLf, oL )
		self.Tobj_b = SATools( path+'Text_b', 'schbk', self.calen, code[0], path+'Text_b_SA', lb, nLb, oL )
		
		#cache prepare
		self.saveCT = 5000			#大於等於多少筆以上的資料暫存到以下的 Pool
									#如果 cache 大小大於 ofst sub-index 大小，直接用 sub-index 即可。
		if self.saveCT > self.ofstlimit: self.saveCT = self.ofstlimit
		
		#以下三暫存沒有正反向問題
		self.Pool = {}				#offset list sort by offset.
		self.Poolsutra = {}			#字串出現過經文及其次數的 dic
		self.Poolindex = ['']*150	#暫存字串索引及數量
		
		'''
		secSatL: 計算字串出現在各單元（檔案）中的次數，只需正向檔中的 lb 範圍。 getTotalSutraInf()
		secSatD: 顯示整體所有單元（檔案）的字數統計。 getSectionSat(), SearchCBETA.getSutraSat()
		secSatCBD: SearchCBETA 時經號的 offset 範圍資訊。 SearchCBETA.getSecOfstRange()
		'''
		Satn = self.cacheSectionInf()
		self.secSatL = Satn[0]				#[(sec_name, start_ofst, end_ofst), ...]
		self.secSatD = Satn[1]				#{'sec_name':chars_ct, ...}
		self.secSutraD = Satn[2]			#{'sec_name':[(fwd_ofst_start, end),(bwd_ofst_start, end)], ...} SearchCBETA getSecOfstRange() 經號字串時要用到

		#offset list cache for subConcordance()
#		self.saveOT = 20
#		self.ofstcache_f = {}	#key: string, value: (offset, position) list sort by offset
#		self.ofstcache_b = {}
		

	# ＃＃＃＃＃＃＃＃	#
	# 取得檢索字串數量	#
	# ＃＃＃＃＃＃＃＃	#
	
	def getFreq(self, term):
		return self.Tobj_f.doSearch(term)[0]


	# ＃＃＃＃＃＃＃＃＃＃＃＃＃	＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃	#
	# 取得字串分布於檔案的資訊（+offset caches 單純數量統計沒有正向反向差別）	#
	# ＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃	#

	def getSectionSat(self):
		'''
		回傳所有 section 名稱和 chars 總數的 Dic {'sec_name':char_ct,...}
		'''
		return self.secSatD
	
	def getStrDistr(self, term):
		'''
		取得字串出現過的經文資訊
		回傳 {經號:次數}
		'''
		n = self.Tobj_f.doSearch(term)
		if n[0] == 0:						#無此字串亦無經號資訊
			n_sutra = {}
		elif n[0] < self.saveCT:			#5000 以下直接取得
			L = self.Tobj_f.getOffsetList(n[1], n[0])
			n_sutra = self.getTotalSutrasInf(L)
		elif term not in self.Poolindex:	#5000 以上無索引即建立
			n2 = self.prepareTermPool(term)
			n_sutra = self.Poolsutra[term]
		else:
			n_sutra = self.Poolsutra[term]	#如果已有取得後改變該記錄的排序位置
			del self.Poolindex[self.Poolindex.index(term)]
			self.Poolindex.insert(0, term)
		return n_sutra
		
	def prepareTermPool(self, term):
		'''
		取得字串數量的同時，進一步建該字串的 pool 備用
		回傳（該字的字頻，該字出現過的經文數）
		* 字頻 5000 以上者才存
		'''
#		T1 = time()
		if term not in self.Poolindex:		#poolindex 裡沒有就建一個在 poolindex 最前面並拿掉最後一個
			n = self.Tobj_f.doSearch(term)
			if n[0] < self.saveCT:	#字頻 < 5000 不存
				return (n[0], -1)	#回傳（字頻，-1）
				
			self.Poolindex.insert(0, term)
			popkey = self.Poolindex.pop()
			if popkey != '':				#表示 poolindex 滿了，最後一個內容不是內定的空值
				del self.Pool[popkey]		#這時 pool 裡面才會有這個 key 可刪
				del self.Poolsutra[popkey]
			#丟進 pool 的 dic 內容： key 是辭彙 value 是 offset 升冪陣列 [2, 408, 1766, ...]
			if n[0] >= self.ofstlimit: self.Pool[term] = self.Tobj_f.getOffsetList2(term)
			else: self.Pool[term] = self.Tobj_f.getOffsetList(n[1], n[0])
			#丟進 poolsutra 的 dic 內容： key 是辭彙 value 是 {'T01n0001':5, '經號':幾次, ...}
			self.Poolsutra[term] = self.getTotalSutrasInf(self.Pool[term])
		else:
			del self.Poolindex[self.Poolindex.index(term)]
			self.Poolindex.insert(0, term)
#		T2 = time()
#		print n, strftime('%H:%M:%S', gmtime(T2-T1))
		return len(self.Pool[term]), len(self.Poolsutra[term])

	def getTotalSutrasInf(self, Lofst):
		'''
		傳入字串 ofst list
		回傳字串出現過的經文資訊 dic {'經號':次數, ...}
		* 超過 5000 筆的 offset, 此結果將存入 Poolsutra. Poolsutra[u'字串'] = {'經號':次數, ...}
		'''
		sutraL = {}
		Lsec = self.secSatL
		c = 0		#offset list 計數器
		i = 0		#section list 計數器
		tmp = 0		#字串計數器
		while c < len(Lofst):			#offset list
			if Lofst[c] < Lsec[i][2]:	#和 section list 比 [(name, start_ofst, end_ofst)]
				tmp += 1
				c += 1
			else:
				if tmp != 0:
					sutraL[Lsec[i][0]] = tmp
				tmp = 0
				i += 1
		sutraL[Lsec[i][0]] = tmp
		return sutraL

	def chkPool(self, term):
		if term not in self.Poolindex:
			return '%s no this term in pool. Pool: %d, Poolsutra: %d.' % (term, len(self.Pool), len(self.Poolsutra))
		else:
			return '%s first offset in Pool: %d. no. of sutras in Poolsutra: %d.\n total Pool: %d, Poolsutra: %d.' % (term, self.Pool[term][0], len(self.Poolsutra[term]), len(self.Pool), len(self.Poolsutra) )
	
	def cacheSectionInf(self):
		'''
		cache 所有 section 的名稱和 chars 數量的陣列 
		{'sec_name':char_ct,...}
		CBETA 的 section 是 lb 不是檔名，非常多，因此 SearchCBETA overwrite 這個 def
		'''
		L = self.Tobj_f.getSectionInf()
		D = {}
		for k in L:
			ct = (k[2]-k[1])/self.calen
			D[k[0]] = ct
		return L, D, []
		

	# ＃＃＃＃＃＃＃＃	#
	# 取得段落文字工具	#
	# ＃＃＃＃＃＃＃＃	#
	
	def getSecOfstRange(self, sec, opt):
		'''
		取得限定範圍的開始結束 offsets
		sec = ['section_name1', 'section_name2', ...] for subConcordance()
		** sec 可從 getSectionSat() 取得
		'''
		secs = []
		sec.sort()
		if opt == 'bwd':
			sec.reverse()					#section 對文本 offset 的大小順序顛倒
			for k in sec:
				r = self.Tobj_b.getRange(k)
				if r == (0,0): continue
				secs.append( (r[1], r[0]) )	#回傳值範圍大小和正向的相反
		else:
			for k in sec:
				r = self.Tobj_f.getRange(k)
				if r == (0,0): continue
				secs.append( (r[0],r[1]) )
		return secs
	
	def getFullTexts(self, fn):
		'''
		取得整篇檔案字串
		'''
		n = self.Tobj_f.getRange(fn)
		return self.Tobj_f.getRangeWords( n[0], n[1] )
		
	def getFullstxeT(self, fn):
		'''
		同上反向字串
		'''
		n = self.Tobj_b.getRange(fn)
		return self.Tobj_b.getRangeWords( n[1], n[0] )
		
		
	# ＃＃＃＃＃＃＃＃＃＃	#
	# 取得文字前後排序工具	#
	# ＃＃＃＃＃＃＃＃＃＃	#

	def getConcordance(self, term, addw=10):
		'''
		輸入 字串、結果的前後長度（內定前後各 10 個字）
		回傳字串與所在檔案名
		'''
		n = self.Tobj_f.doSearch(term)
		if n[0] == 0:
			return [('No records', '')]
		return self.Tobj_f.getTexts(n[1], n[0], addw, countStrLen(term)+addw, 1)
		
	def getConcordanceBK(self, term, addw=10):
		n = self.Tobj_b.doSearch(term)
		if n[0] == 0:
			return [('No records', '')]
		return self.Tobj_b.getTexts(n[1], n[0], addw, countStrLen(term)+addw, 1)
	
	def subConcordance(self, term, sec, addw=10):
		'''
		term: string for search
		sec: ['sec_name1', 'sec_name2', ...]
		'''
		n = self.Tobj_f.doSearch(term)							#確認檢索結果不為 0
		if n[0] == 0: return [('No records', '')]
		secs = self.getSecOfstRange(sec, 'fwd')					#取得範圍的開始結束 offsets
		if n[0] >= self.ofstlimit: ofsts = self.Tobj_f.getOffsetList2(term, 1)
		else: ofsts = self.Tobj_f.getOffsetList(n[1], n[0], 1)	#取得檢索結果的 (offset,postion) 陣列
		L = self.filterOffset(ofsts, secs)						#篩出所需結果
		rst = []
		for k in L:
			rst.append( self.Tobj_f.getText(k[0], addw, countStrLen(term)+addw, 1) )
		return rst

	def subConcordanceBK(self, term, sec, addw=10):
		n = self.Tobj_b.doSearch(term)							#確認檢索結果不為 0
		if n[0] == 0:
			return [('No records', '')]
		secs = self.getSecOfstRange(sec, 'bwd')					#取得範圍的開始結束 offsets
		if n[0] >= self.ofstlimit: ofsts = self.Tobj_b.getOffsetList2(term, 1)
		else: ofsts = self.Tobj_b.getOffsetList(n[1], n[0], 1)	#取得檢索結果的 (offset,postion) 陣列
		L = self.filterOffset(ofsts, secs)						#篩出所需結果
		rst = []
		for k in L:
			rst.append( self.Tobj_b.getText(k[0], addw, countStrLen(term)+addw, 1) )
		return rst
	

	# ＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃#	#
	# Filters Tools (not call any def() from Suffixarray )	#
	# ＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃#	#
	
	def filterOffset(self, ofstL, secs, sortopt=0):
		'''
		傳入 (offsets,position) 陣列及檢索範圍 (offset,offset) 的陣列
		ofstL: [(ofset,p), ...]
		secs: [(2, 18), (36, 104), ...]
		sort = 0 回傳值照語用（offset）排序
		sort = 1 回傳值照位置（position）排序
		回傳在 secs 範圍內的 [(offsets, position), ...] 陣列
		'''
		sc = oc = 0				# secs 與 ofstL 的計數器
		endr = secs[-1][1]		# secs 最後的範圍
		L = []
		while oc < len(ofstL):					# ofstL 跑到結束
			if ofstL[oc][0] > endr:				#	若到了最後範圍直接跳出
				break				
			if ofstL[oc][0] < secs[sc][0]:		#	尚未到目前 secs 的範圍內
				oc += 1							#		ofstL 推進一個位置
			elif ofstL[oc][0] > secs[sc][1]:	#	超出目前 secs 範圍時
				sc += 1							#		secs 推進一個位置（ofstL 位置不變）
			elif ofstL[oc][0] >= secs[sc][0]:	#	落在目前 secs 範圍內
				L.append(ofstL[oc])				#		留下這筆記錄
				oc += 1							#		ofstL 推進一個位置
		if sortopt == 0:
			L.sort(lambda x,y: cmp(x[1],y[1]))
		return L


	# ＃＃＃＃＃＃＃＃	#
	# 進階類檢索工具	#
	# ＃＃＃＃＃＃＃＃	#
	
	def getNextWords(self, term, extlen=1):
		'''
		term: string
		extlen: search for next n chars
		return: [('next chars', freq), ...]
		'''
		n = self.Tobj_f.doSearch(term)
		if n[0] == 0: return 'No Record'
		gram = countStrLen(term)

		try: fn = str( self.Tobj_f.NL[extlen-1][term] )
		except: return self.Tobj_f.getNextWords(n[1], n[0], gram, extlen)
		
		lastSAspot = n[1]+n[0]*calcsize('I')
		return self.Tobj_f.getNextWords2(fn, gram, lastSAspot, extlen)
					
	def getPreWords(self, term, extlen=1):
		n = self.Tobj_b.doSearch(term)
		if n[0] == 0: return 'No Record'
		gram = countStrLen(term)
		
		try: fn = str( self.Tobj_b.NL[extlen-1][term] )
		except: return self.Tobj_b.getNextWords(n[1], n[0], gram, extlen)
		
		lastSAspot = n[1]+n[0]*calcsize('I')
		return self.Tobj_b.getNextWords2(fn, gram, lastSAspot, extlen)

	def getStrOffsetDistr(self, term1, term2, limit='all'):
		return self.Tobj_f.getDistances(term1, term2, limit)


	# ＃＃＃＃＃＃	#
	# 統計類工具	#
	# ＃＃＃＃＃＃	#
	
	def getNextInf(self, list, opt=''):
		c1 = len(list)
		c2 = c3 = c4 = c5 = 0
		for k in list:
			if self.chkChinese(k[0]) == 0:	#是中文
				if k[1] > c2: c2 = k[1]
			else:
				try:
					if k[1] > c3: c3 = k[1]
					c4 += 1
					c5 += k[1]
				except:					#### 有問題 ####
					print self.convertStr2List(opt, 1), 'get wrong!'
					return 0, 0, 0, 0, 0
		return c1, c2, c3, c4, c5
		
	def getNextWordInf(self, term):
		'''
		return information bellow:
		1. No. of next distinct characters
		2. Highest frequency of the next distinct character (Chinses)
		3. Highest frequency of the next distinct character (non-Chinses)
		4. No. of next distinct break points (non-Chinese characters) 
		5. Total No. of break points
		'''
		return self.getNextInf( self.getNextWords(term, 1), term )

	def getPreWordInf(self, term): return self.getNextInf( self.getPreWords(term, 1) )
	
	
	# ＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃	#
	#  取得純字串工具（ML data preparing）	#
	# ＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃＃	#
	'''
	以下工具為取得較底層的資訊，因此均須明確指呼叫的是正向檔或反向檔。
	'''
	def binarySch(self, term, opt):
		'''
		return (frequency, first_SAspot)
		opt: 'f' or 'b'
		'''
		if opt == 'f': return self.Tobj_f.doSearch(term)
		elif opt == 'b': return self.Tobj_b.doSearch(term)
		else: return 'opt="f" or opt="b"'
	
	def getOffsetList(self, term, opt, opt2=0):
		'''
		回傳 offset list
		opt: 'f' or 'b'
		opt2: offset list or (offset,position) list
		'''
		if opt == 'f': objtmp = self.Tobj_f
		elif opt == 'b': objtmp = self.Tobj_b
		else: return 'opt="f" or opt="b"'
		n = objtmp.doSearch(term)
		if n[0] == 0: ofsts = []		#確認檢索結果不為 0
		elif n[0] >= self.ofstlimit: ofsts = objtmp.getOffsetList2(term, opt2)
		else: ofsts = objtmp.getOffsetList(n[1], n[0], opt2)
		return ofsts
		
	def getOffsetPositionList(self, term, opt):
		'''也可直接用 getOffsetList(term, opt, 0)'''
		return self.getOffsetList(term, opt, 1)
	
	def getSequence(self, ofst, bw, aw, opt):
		'''
		輸入 offset, 前後欲取自串長度, 正向或反向索引
		回傳「單筆」：字串
		opt = 'f' or 'b'
		u\u204B' = ⁋
		'''
		if opt == 'f': return self.Tobj_f.getText(ofst, bw, aw)
		elif opt == 'b': return self.Tobj_b.getText(ofst, bw, aw)
		else: return 'opt="f" or opt="b"'
	
	
	# ＃＃＃＃＃＃	#
	#  布林合併	#
	# ＃＃＃＃＃＃	#
	
	
	
	# ＃＃＃＃＃＃	#
	#  其他工具	#
	# ＃＃＃＃＃＃	#
	def countStrLen(self, strg):
		return countStrLen(strg)
	
	def convertStr2List(self, strg, opt=0):
		'''
		將字串轉為以單字為內容的陣列（ Ext.B 以上的五碼 unicode 需要 ）
		opt = 0: 陣列內容為 unicode 字				ex. [u'我']
		opt = 1: 陣列內容為 unicode 16 進位編碼		ex. ['6211']
		'''
		return convertStr2List(strg, opt)
	
	def chkChinese(self, n):
		'''
		unicode 中文字碼的範圍：
			[0x2E84, ⺄; 0x3021, 〡; 0x3026, 〦]
			[0x3100, 0x312F, 'Bopomofo']
			[0x3400, 0x4DBF, 'CJK Ideographs Ext.A']
			[0x4E00, 0x9FCF, 'Unified CJK Ideographs']
			[0xF900, 0xFAFF, 'CJK Compatibility Ideographs']
			[0xFE30, 0xFE4F, 'CJK Compatibility Forms']
			** [0xFF00, 0xFFEF, 'Halfwidth & Fullwidth Forms'] < jump over this area >
			[0x20000, 0x2A6DF, 'CJK Ideographs Ext.B']
			[0x2A700, 0x2B734, 'CJK Ideographs Ext.C']
		'''
		if (n >= u'\u3100' and n <= u'\uFE4F') or\
			(n >= u'\U00020000' and n <= u'\U0002A6DF') or\
			(n >= u'\U0002A700' and n <= u'\U0002B73F') or\
			n == u'\u2E84' or n == u'3021' or n == u'3026':
			return 0
		else: return 1
	
	
### Search Class for CBETA ###
class SearchCBETA(Search):
	'''
	[tool.py]
	暫存索引除了 offset list 外
	還應有 (offset, position) list
	
	[rpc_api.py]
	其他排序
		部類、時空、人物等對照表的使用（不透過 API 則使用者須自行準備 tables 再 mapping）
		與 filter 過後的 offsetList 對照後呈現的工作
	全文呈現
		再另建一個以品為單位的索引
		經 -> 品 -> 該品的所有行號
		再以各行號依序列出全文（正或反）
		可配合字典進行服務
	'''
	###		
	def cacheSectionInf(self):
		'''
		快取以經名為 section 的 cache (3000多經)
		overwrite tools.Search.cacheSectionInf()
		因為直接用 tools.Search.cacheSectionInf() 的話，是 lb 的資料不是經號的資料。
		'''
		fn = self.path+'sub_lb_sutra'
		f = open(fn, 'rb')
		flen = os.stat(fn)[6]
		
		Li = self.Tobj_f.getSectionInf(f, flen)
		D = {}
		for k in Li:
			ct = (k[2]-k[1])/self.calen
			D[k[0]] = ct
		
		D2 = {}
		Lb = self.Tobj_b.getSectionInf(f, flen)
		for c in range(len(Li)):
			if Li[c][0] != Lb[c][0]:
				print 'cacheSectionInf() wrang!, sub_lb_sutra problem.'
				raw_input()
			D2[Li[c][0]] = ( (Li[c][1], Li[c][2]), (Lb[c][2], Lb[c][1]) )
		return Li, D, D2
	
	def getSutraSat(self):
		'''
		Search 中 getSectionSat() 的功能
		回傳的是 3000 多筆經號的資訊
		沒有回傳所有 lb 的 def（太多了）
		'''
		return self.secSatD	

	def getSectionSat(self):
		return self.getSutraSat()


	###	
	def getSecOfstRange(self, sec, opt):
		'''
		在一般語料取得 OfstRange 是以檔名為單位（使用者切分 sub_lb 中最小的單位）
		在 CBETA 中有三種情況：
			"單一行號"： 本 def overwrite getSecOfstRange()（前面加了辨識）
			"單一經號"： __getSutraOfstRange( ['sec',...], opt )
			"開始行號-結束行號"： __getLBsOfstRange( ["sec_s-sec_e", ...], opt )
			** 未來是否會擴充以品分 **
		目前都只有 subConcordance() 會用到
		'''
		L = []
		sec.sort()
		if opt == 'bwd':
			sec.reverse()
		for k in sec:
			n = k.strip()
			if '-' in k:											#兩行號範圍
				tmp = self.__getLBsOfstRange(n, opt)
				if tmp != (0,0): L.append( tmp )
			elif re.match(r'[JTX]\d\dn.\d{3}.p\d{4}[abc]\d\d', n):	#行號
				#以下和原 getSecOfstRange() 不同的是以字串進字串出
				#原來是陣列進陣列出（因為狀況單純只有檔名）
				if opt == 'bwd':
					r = self.Tobj_b.getRange(n)
					if r != (0,0): L.append( (r[1], r[0]) )	#回傳值範圍大小和正向的相反
				else:
					r = self.Tobj_f.getRange(k)
					if r != (0,0): L.append( (r[0],r[1]) )
			elif re.match(r'[JTX]\d\dn.\d{3}.?', n):				#經號
				if n not in self.secSutraD: continue
				if opt == 'bwd':
					L.append( (self.secSutraD[n][1][0], self.secSutraD[n][1][1]) )
				else:
					L.append( (self.secSutraD[n][0][0], self.secSutraD[n][0][1]) )
		return L
		
	def __getLBsOfstRange(self, sec, opt):
		'''
		sec = "起始行號-結束行號"
		'''
		tmp = sec.split('-')
		s = tmp[0].strip()
		e = tmp[1].strip()
		if s >= e or not re.match(r'[JTX]\d\dn.\d{3}.p\d{4}[abc]\d\d', s) or\
			not re.match(r'[JTX]\d\dn.\d{3}.p\d{4}[abc]\d\d', e):
			return (0,0)
		L = []
		if opt == 'bwd':
			r1 = self.Tobj_b.getRange(s)
			r2 = self.Tobj_b.getRange(e)
			if r1 != (0,0) and r2 != (0,0): return r2[1], r1[0]		#回傳值範圍大小和正向的相反
		else:
			r1 = self.Tobj_f.getRange(s)
			r2 = self.Tobj_f.getRange(e)
			if r1 != (0,0) and r2 != (0,0): return r1[0], r2[1]


	###
	def getFullTexts(self, fn):
		'''
		fn: 行號、經號、行號範圍 其中一種的字串。
		Search 只有檔名（同行號），所以直接 call SATools.getRange()。
		overwrite 後 call SearchCBETA.getSecOfstRange()。
		'''
		sec = [fn]
		n = self.getSecOfstRange(sec, 'fwd')[0]
		return self.Tobj_f.getRangeWords( n[0], n[1] )
		
	def getFullstxeT(self, fn):
		sec = [fn]
		n = self.getSecOfstRange(sec, 'bwd')[0]
		return self.Tobj_b.getRangeWords( n[0], n[1] )

	
	###
	def printLbText(self):
		pass
		
	def getWebTIFLink(self, lb):
		lb = lb.strip()
		httph = 'http://dev.ddbc.edu.tw/~trueming/CBfax/%s_TIF/%s-g4/' % (lb[0], lb[:3])
		pg = int( lb.split('p')[1][:4] )
		i = 1
		range = ''
		while i < 2000:
			e = i+99
			if pg >= i and pg <= e:
				range = '%s-%s/' % ( ('00'+str(i))[-3:], str(e) )
				break
			i += 100
		if pg <= 1000:
			pg = ('000'+str(pg))[-3:]
		else:
			pg = str(pg)
		return '%s%s%s-%s.TIF' % (httph, range, lb[1:3], pg)
		
	def getGaijiImg(self, ):
		pass
		
	def chkChinese(self, n):
		'''
		CBETA 用到的中文字碼 unicode 範圍：
		除 unicode 現有中文區外，增加一個自定區：[0xF0000, 0xF270F, 'CB Gaiji']。
		'''
		if (n >= u'\u3100' and n <= u'\uFE4F') or\
			(n >= u'\U00020000' and n <= u'\U0002A6DF') or\
			(n >= u'\U0002A700' and n <= u'\U0002B73F') or\
			(n >= u'\U000F0000' and n <= u'\U000F270F') or\
			n == u'\u2E84' or n == u'3021' or n == u'3026':
			return 0
		else: return 1


if __name__=='__main__':
	obj = Index()
#	obj.runCBETA( ['xml_index_test'], 'cbeta_index2', 1, 1, (1,20,(1,2,3,4)) )
#	obj.runCBETA( ['sources/fahua_te'], 'indexes/cbeta_v10_packs/fahua_te', 1, 1, (1,500,(1,2,3,4)) )
#	obj.runCBETA( ['sources/huayan_te'], 'indexes/cbeta_v10_packs/huayan_te', 1, 1, (1,500,(1,2,3,4)) )
#	obj.runCorpus(['./sources/JinYong'], 'utf8', './indexes/jinyong_v01_pack', 'utf16')
	
	
	path = './cbeta_index2'
	path = './fahua_te'
#	path = 'indexes/cbeta_v10_packs/cbeta_JTX'
#	"""
	obj = SearchCBETA(path)
	strg = (u'沙', u'七祖')
	
	term = strg[0]
	print obj.binarySch(term, 'f')
#	rst = obj.getOffsetList(term, 'f')
#	print rst
#	print obj.getOffsetPositionList(term, 'f')
#	for k in rst:
#		print obj.getSequence(k, 5, 5, 'f')
	
	print obj.chkChinese(u'，')
#	"""
	
#	"""
	print obj.getFreq(strg[0])
	print 'con_f'
	rst = obj.getConcordance(strg[0])
	for k in rst:
		print k[0].replace('\n', u"\u204B "), k[1]
	"""
	print 'sub_f'
	rst = obj.subConcordance(strg[0], ['J15nB005','X01n0001'])
	for k in rst:
		print k[0].replace('\n', u"\u204B "), k[1]
	print 'sub_b'
	rst = obj.subConcordanceBK(strg[0], ['J15nB005','T01n0001'])
	for k in rst:
		print k[0].replace('\n', u"\u204B "), k[1]

	"""

#	print obj.getSectionSat()
#	print obj.getStrDistr(strg[0])
	
#	print obj.getSecOfstRange(['J15nB005','T01n0001'], 'bwd')
#	print obj.getSecOfstRange(['J15nB005','T01n0001','J15nB005_p0643a11','J15nB005_p0646a26-J15nB005_p0646a30'], 'bwd')
	
#	print obj.getFullTexts('J15nB005_p0646a26-J15nB005_p0646a30')
#	print obj.getFullstxeT('J15nB005_p0646a26-J15nB005_p0646a30')

#	print obj.getStrOffsetDistr(strg[0], strg[1])

#	print obj.getNextWords(strg[0])
#	print obj.getPreWords(strg[0])

	print obj.getNextWordInf(strg[0])
#	print obj.getPreWordInf(strg[0])
	
#	print obj.getWebTIFLink('T01n0001_p0003a17')

