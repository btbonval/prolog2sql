# Copyright 2018 Bryan Bonvallet.
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

SETUP="""
CREATE TABLE symbol (id SERIAL PRIMARY KEY, symbol VARCHAR(140), arity SMALLINT);
CREATE INDEX symbol_arity ON symbol (symbol, arity);
CREATE TABLE pl_nullary (functor_id INT REFERENCES symbol(id));
CREATE TABLE pl_unary (functor_id INT REFERENCES symbol(id), arg1_id INT REFERENCES symbol(id));
CREATE TABLE pl_binary (functor_id INT REFERENCES symbol(id), arg1_id INT REFERENCES symbol(id), arg2_id INT REFERENCES symbol(id));
CREATE TABLE pl_trinary (functor_id INT REFERENCES symbol(id), arg1_id INT REFERENCES symbol(id), arg2_id INT REFERENCES symbol(id), arg3_id INT REFERENCES symbol(id));
"""

TEARDOWN="""
DROP TABLE pl_trinary CASCADE;
DROP TABLE pl_binary CASCADE;
DROP TABLE pl_unary CASCADE;
DROP TABLE pl_nullary CASCADE;
DROP TABLE symbol CASCADE;
"""

def output():
    return print
