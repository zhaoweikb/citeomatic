#!/usr/bin/env python
import json
import os
import random
import time

from citeomatic import features
from citeomatic.common import FieldNames
from citeomatic.corpus import Corpus


def _time(op):
    st = time.time()
    r = op()
    ed = time.time()
    print(op, ed - st)
    return r


WORDS = '''
Ashikaga
Boone's
Charybdis's
Decker
Eurasia
Gounod
Idaho's
Keven
Lubavitcher
Merck's
Nisan
Platonist
Rowling's
Soave's
Tomas
Wilkes
accretion
agreeably
anguishing
armor
avenues
bassoon
bier's
bobs
brightest
bystander's
carpetbags
charbroiling
civilian
collaboration
condition's
convincingly
crankcases
curtsying
deeper
designate
disbursements
divorce
duckbill's
elliptical
enviously
exiling
fateful
fixture
forces
fulcra
geologic
graffiti
gyration's
hearten
homeyness's
hyphenated
inbreed
injections
inundate
jubilantly
lamebrain
liberalism
loss
manna
memorials
miscasting
mortifies
naturalistic
noses
opened
overpopulation's
parqueted
perform
pillow
politest
preferable
pronoun
pyjamas's
rattles
referees
representation's
rhino's
rumples
scarcity's
seldom
shipments
sizes
sneeringly
speakers
stake
stratums
summoning
synthetic's
tenderness's
tingle
transiting
turncoat
uneasily
urchin's
violets
wayfaring's
wintertime
zaniest
'''.split('\n')

WORDS = WORDS * 100
print(len(WORDS))


def build_test_corpus(source_file, target_file):
    try:
        os.unlink(target_file)
    except:
        pass

    with open(source_file, 'w') as tf:
        for i in range(100):
            json.dump({
                FieldNames.TITLE: ' '.join(random.sample(WORDS, 10)),
                FieldNames.ABSTRACT: ' '.join(random.sample(WORDS, 1000)),
                FieldNames.AUTHORS: [],
                FieldNames.OUT_CITATIONS:[
                    str(x) for x in random.sample(range(1000), 10)
                ],
                FieldNames.YEAR: 2011,
                FieldNames.PAPER_ID: str(i),
                FieldNames.VENUE:''
            }, tf
            )
            tf.write('\n')

    Corpus.build(target_file, source_file)


def test_corpus_conversion():
    build_test_corpus('/tmp/foo.json', '/tmp/foo.sqlite')


def test_data_gen():
    build_test_corpus('/tmp/foo.json', '/tmp/foo.sqlite')
    corpus = Corpus.load('/tmp/foo.sqlite')
    featurizer = features.Featurizer(
        allow_duplicates=False
    )
    featurizer.fit(corpus, max_df_frac=1.0)
    dg = features.DataGenerator(corpus, featurizer)
    gen = dg.triplet_generator(
        paper_ids=corpus.train_ids,
        candidate_ids=corpus.train_ids,
        batch_size=128,
        neg_to_pos_ratio=5
    )

    for i in range(100):
        print(i)
        next(gen)


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-s'])
