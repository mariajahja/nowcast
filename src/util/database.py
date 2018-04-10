"""
===============
=== Purpose ===
===============

A simple wrapper for the nowcast database.


=======================
=== Data Dictionary ===
=======================

Nowcasts (value and standard deviation) are stored in the `nowcasts` table.
+----------+------------+------+-----+---------+----------------+
| Field    | Type       | Null | Key | Default | Extra          |
+----------+------------+------+-----+---------+----------------+
| id       | int(11)    | NO   | PRI | NULL    | auto_increment |
| epiweek  | int(11)    | NO   | MUL | NULL    |                |
| location | varchar(8) | NO   | MUL | NULL    |                |
| value    | float      | NO   |     | NULL    |                |
| std      | float      | NO   |     | NULL    |                |
+----------+------------+------+-----+---------+----------------+
id: unique identifier for each record
epiweek: the epiweek for which (w)ILI is being predicted
location: where the data was collected (nat, hhs, cen, and states)
value: nowcast point prediction
std: nowcast standard deviation
"""


# standard library
import time

# third party
import mysql.connector

# first party
from delphi.operations import secrets


class NowcastDatabase:
  """
  A database wrapper that provides an interface for updating the nowcast table.
  """

  SQL_INSERT = """
    INSERT INTO `nowcasts`
      (`epiweek`, `location`, `value`, `std`)
    VALUES
      (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      value = %s, std = %s
  """

  @staticmethod
  def new_instance(test_mode):
    """
    Return a new instance under the default configuration. If `test_mode` is
    true, database changes will not be committed.
    """
    return NowcastDatabase(mysql.connector, test_mode)

  def __init__(self, connector, test_mode):
    self.connector = connector
    self.test_mode = test_mode

  def connect(self):
    """Open a connection to the database."""
    u, p = secrets.db.epi
    self.cnx = self.connector.connect(user=u, password=p, database='epidata')
    self.cur = self.cnx.cursor()

  def disconnect(self):
    """
    Close the connection to the database. Unless test mode is enabled,
    outstanding changes will be committed at this point.
    """
    self.cur.close()
    if self.test_mode:
      print('test mode - nowcasts not saved')
    else:
      self.cnx.commit()
    self.cnx.close()

  def insert(self, epiweek, location, value, stdev):
    """
    Add a new nowcast record to the database, or update an existing record with
    the same key.
    """
    args = (epiweek, location, value, stdev, value, stdev)
    self.cur.execute(NowcastDatabase.SQL_INSERT, args)

  def set_last_update_time(self):
    """
    Store the timestamp of the most recent nowcast update.

    This hack was copied from the old nowcast.py, which has this to say:
    > Store the unix timestamp in a meta row representing the last update time.
    > The key to this row is `epiweek`=0, `location`='updated'. The timestamp
    > is stored across the `value` and `std` fields. These are 32-bit floats,
    > so precision is limited (hence, using both fields).
    """
    t = round(time.time())
    a, b = t // 100000, t % 100000
    self.insert(0, 'updated', a, b)

  def __enter__(self):
    self.connect()
    return self

  def __exit__(self, *error):
    self.disconnect()
