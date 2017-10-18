import logging
import sqlite3

import tqdm

from citeomatic import file_util
from citeomatic.common import FieldNames
from citeomatic.utils import batchify
from citeomatic.schema_pb2 import Document


def stream_papers(data_path):
    for line_json in tqdm.tqdm(file_util.read_json_lines(data_path)):
        citations = set(line_json[FieldNames.OUT_CITATIONS])
        citations.discard(line_json[FieldNames.PAPER_ID])  # remove self-citations
        citations = list(citations)
        yield Document(
            id=line_json[FieldNames.PAPER_ID],
            title=line_json[FieldNames.TITLE],
            abstract=line_json[FieldNames.ABSTRACT],
            authors=line_json[FieldNames.AUTHORS],
            citations=citations,
            year=line_json.get(FieldNames.YEAR, 2017),
            venue=None,
        )


def build_corpus(db_filename, corpus_json):
    """"""
    with sqlite3.connect(db_filename) as conn:
        conn.execute('PRAGMA synchronous=OFF')
        conn.execute('PRAGMA journal_mode=MEMORY')
        conn.row_factory = sqlite3.Row
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS ids (id STRING, year INT)'''
        )
        conn.execute(
            '''CREATE TABLE IF NOT EXISTS documents
                    (id STRING, year INT, payload BLOB)'''
        )
        conn.execute('''CREATE INDEX IF NOT EXISTS year_idx on ids (year)''')
        conn.execute('''CREATE INDEX IF NOT EXISTS id_idx on ids (id)''')
        conn.execute('''CREATE INDEX IF NOT EXISTS id_doc_idx on documents (id)''')

        for batch in batchify(stream_papers(corpus_json), 1024):
            conn.executemany(
                'INSERT INTO ids (id, year) VALUES (?, ?)',
                [
                    (doc.id, doc.year)
                    for doc in batch
                ]
            )
            conn.executemany(
                'INSERT INTO documents (id, payload) VALUES (?, ?)',
                [
                    (doc.id, doc.SerializeToString())
                    for doc in batch
                ]
            )

        conn.commit()


def load(data_path, train_frac=0.80):
    return Corpus(data_path, train_frac)


class Corpus(object):
    def __init__(self, data_path, train_frac):
        self._conn = sqlite3.connect(
            'file://%s?mode=ro' % data_path, check_same_thread=False, uri=True
        )
        self.train_frac = train_frac
        id_rows = self._conn.execute(
            '''
            SELECT id from ids
            ORDER BY year
        '''
        ).fetchall()
        self.n_docs = len(id_rows)

        self.all_ids = [str(r[0]) for r in id_rows]
        self._id_set = set(self.all_ids)
        n = len(self.all_ids)
        n_train = int(self.train_frac * n)
        n_valid = (n - n_train) // 2
        n_test = n - n_train - n_valid
        self.train_ids = self.all_ids[0:n_train]
        self.valid_ids = self.all_ids[n_train:n_train + n_valid]
        self.test_ids = self.all_ids[n_train + n_valid:]
        logging.info('%d training docs' % n_train)
        logging.info('%d validation docs' % n_valid)
        logging.info('%d testing docs' % n_test)

        logging.info("Loading documents into memory")
        self.documents = [doc for doc in self._doc_generator()]
        self.doc_id_to_index_dict = {doc.id: idx for idx, doc in enumerate(self.documents)}

    @staticmethod
    def load(data_path, train_frac=0.80):
        return load(data_path, train_frac)

    @staticmethod
    def build(db_filename, source_json):
        return build_corpus(db_filename, source_json)

    def _doc_generator(self):
        with self._conn as tx:
            for row in tx.execute(
                    'SELECT payload from documents ORDER BY year'
            ):
                doc = Document()
                doc.ParseFromString(row[0])
                yield doc

    def __len__(self):
        return self.n_docs

    def __iter__(self):
        for doc in self.documents:
            yield doc

    def __contains__(self, id):
        return id in self._id_set

    def __getitem__(self, id):
        index = self.doc_id_to_index_dict[id]
        return self.documents[index]

    def select(self, id_set):
        for doc in self.documents:
            if doc in id_set:
                yield doc.id, doc

    def filter(self, id_set):
        return self._id_set.intersection(id_set)
