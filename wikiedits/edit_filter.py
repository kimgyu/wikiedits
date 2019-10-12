# -*- coding: utf-8 -*-

from wikiedits.diff_finder import DiffFinder

import nltk.data
import Levenshtein
import math

import sentencepiece as sp
import os
import logging
log = logging.getLogger(__name__)

class Tokenizer(object):
    '''
    model is expected to be in default path
    feed path with
    '''
    def __init__(self, lang='english', tokenizer_model_path='../model/kobert-setencepiece.model'):
        self.lang = lang
        if self.lang == 'english' :
            self.tokenizer =  nltk.data.load('tokenizers/punkt/english.pickle')
        elif self.lang == 'korean' :
            path = os.path.abspath(tokenizer_model_path)
            sptk = sp.SentencePieceProcessor()
            sptk.load(path)
            self.tokenizer = sptk

    def tokenize(self, text):
        if self.lang == 'english':
            return [frag
                for sent in self.tokenizer.tokenize(text)
                for frag in sent.split('; ')]
        elif self.lang == 'korean':
            return self.tokenizer.EncodeAsPieces(text)


class EditFilter(object):

    def __init__(self,
                 lang='english',
                 min_words=15,
                 max_words=150,
                 length_diff=4,
                 edit_ratio_max=0.3,
                 edit_ratio_min=0.01,
                 min_chars=10,
                 ):

        self.tokenizer = Tokenizer(lang=lang)

        self.LEVENSHTEIN_RATIO_LOG_BASE = 20
        self.MIN_TEXT_LENGTH = min_chars                # in characters
        self.MIN_WORDS_IN_SENTENCE = min_words          # in words
        self.MAX_WORDS_IN_SENTENCE = max_words          # in words
        self.MAX_LENGTH_DIFF = length_diff              # on words
        self.MAX_LEVENSHTEIN_RATIO = edit_ratio_max         # on token
        self.MIN_LEVENSHTEIN_RATIO = edit_ratio_min  # on token

    def filter_edits(self, old_text, new_text):
        log.debug("processing texts:  >>> %s  >>> %s", old_text, new_text)
        if not self.__looks_like_text_edition(old_text, new_text):
            return []

        edits = []
        for old_sent, new_sent in self.__sentence_pairs(old_text, new_text):
            old_sent = old_sent.strip()
            new_sent = new_sent.strip()

            scores = self.__looks_like_sentence_edition(old_sent, new_sent)
            if not scores:
                continue
            log.debug("\tedit sentence:\n\told >>> %s\n\tnew >>> %s\nscores>>", old_sent, new_sent,scores)
            edits.append((old_sent, new_sent, scores))

        log.info("got %i edited sentence(s)", len(edits))
        return edits

    def __looks_like_text_edition(self, old_text, new_text):
        if not old_text or not new_text:
            log.debug("either old or new text fragment is empty")
            return False

        if old_text == new_text:
            log.debug("texts are equal")
            return False

        if len(old_text) < self.MIN_TEXT_LENGTH \
                or len(new_text) < self.MIN_TEXT_LENGTH:
            log.debug("either old or new text fragment is too short")
            return False

        return True

    def __looks_like_sentence_edition(self, old_sent, new_sent):
        if old_sent == new_sent:
            log.info("sentences are equal")
            return False

        old_tokens = self.tokenizer.tokenize(old_sent)
        new_tokens = self.tokenizer.tokenize(new_sent)

        counts = [len(old_tokens), len(new_tokens)]
        diff = abs(counts[0] - counts[1])

        if diff > self.MAX_LENGTH_DIFF:
            log.info("too large difference in number of words %i", diff)
            return False

        if min(counts) < self.MIN_WORDS_IN_SENTENCE:
            log.info("shorter sentence has too few words")
            return False

        if max(counts) > self.MAX_WORDS_IN_SENTENCE:
            log.info("longer sentence has too many words")
            return False

        # ratio, dist = self.__levenshtein_ratio(old_sent, new_sent)
        ratio, dist = self.__levenshtein_ratio(old_tokens, new_tokens)

        if ratio > self.MAX_LEVENSHTEIN_RATIO or ratio < self.MIN_LEVENSHTEIN_RATIO:
            log.debug('Levenshtein Edit Too high or Low')
            return False

        log.debug('Levenshtein Edit Valid')

        return (ratio, dist)

    '''
    return sentence pair (old,new) from wiki dump text
    '''
    def __sentence_pairs(self, old_frag, new_frag):

        old_sents = old_frag.split('\n')
        new_sents = new_frag.split('\n')

        min_size = min(len(old_sents), len(new_sents))
        for idx in range(min_size):
            log.debug("feeding sentences\nold >>> {}\nnew >>> {}".format(old_sents[idx], new_sents[idx]))
            yield (' '.join(old_sents[idx].split()),
                   ' '.join(new_sents[idx].split()))

    def __levenshtein_ratio(self, old_tokens, new_tokens):
        min_words_len = min(len(old_tokens), len(new_tokens))

        dist = Levenshtein.distance(''.join(old_tokens), ''.join(new_tokens))

        ratio = dist / float(min_words_len) * math.log(min_words_len,
                                                       self.LEVENSHTEIN_RATIO_LOG_BASE)

        return (ratio, dist)