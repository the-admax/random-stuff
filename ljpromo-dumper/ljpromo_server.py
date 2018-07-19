# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import json
import sqlite3
import logging
from collections import OrderedDict

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = None

def _db_col_opt(fspec):
  _DB_TYPES = {
    int: 'INT',
    str: 'STRING',
    }

  return "%s %s " % (
    _DB_TYPES[fspec[0]],
    fspec[1] if len(fspec) > 1 else '')


# Form a DB of recent posts
SCHEMA = {
  'posts': OrderedDict([
    ('id',          (int, 'PRIMARY KEY')),
    ('journal_id',  (int, )),
#    ('title',       (str, )),
    ('url',         (str, )),
    ('reply_count', (int, )),
#    ('username',    (str, )),
    ('pub_date',    (str, )),
    ('subject',     (str, )),
    ('body',        (str, ))]),

  'journals': OrderedDict([
    ('id',  (int, 'PRIMARY KEY')),
    ('promo_id',    (int, )),
    ('url',         (str, )),
    ('title',       (str, )),
    ('username',    (str, )),
  ])
}

def _create_tables(db, schema):
  for name, fields in schema.items():
    db.cursor().execute("CREATE TABLE IF NOT EXISTS {name} ({fields})"
      .format(
        name=name,
        fields=", ".join([
        "%s %s" % (name, _db_col_opt(fspec)) for name, fspec in fields.items()
        ])
      )
    )

def _insert_record(db, tbl_name, record):
  global n_posts
  db.cursor().execute("INSERT OR REPLACE INTO {tbl_name} VALUES ({v})".format(
      tbl_name=tbl_name,
      v='?' + ', ?'*(len(SCHEMA[tbl_name]) - 1),
    ),
    [ record.get(name, '') for name in SCHEMA[tbl_name].keys() ]
  )


class UploaderHandler(tornado.web.RequestHandler):
  def get(self):
    self.set_header("Content-Type", "text/plain")
    self.finish('For script')

  def post(self):
    global db
    items = json.loads(self.get_argument('items'), encoding='utf-8')
    type = self.get_argument('type')
    if type == 'entry':
      for item in items:
        _insert_record(db, 'posts', item)
    elif type == 'journal':
      for item in items:
        _insert_record(db, 'journals', item)
    elif type == '1':
      for item in items:
        print(item)
    else:
      raise NotImplementedError()
    db.commit()
    logger.info("%d items successfully added" % len(items))

    self.set_header("Content-Type", "text/plain")
    self.finish(json.dumps({'status': 'ok', 'items_saved': len(items)}))


application = tornado.web.Application([
  (r"/save-items", UploaderHandler),
  ])

if __name__ == "__main__":
  db = sqlite3.connect('ljposts.db')
  _create_tables(db, SCHEMA)

  application.listen(8080)
  tornado.ioloop.IOLoop.instance().start()

