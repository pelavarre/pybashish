#!/usr/bin/env python3

"""
explore more than "ast.literal_eval" of:  import ast
"""

import ast
import textwrap

PY = textwrap.dedent(
    """

    def a(a0, a1):
        pass

    def b(a0):
        pass

    def c():
        pass

    def d():
        pass

    a(b(c()), d())

    """
).strip()


class AstNodeVisitor(ast.NodeVisitor):
    def visit(self, node):
        words = list()
        words.append(str(node))
        if hasattr(node, "id"):
            words.append("id={}".format(node.id))
        # if hasattr(node, "args"):
        #     words.append("len(args)={}".format(len(node.args)))
        print(" ".join(words))
        super().visit(node)


visitor = AstNodeVisitor()
top_node = ast.parse(PY)
visitor.visit(top_node)

print()
print(ast.dump(top_node))

print()
print(ast.unparse(top_node))


# copied from:  git clone https://github.com/pelavarre/pybashish.git
