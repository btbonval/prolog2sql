# Copyright 2020 Bryan Bonvallet.
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Database():
    tables = {}
    engine = None
    session = None
    aliases = {}
    parameters = {}

    def __init__(self):
        class Symbol(Base):
            __tablename__ = 'symbol'
            id = sa.Column(sa.Integer, primary_key=True)
            symbol = sa.Column(sa.String(140))
            arity = sa.Column(sa.Integer) # smallint?

        sa.schema.Index('symbol_arity', Symbol.symbol, Symbol.arity)
        
        self.tables[0] = Symbol
        
        for i in range(1,5):
            #class fact(Base):
            #    __tablename__ = 'fact_{}ary'.format(i)
            #    functor_id = sa.Column(sa.Integer, sa.ForeignKey(Symbol.id), primary_key=True) # FK symbol.id
            class_name = "Fact{}".format(i)
            fact = type(class_name, (Base,), {
              "__tablename__": 'fact_{}ary'.format(i),
              "functor_id": sa.Column(sa.Integer, sa.ForeignKey(Symbol.id), primary_key=True), # FK symbol.id
            })

            for j in range(0,i):
                setattr(fact, 'arg{}_id'.format(j+1), sa.Column(sa.Integer, sa.ForeignKey(Symbol.id), primary_key=True)) # FK symbol.id
            self.tables[i] = fact
    
    def build(self, resource, debug=False):
        self.engine = sa.create_engine(resource, echo=debug)
        Base.metadata.create_all(self.engine)
        self.begin()

    def output_rows(self, result):
        if result.returns_rows:
           bools = False
           rkeys = result.keys()
           # TODO this might only work when SQLite
           if len(rkeys) == 1 and rkeys[0].startswith('count'):
               bools = True
           for row in result.fetchall():
               if bools:
                   print('% {}'.format('yes' if row[0] else 'no'))
               else:
                   results = []
                   for i in range(0,len(rkeys)):
                       results.append(' {} = {}'.format(rkeys[i], row[i]))
                   print('%' + ','.join(results))

    def execute(self, query, **kwargs):
        x_keys = []
        for key in kwargs:
            if key not in self.parameters:
                print("Extraneous key {} included in execute()".format(key))
                x_keys.append(key)
        for key in x_keys:
            del kwargs[key]
        ## TODO no way to tell from query what parameters are required without a lot of work.
        ## and passing them in would be redundant with supplying them as kwargs anyway.
        #for key in self.parameters:
        #    if key not in kwargs:
        #        raise Exception("Required parameter {} missing from execute()".format(key))
        with self.engine.connect() as cnxn:
            result = cnxn.execute(query, **kwargs)
        self.output_rows(result)

    def add(self, obj):
        self.session.add(obj)

    def begin(self):
        self.session = sa.orm.sessionmaker(bind=self.engine)()

    def commit(self):
        self.session.commit()
        self.aliases = {}
        self.parameters = {}

    def query(self, *args, **kwargs):
        return self.session.query(*args, **kwargs)

    def new_alias(self, table, key=None):
        if table not in self.aliases:
            self.aliases[table] = {'_max': 0}
        if not key:
            m = self.aliases[table]['_max']
            key = m
            self.aliases[table]['_max'] = m+1
        alias = sa.orm.aliased(table)
        self.aliases[table][key] = alias
        return alias

    def get_alias(self, table, key):
        return self.aliases[table][key]

    def get_parameter(self, rule, name):
        key = str((rule,name))
        if key not in self.parameters:
            self.parameters[key] = sa.sql.bindparam(key)
        return self.parameters[key]

    def count(self, *args, **kwargs):
        return sa.func.count(*args, **kwargs)
