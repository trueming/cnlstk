#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
Updated by TRuEmInG (2011 spring) at NTU ESOE for CNLSTK
"""

import os, re


def getFiles( folder ):
	'''
	傳入路徑
	回傳該路徑下所有檔案名稱陣列
	'''
	if folder[-1] != '/': folder += '/'
	Li = os.listdir( folder )
	L = []
	for k in Li:
		if os.path.isdir( folder+k ): L += getFiles(folder+k+'/')
		else: L.append(folder+k)
	L.sort()
	return L

def countStrLen(strg):
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
	
def chkChinese(n):
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

def chkChineseCB(n):
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

def tackoutPunctuation(text):
	'''
	去掉中文標點符號，檢索無標點內文時用
	資訊來自 CBETA 字元統計表
	3000~301F: CJK Symbols & Punctuation
	FF01:！, FF08:（, FF09:）, FF0C:，, FF0D:－, FF0E:．, FF1A:：, FF1B:；, FF1D:＝, FF1F:？
	'''
	puncs = ur'[、。〈〉《》「」『』【】〔〕！（），－．：；＝？]'
	return re.sub(puncs, '', text)

def convertFiles2utf16(folder, code): __convertFiles(folder, code, 'utf16')

def convertFiles2utf32(folder, code): __convertFiles(folder, code, 'utf32')

def __convertFiles(folder, org_code, new_code):
	'''
	將檔案轉存成 utf16 or utf32
	folder: 檔案存放的資料夾
	org_code: 原來的編碼方式
	new_code: 新的編碼方式
	'''

	if folder[-1] == '/':
		nfolder = folder[:-1] + '_%s/' % new_code
	else:
		nfolder = folder + '_%s/' % new_code

	if not os.path.isdir(nfolder):
		os.mkdir(nfolder)
	
	Lw = []
	L = getFiles(folder)
	i = 0
	for fn in L:
		try:
			f = codecs.open(fn, 'r', org_code)
			l = f.read()
			f.close()
		
			n = os.path.split(fn)[1]
			fw = codecs.open(nfolder+n, 'w', new_code)
			fw.write(l)
			fw.close()
			i += 1
		except:
			Lw.append(fn)
	
	print i, 'files converted in %s' % nfolder
	if len(Lw) == 1:
		print '* one file convert failed. please see return list.'
	elif len(Lw) > 0:
		print '** %d files convert failed. please see return list.'
	else:
		pass
	return Lw


if __name__=='__main__':
	pass
	