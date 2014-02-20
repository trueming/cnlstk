#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2006 summer) at The Chung Hwa Institute of Buddhist Studies
Updated by TRuEmInG (2010 fall) at NTU ESOE for CNLSTK
"""

import codecs, re, os, cPickle
from struct import *
from time import time, strftime, gmtime

def checkChineseUnicode(char):
	#檢查字碼是否在中文Unicode範圍內, 不包含標點符號與注音符號
	#2e80 2fd5: 部首
	#3400 9fa5: 中文字集
	#f900 fa2d: 韓文後面又有一些中文字集

	#	if checkChineseUnicode(k)=="yes" and k!=u'\u7684' and k!=u'\u662f' and k!=u'\u6709' and k!=u'\u4e00':	#只處理中文字碼, 略過 "的,是,有,一"

	if(char >= u'\u2e80' and char <= u'\u2fd5') or \
		(char >= u'\u3400' and char <= u'\u9fa5') or \
		(char >= u'\uf900' and char <= u'\ufa2d'):
		return "yes"

class SFTools:
	'''
	Class for create, check and search in index, Signature Files.
	'''
	
	def __init__(self, folder):
		self.Dic_uni = {}				#單字詞的dictionary
		self.Dic_bi = {}				#雙字詞的dictionary
		self.No_uni = 1000			#單字詞Signature Files 的數量
		self.No_bi = 5000			#雙字詞Signature Files 的數量
		self.Word_combine = {}	#組字式紀錄
			
		self.Filelist = []				#取得所有檔案陣列
		self.__getFiles(folder)
		self.Filelist.sort()

	def __getFiles(self, folder):
		#取得一目錄下所有要統計 Signature Files 的檔案
		#folder: 來源最高的目錄
		if folder[-1] != "/":
			folder = folder + "/"

		Li = os.listdir(folder)
		for k in Li:
			if os.path.isdir(folder+k):
				self.__getFiles(folder+k+'/')
			else:
				self.Filelist.append(folder+k)

	def __c_mul(self, a, b):
		return eval(hex((long(a) * b) & 0xFFFFFFFFL)[:-1])

	def __uni2ord(self, uni, ot):
		#將單字與雙字辭unicode字碼轉為位元, 再取得餘數
		#uni: unicode字串
		#ot: ot='one' 單字辭; ot='two' 雙字詞
	
		if ot == "one":
			cc = ord(uni)
			cc = cc % self.No_uni		#當代文獻單字辭建1000 signature
		if ot == "two":
			#cc = (ord(uni[0])<<8) + ord(uni[1])
			#cc = ord(uni[0]) + ord(uni[1])
			cc = ord(uni[0])<<7
			for char in uni:
				cc = self.__c_mul(1000003, cc) ^ ord(char)
			cc = cc ^ len(uni)
			if cc == -1:
				cc = -2
			cc = cc % self.No_bi		#當代文獻雙字詞用5000 signature
			if cc < 0:
				print uni
				raw_input()
		return cc

	def getSFiles(self, uni_folder, bi_folder, encode='utf8'):
		#建立單字及雙字的 Signature Files
		#source_folder : 所有檔案所在資料夾
		#uni_folder / bi_folder: 輸出 Signature Files 的資料夾
	
		fc = 0
		i = 0
		tot_fc = len(self.Filelist)
		for fn in self.Filelist:
			i += 1
			print i, '/', tot_fc, ' ...file count / total files'
			
			f = codecs.open(fn, 'r', encode)
			#單字詞
			tmp_uni = []		#同一檔案中, 儲存出現過的字, 避免對相同的字做動作(比對相同字碼跳過)
			for line in f:
				'''
				chk = re.findall(r'\[[^\]]*[\?\+\-\*/@][^\]]*\]', line)
				if chk != []:	#有組字式
					for cw in chk:
						if cw not in self.Word_combine:
							self.Word_combine[cw] = [fn]
						else:
							if fn not in self.Word_combine[cw]:
								self.Word_combine[cw].append(fn)
					line = re.sub(r'\[[^\]]*[\?\+\-\*/@][^\]]*\]', '', line)
				'''
				
				for k in line:
					if checkChineseUnicode(k)=="yes":
						if k in tmp_uni:
							continue
						else:
							tmp_uni.append(k)
						gcc = self.__uni2ord(k, "one")	#取得該字的餘數
#						print k, gcc
#						raw_input()

						if gcc not in self.Dic_uni:				#新的字先給一個值 "0"
							self.Dic_uni[gcc] = 0
						#原來的值與新的值做聯集. 新的值為 "1"向左移fc個位置(fc=0, 移0個位置=沒移動=>第一個檔案)
						#輸出的signature files第一個檔案在最右邊, 最後一個檔案再最左邊
						self.Dic_uni[gcc] = self.Dic_uni[gcc] | (1 << fc)
#						print len(self.Dic_uni), self.Dic_uni[gcc]
#						raw_input()
			tmp_uni = []			
#			print "uni-gram ok!"

			#雙字詞
			f.seek(0)
			tmp_bi = []
			bgw = ''
			for line in f:
				for k in line:
					if checkChineseUnicode(k)=='yes':	#只處理中文
						if bgw == '':
							bgw = k
							continue
						bgw = bgw+k			#取得雙字詞
						if bgw in tmp_bi:	#重複的雙字詞跳過不處理
							bgw = k
							continue
						else:
							tmp_bi.append(bgw)
						gcc = self.__uni2ord(bgw, "two")	#取得雙字詞的餘數
#						print bgw, gcc
#						raw_input()
						
						if gcc not in self.Dic_bi:
							self.Dic_bi[gcc] = 0
						self.Dic_bi[gcc] = self.Dic_bi[gcc] | (1 << fc)
#						print len(self.Dic_bi), self.Dic_bi[gcc]
#						raw_input()
						bgw = k
					else:
						bgw = ''
			
			fc += 1	#檔案loop累計

#			print "bi-gram ok!"
			f.close()
		
		print "outputing ..."
		rst = self.__outputSFiles(uni_folder, self.No_uni, self.Dic_uni)
		rst = self.__outputSFiles(bi_folder, self.No_bi, self.Dic_bi)
		
		return ( len(self.Dic_uni), len(self.Dic_bi), len(self.Word_combine) )
		
	def __outputSFiles(self, folder, no, dic):
		#輸出 getSFiles() 的 Signature Files
		#輸出組字式資料

		if os.path.isdir(folder):		#先檢查建資料夾, 存放所有結果
			pass
		else:
			os.mkdir(folder)
		
		if folder[-1] != "/":
			folder = folder + "/"
		
		for k in range(no):
			if k not in dic:
				continue
			fw = open(folder+str(k), 'w')
			cPickle.dump(dic[k], fw)
			fw.close()
		
		'''
		fw = codecs.open('./combineWord', 'w', 'utf8')
		for k in self.Word_combine:
			fw.write(k+"\t")
			for ks in self.Word_combine[k]:
				fw.write(ks+",")
			fw.write("\n")
		fw.close()
		'''
		
		return "ok"

	def checkSFiles(self, w, uni_SF, bi_SF):
		#取得單字詞及雙字詞的編號與 Signature Files
		#傳入字串(多個字串用分號隔開), 及單字與雙字 Signature Files 的目錄位置
		
		L = w.split(";")
		for k in L:
			if k == "":
				continue
			if len(k) == 1:
				ww = self.__uni2ord(k, "one")
				try:
					f = open(uni_SF+str(ww))
					l = cPickle.load(f)
					f.close()
					print "(%s, %d) %d" % (k, ww, l)
				except:
					print "(%s, %s) not in Signature Files" % (k, ww)
			elif len(k) == 2:
				ww = self.__uni2ord(k, "two")
				try:
					f = open(bi_SF+str(ww))
					l = cPickle.load(f)
					f.close()
					print "(%s, %d) %d" % (k, ww, l)
				except:
					print "(%s, %s) not in Signature Files" % (k, ww)
			else:
				print "(%s, none) only uni_gram or bi_gram in Signature Files." % k

	def doSearch(self, term, SF_u, SF_b, encode='utf8'):
		u = []
		b = []
		tmp_k = ''
		for k in term:
			u.append([k, self.__uni2ord(k, 'one')])
			if tmp_k != '':
				tmp_k += k
				b.append([tmp_k, self.__uni2ord(tmp_k, 'two')])
			tmp_k = k

		if SF_u[-1] != '/':
			SF_u += '/'
		if SF_b[-1] != '/':
			SF_b += '/'
		
		self.countSF = {}
#		for k in u:
#			if os.path.exists( SF_u + str(k[1]) ) == True:
#				self.__countSF(k[0], SF_u + str(k[1]))
		for k in b:
			if os.path.exists( SF_b + str(k[1]) ) == True:
				self.__countSF(k[0], SF_b + str(k[1]), encode)
			
		L = self.countSF.items()
		L.sort(lambda x,y: cmp(x[1], y[1]))
		print len(L)
		for k in L:
			if k[1] <= 2:
				continue
			print k[0], k[1]
			raw_input()
		
	def __countSF(self, kw, SF, encode):
		f = open(SF)
		SF = cPickle.load(f)
		f.close()

#		for k in range(len(self.Filelist)):
		for k in range(2471):
			if SF & 1 == 1:
#				print self.Filelist[k], kw.encode('cp950')
#				raw_input()
				f = codecs.open(self.Filelist[k], 'r', encode)
				l = f.read()
				f.close()
				if kw in l:
#					print self.Filelist[k]
#					raw_input()
					if self.Filelist[k] not in self.countSF:
						self.countSF[self.Filelist[k]] = 1
					else:
						self.countSF[self.Filelist[k]] += 1
			SF = SF >> 1
		


if __name__ == '__main__':
	T_1 = time()
	
	source_path = 'sources/xsfh_utf16'
	encode = 'utf16'
	SF_path_u = 'index/test1/SFu/'
	SF_path_b = 'index/test1/SFb/'
	
	obj = SFTools(source_path)

#	print len(obj.Filelist)
#	for k in obj.Filelist:
#		print k,

#	rst = obj.getSFiles( SF_path_u, SF_path_b, 'utf16' )
#	print "No. of uni_gram: %d, bi_gram: %d, combine_word: %d" % (rst[0], rst[1], rst[2])
		
#	obj.checkSFiles(u"研;縮回;鳥", SF_path_u, SF_path_b)
	
	rst = obj.doSearch(u'縮回', SF_path_u, SF_path_b, 'utf16')
#	for k in rst:
#		print k
	
	T_2 = time()
	print T_2, T_1
	print strftime('%H:%M:%S', gmtime(T_2-T_1))
	