#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
Created by TRuEmInG (2011 summer) at NTU ESOE for CNLSTK
"""

from tools import *
from utility import *

def help(opt=''):
	if opt == 'quick':
		print '''
Chinese Nautral Language Statistical Toolkit

Package: cnlstk

Function:
	convertFiles2utf16( 'folder', 'encode' )
	
Class: Index
	Function:
		makeSuffixArray( src_folders, src_encode, index_folder, index_encode, opt=0, opt='off' )
	Example:
		obj = cnlstk.Index()
		
		# Case 1:
		# Source files, encoded by 'utf8', are prepared in 'path_1' and 'path_2'.
		# Indexes are going to be built in 'path_new' and using 'utf16' environment.
		obj.makeSuffixArray( ['path_1','path_2'], 'utf8', 'path_new', 'utf16' )
		
		# Case 2:
		# Source files, encoded by 'ascii', and prepared in 'path'.
		# Indexes are going to be built in 'path_new' and using 'ascii' environment.
		# The script is indexing 4 bytes (4 alphabet) at a time.
		obj.makeSuffixArray( ['path'], 'ascii', 'path_new', 'ascii', 4 )

Class: Search
	Function:
	obj = cnlstk.Search()
	obj.getStrCount( u'string' )
	obj.getSectionInf()
	obj.getStrDistr( u'string' )
	obj.getFullTexts( 'file_name' )
	obj.getFullstxeT( 'file_name' )
	obj.getConcordance( u'string' )
	obj.getConcordanceBK( u'string' )
	obj.subConcordance( u'string', ['file_name1','file_name2'] )
	obj.subConcordanceBK( u'string', ['file_name1','file_name2'] )
	obj.getNextWords( u'string' )
	obj.getPreWords( u'string' )
	obj.getNextWordsInf( u'string' )
	obj.getPreWordsInf( u'string' )
	obj.getDistances( u'str1', u'str2' )
~EOF~
		'''
	elif opt == 'zh' or opt == 'chi':
		print '''
中文自然語言檢索統計工具
Chinese Nautral Language Statistical Toolkit

Package: cnlstk

Function:
	- convertFiles2utf16( folder, encode )
		folder (str)	-> 放純文字檔的資料夾
		encode (str)	-> 純文字檔的編碼形態 如：'utf8', 'cp950', 'big5'
		回傳轉好的檔案位置
	Example:
		rst = cnlstk.convertFiles2utf16( './your_path/', 'utf8' )
			
class: Index, Search
	Index
		- makeSuffixArray( folders, index_path )
			folders (list)		-> 一個以上存放 utf16 編碼的純文字檔資料夾
			index_path (str)	-> 索引檔案欲放置的新資料夾
			回傳 dictionary 說明建好檔案的檔名
		Example:
		obj = cnlstk.Index()
		rst = obj.makeSuffixArray( ['./files_path1/','./files_path2/'], './your_path/' )
		
	Search
		- getStrCount(string, [opt])
			string (str)	-> 查詢字串總數
			opt = 'all'		-> 多取得該字串索引起始位置
			回傳總數的 integer 或 opt='all' 時回傳 (總數,offset) 的陣列
		Example:
		obj = cnlstk.Search( './index_path/' )
		rst = obj.getTotalNo(u'字串')
		
		- getSectionInf([opt])
			opt = 'ofst'
			回傳 dictionary。keys 是檔名；values 是檔案的字數。opt='ofst' 的話 values 是檔案的起始 offset
					
		- getStrDistr(string)
			string (str)	-> 取得字串分布在每個檔案中的數量
			回傳 dictionary。keys 是檔名；values 是字頻
				
		- getFullTexts(file_name)
			file_name (str)	-> 檔案名稱（與建索引前的檔名相同）
			回傳檔案文字內容
			
		- getFullstxeT(file_name)
			file_name (str)
			回傳檔案反向文字內容
		
		- getConcordance(string, [addw])
			string (str)	-> 取得字串的語用排序
			addw (int)		-> 設定顯示字串前後多少個字 內定為前後各 10 個字
			回傳一個二維陣列 [ [字串結果, 出現檔名], ... ]
			
		- getConcordanceBK(string, [addw])
			同上，反向結果
			
		- subConcordance(string, file, [addw])
			string (str)	-> 與 getConcordance() 的參數相同
			file (str)		-> 檔名陣列
			addw (int)		-> 與 getConcordance() 的參數相同
			回傳限定檔名中的 concordance 結果
		
		- subConcordanceBK(string, file, [addw])
			同上，反向結果
		
		- getNextWords(string, [len])
			string (str)	-> 檢索輸入字串的下一個字及其數量
			len (int)		-> 下一個字的長度 內定為 1
			回傳二維陣列 [ [u'字', 4], ... ]
			
		- getPreWords(string, [len])
			同上，回傳前一個字的資訊
			
		- getNextWordsInf(string, [len])
			string (str)	-> 取得輸入字串下一個字的統計資訊
								1.不重複的下一個字的數量
								2.下一個字非中文的數量
								3.不重複的下一個字中最高的數量
			len (int)		-> 下一個字的長度 內定為 1
			回傳 dictionary。keys 是說明文字；values 是值
		
		- getPreWordsInf(string, [len])
			同上，回傳前一個字的資訊
		
		- getDistances(str1, str2, [limit])
			str1 (str)	-> 字串 1
			str2 (str)	-> 字串 2
			limit (str)	-> 指定檔名 內定是所有檔案
			回傳二維陣列
				list[0] 是字串 1,2 的 offsets 升冪排序結果
				list[1] 標示 list[0] 裡面的 offsets 是字串 1 或 2。字串 1 = 0，字串 2 = 1
				example:
					[0, 124, 342, 760, 1228, 30406]
					['s', 1,   0,   1,    1,   'e']
					's' 與 'e' 代表檔案開始與結束
（完）
'''
	else:
		print '''
Chinese Nautral Language Statistical Toolkit

Package: cnlstk

Function:
	- convertFiles2utf16( folder, encode )
		folder (str)	-> The folder within all fulltexts files
		encode (str)	-> The encode of fulltexts in the folder
		Return a python list of created file_names
	Example:
		rst = cnlstk.convertFiles2utf16( './your_path/', 'utf8' )
			
class: Index, Search
	Index
		- makeSuffixArray( folders, index_path )
			folders (list)		-> Folders within fulltext "utf16" files
			index_path (str)	-> The path for saving index files
			Return a python dictionary of created file_names(index) in the "index_path"
		Example:
		obj = cnlstk.Index()
		rst = obj.makeSuffixArray( ['./files_path1/','./files_path2/'], './your_path/' )
		
	Search
		- getStrCount(string, [opt])
			string (str)	-> get the word count of the gaven string
			opt = 'all'		-> get word count and first offset in the index
			Return a integer or a python list (opt='all')
		Example:
		obj = cnlstk.Search( './index_path/' )
		rst = obj.getTotalNo(u'字串')
		
		- getSectionInf([opt])
			opt = 'ofst'
			Return a python dictionary. keys: file_names, values: char-counts or start offsets of files
					
		- getStrDistr(string)
			string (str)	-> get the frequency distribution of the gaven string in all indexed files
			Return a python dictionary. keys: file_names, values: the string frequency
				
		- getFullTexts(file_name)
			file_name (str)	-> the same as the name before making Suffix Array
			Return fulltext of the gaven file_name
			
		- getFullstxeT(file_name)
			file_name (str)
			Return backward sequence fulltext of the gaven file_name
		
		- getConcordance(string, [addw])
			string (str)	-> get concordance of the gaven string
			addw (int)		-> the length of character adding before and after the gaven string (defult 10)
			Return a 2 dimension python list ordered as concordance. [ [sequence, file], ... ]
			
		- getConcordanceBK(string, [addw])
			Return backward concordance
			
		- subConcordance(string, file, [addw])
			string (str)	-> same as getConcordance()
			file (str)		-> a python list of file_names
			addw (int)		-> same as getConcordance()
			Return concordance of the gaven string in gaven files
		
		- subConcordanceBK(string, file, [addw])
			Return backward results of narrowConcordance()
		
		- getNextWords(string, [len])
			string (str)	-> get next characters and char-count of the gaven string
			len (int)		-> the length of next characters (defult 1)
			Return a 2 dimension python list. [ [u'字', 4], ... ]
			
		- getPreWords(string, [len])
			Return samething as getNextWords() but for pre-words
			
		- getNextWordsInf(string, [len])
			string (str)	-> get statistical information of next characters
								1.distict next word-count
								2.non-chinese next word-count
								3.the mix word-count of distict next words
			len (int)		-> same as getNextWords()
			Return a python dictionary. keys: intro text of each value, values: integer
		
		- getPreWordsInf(string, [len])
			Return samething as getNextWordCounts() but for pre-words
		
		- getDistances(str1, str2, [limit])
			str1 (str)	-> the first gaven string
			str2 (str)	-> the second gaven string
			limit (str)	-> the file_name (defult is in all files)
			Return a 2 dimension python list.
				list[0] is offsets of 2 gaven strs ordered by ASC
				list[1] is marks of 2 gaven strs 0 refers to str1 and 1 refers to str2
				example:
					[0, 124, 342, 760, 1228, 30406]
					['s', 1,   0,   1,    1,   'e']
					's' and 'e' refers to the begin and end of files (or a file)
~EOF~		
'''
