import MySQLdb

from db import MergeRequest
from config import *

db = MySQLdb.connect(host=MYSQL['host'],
        user=MYSQL['username'],
        passwd=MYSQL['password'],
        db=MYSQL['database'])

mreqs = MergeRequest(db, MERGER_USER_ID)
for req in mreqs:
    print req
