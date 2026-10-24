"""
regex_parser.py  --  Step 1: Regex Input, Tokenizer and Parser
================================================================
Two stages turn a regular expression string into an Abstract Syntax Tree (AST):

  1. TOKENIZER (Lexer): scans the characters and produces a list of tokens
        SYMBOL  ANY  CLASS  UNION  STAR  PLUS  OPTIONAL  LPAREN  RPAREN
     Escapes (\\. \\d \\w) and character classes ([a-z] [^x]) become single tokens.
  2. PARSER: a hand-written recursive-descent parser reads the tokens.

Supported syntax
    ab        concatenation
    a|b       union
    a*  a+  a?   Kleene star, plus, optional
    ( )       grouping
    .         any single character
    [abc] [a-z0-9] [^abc]   character classes (ranges and negation)
    \\d \\w     digit / word character shortcuts
    \\. \\* \\( ...   escaped literals (also \\n and \\t)
Matching is a FULL match: the whole string must be accepted by the automaton.

Grammar (lowest -> highest precedence)
    regex  -> term ( UNION term )*
    term   -> factor*
    factor -> atom ( STAR | PLUS | OPTIONAL )*
    atom   -> LPAREN regex RPAREN | SYMBOL | ANY | CLASS
"""
from dataclasses import dataclass

# Sentinel meaning "any character that is not named anywhere in the regex".
# Needed so that '.' and negated classes can be handled with a finite alphabet.
OTHER = "<other>"


class RegexSyntaxError(Exception):
    def __init__(self, message, pos):
        super().__init__(f"{message} (at position {pos})")
        self.message = message
        self.pos = pos


def show_char(c):
    """Printable form of a character for labels and messages."""
    return {"\n": "\\n", "\t": "\\t", " ": "␣"}.get(c, c)


# ---------------------------------------------------------------- matchers
@dataclass(frozen=True)
class CharSet:
    """Label on an NFA edge: a (possibly negated) set of characters."""
    chars: frozenset
    negated: bool = False
    label: str = ""

    def matches(self, sym):
        if sym == OTHER:
            return self.negated
        return (sym in self.chars) != self.negated


def literal(c):
    return CharSet(frozenset([c]), False, show_char(c))


ANY = CharSet(frozenset(), True, ".")
DIGITS = CharSet(frozenset("0123456789"), False, "\\d")
WORD = CharSet(frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"), False, "\\w")


# ------------------------------------------------------------------ tokens
@dataclass(frozen=True)
class Token:
    kind: str          # SYMBOL, ANY, CLASS, UNION, STAR, PLUS, OPTIONAL, LPAREN, RPAREN
    text: str          # the source text of the token
    pos: int           # index of the token in the regex string
    cs: object = None  # CharSet for SYMBOL / ANY / CLASS tokens


QUANTIFIERS = ("STAR", "PLUS", "OPTIONAL")


class Lexer:
    MAX_CLASS = 300
    OPERATORS = {"|": "UNION", "*": "STAR", "+": "PLUS", "?": "OPTIONAL",
                 "(": "LPAREN", ")": "RPAREN"}

    def __init__(self, text):
        self.s = text
        self.i = 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def tokens(self):
        out = []
        while self.i < len(self.s):
            start = self.i
            c = self.s[self.i]
            if c in self.OPERATORS:
                self.i += 1
                out.append(Token(self.OPERATORS[c], c, start))
            elif c == "[":
                cs = self.char_class()
                out.append(Token("CLASS", self.s[start:self.i], start, cs))
            elif c == ".":
                self.i += 1
                out.append(Token("ANY", ".", start, ANY))
            elif c == "\\":
                self.i += 1
                if self.i >= len(self.s):
                    raise RegexSyntaxError("Dangling backslash", start)
                e = self.s[self.i]
                self.i += 1
                if e == "d":
                    out.append(Token("CLASS", "\\d", start, DIGITS))
                elif e == "w":
                    out.append(Token("CLASS", "\\w", start, WORD))
                else:
                    ch = {"n": "\n", "t": "\t"}.get(e, e)
                    out.append(Token("SYMBOL", self.s[start:self.i], start, literal(ch)))
            else:
                self.i += 1
                out.append(Token("SYMBOL", c, start, literal(c)))
        return out

    def class_char(self):
        c = self.peek()
        self.i += 1
        if c == "\\":
            e = self.peek()
            if e is None:
                raise RegexSyntaxError("Dangling backslash", self.i - 1)
            self.i += 1
            return {"n": "\n", "t": "\t"}.get(e, e)
        return c

    def char_class(self):
        start = self.i
        self.i += 1
        negated = False
        if self.peek() == "^":
            negated = True
            self.i += 1
        chars, first = set(), True
        while True:
            c = self.peek()
            if c is None:
                raise RegexSyntaxError("Missing closing ']'", start)
            if c == "]":
                if first:
                    raise RegexSyntaxError("Empty character class", start)
                self.i += 1
                break
            lo = self.class_char()
            if self.peek() == "-" and self.i + 1 < len(self.s) and self.s[self.i + 1] != "]":
                self.i += 1
                hi = self.class_char()
                if ord(lo) > ord(hi):
                    raise RegexSyntaxError(f"Invalid range '{lo}-{hi}'", self.i - 1)
                chars.update(chr(x) for x in range(ord(lo), ord(hi) + 1))
            else:
                chars.add(lo)
            if len(chars) > self.MAX_CLASS:
                raise RegexSyntaxError("Character class is too large", start)
            first = False
        return CharSet(frozenset(chars), negated, self.s[start:self.i])


def tokenize(text):
    """Split a regex string into tokens (raises RegexSyntaxError)."""
    return Lexer(text).tokens()


def tokens_pretty(tokens):
    return "\n".join(f"{t.pos:>3}  {t.kind:<8} {t.text}" for t in tokens) or "(no tokens: empty expression)"


# --------------------------------------------------------------- AST nodes
@dataclass
class Empty:
    pass


@dataclass
class Atom:
    cs: CharSet


@dataclass
class Concat:
    left: object
    right: object


@dataclass
class Union:
    left: object
    right: object


@dataclass
class Star:
    child: object


@dataclass
class Plus:
    child: object


@dataclass
class Optional:
    child: object


# ------------------------------------------------------------------ parser
class Parser:
    """Recursive-descent parser over the token list."""

    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def parse(self):
        node = self.regex()
        tk = self.peek()
        if tk is not None:                   # only an unmatched ')' can remain
            raise RegexSyntaxError("Unmatched ')'", tk.pos)
        return node

    def regex(self):
        node = self.term()
        while self.peek() is not None and self.peek().kind == "UNION":
            self.i += 1
            node = Union(node, self.term())
        return node

    def term(self):
        node = None
        while self.peek() is not None and self.peek().kind not in ("UNION", "RPAREN"):
            f = self.factor()
            node = f if node is None else Concat(node, f)
        return node if node is not None else Empty()

    def factor(self):
        node = self.atom()
        while self.peek() is not None and self.peek().kind in QUANTIFIERS:
            kind = self.peek().kind
            self.i += 1
            node = {"STAR": Star, "PLUS": Plus, "OPTIONAL": Optional}[kind](node)
        return node

    def atom(self):
        tk = self.peek()
        if tk.kind == "LPAREN":
            self.i += 1
            node = self.regex()
            if self.peek() is None or self.peek().kind != "RPAREN":
                raise RegexSyntaxError("Missing closing ')'", tk.pos)
            self.i += 1
            return node
        if tk.kind in ("SYMBOL", "ANY", "CLASS"):
            self.i += 1
            return Atom(tk.cs)
        raise RegexSyntaxError(f"Nothing to repeat before '{tk.text}'", tk.pos)


def parse(text):
    """Tokenize and parse a regex string into an AST (raises RegexSyntaxError)."""
    return Parser(tokenize(text)).parse()


def ast_pretty(node, depth=0):
    """Indented text rendering of the AST, for display."""
    pad = "  " * depth
    if isinstance(node, Empty):
        return pad + "ε (empty)"
    if isinstance(node, Atom):
        return pad + f"Symbol  {node.cs.label}"
    if isinstance(node, (Concat, Union)):
        name = "Concat" if isinstance(node, Concat) else "Union (|)"
        return "\n".join([pad + name, ast_pretty(node.left, depth + 1), ast_pretty(node.right, depth + 1)])
    name = {Star: "Star (*)", Plus: "Plus (+)", Optional: "Optional (?)"}[type(node)]
    return pad + name + "\n" + ast_pretty(node.child, depth + 1)
