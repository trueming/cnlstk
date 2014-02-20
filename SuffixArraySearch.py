#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2006 winter) at The Chung Hwa Institute of Buddhist Studies
Updated by TRuEmInG (2008 fall) at NTU ESOE
Updated by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
Updated by TRuEmInG (2011 spring) at NTU ESOE for CNLSTK, Web API
Updated by TRuEmInG (2013 winter) at NTU ESOE for CNLSTK, modify package structure
"""

"""
section 的統一輸入設計		id, name, time, time_id, place, place_id
"""

import os, re, sys, cPickle
from struct import *
from time import time, strftime, gmtime
from utility import *


class SA_Search:
	'''建立與檢索 Suffix Array 的 class'''
	
	def __init__( self, fname, opt, salen, coding, suffix='', lbindex='', next=[], ofst=[] ):
		'''
		[ fname ] = the main text file. 
		[ opt ] = 'index', 'sch', 'schbk'
		[ salen ] = Suffix Array index length
		[ coding ] = main text encode
		[ suffix ] = the Suffix Array of fname
		[ lbindex ] = section index of fname
		[ next ] = list of next indexes files (next[0]=index folder, next[1:]=ext dictionary indexes)
		[ ofst ] = list of freq. ofst indexes info. (folder, freq.)
		'''
		ntf = open(os.path.split(fname)[0]+'/encode', 'w')
		ntf.write(coding+','+str(salen))
		ntf.close()
		
		self.F = open( fname, 'rb' )			##開啟主文字檔##
		self.F_len = os.stat( fname )[6]		##主文字檔大小
		self.File_main = fname					##主要檔的檔名##
		self.opt = opt
		self.salen = salen						##檔案中索引距離的長度（與 self.coding 相應）
		self.coding = coding					##檔案編碼
		
		'''
		若有 BOM 在反向檔會影響 getRangWords()，要將其 offset 加回去。
		getBL(), getRange(), getSectionInf() 等若改成反向檔用算的不用目前的反向索引 BOM 將有影響
		'''
		bom = ['\xff\xfe', '\xfe\xff']			##檢查全文檔頭是否有 BOM
		if self.F.read(2) not in bom:
			self.bom = 'N'
		else:
			self.bom = 'Y'
		self.F.seek(0)
		
		if suffix != '':
			self.S = open( suffix, 'rb' )		##主要檔案的 Suffix Array##
			self.S_len = os.stat( suffix )[6]	##Suffix Array 的檔案大小##
			self.Suffix_A = suffix				##主要 Suffix Array 的檔名##
			if self.S_len > 1000000:				#1mb 大小以上的 Suffix Array 才建索引 cache
				self.cache_qt = 2048				#cache 陣列大小（最理想是改成和 self.S_len 長度動態對稱）
				self.cache_p = [0]*self.cache_qt	##紀錄 Suffix Array 位置的 cache##
				self.cache_w = ['']*self.cache_qt	##紀錄 self.cache_p 對應回 self.S 再對應回 self.F 的內容字串##
				self.__getCache( 0, self.S_len/calcsize('I'), 1 )

		if lbindex != '':
			self.cache_line = open( lbindex, 'rb' )
			self.cache_line_len = os.stat( lbindex )[6]
		
		self.nextPh = ''
		self.nextlimit = 0				#over this freq. 有 next index
		if next != []:
			if next[0][-1] != '/':
				next[0] += '/'
			self.nextPh = next[0]
			self.NL = []
			for k in next[1:]:
				f = open(k)
				self.NL.append( cPickle.load(f) )
				f.close()
		
		self.ofstPh = ''
		self.ofstlimit = self.F_len		#不可能有 frequency 大於檔案大小
		if ofst != []:
			if ofst[0][-1] != '/':
				ofst[0] += '/'
			self.ofstPh = ofst[0]
			self.ofstlimit = ofst[1]	#大於某個 frequency 就有獨立索引
		'''
		# ** self.nextlimit 可以不用 **
		# ** self.ofstlimit 用在 getDistances() 中辨識是否大於 **
		# ** getOffsetList2(), getNextWords2() 在開 sub 索引檔時辨識檔名因此沒用到 self.nextlimit & self.ofstlimit **
		'''

### Basic Utility ###
	def __getCache( self, i, j, c ):
		'''
		Create 2 cache lists for search.
		[ i ] = the start position
		[ j ] = the end position
		[ c ] = position of cache list
		'''
		if c < self.cache_qt:
			k = ( i+j )/2		##中間位置 ( k ) = 首尾位置 ( i, j ) 除以 2##
			self.cache_p[c] = k
			self.S.seek( k*calcsize('I') )
			ofst = unpack( 'I', self.S.read( calcsize('I') ) )[0]	##提出 self.S 實際值##
			w = self.__getWords( ofst, 32 )							##取出 self.F 32個字（使用者輸入的 cache 比對字串長度）##
			self.cache_w[c] = w
			
			self.__getCache( i, k, c*2 )
			self.__getCache( k, j, c*2+1)

	def __getWords( self, ofst, length ):
		'''
		輸入 offset + 要取的字串長度
		回傳 offset 開始向後（右）要取的長度字串
		'''
		self.F.seek( ofst )
		bytes = length * self.salen		#轉成 bytes 數
		return self.F.read(bytes).decode(self.coding)
		
	def __getsdroW( self, ofst, length ):
		'''
		輸入 offset + 要取的字串長度
		回傳 offset 向前（左）要取的長度字串
		'''
		nofst = ofst - length * self.salen
		bytes = length * self.salen		#轉成 bytes 數
		if nofst < 0:					#若檔首不足需求數
			nofst = 0
			bytes = ofst
		self.F.seek( nofst )
		return self.F.read(bytes).decode(self.coding)

### Display Utility ###
	def __backwardStr( self, strg ):
		'''
		Return a backward string of "strg", and its length
		回傳 字串及長度（ len(一個unicode五碼字) = 2 ）
		'''
		L = convertStr2List(strg)
		L.reverse()
		return (''.join(L), len(L))

	def getTexts(self, SAspot, ct, bw, aw, opt=0):
		'''
		輸入 Suffix Array position, 筆數、前後欲取自串長度
		回傳「多筆」：
			opt = 0 全文的陣列
			opt = 1 全文與行號資訊的陣列
		u\u204B' = ⁋
		'''
		L = []
		self.S.seek( SAspot )
		for k in range(ct):
			offset = unpack( 'I', self.S.read( calcsize('I') ) )[0]
			tmp = self.__getsdroW( offset, bw ) + self.__getWords( offset, aw )
			if self.opt == 'schbk':
				tmp = self.__backwardStr( tmp )[0]
			if opt == 1:
				L.append( (tmp, self.getLB(offset)) )
			else:
				L.append(tmp)
		return L
		
	def getText(self, offset, bw, aw, opt=0):
		'''
		輸入單筆 offset, 前後欲取自串長度
		回傳「單筆」：
			opt = 0 全文字串
			opt = 1 全文字串與行號資訊
		'''
		tmp = self.__getsdroW( offset, bw ) + self.__getWords( offset, aw )
		if self.opt == 'schbk':
			tmp = self.__backwardStr( tmp )[0]
		if opt == 1:
			return tmp, self.getLB(offset)
		else:
			return tmp
	
	def getLB(self, offset):
		'''
		輸入 offset, 回傳該 offset 所在檔案
		'''
		tps = ''
		i = 0
		j = p_end = self.cache_line_len/calcsize('17sII')
		while i <= j:
			p = (i+j)/2
			if p == p_end:
				break
			self.cache_line.seek(p*calcsize('17sII'))
			position = unpack( '17sII', self.cache_line.read(calcsize('17sII')) )

			if self.opt == 'schbk':
				if offset > position[2]:
					j = p-1
				else:
					i = p+1
					tps = position[0]
			elif self.opt == 'sch':
				if offset < position[1]:
					j = p-1
				else:
					i = p+1
					tps = position[0]
#		print self.opt, offset, tps, position[0], position[1], position[2]
		return tps.replace('\x00', '')

	def getOffsetList(self, SAspot, times, opt=0):
		'''
		回傳字串 offset list
		opt = 0 ( [offset] list, sort by offset )
		opt = 1 ( [(offset, position)] list, sort by offset )
		'''
		D = []
		if times == 0 or SAspot == -1:
			return D
		self.S.seek(SAspot)
		if opt == 0:
			for k in range(times):
				D.append( unpack( 'I', self.S.read(calcsize('I')) )[0] )
			D.sort()
		else:
			c = 0
			for k in range(times):
				D.append( (unpack( 'I', self.S.read(calcsize('I')) )[0], c) )
				c += 1
			D.sort(lambda x,y: cmp(x[0],y[0]))
		return D
		
	def getOffsetList2(self, strg, opt=0):
		strgL = convertStr2List(strg, 1)
		fn = self.ofstPh + '_'.join(strgL)
		strpt = 'II'
		if self.opt == 'schbk':
			opt = 1					#如果是反向物件，opt 不可以是 1 以外的數。
			fn += '-b'
		elif opt == 1: fn += '-f'
		else: strpt = 'I'
#		print 'open:', fn
		if not os.path.isfile(fn): return 'no this offset-list index'
		f = open( fn, 'rb' )
		times = os.stat( fn )[6] / calcsize(strpt)
		D = []
		for k in range(times):
			if opt == 1: D.append( unpack( 'II', f.read(calcsize('II')) ) )
			else: D.append( unpack( 'I', f.read(calcsize('I')) )[0] )
		return D
		

### Section Matadata and Fulltext Retrieval ###
	'''
	CBETA 有經號與行號之分、一般文獻只有檔名資訊。
	這裡統一處理，getSectionInf() 只要有資料就輸出，getRange() 也是負責取得 offset。
	* getSectionInf() 就是輸出全部，getRange() 是輸出指定的 section。
	* getSectionInf(), getRange(), getRangeWords() 都有正反檔之分。
	** 比較：getWords(), getsdroW() 有正反檔之分，但 getText(), getTexts() 反向檔檢索結果都會轉回正向。
	
	進一步計算字數，或單要 cbeta 經號的 Ragne，或顯示行號 + 文字等功能，在上層 tool 中再處理。
	可配合 cache 的經錄等 table metadata。
	'''
	def getSectionInf(self, subfn='', subfnlen=''):
		'''
		內定直接使用 sub_lb（CBETA 就是行號索引；一般語料是檔名索引）
		** 亦可輸入其他 sub_lb 例如 sub_lb_sutra（CBETA 特別做的經號索引）在 tools.SearchCBETA.cacheSectionInf() 有使用
		subfn: sub_lb 的開檔物件
		subfnlen: sub_lb 的大小
		回傳 section name, start offsets, end offset（反向檔 offset 大者在前）
		fwd: [ ('lb_or_file_name', 4, 104), ...]
		bwd: [ ('lb_or_file_name', 104, 4), ...]
		** CBETA 以 lb 為 section 會非常多，而且照順序跑花時間。
		'''
		if subfn == '' or subfnlen == '':		#給內定的 lb
			subfn = self.cache_line
			subfnlen = self.cache_line_len
		Li = []
		c = 0		#loop count
		ct = 0		#offset
		fn = ''		#section name
		pre = ''
		subfn.seek(0)
		while c < subfnlen:
			pos = unpack('17sII', subfn.read( calcsize('17sII') ))
			if self.opt == 'schbk':
				ct = pos[2]
			else:
				ct = pos[1]
			fn = pos[0].replace('\x00', '')
			if pre != '':
				Li.append( (pre[0], pre[1], ct) )
			pre = (fn, ct)
			c += calcsize('17sII')
		if self.opt == 'schbk':
			Li.append( (pre[0], pre[1], 0) )
		else:
			Li.append( (pre[0], pre[1], self.F_len) )
		return Li
		
	def getRange(self, lb):
		'''
		輸入 section 代號，回傳該首尾 offset（反向檔大者在前）
		'''
		ans_s = 0
		ans_e = 0
		i = 0
		j = self.cache_line_len/28			#長度相同所以沒換
		while i <= j:
			p = (i+j)/2
			self.cache_line.seek(p*28)
			position = unpack( '17sII', self.cache_line.read(calcsize('17sII')) )
			#position = ('T01n0001_p0001a01', 24, 290876352)
			if self.opt == 'schbk':
				post = position[2]
			else:
				post = position[1]
			
			if lb < position[0].replace('\x00', ''):
				j = p-1
				ans_e = post
#				print '<', ans_s, ans_e
			else:
				i = p+1
				ans_s = post
#				print '>=', ans_s, ans_e
		return ans_s, ans_e

	def getRangeWords( self, start, end ):
		'''
		取得起始與結束 offset 間的文字（有正反檔案之分）
		'''
		if (end <= start) or (start < 0) or (end < 0):
			return 'wrong offset range!'
		else:
			if self.opt == 'schbk' and self.bom == 'Y':	#反向檔有 bom 要加上
				start += 4
				end += 4
			self.F.seek( start )
			return self.F.read( end - start ).decode(self.coding)


### Words Distance ###
	def getDistances(self, term1, term2, limit='all'):
		'''
		輸入兩個字串
		range: 檔名
		回傳兩個陣列
			offsets ASC: [0, 233, 455, 877, 1088, ..., end offset]
			term_id    : ['s', 0, 1, 0, 0, ..., 'e']
		'''
		n = self.doSearch(term1)
		if n[0] >= self.ofstlimit: Os1 = self.getOffsetList2(term1)
		else: Os1 = self.getOffsetList(n[1], n[0])
		n = self.doSearch(term2)
		if n[0] >= self.ofstlimit: Os2 = self.getOffsetList2(term2)
		else: Os2 = self.getOffsetList(n[1], n[0])
		
		Lo = []		#offset
		Ls = []		#term 1 or 2 (0 or 1)
		
		c1 = c2 = 0
		m1 = 0
		m2 = 1
		
		while c1 < len(Os1) and c2 < len(Os2):
			if Os1[c1] > Os2[c2]:
				Lo.append(Os2[c2])
				Ls.append(m2)
				c2 += 1
			else:
				Lo.append(Os1[c1])
				Ls.append(m1)
				c1 += 1
		if c1 == len(Os1):
			Lo.extend(Os2[c2:])
			Ls.extend( [m2]*(len(Os2)-c2) )
		else:
			Lo.extend(Os1[c1:])
			Ls.extend( [m1]*(len(Os1)-c1) )
		
		if limit == 'all':
			Lo.insert(0, 0)
			Ls.insert(0,'s')
			Lo.append(self.F_len)
			Ls.append('e')
		else:
			n = self.getRange(limit)
#			print n
#			if Lo[0] > n[1] or Lo[-1] < n[0]:
#				return [], []
			i = c = 0
			for k in Lo:
				if k < n[1]:
					c += 1
				if k < n[0]:
					i += 1
				if k > n[1]:
					break
			Lo = Lo[i:c]
			Lo.append(n[1])
			Lo.insert(0,n[0])
			Ls = Ls[i:c]
			Ls.append('e')
			Ls.insert(0, 's')
		return Lo, Ls
		

### Next Words Search ###
	def getNextWords(self, SAspot, times, kwlen, extlen=1):
		'''
		SAspot: SA spot
		times: SA count
		kwlen: string length
		extlen: how many next words
		return [(next str, count), (next str, count), ...]
		'''
#		n = self.doSearch(kw)
#		times = n[0]
#		SAspot = n[1] 
		
		nL = []		#有索引的 Next Word 的記錄
		ct = 0
		while times > ct:		
			self.S.seek( SAspot )
			offset = unpack( 'I', self.S.read(calcsize('I')) )[0]
			n = self.__getWords( offset, kwlen+extlen )
			m = self.__getWords( offset+(kwlen*calcsize('I')), extlen)
			
			#backward 的字串要反過來
			if self.opt == 'schbk':
				n = self.__backwardStr(n)[0]
				if extlen > 1:
					m = self.__backwardStr(m)[0]
			rst = self.doSearch(n)
			
			if rst[0] == 0:			#should not happen
				nL = [('err-1', 0)]	#err-1
				break
			
			nL.append( (m, rst[0]) )
			ct += rst[0]
			SAspot = SAspot + rst[0]*calcsize('I')
#			print rst[0], ct, '/', times
#			raw_input()
		return nL

	'''以下兩個 def 需要在 __init__() 中給 next=[] 參數'''
	def getNextWords2(self, fn, kwlen, lastSAspot, extlen):
		'''
		return the samething as getNextWords() but using "next index"
		fn: index file name
		kwlen: length of the string
		lastSAspot: length of SAspot
		extlen: length of next string
		'''
#		kwlen = countStrLen(string)
#		fn = str( self.NL[extlen-1][string] )
		
		fn = self.nextPh+('0'+fn)[-2:]+'/'+fn
		if not os.path.isfile(fn): return 'no this next sub-index'
		f = open( fn, 'rb' )	#open the next index of 'string' with next 'extlen' characters
		preSA = m = ''			#preSA saves 'pre-SAspot' and m saves 'next string'
		nL = []
#		print '2 count:', os.stat( fn )[6]/calcsize('I')
		for k in range( os.stat( fn )[6]/calcsize('I') ):
			SApost = unpack( 'I', f.read(calcsize('I')) )[0]
			if preSA != '':
				nL.append( ( m, (SApost-preSA)/calcsize('I') ) )		#SApost 前後相減便是該 ext 的數量
			self.S.seek(SApost)											#索引中記錄的是 SAspot 所以要先去 self.S 中取出 offset 在去 self.F 中取得字串
			offset = unpack( 'I', self.S.read(calcsize('I')) )[0]
			n = self.__getWords( offset, kwlen+extlen )
			m = self.__getWords( offset+(kwlen*calcsize('I')), extlen)
			if self.opt == 'schbk' and extlen > 1:
				m = self.__backwardStr(m)[0]
			preSA = SApost
		nL.append( (m, (lastSAspot-SApost)/calcsize('I') ) )			#最後一個 ext 的數量用 lastSAspot 減出結果
		f.close()
		return nL
		
	def getNL(self):
		try: return self.NL
		except: return 'no next sub-indexes'

	
### Basic Binary Search ###
	def doSearch( self, KW ):
		'''
		輸入欲查詢的字串
		回傳 (該字串出現次數, SuffixArray 檔的起始 offset)
		無此字串時回傳 (0, -1)
		'''
		ans = ( 0, -1 )		##搜尋結果參數##
		if KW == '': return ans
		
		KW = ''.join( convertStr2List(KW)[:32] )	#cache 記錄的字串長度是 32
		if self.opt == 'schbk':
			KW = self.__backwardStr( KW )[0]
			
		kw_len = countStrLen( KW )						##欲搜尋字串的字數##
		S_end = self.S_len/calcsize('I')			##suffix array 的長度(個數)##
		i = 0										##binary search 的起始位置##
		j = self.S_len/calcsize('I')				##binary search 的結束位置##
#		print "search for %s, len: %d, sa: %d, sa_s: %d, sa_e: %d" % (KW, kw_len, self.S_len, i, j)
		if self.S_len > 1000000:					#有 cache
			ck = 1									##cache lists 位置的參數##
			while ck < self.cache_qt:
				k = self.cache_p[ck]				##位置 cache 的參數##
#				w = self.cache_w[ck][0:kw_len]		##字串 cache 的參數##
				w = ''.join( convertStr2List(self.cache_w[ck])[:kw_len] )
				
				if KW < w:
					j = k-1
					ck = ck*2
				elif KW > w:
					i = k+1
					ck = ck*2+1
				else:
					break	#比對到直接跳出, 剛剛的 i, j 傳給下一個迴圈
#			print i, j
#			raw_input()

		while i <= j:
			k = ( i+j )/2
			if k == S_end:	#最後一個位置, 後面沒有資料
				break
			self.S.seek( k*calcsize('I') )
			offset = unpack( 'I', self.S.read( calcsize('I') ) )[0]	##suffix array 中該位置紀錄的 offset (for self.F)##
			w = self.__getWords( offset, kw_len )		##每個offset向後抓KW同長度的字串##
#			print w
#			raw_input()	
			if KW == w:	#比對到第一個
				sa_start_p = k		##紀錄出現該字串 suffix array 的開始與結束位置##
				sa_end_p = k	
				
				k_bk = k
				while i <= k_bk:	#前半
					ks = ( i+k_bk )/2
					self.S.seek( ks*calcsize('I') )
					offset = unpack( 'I', self.S.read( calcsize('I') ) )[0]
					w = self.__getWords( offset, kw_len )	#到每個offset向後抓KW同長度的字串來比
					if KW == w:
						sa_start_p = ks
						k_bk = ks-1
					elif KW != w:
						i = ks+1
						sa_start_p = i	#目前的 ks 確定不是, 下一個才可能是
				while k <= j:	#後半
					ks = ( k+j )/2
					if ks == S_end:
						break
					self.S.seek( ks*calcsize('I') )
					offset = unpack( 'I', self.S.read( calcsize('I') ) )[0]
					w = self.__getWords( offset, kw_len )	#到每個offset向後抓KW同長度的字串來比
					if KW == w:
						sa_end_p = ks
						k = ks+1
					elif KW != w:
						j = ks-1
						sa_end_p = j
				c = sa_end_p - sa_start_p + 1				##搜尋到[ KW ]的總數 = 開始位置 - 結束位置 + 1 ##
				ans = ( c, sa_start_p*calcsize('I') )		##搜尋結果. 回傳次數與起始的 suffix array 檔的 bytes數##
				break
				
			elif KW < w:
				j = k-1
			else:
				i = k+1
		return ans


if __name__ == '__main__':
#	print SATools.__doc__
#	print SATools.doSearch.__doc__

### 建正反檔的 Suffix Array ###
	"""
	Tsa1 = time()
	n = ('./cbeta_index/Text_f', './cbeta_index/Text_b')
	for k in n:
		SA = SATools(k, 'index', 4, 'utf32')
		SA.index()
	
	Tsa2 = time()
	print strftime('%H:%M:%S', gmtime(Tsa2-Tsa1))
	"""

### 建正反檔的 offset list cache index ###
	"""
	path = 'cbeta_index'
	path = 'cores/indexes/cbeta_v10_packs/cbeta_JTX'
	encode = 'utf32'
	length = 4
	obj_f = SATools('%s/Text_f' % path, 'sch', length, encode, '%s/Text_f_SA' % path)
	obj_b = SATools('%s/Text_b' % path, 'schbk', length, encode, '%s/Text_b_SA' % path)
	se = (obj_f, obj_b)
	for k in se:
		k.inofst(4)
	"""

### 建正反檔的 next word index ###
	"""
	path = 'cbeta_index'
#	path = 'jinyong_index_nt'
	path = 'indexes/cbeta_v10_packs/cbeta_JTX2'
#	path = 'indexes/jinyong_v01_packs_old'
	encode = 'utf32'
	length = 4
	obj_f = SATools('%s/Text_f' % path, 'sch', length, encode, '%s/Text_f_SA' % path)
	obj_b = SATools('%s/Text_b' % path, 'schbk', length, encode, '%s/Text_b_SA' % path)
	se = (obj_f, obj_b)
	
	gram = (1,2,3,4,5)
	ext = 3
	limit = 1000
	
	for k in se:
		k.innext(gram, ext, limit)
	"""

### lb 索引檔檢測 ###
	"""
	path = 'cbeta_index'
	f = open(path+'/sub_lb', 'rb')
	c = 0
	while c < os.stat(path+'/sub_lb')[6]:
		pos = unpack('17sII', f.read( calcsize('17sII') ))
		print pos[0], pos[1], pos[2]
		c += calcsize('17sII')
	"""


### 檢索功能測試 ###
	path = 'cbeta_index'
#	path = 'indexes/cbeta_v10_packs/cbeta_JTX'
	
	encode = 'utf32'
	enlength = 4

	nfL = nbL = []
	nfL = [path+'/next/f-5-1_2_3_4_5-20',path+'/next/f_ext-1',path+'/next/f_ext-2',path+'/next/f_ext-3',path+'/next/f_ext-4',path+'/next/f_ext-5']
	nbL = [path+'/next/b-5-1_2_3_4_5-20',path+'/next/b_ext-1',path+'/next/b_ext-2',path+'/next/b_ext-3',path+'/next/b_ext-4',path+'/next/b_ext-5']
#	nfL = [path+'/next/f-2-1_2_3-2000',path+'/next/f_ext-1',path+'/next/f_ext-2']
#	nbL = [path+'/next/b-2-1_2_3-2000',path+'/next/b_ext-1',path+'/next/b_ext-2']

	ofsLf = ofsLb = []
	ofsLf = ['%s/ofst-20'%path, 20]
	ofsLb = ['%s/ofst-20'%path, 20]
#	ofsLf = ['%s/ofst-100000'%path, 100000]
#	ofsLb = ['%s/ofst-100000'%path, 100000]

#	obj_f = SATools('%s/Text_f' % path, 'sch', enlength, encode, '%s/Text_f_SA' % path, '%s/sub_lb' % path, nfL, ofsLf)
#	obj_b = SATools('%s/Text_b' % path, 'schbk', enlength, encode, '%s/Text_b_SA' % path, '%s/sub_lb' % path, nbL, ofsLb)
#	obj = obj_b
	
## 有 ofst-100000 索引但查不到頻率的字串：
	"""
	strg = [u'，A',u'。A',u'也。A',u')。A']
	for k in strg:
		print obj_f.doSearch(k), obj_b.doSearch(k)	
	raw_input()
	"""

## getOffsetList() 速度測試
	"""
	n = obj_f.doSearch(u'無')
	print n
	rst = obj_f.getOffsetList(n[1], n[0], 1)
	print 'sort'
	rst.sort(lambda x,y: cmp(x[1], y[1]) )
	print len(rst)
	"""

## section info forward
	"""
	rst = obj_f.getSectionInf()
	for k in rst:
		print k
		tmp = obj_f.getRange(k[0])
		print 'getRagne :', tmp
		line = obj_f.getRangeWords(tmp[0], tmp[1])
		print 'getRangeW_F:', re.sub(r'^\n+|\n+$', '', line)
		line = obj_b.getRangeWords(14348-tmp[1]+4, 14348-tmp[0]+4)
		print 'getRangeW_B:', re.sub(r'^\n+|\n+$', '', line)
		raw_input()
#		print k, text.replace('\n', u"\u204B "), rst[k][0]
	"""

##  doSearch & Concordance
	"""
	string = [u'一']
	
	n = obj.doSearch(string[0])
	print n
	print obj.getOffsetList(n[1], n[0])
	line = obj.getTexts(n[1], n[0], 10, 10+countStrLen(string[0]), 1)
	for ks in line:
		print ks[0].replace('\n', u"\u204B "), ks[1]
#		raw_input()
	"""

## 	Distance
	"""
	string = (u'七祖', u'\U000243d9', u'退屈')
	
	tmp = obj_f.getDistances(string[0], string[2])
	print tmp[0]
	print tmp[1]
	raw_input()
	"""

## Next words
	"""
	rst = obj.getNextWords(k)
	for ks in rst:
		print ks
	print obj.getNextWordCounts(k)
	"""

## 查看 Next metadata index (dictionary)
	"""
	rst = obj.getNL()
	print len(rst)
	for k in rst:
		print len(k), type(k)
		for ks in k:
			print ks, k[ks]
		raw_input()
	"""
	
## Next 索引效能測試
	"""	
	ext = 5
	string = u'\u3000'
#	string = u'不'
	
	n = obj.doSearch(string)
	print 'basic'
	te1 = time()
	rst1 = obj.getNextWords(n[1], n[0], countStrLen(string), ext)
	te2 = time()
	print strftime('%H:%M:%S', gmtime(te2-te1))
	if n[0] >= obj.nextlimit:
		fn = str( obj.NL[ext-1][string] )
		lastSAspot = n[1]+n[0]*calcsize('I')
		print 'sub'
		te1 = time()
		rst2 = obj.getNextWords2(fn, countStrLen(string), lastSAspot, ext)
		te2 = time()
		print strftime('%H:%M:%S', gmtime(te2-te1))
		
		print len(rst1), '==', len(rst2)
		for k in range(len(rst1)):
			print k, ':', rst1[k][0].replace('\n','-').encode('utf8'), '==', rst2[k][0].replace('\n','-').encode('utf8'), 'and', rst1[k][1], '==', rst2[k][1]
			raw_input()
		print 'crecct!'
	else:
		print 'no sub-index'
	
	"""

## ofst sub 索引效能測試
	"""
	opt = 1				#opt=0: 只有 offset 的陣列；opt=1: (offset, position) 的陣列
	string = u'一切'	

	n = obj.doSearch(string)
	print 'basic',
	ts1 = time()
	rst1 = obj.getOffsetList(n[1], n[0], opt)
	ts2 = time()
	print strftime('%H:%M:%S', gmtime(ts2-ts1))
	if n[0] >= obj.ofstlimit:
		print 'sub',
		ts1 = time()
		rst2 = obj.getOffsetList2(string, opt)
		ts2 = time()
		print strftime('%H:%M:%S', gmtime(ts2-ts1))
		
		print len(rst1), '==', len(rst2)
		print rst1[0], rst2[0]
		print rst1[1], rst2[1]
		print rst1[-2], rst2[-2]
		print rst1[-1], rst2[-1]
	else:
		print 'no sub-index'
	"""
