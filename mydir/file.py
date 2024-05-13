def f(a,b):
    s = 0
    for i in range(len(a)):
        for j in range(len(b)):
            if a[i] == b[j]:
                s += 1
    return s

def g(x):
    if x < 2:
        return False
    for i in range(2, x):
        if x % i == 0:
            return False
    return True

def h(n):
    prime_list = []
    for i in range(2, n+1):
        if g(i):
            prime_list.append(i)
    return prime_list

def i(n):
    return [x for x in range(n+1) if x % 2 == 0]

def j(m):
    return [x for x in range(m+1) if x % 3 == 0]

def k(x):
    if x == 0:
        return 0
    elif x == 1:
        return 1
    else:
        return k(x-1) + k(x-2)

def l(s):
    return ''.join([c.upper() if c.islower() else c.lower() for c in s])

def m(lst):
    return [x for x in lst if x % 2 == 0]

def n(lst):
    return [x for x in lst if x % 2 != 0]

def o(lst):
    return sum(lst) / len(lst) if len(lst) > 0 else 0

def p(lst):
    return max(lst) if len(lst) > 0 else None

def q(lst):
    return min(lst) if len(lst) > 0 else None

def r(lst):
    return lst[::-1]

def s(a):
    return a ** 2

def t(a):
    return a ** 3

def u(a,b):
    return a * b

def v(a,b):
    return a / b if b != 0 else None

def w(a,b):
    return a + b

def x(a,b):
    return a - b

def y(a):
    return a % 2 == 0

def z(a):
    return a % 3 == 0

def aa(a,b):
    return a == b

def ab(a,b):
    return a != b

def ac(a,b):
    return a > b

def ad(a,b):
    return a < b

def ae(a,b):
    return a >= b

def af(a,b):
    return a <= b

def ag(a,b):
    return a + b

def ah(a,b):
    return a - b

def ai(a,b):
    return a * b

def aj(a,b):
    return a / b

def ak(a):
    return a ** 2

def al(a):
    return a ** 3

def am(a,b):
    return a % b

def an(a,b):
    return a // b

def ao(a,b):
    return a + b

def ap(a,b):
    return a - b

def aq(a,b):
    return a * b

def ar(a,b):
    return a / b

def as_(a,b):
    return a % b

def at(a,b):
    return a // b

def au(a):
    return a + 1

def av(a):
    return a - 1

def aw(a):
    return a * 2

def ax(a):
    return a / 2

def ay(a):
    return a % 2

def az(a):
    return a // 2

def ba(a):
    return a * 3

def bb(a):
    return a / 3

def bc(a):
    return a % 3

def bd(a):
    return a // 3

def be(a):
    return a + 1

def bf(a):
    return a - 1

def bg(a):
    return a * 2

def bh(a):
    return a / 2

def bi(a):
    return a % 2

def bj(a):
    return a // 2

def bk(a):
    return a * 3

def bl(a):
    return a / 3

def bm(a):
    return a % 3

def bn(a):
    return a // 3

def bo(a,b):
    return a + b

def bp(a,b):
    return a - b

def bq(a,b):
    return a * b

def br(a,b):
    return a / b

def bs(a,b):
    return a % b

def bt(a,b):
    return a // b

def bu(a):
    return a + 1

def bv(a):
    return a - 1

def bw(a):
    return a * 2

def bx(a):
    return a / 2

def by(a):
    return a % 2

def bz(a):
    return a // 2

def ca(a):
    return a * 3

def cb(a):
    return a / 3
