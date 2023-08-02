import sqlite3

con = sqlite3.connect('times.db')
cur = con.cursor()

cur.execute("DROP TABLE Times")
cur.execute("""CREATE TABLE Times WHERE NONE EXISTS
                (target text,
                type string,
                time float,
                bearer int,
                vpsNum int,
                code int,
                offset float
                CONSTRAINT checkType CHECK (type == \"send\" or type == \"receive\")
                );""")

cur.execute("""INSERT INTO Times (target, type, time, bearer, vpsNum, code, offset)
                    VALUES ("Test", "receive", 200, 1, 2, 200, 30.3)""")