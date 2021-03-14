# Copyright 2020 Bryan Bonvallet.
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.

from __future__ import print_function
import argparse
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

# PEG rules parsed by Parsimonious
# https://github.com/erikrose/parsimonious

# Prolog Grammar
# https://en.wikipedia.org/wiki/Prolog_syntax_and_semantics
grammar = Grammar("""
clause = (comment / query / rule / fact)*
comment = ~"%[^\\r\\n]*" _
rule = term _ ":-" _ predicate+ terminator_mark
query = _ "?-" _ predicate+ terminator_mark
predicate = term (conjunction / disjunction)*
conjunction = _ "," _ term
disjunction = _ ";" _ term
fact = term terminator_mark
terminator_mark = _ "." _
term = functor / symbol / variable
symbol = number / atom
functor = atom "(" term (_ "," _ term)* ")"
atom = ~"[a-z]+|'[A-Z a-z]*'"
number = ~"[0-9]+|[0-9]*\.[0-9]+"
variable = ~"[A-Z][A-Za-z0-9]*"
_ = ~"\s*"
""")

class PrologTree(NodeVisitor):
    symbols = set()
    variables = set()
    queries = []
    functors = {}
    facts = []
    rule_names = set()
    rule_args = {}
    rule_defs = {}

    def _store_symbol(self, node, store, arity=0):
        getattr(self, store).add((node.text,arity))
        return node.text

    def visit_term(self, node, touched):
        return touched[0]

    # Collect Symbols
    def visit_symbol(self, node, touched):
        return self._store_symbol(node, 'symbols')

    # Collect Variables
    def visit_variable(self, node, touched):
        return self._store_symbol(node, 'variables')

    # Collect Facts and Functors
    def visit_fact(self, node, touched):
        node = argparse.Namespace
        node.text = touched[0][0]
        self._store_symbol(node, 'symbols', touched[0][1])
        self.facts.append(touched[0])
        return node

    def visit_functor(self, node, touched):
        # this term contains a functor
        # children: [functor, "(", arg1, [",", arg2, ... , ",", argN], ")" ]
        # zeroth child is functor
        functor = node.children[0].text
        # collect arguments
        args = [node.children[2].text]
        # ","args2 to ","argsN in third child
        # within each of those, argsN in the third child
        args.extend([n.children[3].text for n in node.children[3].children])
        arity = len(args)

        # track the actual contents
        if arity not in self.functors:
            self.functors[arity] = {}
        if functor not in self.functors[arity]:
            self.functors[arity][functor] = []
        self.functors[arity][functor].append(args)

        return [functor, arity, args]

    def _recurse_regexnodes(self, regexnodes, root):
        if root.expr_name == 'atom':
            regexnodes.append([root.text, []])
        if root.expr_name == 'variable':
            regexnodes[-1][1].append(root.text)
        if root.expr_name == 'conjunction':
            regexnodes.append('AND')
        children = root.children or []
        for child in children:
            regexnodes = self._recurse_regexnodes(regexnodes, child)
        return regexnodes

    # Build Rules
    def visit_rule(self, node, touched):
        rname = touched[0][0]
        rin = touched[0][2]
        arity = len(rin)
        func = touched[4] and touched[4].children[0]

        node = argparse.Namespace
        node.text = rname
        self._store_symbol(node, 'rule_names', arity)

        self.rule_args[(rname,arity)] = rin

        rule_def = tuple(self._recurse_regexnodes([], func))
        self.rule_defs[(rname,arity)] = rule_def

        return (rname, arity, tuple(rin), rule_def)

    def _find_variables(self, node, var_list):
        # leaf nodes
        if node.expr_name == 'variable':
            return var_list + [node.text]
        if not node.children:
            return var_list
        # intermediary nodes
        for child in node.children:
            var_list = self._find_variables(child, var_list)
        return var_list

    # Execute Queries
    def visit_query(self, node, touched):
        # only touched[3] stores useful info, the rest is fluff
        query = touched[3].children[0].children[0].children[0]
        # node.children: functor, (, o1, o2, o3, ... ,oN, )
        functor = query.children[0].text
        #arity = len(query.children)-3
        # collect arguments
        args = [query.children[2].text]
        # ","args2 to ","argsN in third child
        # within each of those, argsN in the third child
        args.extend([n.children[3].text for n in query.children[3].children])
        # any args are variables?
        variables = self._find_variables(query, [])
        result = (functor, len(args), tuple(args), tuple(variables), query.text)
        self.queries.append(result)
        return result

    def generic_visit(self, node, touched):
        return node

class OutputHandler(object):

    def _arity(self, value):
        return 'fact_{}ary'.format(value)

    def __init__(self, driver, prolog_tree):
        self.driver = driver
        self.output = driver.execute
        self.prolog_tree = prolog_tree

    def combine_symbol_arity(self, symbol, arity):
        return symbol + '/' + str(arity)

    def query_rule(self, query, symbols, rules):
        functor, arity, args, var_names, _ = query
        functor = self.combine_symbol_arity(functor, arity)
        return rules[functor]

    def query_fact(self, query, symbols, rules):
        functor, arity, args, var_names, _ = query
        functor = self.combine_symbol_arity(functor, arity)

        symbol_table = self.driver.tables[0]
        arity_table = self.driver.tables[arity]

        if functor in rules:
            return self.query_rule(query, symbols, rules)

        alias_cols = []
        for var_name in var_names:
            alias = self.driver.new_alias(symbol_table, var_name)
            alias_cols.append(alias.symbol.label(var_name))

        #   YES: SELECT symbol AS "VARNAME"
        #        INNER JOIN symbol ON (argX_id = id AND arity=0)
        #    NO: SELECT count(*)>0
        if not var_names:
            sqa = self.driver.query(self.driver.count(arity_table.functor_id))
        else:
            # Make the N-ary table the primary FROM object
            # (Unfortunately SELECTs all columns as well)
            sqa = self.driver.query(arity_table)
            # Select columns of actual interest: variable symbols
            sqa = sqa.add_columns(*alias_cols)
        for var_name in var_names:
            # Manage variables in the query
            j = args.index(var_name)+1
            alias = self.driver.get_alias(symbol_table, var_name)
            col = getattr(arity_table, 'arg{}_id'.format(j))
            sqa = sqa.join(alias, (col == alias.id) & (alias.arity == 0))
        if functor not in rules:
            f_id = symbols[functor].id
            sqa = sqa.filter(arity_table.functor_id == f_id)
        for i in range(0, len(args)):
            arg = args[i]
            if arg in var_names:
                # This is a variable. Variables were handled already in loop above.
                continue
            if str(arg)[0] == ':':
                # This is a parameter. Look up the parameter's matching symbol in a subquery.
                symbol_table = self.driver.tables[0]
                arg_id = self.driver.query(symbol_table.id).filter(symbol_table.symbol == arg)
            else:
                # Not a parameter. Look up the appropriate symbol id in the DB.
                arg_id = symbols[self.combine_symbol_arity(arg, 0)].id
            col = getattr(arity_table, 'arg{}_id'.format(i+1))
            sqa = sqa.filter(col == arg_id)
        if var_names:
            # SQLAlchemy forces columns of the initial FROM table to be
            # selected. Turn the query into subquery and SELECT only the
            # columns of interest.
            sqa = sqa.from_self(*var_names)
        return sqa

    def handle(self):
        # convert symbols into table values
        # track their ids
        current_id = 1
        symbol_id = {}
        symbols = {}
        for symbol in self.prolog_tree.symbols:
            obj = self.driver.tables[0](symbol=symbol[0], arity=symbol[1])
            self.driver.add(obj)
            symbols[self.combine_symbol_arity(*symbol)] = obj

            # convert ('functor', 0) into 'functor/0' for storing ids
            symbol_id[self.combine_symbol_arity(*symbol)] = current_id
            current_id += 1
        self.driver.commit()

        # convert facts into table values
        for fact in self.prolog_tree.facts:
            arity = fact[1]
            symbol = symbols[self.combine_symbol_arity(fact[0], arity)]

            data = { 'functor_id': symbol.id }
            args = fact[2]
            for i in range(0,len(args)):
                data['arg{}_id'.format(i+1)] = symbols[self.combine_symbol_arity(args[i],0)].id

            relation = self.driver.tables[arity](**data)
            self.driver.add(relation)
        self.driver.commit()

        rule_names = list(self.prolog_tree.rule_names)
        rule_arg_names = {}
        rules = {}
        ctr = 0
        # Build subqueries until no more rules are left
        while rule_names:
            # Iterate all current rules
            for rule in rule_names:
                # figure out which arguments are variables for top-most SELECT
                # figure out which arguments go with which arguments across fact subqueries
                # replace subquery parameters with rule parameters IFF rule parameter is symbol
                # build top-most query with count or vars
                # build each subquery
                # if subquery interrogates fact, then build parameters for self.query_fact
                # if subquery interrogates rule, then inject rule
                # apply where clauses to join all variables together

                rulesymbol = self.combine_symbol_arity(*rule)
                rule_def = self.prolog_tree.rule_defs[rule]
                rule_args = self.prolog_tree.rule_args[rule]

                query = None
                for clause in rule_def:
                    tablearity = len(clause[1])
                    tablesymbol = self.combine_symbol_arity(clause[0],tablearity)
                    if tablesymbol in symbols:
                        varset = []
                        freev = []
                        for symbol in clause[1]:
                            if symbol in rule_args:
                                # TODO this adds parameters to all queries, not just the one... prefix helps but not perfect solution
                                varset.append(self.driver.get_parameter(rulesymbol, symbol))
                                # Cache these symbols to the rule signature
                                if rulesymbol not in rule_arg_names:
                                    rule_arg_names[rulesymbol] = []
                                rule_arg_names[rulesymbol].append(symbol)
                            else:
                                varset.append(symbol)
                                freev.append(symbol)
                        # free variables
                        # TODO replace clause[1] input arguments with functional values
                        #freev = tuple(set(clause[1]).difference(set(rule_args)))
                        # this can be directly queried
                        subquery = self.query_fact([clause[0], tablearity, varset, freev, None], symbols, rules)
                        # sq_alias acts like a table, but forces a subquery
                        #sq_alias = subquery.cte(recursive=False)
                        sq_alias = subquery
                        if query is None:
                            query = sq_alias
                    else:
                        raise NotImplemented("Unsupported rule cascade.")

                rules[rulesymbol] = query
                # Debugging
                #for rule_name in rules:
                #    print('{}\n---\n{}\n---\n'.format(rule_name, rules[rule_name]))
                rule_names.remove(rule)

            # At this point, the rules left are those which rely on other rules
            # which were not previously available. Howboutnow?
            ctr = ctr + 1
            if ctr > 10:
                raise Exception('Recursive rule depth passed. Check for circular dependencies between rules.')

        # queries
        for query in self.prolog_tree.queries:
            print('?- ' + query[4])
            symbol_vals = query[2]
            rulesymbol = self.combine_symbol_arity(query[0], query[1])
            rule_arg_vals = None
            if rulesymbol in rule_arg_names:
                # Prepare a dictionary linking the argument names with the argument values
                rule_arg_vals = {}
                these_symbols = rule_arg_names[rulesymbol]
                for i in range(0,len(these_symbols)):
                    this_symbol = these_symbols[i]
                    rule_arg_vals[str((rulesymbol,this_symbol))] = symbol_vals[i]
            sqa = self.query_fact(query, symbols, rules)
            if rule_arg_vals:
                self.output(sqa.with_labels().statement, **rule_arg_vals)
            else:
                self.output(sqa.with_labels().statement)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert prolog code into SQL.')
    parser.add_argument('filename', type=argparse.FileType('r'), help='prolog file')
    parser.add_argument('--driver', type=str, default='sqlite', help='prolog file')
    args = parser.parse_args()

    from importlib import import_module
    driver = import_module('driver.' + args.driver)

    prolog_tree = PrologTree()
    prolog_tree.visit(grammar.parse(args.filename.read()))
    pp = OutputHandler(driver.build_driver(debug=False), prolog_tree)
    pp.handle()
