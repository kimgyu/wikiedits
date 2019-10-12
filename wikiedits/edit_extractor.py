# -*- coding: utf-8 -*-

from wikiedits.diff_finder import DiffFinder
from wikiedits.edit_filter import EditFilter

import re
import logging
log = logging.getLogger(__name__)

class PreProcessor(object):
    def __init__(self, lang='korean'):
        self.lang = lang

    def __only_korean_allowed(self, text):
        #delete string in parentheses and parentheses
        tmp = re.sub(r'\([^)]*\)', '', text)
        #korean characters, digits, \., \,
        tmp = re.sub(r'[^ \u3131-\u3163\uac00-\ud7a3\d\.\,]+','', tmp)
        tmp = re.sub(r'(\d+)','쉟', tmp)
        tmp = re.sub(r' {2,}',' ',tmp)
        return tmp

    def preprocess(self,sentence):
        if self.lang == 'korean':
            return self.__only_korean_allowed(sentence)
        else :
            return sentence

class EditExtractor(object):

    def __init__(self, **kwargs):
        self.diff = DiffFinder()
        self.filter = EditFilter(**kwargs)
        self.lang = kwargs['lang']
        self.preprocessor = PreProcessor(self.lang)

    def extract_edits(self, old_text, new_text):

        # split wikidump paragraph to newline(\n) and dot(.)
        old_text_processed = [self.preprocessor.preprocess(d) for s in old_text.split("\n") for d in s.split('.')]
        new_text_processed = [self.preprocessor.preprocess(d) for s in new_text.split("\n") for d in s.split('.')]

        frags = self.diff.edited_fragments(old_text_processed,
                                           new_text_processed)

        # Generator is not used as it doesn't allow to check how many edits
        # have been returned.
        try:
            return [edit for frag_pair in frags
                         for edit in self.filter.filter_edits(*frag_pair)]
        except:
            return []
