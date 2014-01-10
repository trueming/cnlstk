#!/usr/bin/env python
# -*- coding: utf-8 *-*
"""
Created by TRuEmInG (2008 fall) at NTU ESOE
Updated by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
"""

import codecs, sys, os, re
from struct import *
from time import time, strftime, gmtime

from utility import *


class TextParser:
	'''
	1. 將個別的文字檔存成一個連續文字檔
	2. 輸出各別檔案 title 與 offset 範圍的對照檔
	[ location ] 結果（1,2）的存放位置
	[ source ] 要處理的檔案陣列
	'''
	
	def __init__(self, location):
		if location[-1] == '/':			#統一參數（for os.path.split(), or location+'/...'）
			location = location[:-1]
		self.location = location		#結果（與索引）存放位置
		
		self.index_log = open(location + '/index.log', 'w')

	def run(self, texts, org_code, new_code, clen):
		'''
		合併原始文件群，輸出正反兩全文檔案。
		texts: 檔名陣列
		org_code: 所有檔案編碼
		new_code: 新檔案編碼
		clen: 單位長度
		'''
		
		fwf = codecs.open(self.location+'/Text_f', 'w', new_code)	#純文字檔
		fwl = open(self.location+'/Text_f_lb', 'wb')				#檔案 offset 索引
		
		os.mkdir( self.location+'/bktmpf' )							#反向檔暫存區
		
		offset = clen												#總 offset byte (BOM)
		
		#parse 每個檔案，文字累加存檔，處理標記
		fct = 0
		for k in texts:
			fct += 1
			if fct%300 == 0:
				print '\r', fct, '/', len(texts), 'parsed.'
				sys.stdout.flush()
				self.index_log.write('%d / %d parsed.\n' % (fct, len(texts)) )
			
			bkn = os.path.split(k)
			f_tmp = codecs.open(self.location+'/bktmpf/'+bkn[1], 'w', new_code)		#全文暫存，給反向檔 reverse()
			
			fwl.write( pack('17sI', str(bkn[1]), offset) )
			
			f_tmp.write('\n')
			fwf.write('\n')
			offset += clen
			
			f = codecs.open(k, 'r', org_code)
			l = f.read()
			f.close()

			for w in l:					#陣列處理約比對檔案 binary 處理快 4 倍
#				print ord(w), w.replace('\n', '-'), offset
#				raw_input()
				f_tmp.write(w)
				fwf.write(w)
				offset += clen

			f_tmp.write('\n')				#每個檔案頭尾都個加一個換行符號
			fwf.write('\n')
			offset += clen

			f_tmp.close()
		print '\r', fct, '/', len(texts), 'parsed.'
		sys.stdout.flush()
		self.index_log.write('%d / %d parsed.\n' % (fct, len(texts)) )
		
		fwf.close()
		fwl.close()
		
		print 'Creating backword fulltext ...'
		print self.__getBackwardFulltext(self.location+'/bktmpf', 'Text_b', new_code)
		self.index_log.write( 'backword fulltext created.\n' )
		
		print 'Updating lb subindex ...'
		print self.__completeLBindex(self.location+'/Text_f_lb', offset, 'sub_lb')
		self.index_log.write( 'lb subindex updated.\n' )
		
		#回傳 ( 正檔名, 反檔名, 檔案大小（offset 大小）, 行號索引檔名, 正向 g, anchor 索引檔名 ) 
		return self.location+'/Text_f', self.location+'/Text_b', offset, self.location+'/sub_lb'


	def __modBackwardExtB(self, L):
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
	
		
	def __getBackwardFulltext(self, folder, fn, coding):
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
		
		fwb = codecs.open(self.location+'/'+fn, 'w', coding)	#反向檔
		for k in L:
			f_tmp = codecs.open(k, 'r', coding)
			l_tmp = f_tmp.read()
			f_tmp.close()
			os.remove(k)
			
			tmp_bk = list( l_tmp )					#檔案字串轉陣列
			tmp_bk = self.__modBackwardExtB(tmp_bk)	#處理陣列中被分開的五碼的 unicode
			tmp_bk.reverse()						#reverse 陣列
			tmp_bk = ''.join(tmp_bk)				#合併陣列為字串
			fwb.write( tmp_bk )

		fwb.close()
		os.rmdir(folder)
		return 'backward fulltext %s ok.' % fn


	def __completeLBindex( self, FWsubindex, totalofst, fn ):
		'''
		用正向檔行號 subindex 算反向的行號位置
		產生完整行號索引檔
		FWsubindex = 正向檔行號索引檔
		totalofst = 正向檔總 offset 值
		fn = 產生新檔案的名稱
		'''
		flb = open(self.location+'/'+fn, 'wb')
		f = open(FWsubindex, 'rb')
		len1 = len2 = ''		#記錄第一筆 offset 資料（要放到 lb 索引最後）
		secn = ''				#記錄每次的檔名為了取最後一個檔名
		while f.tell() < os.stat( FWsubindex )[6]:
			tmplb = unpack( '17sI', f.read(24) )
			bkofst = totalofst - tmplb[1]
			secn = tmplb[0]
			if len1 == '':		#因為 lb 索引記錄的都是起始 offsets 故最後須要插一個結束的 offset 檢索最後一個時才不會出錯
				len1 = bkofst
				len2 = tmplb[1]
			flb.write( pack('17sII', tmplb[0], tmplb[1], bkofst) )
		flb.write( pack('17sII', secn.replace('\x00', '')+'e', len1, len2) )
		f.close()
		flb.close()
		os.remove(FWsubindex)
		return 'backward subindex %s ok.' % fn


def readLBpack(ff, fb, fn, code, clen):
	'''
	給正反檔及行號檔
	測試行號索引是否正確
	'''
	ff = open(ff, 'rb')
	fb = open(fb, 'rb')
	f = open(fn, 'rb')
	i = 0
	length = 20		#讀幾個 bytes
	while f.tell() < os.stat( fn )[6]:
		i += 1
		tmp = unpack( "17sII", f.read(28) )
		if tmp[0].replace('\x00', '') == 'lc003.txt' or tmp[0].replace('\x00', '') == 'xs008.txt':
			ff.seek(tmp[1])
			n1 = ff.read(length).decode(code)
			fb.seek(tmp[2] + clen - length)		# +clen 因為檔首有 BOM 檔尾沒有
			n2 = fb.read(length).decode(code)
			print i, tmp[0]
			print n1.replace('\n', u"\u204B "), tmp[1]
			print n2.replace('\n', u"\u204B "), tmp[2]
			raw_input()
	f.close()
	fb.close()
	ff.close()


def preparseCorpus(orgf, org_code, newf, new_code):
	'''
	orgf: 檔案來源資料夾陣列
	newf: 新檔案儲存位置（正向檔、反向檔、檔名對應offset索引）
	'''
	if new_code == 'utf32':
		clen = 4
	elif new_code == 'utf16':
		clen = 2
	elif new_code == 'ascii':
		clen = 1
	else:
		print 'please set the encode of new file to "utf16", "utf32", or "ascii".'
		print 'ex. preparseCorpus( ["corpus_path/"], "utf8", "new_file_path/", "utf16" )'
		return 1
	L = []
	for k in orgf:
		tmp = getFiles(k)
		tmp.sort()
		L.extend(tmp)
	
	if len(L) == 0:
		print 'Wrong: No files in %s!' % orgf
		sys.exit()
	
	if os.path.isdir(newf):
#		print 'Warning: %s is exist!\n Press "enter" to CLEAN it and Continue ...\n Press "Ctrl+c" to Exit.' %  newf
#		raw_input()
		os.system('rm -rf '+newf)
	os.mkdir(newf)
	
	print 'Step1/3: gathering all files ...'
	Ts = time()
	obj = TextParser(newf)
	n = obj.run(L, org_code, new_code, clen)
	Te = time()
	
	print strftime('%H:%M:%S', gmtime(Te-Ts))
	n = list(n)
	n.append(clen)
	return n			#回傳 ( 正檔名, 反檔名, 檔案大小（offset 大小）, 行號索引檔名, 內定索引長度 )


if __name__ == "__main__":

#	測試正反檔及行號索引
#	readLBpack('./index/test1/Text_f','./index/test1/Text_b','./index/test1/Text_lb')
#	raw_input()
	
#	建正反擋及副索引（行號、缺字、版本）
#	get the list of files
	"""
	path = 'sources/'
	folders = [path+'hlm']
	nfolders = []
	for k in folders:
		tmp = convertFiles2utf16(k, 'utf8')
		nfolders.append(tmp)
	"""	
	orgfiles = ['../../cnlstk/sources/lcj_utf16']
	newfolder = '../../cnlstk/index/test7'
	preparseCorpus(orgfiles, 'utf16', newfolder, 'utf32')
	