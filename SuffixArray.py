#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2006 winter) at The Chung Hwa Institute of Buddhist Studies
Updated by TRuEmInG (2008 fall) at NTU ESOE
Updated by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
Updated by TRuEmInG (2011 spring) at NTU ESOE for CNLSTK, Web API
"""
"""
section 的統一輸入設計		id, name, time, time_id, place, place_id
"""

import os, re, sys, cPickle
from struct import *
from time import time, strftime, gmtime

from utility import *

"""
def ctwlen(strg):
	'''
	計算字串長度（避免五碼以上 unicode 字串長度 +1 的計算）
	'''
	ct = len(strg)
	for k in strg:
		if ord(k) >= 0xD800 and ord(k) <= 0xDBFF: ct -= 1
	return ct
		
def convertStr2List(strg, opt=0):
	'''
	將字串轉為以單字為內容的陣列（ Ext.B 以上的五碼 unicode 需要 ）
	opt = 0: 陣列內容為 unicode 字				ex. [u'我']
	opt = 1: 陣列內容為 unicode 16 進位編碼		ex. ['6211']
	'''
	L = []
	tmp = ''
	for k in strg:
		if ord(k) >= 0xD800 and ord(k) <= 0xDBFF:
			tmp = k
		elif ord(k) >= 0xDC00 and ord(k) <= 0xDFFF:
			if opt == 1: L.append( '%X' % ( (ord(string[c])-0xd800)*0x400 + (ord(string[c+1])-0xdc00) + 0x10000 ) )
			else: L.append(tmp+k)
			tmp = ''
		else:
			if opt == 1: L.append( '%X' % ord(k) )
			else: L.append(k)
	return L
"""

class SATools:
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


######################
# Bulid Suffix Array #
######################
	def index( self, opt=0, cache=1000000 ):
		'''
		Create the suffix array of self.F.
		[opt] = 0: pass '\n'
		[ cache ] = No. of chars to save a tmp file.
		'''	
		if self.opt != 'index':
			print 'index function locked!'
			return
		
		Ts = time()		##開始時間##
		print 'indexing', self.File_main
		p = os.path.split( self.File_main )		##拆檔名 p[0] = 路徑, p[1] = 檔名##
		if os.path.isdir( p[0]+'/tmp' ):		#建 tmp 資料夾
			pass
		else:
			os.mkdir( p[0]+'/tmp' )
		tmpath = p[0]+'/tmp/'					##暫存目錄完整路徑##
		
		if os.path.isfile(p[0]+'/index.log'):	#建索引過程的 log 檔
			flog = open(p[0]+'/index.log', 'r')
			llog = flog.read()
			flog.close()
		else:
			llog = ''
		self.index_log = open(p[0]+'/index.log', 'w')
		self.index_log.write(llog+'\n')
		
		D = []						##offset, position 與 chars-context 的暫存陣列. 每次紀錄至 cache 大小後排序, 暫存出去, 再清空##
		c = n = 0					##c = 已處理中文字數的累加, n = 排序暫存檔數的累加 ##
		
		if opt == 0: jump = u'\n'
		else: jump = u''
		
		self.F.seek(0)	
		while self.F.tell() < self.F_len:
			offset = self.F.tell()			## self.F 目前的 offset ##
			w1 = self.F.read(self.salen).decode(self.coding)
			
			if w1 == u'' or w1 == jump:		#不建 suffix array 的字（BOM & '\n'）
				pass						#w1 == '' BOM, ord(u'\n') = 10
			else:
				c += 1
				try:
					w2 = self.__getWords( offset+self.salen, 127 )	#每次比128個字
				except:
					print c
					raw_input()
				D.append( (offset, w1+w2) )
#				print "%d, [%d: %s]\n%s" % ( c, offset, w1, w2 )
#				raw_input()
				
			if (c > 0 and c % cache == 0 and len(D) > 0) or offset+self.salen == self.F_len:	#每一百萬字 or 檔案結束 儲存
				n += 1
				rst1 = self.__saveTmpFiles( D, n, tmpath )
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
		Tm = time()		##分批排序暫存完畢後的時間##
		print strftime('%H:%M:%S', gmtime(Tm-Ts))
		
		print 'Step3/3: sorting separated char-groups ...'
		fn = self.__combinTmps( tmpath, p[1] )	#合併 suffix array 暫存檔
		Te = time()		##結束時間##
		print strftime('%H:%M:%S', gmtime(Te-Ts))
			
	def __saveTmpFiles( self, L, no, path ):
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
		
	def __combinTmps( self, path, orgfn ):
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
					f1w = self.__getWords( f1_ofst[0], 128 )			##取單數檔 128 個字##
					f2_ofst = unpack( 'I', f2.read( calcsize('I') ) )	##取得雙數檔的 offset ##
					f2w = self.__getWords( f2_ofst[0], 128 )			##取雙數檔 128 個字##
	
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
								f1w = self.__getWords( f1_ofst[0], 128 )
							except:
								flag1 = 'off'
						elif f1w > f2w:
							fw.write( pack('I', f2_ofst[0]) )	# 1> 2 寫入 2
							try:
								f2_ofst = unpack( 'I', f2.read( calcsize('I') ) )
#								self.F.seek( f2_ofst )
								f2w = self.__getWords( f2_ofst[0], 128 )
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


####################
# Search Functions #
####################

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
