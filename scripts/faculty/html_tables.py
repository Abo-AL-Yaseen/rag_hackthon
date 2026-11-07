"""Authored DOM-order parser; never reverses Arabic or infers table operators."""
from html.parser import HTMLParser

class Node:
    def __init__(self, tag='', attrs=(), parent=None):
        self.tag, self.attrs, self.parent, self.children = tag, dict(attrs), parent, []
    def text(self, sep=' '):
        return sep.join(c.text(sep) if isinstance(c, Node) else c for c in self.children)
    def find(self, tag):
        result = []
        for c in self.children:
            if isinstance(c, Node):
                if c.tag == tag: result.append(c)
                result.extend(c.find(tag))
        return result

class Tree(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Node('root'); self.current = self.root
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current); self.current.children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.current = node
    def handle_endtag(self, tag):
        node = self.current
        while node.parent:
            if node.tag == tag:
                self.current = node.parent; return
            node = node.parent
    def handle_data(self, text): self.current.children.append(text)

def clean(s): return ' '.join(s.split())
