from z3 import Solver, Bool, And, Or, Not, sat
import json
import re
from time import time

class Puzzle():
    def __init__(self, data):
        self.metadata = data
        if not re.match(r'^shakashaka/\d+/\d+/[a-eg-z\.\d]+/?$',data['pzv']):
            raise ValueError(f"Bad data: {repr(data['pzv'])}")
        _, w, h, content, *_ = data['pzv'].split('/')
        w = int(w)
        h = int(h)
        self.w = w
        self.h = h
        self.data = [[None] * w for _ in range(h)]
        head = 0
        def write(v):
            if head >= w*h:
                raise ValueError(f"Data too long: {repr(data['pzv'])}")
            self.data[head//w][head%w] = v
        for c in content:
            if '0' <= c <= '4':
                write(ord(c)-ord('0'))
            elif '5' <= c <= '9':
                write(ord(c)-ord('5'))
                head += 1
            elif 'a' <= c <= 'e':
                write(ord(c)-ord('a'))
                head += 2
            elif 'g' <= c <= 'z':
                head += ord(c)-ord('g')
            elif c == '.':
                write(-1)
            else:
                assert(False) #unreachable
            head += 1

    def __str__(self):
        lookup = {None: '.', -1: '■', 0: '0', 1: '1', 2: '2', 3: '3', 4: '4'}
        return '\n'.join(
            ''.join(
                lookup[self.data[y][x]] for x in range(self.w)
                ) for y in range(self.h)
            )

    def gen_sat_instance(self):
        symbols = {}
        clauses = []
        dirs = 'NESW'
        w,h = self.w,self.h
        for x in range(-1,w+1):
            for y in range(-1,h+1):
                pfx = f'{x}_{y}_'
                for d in dirs:
                    symbols[x,y,d] = Bool(pfx + d)
                if x == -1 or y == -1 or x == w or y == h or self.data[y][x] is not None:
                    for d in dirs:
                        clauses.append(symbols[x,y,d])
                else:
                    s1, s2, s3, s4 = (symbols[x,y,d] for d in dirs)
                    clauses.append(
                        Or(
                            And(s1,s2,Not(s3),Not(s4)),
                            And(s2,s3,Not(s4),Not(s1)),
                            And(s3,s4,Not(s1),Not(s2)),
                            And(s4,s1,Not(s2),Not(s3)),
                            And(Not(s1),Not(s2),Not(s3),Not(s4))
                        )
                    )
        for x in range(w+1):
            for y in range(h+1):
                s = [symbols[  x,  y,'N'], symbols[  x,  y,'W'],
                     symbols[x-1,  y,'E'], symbols[x-1,  y,'N'],
                     symbols[x-1,y-1,'S'], symbols[x-1,y-1,'E'],
                     symbols[  x,y-1,'W'], symbols[  x,y-1,'S']]
                for i in range(8):
                    clauses.append(
                        Not(
                            And(
                                s[i],
                                Not(s[i-1]),
                                s[i-2]
                            )
                        )
                    )
                    clauses.append(
                        Not(
                            And(
                                s[i],
                                Not(s[i-1]),
                                Not(s[i-2]),
                                Not(s[i-3]),
                                s[i-4]
                            )
                        )
                    )
                    clauses.append(
                        Not(
                            And(
                                s[i],
                                Not(s[i-1]),
                                Not(s[i-2]),
                                Not(s[i-3]),
                                Not(s[i-4]),
                                Not(s[i-5])
                            )
                        )
                    )
        for x in range(w):
            for y in range(h):
                if self.data[y][x] in (0,1,2,3,4):
                    clue = self.data[y][x] + \
                           (x == 0 or self.data[y][x-1] is not None) + \
                           (x == w-1 or self.data[y][x+1] is not None) + \
                           (y == 0 or self.data[y-1][x] is not None) + \
                           (y == h-1 or self.data[y+1][x] is not None)
                    s1,s2,s3,s4 = symbols[x-1,y,'E'],symbols[x,y-1,'S'],symbols[x+1,y,'W'],symbols[x,y+1,'N']
                    match clue:
                        case 0:
                            clauses.append(
                                And(Not(s1),Not(s2),Not(s3),Not(s4))
                            )
                        case 1:
                            clauses.append(
                                Or(
                                    And(s1,Not(s2),Not(s3),Not(s4)),
                                    And(s2,Not(s1),Not(s3),Not(s4)),
                                    And(s3,Not(s1),Not(s2),Not(s4)),
                                    And(s4,Not(s1),Not(s2),Not(s3))
                                )
                            )
                        case 2:
                            clauses.append(
                                Or(
                                    And(s1,s2,Not(s3),Not(s4)),
                                    And(s1,s3,Not(s2),Not(s4)),
                                    And(s1,s4,Not(s2),Not(s3)),
                                    And(s2,s3,Not(s1),Not(s4)),
                                    And(s2,s4,Not(s1),Not(s3)),
                                    And(s3,s4,Not(s1),Not(s2))
                                )
                            )
                        case 3:
                            clauses.append(
                                Or(
                                    And(s1,s2,s3,Not(s4)),
                                    And(s1,s2,s4,Not(s3)),
                                    And(s1,s3,s4,Not(s2)),
                                    And(s2,s3,s4,Not(s1))
                                )
                            )
                        case 4:
                            clauses.append(
                                And(s1,s2,s3,s4)
                            )
                        case _:
                            raise ValueError("Clue too large")
        self.symbols = symbols
        self.clauses = clauses

    def solve(self):
        s = Solver()
        s.add(self.clauses)
        if not s.check() == sat:
            raise ValueError("Unsolvable Puzzle")
        self.solution = s.model()

    def solved_grid(self):
        def get_symbol(x,y):
            a,b,c,d = self.solution[self.symbols[x,y,'N']], \
                    self.solution[self.symbols[x,y,'E']], \
                    self.solution[self.symbols[x,y,'S']], \
                    self.solution[self.symbols[x,y,'W']]
            match (a.py_value(),b.py_value(),c.py_value(),d.py_value()):
                case (True,True,False,False):
                    return '◥'
                case (False,True,True,False):
                    return '◢'
                case (False,False,True,True):
                    return '◣'
                case (True,False,False,True):
                    return '◤'
                case (False,False,False,False):
                    return ' '
                case _:
                    raise ValueError(f"Malformed solution data: {x,y,(a,b,c,d)}")
        lookup = {-1: '■', 0: '0', 1: '1', 2: '2', 3: '3', 4: '4'}
        return '\n'.join(
            ''.join(
                lookup[self.data[y][x]] if self.data[y][x] is not None else get_symbol(x,y) for x in range(self.w)
            ) for y in range(self.h)
        )

puzzles = []

print('Loading puzzle data.')

t1 = time()

with open("pzvs_anon.json") as f:
    for line in json.loads(f.read()):
        try:
            puzzles.append(Puzzle(line))
        except ValueError as e:
            print(e)

t2 = time()

print(f'Puzzle data loaded for {len(puzzles)} puzzles in {t2-t1} seconds.')

print('Generating SAT instances.')

t1 = time()

for p in puzzles:
    p.gen_sat_instance()

t2 = time()

print(f'SAT instances generated in {t2-t1} seconds.')

print('Solving puzzles.')

t1 = time()

for p in puzzles:
    p.solve()

t2 = time()

print(f'Puzzles solved in {t2-t1} seconds.')














