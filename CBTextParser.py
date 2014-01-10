#!/usr/bin/env python
# -*- coding: utf-8 *-*
"""
Created by TRuEmInG (2008 fall) at NTU ESOE
Updated by TRuEmInG (2010~11 winter) at NTU ESOE for CNLSTK, Web API
"""

import codecs, os, re
from struct import *
from time import time, strftime, gmtime

from utility import *


class TextParser:
	'''
	將 CBETA XML檔案轉成欲建 Suffix Array 的連續文字
	去除原本換行、使用換行標記換行、處理標點符號、記錄內容標記位置（lb, dharani, lg, anchor...）
	一律輸出成 utf32 編碼檔案
	'''
	def __init__(self, location):
		'''
		location: 結果（與索引）存放位置
		'''
		if location[-1] == '/':			#統一參數（for os.path.split(), or location+'/...'）
			location = location[:-1]
		self.location = location		#結果（與索引）存放位置
		if not os.path.exists(self.location): os.mkdir(self.location)

	def __savelb( self, tag, offset ):
		'''
		處理儲存內容標記 lb
		fw.write( pack('17sI', str(line), f.tell()-2) )
		
		<lb ed="J" n="0643a11"/>
		<lb n="0081a01" ed="T"/>
		<lb ed="X" n="0001a04"/>
		'''
		if 'lb' not in tag:
			print self.cat, tag
			raw_input()
		
		if 'ed="T"' in tag or 'ed="J"' in tag or 'ed="X"' in tag:
			pg = re.findall(r'n="([^"]+)"', tag)
			if len(self.cat) == 8:
				val = self.cat + '_p' + pg[0]
			else:
				val = self.cat + 'p' + pg[0]
			self.fwl.write( pack('17sI', str(val), offset) )
		return


	def breakTags(self, text):
		'''
		去掉原本的換行符號，處理要斷行的及內容標記
		* 2010 P5 版請小花輸出的檔案中需要斷行的標記：<div>, <p>, <l>, <title>, <byline>, <docNumber>, <head>.
		* 改符號輸出後再處理的標記：p:dharani, lg
		* 可直接去除的標記：g （因有其他處理價值所以仍先請小花輸出，否則可不用輸出）
		* 先去除，之後再討論如何處理的標記：foreign, anchor
		'''
		text = text.replace('\n', '')
		text = re.sub(r'<\?[^>]+\?>', r'', text)		#第一行
		text = re.sub(r'<foreign[^>]+>', r'', text)
		text = re.sub(r'</foreign>', r'', text)
		text = re.sub(r'<anchor[^>]+>', r'', text)
		text = re.sub(r'<g[^>]+>', r'', text)
		text = re.sub(r'</g>', r'', text)
		
		text = re.sub(r'<lg[^>]+>|<lg>', ur'‹', text)
		text = re.sub(r'</lg>', ur'›', text)

		text = re.sub(r'<p[^>]+>', r'\n', text)
		text = re.sub(r'<div[^>]+>', r'\n', text)
		text = re.sub(r'<title[^>]+>', r'\n', text)
		text = re.sub(r'<byline[^>]+>', r'\n', text)
		text = re.sub(r'<docNumber[^>]+>', r'\n', text)
		text = re.sub(r'<head[^>]+>', r'\n', text)
		text = re.sub(r'<l [^>]+>', r'\n', text)
		text = re.sub(r'<div>|<l>|<p>|<title>|<byline>|<docNumber>|<head>', '\n', text)
		text = re.sub(r'</[^>]+>', '\n', text)
		text = re.sub(r'\n+', '\n', text)		#一個以上連續的換行符號全部換成一個
		return text
		

	def run(self, fL, coding, pun=0):
		'''
		合併原始文件群，輸出正反兩全文檔案（純文字＋換行）。
		忽略原檔所有換行符號，以內定 tags 為新換行點。換行 tags 如下:
		p, lg, l, title, byline, docNumber, head, div.（其中 <div> CBETA 文件無）
		
		記錄 lb, lg, dharani 三種內容標記的 offset
		
		texts = list of files
		coding = coding of input files
		pun = 0 keep punctuations, else erase punctuations.
		'''
		texts = []
		for fs in fL:
			l = getFiles(fs)
			texts.extend(l)
		texts.sort()
		print 'total %d files' % len(texts)
		
		fwf = codecs.open(self.location+'/Text_f', 'w', 'utf32')	#純文字檔
		self.fwl = open(self.location+'/Text_f_lb', 'wb')			#行號索引 lb
		self.fwl2 = open(self.location+'/Text_f_lb2', 'wb')			#經號索引 lb
		self.fwlg = open(self.location+'/sub_lg', 'wb')				#韻文索引
		self.fwd = open(self.location+'/sub_d', 'wb')				#咒語索引 
		os.mkdir( self.location+'/bktmpf' )							#反向檔暫存區
		
		offset = 4													#總 offset byte (BOM)
		
		#parse 每個檔案，文字累加存檔，處理標記
		fct = 0
		for k in texts:
			fct += 1
			if fct%300 == 0:
				print fct, '/', len(texts), 'parsed.'
			
			bkn = os.path.split(k)
			f_tmp = codecs.open(self.location+'/bktmpf/'+bkn[1], 'w', 'utf32')		#全文暫存，給反向檔 reverse()

			f_tmp.write('\n')
			fwf.write('\n')
			offset += 4
		
			f = codecs.open(k, 'r', coding)
			l = f.read()
			f.close()
			l = self.breakTags(l)
			if pun != 0: l = tackoutPunctuation(l)
			
			#檔案的 lb inedx
			self.cat = bkn[1].replace('.xml', '')
			self.fwl.write( pack('17sI', self.cat, offset) )
			self.fwl2.write( pack('17sI', self.cat, offset) )
			
			pre = '\n'					#記錄正要處理字元的前一個字元
			flag = 'off'				#記錄 lb tage 用
			dht = []					#記錄咒語位置用
			lgt = []					#記錄韻文位置用
			for w in l:					#陣列處理約比對檔案 binary 處理快 4 倍
				#遇到標記（lb, lg）
				if w == u'<':
					flag = 'on'
					tag = ''
					continue
				if w == u'>':
					flag = 'off'
					self.__savelb( tag, offset )
					continue
				if flag == 'on':
					tag += w
					continue
				
				#Dharani
				if w == u'‴':
					dht = [offset]
					continue
				if w == u'‷':
					if len(dht) != 1:
						print self.cat, 'Dharani wrong!'
						raw_input()
						
					dht.append(offset)
					self.fwd.write( pack('II', dht[0], dht[1]) )
					continue
				
				#lg
				if w == u'‹':
					lgt = [offset]
					continue
				if w == u'›':
					if len(lgt) != 1:
						print self.cat, 'lg wrong!'
						raw_input()
						
					lgt.append(offset)
					self.fwlg.write( pack('II', lgt[0], lgt[1]) )
					continue
				
				#多餘換行符號
				if w == '\n' and pre == '\n':		#雖然先處理過連續換行，處理完行號後還可能出現連續換行
					continue						#ex: \n(</title>)<lb.../>\n(<doc>)

				if ord(w) >= 0xD800 and ord(w) <= 0xDBFF:
					pre = w
					continue
				elif ord(w) >= 0xDC00 and ord(w) <= 0xDFFF:
					w = pre+w

				f_tmp.write(w)
				fwf.write(w)
				offset += 4
				pre = w

			f_tmp.write('\n')				#每個檔案頭尾都個加一個換行符號
			fwf.write('\n')
			offset += 4

			f_tmp.close()
		print fct, '/', len(texts), 'parsed.'
		
		fwf.close()
		self.fwl.close()
		self.fwl2.close()
		self.fwlg.close()
		self.fwd.close()
		
		print 'The foward fulltext file, Text_f, created!'
		print 'Creating backword fulltext ...'
		print self.__getBackwardFulltext(self.location+'/bktmpf', 'Text_b')

		print 'Updating all subindex ...'
		print self.__completeLBIndex(self.location+'/Text_f_lb', offset, 'sub_lb')
		print self.__completeLBIndex(self.location+'/Text_f_lb2', offset, 'sub_lb_sutra')
#		print self.__completeRangeIndex( self.location+'/Text_f_lg', offset, 'sub_lg' )
#		print self.__completeRangeIndex( self.location+'/Text_f_d', offset, 'sub_d' )
		#回傳 ( 正檔名, 反檔名, 檔案大小（offset 大小） ) 
		return self.location+'/Text_f', self.location+'/Text_b', offset

	
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
	

	def __getBackwardFulltext(self, folder, fn):
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
		
		fwb = codecs.open(self.location+'/'+fn, 'w', 'utf32')	#反向檔
		for k in L:
			f_tmp = codecs.open(k, 'r', 'utf32')
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
		return 'The backward fulltext file, %s, created!' % fn


	def __completeRangeIndex( self, FWsubindex, totalofst, fn ):
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
		
	def __completeLBIndex( self, FWsubindex, totalofst, fn ):
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
	
#	print TextParser.__doc__
#	print TextParser.getSuffixArray.__doc__
#	print TextParser.doSearch.__doc__

#	測試正反檔及行號索引
#	readLBpack('./SuffixArray/cbetat2/Text_f','./SuffixArray/cbetat2/Text_b','./SuffixArray/cbetat2/Text_lb')
#	raw_input()
	
	
#	建正反擋及副索引（行號、缺字、版本）
	sourcefolders = ['./xml_index_test']
	ifolder = './cbeta_index'
	
#	parse dataset create 2 main files and sub offset files.
	Ts = time()
	obj = TextParser(ifolder)			#ifolder: index 存放的資料夾
	n = obj.run(sourcefolders, 'utf8')
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
	