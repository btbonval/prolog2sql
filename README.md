# prolog2sql

The original intention of this project was to convert any Prolog script into a
series of SQL queries against a static relational schema built to support
prolog-like queries.

Support is probably going to be closer to an offshoot like datalog.

## Requirements

* [Parsimonious](https://github.com/erikrose/parsimonious) using Python.
* [SQLAlchemy](https://www.sqlalchemy.org/) also using Python.
* A relational database; SQLite will suffice.

I highly recommend using [VirtualEnv](https://pypi.org/project/virtualenv/) for
managing requirements in a sandbox environment.

## Running

Activate the virtualenv, if any.

Run `python prolog2sql.py <some pl file>`.

## How does it work?

### Syntax and Parsimonious

Prolog syntax is encoded as a set of Parsing Expression Grammar (PEG) rules,
which is parsed into a tree by Parsimonious in Python. Syntax
concepts like "atom", "term", "comment", are all defined in this PEG.

While stepping through the tree, local mappings and lists of symbols, variables,
and so on are stored in local memory.

### Relational Schema

The pgsql and sqlite database drivers give an idea of the schema in a more
literal way. However, these are hard coded and no longer supported.

The SQLAlchemy driver dynamically generates a fundamental schema. Each arity
has its own table. This means that the max arity must be known ahead of time,
but only requires changing a single value to work with higher arities.

### Interpretation

The in-memory cache built from stepping through the tree is parsed in multiple
parts.

First, all symbols are read and inserted into the symbol table.

Next, all facts are inserted into the appropriate arity table.

Then all rules are built as subqueries which are cached in-memory. In the
future, rules might be reframes as views.

Finally, each queries is read. The prolog query is deconstructed for rules
into SQL subqueries. Regardless of rules, the prolog query is converted into a
SQL query against the fact able (with joins against rule subqueries as needed).

### Testing

Find random `.pl` files from around the internet. Various online courses, like
[this prolog tutorial from J.R.Fisher](https://www.cpp.edu/~jrfisher/www/prolog_tutorial/contents.html).
Such examples almost always include expected output. Ensure the files output
correctly.

The problem with this method of testing is that such files are copyrighted by
their respective owners and cannot be distributed with this repository.

## Future Work

Support rule conjunctions (using `,`).

Support negation (using either `!` cut operator or `not()`).

# Goals

The primary goal of this project is do take the power of first-order logic
systems and bring them into more ubiquitous platforms.

Prolog / Datalog serves as the basis for *testing* that a first-order logic
system has been built in a way that can be demonstrated using existing scripts.

With the addition of hierarchical and recursive queries in SQL:1999, it seems
that SQL ought to be able to handle first-order logic systems. Relational
databases are ubiquitous. Drivers for different databases as well as
object-relational models make relational databases very easy to work with.

Once the first-order logic system of this converter is demonstrated reliably
to function over the relational schema, there will be no more need to parse
Prolog or support Prolog syntax.

This project would be deemd "complete" at such time. The next project would
focus on working with first-order logic systems directly in relational
databases.

The SQL schema and lessons learned from parsing rules, etc can be brought
into SQL and/or an ORM like SQLAlchemy. This might require its own
ORM-like wrapper for convenience, or a series of sophisticated `VIEW`s and
`FUNCTION`s in the database. At this stage, the goal of a first-order logic
system on a ubiquitous platform should be achieved.

Such a first-order logic system could be used to maintain consistency or
conform to constraints in video games, interactive fiction, design applications,
or any number of use cases which can integrate a relational database.
