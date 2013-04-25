#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

class DatabaseError(Exception):
    pass

class Model:
    _cursor = None
    _db = None
    _rows = []

    def __init__(self, db):
        self._db = db
        if db:
            self._cursor = db.cursor()
            self._cursor.execute("SET NAMES utf8;")

    def predict_table_name(self):
        def concat(c):
            return ''.join(['_', c.group(1).lower()])

        cls_name = self.__class__.__name__
        return ''.join([cls_name[0].lower(),
            re.sub(r'([A-Z])', concat, cls_name[1:]), 's'])

    def select(self, columns, table, where):
        return 'SELECT {0} FROM `{1}` WHERE {2}'.format(
                ','.join(columns), table, where)

    def execute(self, sql, params=None):
        row_nums = self._cursor.execute(sql, params)
        if row_nums:
            return self._cursor.fetchall()
        else:
            return []

    def fetch_by_ids(self, ids, columns=None, id_name='id'):
        table_name = None
        if hasattr(self, '_table'):
            table_name = self._table
        else:
            table_name = self.predict_table_name()

        if not columns and hasattr(self, '_columns'):
            columns = self._columns

        sql = None
        if type(ids) in (tuple, list, set):
            sql = self.select(columns, table_name,
                    '`{0}` IN ({1})'.format(id_name, 
                        ','.join(map(str, ids))))
        else:
            sql = self.select(columns, table_name,
                    '`{0}` = {1}'.format(id_name, ids))

        self._rows = self.execute(sql)

    def __nonzero__(self):
        return len(self._rows) > 0

    def __bool__(self):
        return len(self._rows) > 0

    def __len__(self):
        return len(self._rows)

    def __getitem__(self, idx):
        return dict(zip(self._columns, self._rows[idx]))

    def __iter__(self):
        for row in self._rows:
            yield dict(zip(self._columns, row))

class Project(Model):
    _table = 'projects'
    _columns = ['id', 'name', 'path', 'creator_id']

    def __init__(self, db, ids):
        Model.__init__(self, db)

        if ids:
            self.fetch_by_ids(ids)


class User(Model):
    _table = 'users'
    _columns = ['id', 'email', 'name', 'username']

    def __init__(self, db, ids):
        Model.__init__(self, db)

        if ids:
            self.fetch_by_ids(ids)

class MergeRequest(Model):
    _table = 'merge_requests'
    _columns = ['id', 'target_branch', 'source_branch', 'project_id',
            'author_id', 'assignee_id', 'title', 'created_at', 'state']

    def __init__(self, db, ids=None, assignee_id=None):
        Model.__init__(self, db)

        if assignee_id:
            self.fetch_by_assignee(assignee_id)
            return

        if ids:
            self.fetch_by_ids(ids)

    def fetch_by_assignee(self, assignee_id):
        sql = self.select(self._columns, self._table, 
                '`assignee_id` = %s AND `state` = "opened"')

        self._rows = self.execute(sql, (assignee_id))
