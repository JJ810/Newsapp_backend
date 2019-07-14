
import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.chunk import conlltags2tree, tree2conlltags

import spacy
from spacy import displacy
from collections import Counter
import os

try:
	import en_core_web_sm
except:
	import os
	os.system('python -m spacy download en_core_web_sm')
	import en_core_web_sm


class TagExtractorNLTK:
	def __init__(self, input_text):
		self.input_text = input_text
		try:
			nltk.pos_tag(nltk.word_tokenize('test phrase'))
			nltk.ne_chunk(pos_tag(word_tokenize('test phrase')))
		except:
			nltk.download('maxent_ne_chunker')
			nltk.download('words')

	def preprocess(self):
	    sent = nltk.word_tokenize(self.input_text)
	    sent = nltk.pos_tag(sent)
	    self.sent = sent

	def chunkparser(self, pattern='NP: {<DT>?<JJ>*<NN>}'):
		cp = nltk.RegexpParser(pattern)
		cs = cp.parse(self.sent)
		iob_tagged = tree2conlltags(cs)
		self.iob_tagged = iob_tagged

	def namedEntities(self, ex):
		ne_tree = nltk.ne_chunk(pos_tag(word_tokenize(self.input_text)))
		return ne_tree

	def extract_tags(self):
		self.preprocess()
		self.chunkparser()
		ner = self.namedEntities(self.input_text)
		tags = [tag[0] for tag in self.iob_tagged if tag[1] in ['NN', 'NNP']]
		return tags


class TagExtractorSpacy:
	def __init__(self, input_text):
		self.input_text = input_text
		self.nlp = en_core_web_sm.load()

	def documentize(self):
		self.doc = self.nlp(self.input_text)

	def extract_tags(self):
		self.documentize()
		return [X.text for X in self.doc.ents]
