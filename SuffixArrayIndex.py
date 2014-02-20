#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2006 winter) at The Chung Hwa Institute of Buddhist Studies
Updated by TRuEmInG (2008 fall) at NTU ESOE
Updated by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
Updated by TRuEmInG (2011 spring) at NTU ESOE for CNLSTK, Web API
Updated by TRuEmInG (2013 winter) at NTU ESOE for CNLSTK, modify package structure
"""

import os, re, sys, cPickle
from struct import *
from time import time, strftime, gmtime
from utility import *


class SA_Index(object):
	'''建 Suffix Array index 的 class'''
	
	def __init__( self, fname, salen=4, coding='utf32' ):
		'''
		[ fname ] = the main text file. 
		[ salen ] = Suffix Array index length
		[ coding ] = main text encode
		'''
		#################################
		# 儲存索引的兩項基本資料於 encode 檔：
		#	1.encoding of the main text file
		#	2.length of an index unit
		# The default is 'utf32,4'
		#################################
		ntf = open(os.path.split(fname)[0]+'/encode', 'w')
		ntf.write(coding+','+str(salen))
		ntf.close()

		####################
		# Initial parameters
		####################		
		self.F = open( fname, 'rb' )			# 開啟主文字檔
		self.F_len = os.stat( fname )[6]		# 主文字檔大小
		self.File_main = fname					# 主要檔的檔名
		self.salen = salen						# 檔案中索引距離的長度（與 self.coding 相應）
		self.coding = coding					# 檔案編碼
		self.jumpchrs = [u'\n']					# 欲跳過不建索引的字元

		#####################
		# 檢查全文檔頭是否有 BOM
		#####################
		bom = ['\xff\xfe', '\xfe\xff']
		if self.F.read(2) not in bom: self.bom = 'N'
		else: self.bom = 'Y'
		self.F.seek(0)		

	def __getWords__( self, ofst, length ):
		'''
		輸入 offset + 欲取的字串長度（字元數）length
		回傳 offset 開始向後（右）length 個字元的字串
		'''
		self.F.seek( ofst )
		bytes = length * self.salen		#轉成 bytes 數
		return self.F.read(bytes).decode(self.coding)


	######################
	# Bulid Suffix Array #
	######################
	def make( self, cache=1000000 ):
		'''
		Create the suffix array of self.F.
		[ cache ] = No. of chars to save a tmp file.
		'''	
		
		Ts = time()								# 開始時間
		print 'indexing', self.File_main
		p = os.path.split( self.File_main )		# 拆檔名 p[0] = 路徑, p[1] = 檔名
		if os.path.isdir( p[0]+'/tmp' ): pass	# 建 tmp 資料夾
		else: os.mkdir( p[0]+'/tmp' )
		tmpath = p[0]+'/tmp/'					# 暫存目錄完整路徑
		
		if os.path.isfile(p[0]+'/index.log'):	# 建索引過程的 log 檔
			flog = open(p[0]+'/index.log', 'r')
			llog = flog.read()
			flog.close()
		else: llog = ''
		self.index_log = open(p[0]+'/index.log', 'w')
		self.index_log.write(llog+'\n')			# 保留原有的資料
		
		D = []								# offset, position 與 chars-context 的暫存陣列. 每次紀錄至 cache 大小後排序, 暫存出去, 再清空
		c = n = 0							# c = 已處理中文字數的累加, n = 排序暫存檔數的累加
		self.F.seek(0)	
		while self.F.tell() < self.F_len:
			offset = self.F.tell()			# self.F 目前的 offset
			w1 = self.F.read(self.salen).decode(self.coding)
			
			if w1 == u'' or w1 in self.jumpchrs:	# 內定不建 suffix array 的字是 BOM & '\n'
				pass								# w1 == '' BOM 解碼後是空字元, ord(u'\n') = 10
			else:
				c += 1
				try:
					w2 = self.__getWords__( offset+self.salen, 127 )	# 每次比128個字
				except:
					print c
					raw_input()
				D.append( (offset, w1+w2) )
#				print "%d, [%d: %s]\n%s" % ( c, offset, w1, w2 )
#				raw_input()
				
			if (c > 0 and c % cache == 0 and len(D) > 0) or offset+self.salen == self.F_len:	# 每一百萬字 or 檔案結束 儲存
				n += 1
				rst1 = self.__saveTmpFiles__( D, n, tmpath )
				D = []
				self.index_log.write( '%d / %d bytes, %d char. tmp %d saved %s.\n' % ( offset, self.F_len, c, n, rst1 ) )
				print '\r\t%d / %d bytes, %d char. tmp %d saved %s.\n' % ( offset, self.F_len, c, n, rst1 )
			self.F.seek( offset + self.salen )
			'''
			cpc = 0		#stdout process %
			if offset/(self.F_len/10) > cpc:
				print '\r', offset/(self.F_len/10), '%',
				cpc = offset/(self.F_len/10)
				sys.stdout.flush()
			'''
		Tm = time()		# 分批排序暫存完畢後的時間
		print strftime('%H:%M:%S', gmtime(Tm-Ts))
		
		print 'Step3/3: sorting separated char-groups ...'
		fn = self.__combinTmps__( tmpath, p[1] )	#合併 suffix array 暫存檔
		Te = time()		##結束時間##
		print strftime('%H:%M:%S', gmtime(Te-Ts))
			
	def __saveTmpFiles__( self, L, no, path ):
		'''
		Sort and save offset dictionary.
			[ L ] = [ (offset, position, 128 chi-char), ... ]
			[ no ] = No. of tmp files
			[ path ] = path of tmp files
		'''
		L.sort( lambda x,y: cmp(x[1], y[1]) )
		fw = open( path+str(no), 'wb' )		##開暫欲寫入的存檔##
		for k in L:
			fw.write( pack('I', k[0]) )
#			print "offset: %d, string: %s" % ( k[0], k[1][0])
#			raw_input()
		fw.close()
		return 'ok'
		
	def __combinTmps__( self, path, orgfn ):
		'''
		Combin sorted tmp files.
			[ orgfn ] = the file name of self.F
			[ path ] = folder of where all tmp files saved
		'''
		path2 = ''				##回傳值（新索引檔的路徑）
		L = os.listdir( path )	##儲存所有暫存檔名的陣列##
#		print len(L)
#		print L
		if len(L) != 1:	#如果資料夾內還有兩個以上的檔案
			print 'merge sorting:', len(L), 'round:'
#			raw_input()
			i = 0		##參數辨別讀到單數或雙數檔##
			for k in L:	#兩兩合併
				i += 1
				if i == 1:
					f1n = k		##暫存單數檔名##
				elif i == 2:
					self.index_log.write( '%s\t%s\n' % (f1n, k) )
					f1 = open( path+f1n, 'rb' )			##開單數檔##
					f2 = open( path+k, 'rb' )			##開雙數檔##
					self.index_log.write( 'merge sorting %s and %s\n' % (f1n, k) )
					print '(%s,%s)' % (f1n, k),
	
					fw = open( path+'tmp', 'wb' )		##每累積兩個檔案就開始合併作業. 結果暫存於 tmp 檔##
					
					f1_ofst = unpack( 'I', f1.read( calcsize('I') ) )	##取得單數檔的 offset ##
					f1w = self.__getWords__( f1_ofst[0], 128 )			##取單數檔 128 個字##
					f2_ofst = unpack( 'I', f2.read( calcsize('I') ) )	##取得雙數檔的 offset ##
					f2w = self.__getWords__( f2_ofst[0], 128 )			##取雙數檔 128 個字##
	
					flag1 = flag2 = 'on'				## flag1, flag2 單雙數兩個檔案是否結束的辨識參數##
					while flag1 == 'on' or flag2 == 'on':
						if flag2 == 'off':
							fw.write( pack('I', f1_ofst[0]) )
							fw.write( f1.read() )
							break							
						elif flag1 == 'off':
							fw.write( pack('I', f2_ofst[0]) )
							fw.write(f2.read())
							break
						elif f1w <= f2w:
#							if f1w == f2w:	#如果兩個 256 bytes 的長字串相等, 值得 check 一下是否為複製
#								print "***ofst_1: %d, ofst_2: %d following same contents !! file may be duplicated." % ( f1_ofst, f2_ofst )
	
							fw.write( pack('I', f1_ofst[0]) )	# 1 <= 2 寫入 1
							try:	# unpack 不出東西, 回傳錯誤, 表示該 tmp 檔跑完.
								f1_ofst = unpack( 'I', f1.read( calcsize('I') ) )
#								self.F.seek( f1_ofst )
								f1w = self.__getWords__( f1_ofst[0], 128 )
							except:
								flag1 = 'off'
						elif f1w > f2w:
							fw.write( pack('I', f2_ofst[0]) )	# 1> 2 寫入 2
							try:
								f2_ofst = unpack( 'I', f2.read( calcsize('I') ) )
#								self.F.seek( f2_ofst )
								f2w = self.__getWords__( f2_ofst[0], 128 )
							except:
								flag2 = 'off'
					f1.close()
					f2.close()
					fw.close()
					
					os.remove( path+f1n )	#合併完後刪除單數檔
					os.remove( path+k )		#刪除雙數檔
					os.rename( path+'tmp', path+f1n )	#將 tmp 更名為單數檔檔名
					i = 0
#					print "check", f1n, k
#					raw_input()
			print 'end this round.'
			path2 = self.__combinTmps( path, orgfn )
		else:
			self.F.close()
			path2 = path.replace( 'tmp/', '' )
			os.rename( path+L[0], path2+orgfn+'_SA' )
			os.rmdir( path[:-1] )	# path = ..../tmp/ << / 去掉才能 rmdir
			self.index_log.write( '%s, %s, suffix array created' % ( L[0], orgfn ) )
#			print '%s, %s, suffix array created' % ( L[0], orgfn )
		return path2+orgfn+'_SA'


#####################
# Bulid sub-Indexes #
#####################	
	'''
	以下兩個副索引都可以考慮跳過標點和空白符號以將索引減肥
	helf of "CJK Symbols & Punctuation" unicode: 3000~3015
	chars in "Halfwidth & Fullwidth Forms": ！FF01, （FF08, ）FF09, ，FF0C, ．FF0E, ：FF1A, ；FF1B, ？FF1F
	不建索引的話，檢索的條件要注意。不修改的話，檢索這些符號會找不到東西。
	'''	
### Next Word Index ###
	def innext( self, gram, nc, limit=1000 ):
		'''
		Create the next indexes of main files
		__init__ peremeters need (fname, opt, salen, coding, suffix='')
		
		gram: 要做到幾 gram 的 next 索引
		nc: length of next(ext) string
		limit: 多少個 next 以上的建索引
		** limit 是真正建索引的條件；gram, nc 是建索引的範圍。
		ex. gram=(1,2,3,4), nc=3, limit=1000
		
		產生 nc 個 pickle 檔，其內容為 Dictionary。
		上述 Dictionary 記錄該延伸長度中，符合索引條件的所有的 n-gram 字串（key）及其索引檔名（value）。
		索引檔名為 int 讀檔時須轉成 str。
		索引檔案內容為升冪的 SAspot 的記錄：
			其數量是該字串延伸該長度的 next word count 總數。
			SAspot 間的差為各個 next word 結果的數量。
			SAspot 對應的主檔的 offset 是取得該字串的位置。
		'''
		Ts = time()		##開始時間##
		#建 next word count 主資料夾 ./next/
		# ** ./next/ 如已存在須先刪除 **
		pth = os.path.split(self.File_main)[0]+'/next/'
		if not os.path.exists(pth): os.mkdir(pth)
			
		#建 next word count 正反索引檔案資料夾（在 ./next/ 下）
		#例：./next/f-5-1_2_3-20/ （正向檔；1,2,3-gram 各建了延伸 1~5 個字的 next word indexes；超過 20 個 next words 才建 index。）
		l = ''
		for k in gram:
			l += str(k)+'_'
		if self.opt == 'sch': un = 'f'
		else: un = 'b'
		path = pth+un+'-'+str(nc)+'-'+l[:-1]+'-'+str(limit)+'/'
		if not os.path.exists(path):
			os.mkdir(path)
		
		#結果 indexes 再分成一百份存檔
		#例：./next/f-5-1_2_3/0~99
		for k in range(100):
			os.mkdir( path+('0'+str(k))[-2:] )
			
		print 'main files: %s and %s' % (self.File_main, self.Suffix_A)
		print 'indexing', gram, 'gram', 'and next(ext)', nc, 'characters, over', limit
		DL = []
		for k in range(nc):	#照 next 的延伸長度分開記錄。每個 Dic 中參雜各個符合建索引條件的 n-gram 字串（key），value 是該字串延伸此長度的索引檔案名稱。
			DL.append({})

		fn = 0				#每個符合條件要件索引的字串的檔案名稱（直接累加）
		for ng in gram:
			print ng, '-gram /', len(gram), '...'
			SAspot = 0
			while SAspot < self.S_len:
				self.S.seek(SAspot)
				offset = unpack( 'I', self.S.read(calcsize('I')) )[0]
				string = self.__getWords( offset, ng )
				
				#長度少於 gram（到了檔尾）就跳過
				if countStrLen(string) < ng:
					SAspot += calcsize('I')
					continue

				#字串頻率數少於 limit 跳過
				#limit 頻率的字串最多有 limit 個 next word。（直接檢索 1000 次的速度尚可接受，無需建索引。）
				#如果比 limit 還少，勢必沒有 > limit 數量的 next，所以跳過不用建索引。
				if self.opt == 'schbk':
					sw = self.__backwardStr(string)[0]
				else:
					sw = string
				n = self.doSearch(sw)
				if n[0] < limit:
					SAspot += calcsize('I') * n[0]
					continue

#				print 'if', SAspot, '==', n[1], ',and then call saving function ...'
#				raw_input()
				for k in range(1, nc+1):
					svpth = path+('0'+str(fn))[-2:]+'/'+str(fn)
					rst = self.__saveNextIndex(svpth, n[1], n[0], ng, k, limit)
					if rst == 'Y':
						DL[k-1][string] = fn
						fn += 1
						
						if fn%1000 == 0:	#每存了 1000 個索引輸出目前進度
							print SAspot, '/', self.S_len
							sys.stdout.flush()
						
				SAspot += calcsize('I') * n[0]

			#每一 gram 做完後，在每個 ext 的索引上累加了幾筆。
			print 'No. of each next(ext) saved files:',
			for d in DL:
				print len(d),
			print ''
			sys.stdout.flush()
#			raw_input()
		
		svflag = 0
		for k in range(len(DL)):
			if len(DL[k]) == 0: continue
			else: svflag = 1
			fo = open( pth+un+'_ext-'+str(k+1), 'w' )
			cPickle.dump(DL[k], fo)
			fo.close()
		if svflag == 0: os.system('rm -rf '+pth )
		
		Tm = time()
		print strftime('%H:%M:%S', gmtime(Tm-Ts))
		return 'next index ok'

	def __saveNextIndex(self, fn, SAspot, times, kwlen, extlen, limit):
		'''
		fn: 如果要存索引的話的檔名
		SAspot: SA 開始位置
		times: 該字串的筆數（未作延伸）
		kwlen: 字串長度
		extlen: 要延伸長度
		limit: 多少比的 next 以上要記錄
		回傳 是否存檔 'Y' or 'N'
		'''
		fw = open(fn, 'wb')	#開檔
		nL = []				#Next Word 的 offset 記錄
		ct = 0				#計算回圈次數

		#以下三段長字串（"""..."""）是 next word counts 的資訊
		#考慮是否要建索引（如果要建可在 dic 中用 tuple 方式放在檔名的後面）
		'''
#		clt = 0				#換行或其他非文字符號（沒建索引的字碼）的次數
		ii = 0				#右側種類數
		max = 0				#右側字串中數量最多的次數
		bb = 0				#斷點數
		'''
		flag = 'N'			#是否超過 limit 的標記
		i = 0
		while times > ct:
			self.S.seek( SAspot )
			offset = unpack( 'I', self.S.read(calcsize('I')) )[0]
			n = self.__getWords( offset, kwlen+extlen )		#取得延伸後的字串
			'''m = n[-extlen:]'''
			if self.opt == 'schbk':
				n = self.__backwardStr(n)[0]
			rst = self.doSearch(n)					#檢索次數
			'''
			if (m[0] >= u'\u3100' and m[0] <= u'\uFE4F') or (m[0] >= u'\U00020000' and m[0] <= u'\U000F789F'):
				if rst[0] > max:
					ii += 1
					max = rst[0]
			else:
				bb += rst[0]
			'''
#			print 'save check:', rst[1], '==', SAspot
#			print rst[0]
#			raw_input()

			if len(nL) < limit:
				nL.append( SAspot )					#記錄目前的 SA 的位置（1.其記錄的 offset 是字串位置 2.其兩兩間差別就是該字串的筆數）
				i += 1
			else:
				if flag == 'N':						#超過 limit 筆的 next words 時開始存檔
					for s in nL:
						fw.write( pack('I', s) )	#先存之前陣列內的資料
					flag = 'Y'
				fw.write( pack('I', SAspot) )		#陣列存過後開始每個存
				i += 1
			ct += rst[0]
			SAspot = SAspot + rst[0]*calcsize('I')
		fw.close()
#		print 'get ext', extlen, i
		if flag == 'N':
			os.remove(fn)							#如果沒超過就刪檔
		return flag


### Long Offset List ###
	def inofst( self, gram, freq=100000 ):
		'''
		記錄超過 100000 頻率的詞的 3 offset lists:
			1. [offset,...]
			2. 正：[ (offset, position),... ]
			3. 反：[ (offset, position),... ]
		存在目錄 ofst-100000/ 下
		** 註：CBETA 2010	正 > 100000 [1-gram:361, 2-gram:81, 3-gram:3, 4-gram:0]
							反 > 100000 [1-gram:361, 2-gram:79, 3-gram:1, 4-gram:0]
		FF0C_A, 3002_A, 4E5F_3002_A, 29_3002_A 四字串無 -b
		'''
		ofstlistpath = os.path.split(self.File_main)[0]+'/ofst-'+str(freq)
		if not os.path.exists(ofstlistpath):
			os.mkdir(ofstlistpath)
		L = ['']* gram		#要做幾字詞的索引
		C = [0] * gram		#對應的 n-gram 的頻率
		T = [0] * gram		#各 n-gram 有幾個 freq 以上的字串
		SAspot = 0
		while SAspot < self.S_len:
			self.S.seek(SAspot)
			offset = unpack( 'I', self.S.read(calcsize('I')) )[0]
			for k in range(gram):
				tmpw = self.__getWords( offset, k+1 )
				if L[k] == tmpw:
					C[k] += 1
				else:
					if C[k] >= freq:
#						tmp = self.doSearch(L[k])
#						print L[k], C[k], tmp
#						raw_input()
						self.__saveOfstList( L[k], ofstlistpath )
						T[k] += 1
					L[k] = tmpw
					C[k] = 1
#				raw_input()
			SAspot += calcsize('I')
		# ** 如果 T 中還有不為 0 的表示可以再加一個 gram 長然後再跑一次
		print 'n-gram >', freq, 'string count:', T
	
	def __saveOfstList( self, string, path ):
		'''
		記錄傳入的字串的兩種正反共四個 offset lists
		'''
		strL = convertStr2List(string, 1)
		if self.opt == 'schbk':
			strL.reverse()
			string = self.__backwardStr(string)[0]	#字串如果是反的要反正後再 doSearch()
		fn = '_'.join(strL)							#索引檔名（正反向檔案都是正向 unicode 碼的檔名）
#		print 'save:', string, fn
		tmp = self.doSearch(string)
		flag = ''
		if self.opt == 'sch':								#只有 offset 排序正反索引結果一樣，只需做一次。
			flag = 'f'
			L = self.getOffsetList(tmp[1], tmp[0], opt=0)	#只有 offset 排序，過濾字串出現在哪些經文用到。
			fw = open( path+'/'+fn, 'wb' )
			for k in L:
				fw.write( pack('I', k) )
			fw.close()
		else:
			flag = 'b'
		L = self.getOffsetList(tmp[1], tmp[0], opt=1)	#offset + position 排序，subConcordance 用到。
		fw = open( path+'/'+fn+'-'+flag, 'wb' )
		for k in L:
			fw.write( pack('II', k[0], k[1]) )
		fw.close()


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
