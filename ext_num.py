# extnum.py
from __future__ import annotations
import json, math, cmath
from enum import Enum, auto
from fractions import Fraction
from numbers import Real, Complex
from typing import Any, Union
from dataclasses import dataclass

class Kind(Enum):
    REAL    = auto()
    COMPLEX = auto()
    OMEGA   = auto()
    BOTTOM  = auto()

@dataclass
class ExtNum:
    kind: Kind
    val: Any
    use_float: bool = False

    # Construction
    @staticmethod
    def real(x: Real | Fraction | float, use_float: bool = False) -> ExtNum:
        v = float(x) if use_float else Fraction(x)
        return ExtNum(Kind.REAL, v, use_float)

    @staticmethod
    def complex(real: Real, imag: Real = 0, use_float: bool = False) -> ExtNum:
        v = complex(float(real), float(imag)) if use_float else complex(Fraction(real), Fraction(imag))
        return ExtNum(Kind.COMPLEX, v, use_float)

    @staticmethod
    def omega(a: Real | Fraction | complex, use_float: bool = False) -> ExtNum:
        a_val = (float(a) if use_float and isinstance(a, Real)
                 else Fraction(a) if isinstance(a, Real)
                 else complex(a))
        if a_val == 0:
            raise ValueError("Ω(0) is undefined; use bottom()")
        return ExtNum(Kind.OMEGA, a_val, use_float)

    @staticmethod
    def bottom() -> ExtNum:
        return ExtNum(Kind.BOTTOM, None, False)

    # Representation
    def __repr__(self) -> str:
        match self.kind:
            case Kind.REAL:    return str(self.val)
            case Kind.COMPLEX: return f"{self.val}" if self.val.imag != 0 else f"{self.val.real}"
            case Kind.OMEGA:   return f"Ω({self.val})"
            case Kind.BOTTOM:  return "⊥"

    def __bool__(self) -> bool:
        if self.kind is Kind.BOTTOM: return False
        if self.kind is Kind.OMEGA:  return True
        return bool(self.val)

    # Equality & Hashing
    def __eq__(self, other: Any) -> bool:
        other = self._coerce(other)
        if self.kind is Kind.BOTTOM and other.kind is Kind.BOTTOM:
            return True
        return self.kind == other.kind and self.val == other.val

    def __hash__(self) -> int:
        return hash((self.kind, self.val, self.use_float))

    # Coercion
    def _coerce(self, other: Any) -> ExtNum:
        if isinstance(other, ExtNum): return other
        if isinstance(other, Real):   return ExtNum.real(other, self.use_float)
        if isinstance(other, Complex):return ExtNum.complex(other.real, other.imag, self.use_float)
        raise TypeError(f"Cannot operate with type {type(other).__name__}")

    # Arithmetic
    def __add__(self, other: Any): return self._add_sub(other, +1)
    def __radd__(self, other: Any): return self._coerce(other).__add__(self)
    def __sub__(self, other: Any): return self._add_sub(other, -1)
    def __rsub__(self, other: Any): return self._coerce(other).__sub__(self)

    def _add_sub(self, other: Any, sign: int) -> ExtNum:
        other = self._coerce(other)
        if Kind.BOTTOM in (self.kind, other.kind):
            return ExtNum.bottom()
        if self.kind is Kind.REAL and other.kind is Kind.REAL:
            return ExtNum.real(self.val + sign*other.val, self.use_float)
        if self.kind is Kind.COMPLEX and other.kind is Kind.COMPLEX:
            v = self.val + sign*other.val
            return ExtNum.complex(v.real, v.imag, self.use_float)
        if self.kind is Kind.OMEGA and other.kind is Kind.OMEGA:
            if self.val == other.val and sign == -1:
                return ExtNum.real(0, self.use_float)
            if abs(self.val) >= abs(other.val):
                return ExtNum.omega(self.val, self.use_float)
            return ExtNum.omega(sign*other.val, self.use_float)
        if self.kind is Kind.OMEGA:
            return self
        if other.kind is Kind.OMEGA:
            return ExtNum.omega(sign*other.val, self.use_float)
        raise ValueError(f"Undefined operation between {self} and {other}")

    def __neg__(self) -> ExtNum:
        if self.kind in (Kind.REAL, Kind.COMPLEX):
            return ExtNum(self.kind, -self.val, self.use_float)
        if self.kind is Kind.OMEGA:
            return ExtNum.omega(-self.val, self.use_float)
        return ExtNum.bottom()

    def __mul__(self, other: Any) -> ExtNum:
        other = self._coerce(other)
        if Kind.BOTTOM in (self.kind, other.kind): return ExtNum.bottom()
        if ((self.kind in (Kind.REAL, Kind.COMPLEX) and self.val == 0) or
            (other.kind in (Kind.REAL, Kind.COMPLEX) and other.val == 0)):
            return ExtNum.real(0, self.use_float)
        if Kind.OMEGA in (self.kind, other.kind):
            return ExtNum.omega(self.val*other.val, self.use_float)
        return ExtNum(self.kind, self.val*other.val, self.use_float)
    __rmul__ = __mul__

    def __truediv__(self, other: Any) -> ExtNum:
        other = self._coerce(other)
        if Kind.BOTTOM in (self.kind, other.kind): return ExtNum.bottom()
        if other.kind in (Kind.REAL, Kind.COMPLEX) and other.val == 0:
            if self.kind in (Kind.REAL, Kind.COMPLEX):
                return ExtNum.bottom() if self.val == 0 else ExtNum.omega(self.val, self.use_float)
            return ExtNum.omega(self.val, self.use_float)
        if Kind.OMEGA in (self.kind, other.kind):
            return ExtNum.omega(self.val/other.val, self.use_float)
        return ExtNum(self.kind, self.val/other.val, self.use_float)
    def __rtruediv__(self, other: Any) -> ExtNum:
        return self._coerce(other).__truediv__(self)

    def __pow__(self, exp: Any) -> ExtNum:
        # float exponent on real → float/complex result
        if self.kind is Kind.REAL and isinstance(exp, float):
            base = float(self.val)
            if base < 0:
                c = cmath.exp(exp * cmath.log(base))
                return ExtNum.complex(c.real, c.imag, True)
            return ExtNum.real(math.pow(base, exp), True)
        # integer exponent
        if isinstance(exp, int):
            if exp == 0:
                return ExtNum.bottom() if self.val == 0 else ExtNum.real(1, self.use_float)
            if self.kind is Kind.COMPLEX:
                return ExtNum.complex(self.val**exp, 0, self.use_float)
            if self.kind is Kind.OMEGA:
                return ExtNum.omega(self.val**exp, self.use_float)
            return ExtNum.real(self.val**exp, self.use_float)
        raise TypeError(f"Unsupported exponent {exp} for kind {self.kind}")

    # Comparisons
    def _cmp_key(self):
        if self.kind is Kind.BOTTOM:
            raise ValueError("⊥ cannot be compared")
        if self.kind is Kind.REAL:
            return (0, self.val)
        if self.kind is Kind.OMEGA:
            return (1, abs(self.val))
        raise ValueError("Complex not ordered")

    def __lt__(self, other: Any): return self._cmp_key() < self._coerce(other)._cmp_key()
    def __le__(self, other: Any): return self == other or self < other
    def __gt__(self, other: Any): return not self <= other
    def __ge__(self, other: Any): return not self < other

    # Helpers
    def is_finite(self) -> bool:   return self.kind in (Kind.REAL, Kind.COMPLEX)
    def is_infinite(self) -> bool: return self.kind is Kind.OMEGA
    def is_undefined(self) -> bool:return self.kind is Kind.BOTTOM
    def subscript(self) -> Any:    return self.val if self.kind is Kind.OMEGA else None

    # Unary functions
    def abs(self) -> ExtNum:
        if self.kind in (Kind.REAL, Kind.COMPLEX):
            return ExtNum.real(abs(self.val), self.use_float)
        if self.kind is Kind.OMEGA:
            return ExtNum.omega(abs(self.val), self.use_float)
        return ExtNum.bottom()

    def sign(self) -> ExtNum:
        if self.kind is Kind.REAL:
            return ExtNum.real(0 if self.val==0 else (1 if self.val>0 else -1), self.use_float)
        if self.kind is Kind.OMEGA:
            return ExtNum.real(1 if self.val>0 else -1, self.use_float)
        return ExtNum.bottom()

    def log(self) -> ExtNum:
        if self.kind is Kind.REAL:
            if self.val <= 0:
                return ExtNum.complex(cmath.log(self.val), 0, self.use_float)
            return ExtNum.real(math.log(self.val), self.use_float)
        if self.kind is Kind.COMPLEX:
            return ExtNum.complex(cmath.log(self.val), 0, self.use_float)
        if self.kind is Kind.OMEGA:
            lv = (cmath.log(self.val) if isinstance(self.val, complex)
                  else math.log(abs(self.val)))
            return ExtNum.omega(lv, self.use_float) if abs(lv)!=0 else ExtNum.bottom()
        return ExtNum.bottom()

    def exp(self) -> ExtNum:
        if self.kind is Kind.REAL:
            return ExtNum.real(math.exp(self.val), self.use_float)
        if self.kind is Kind.COMPLEX:
            return ExtNum.complex(cmath.exp(self.val), 0, self.use_float)
        if self.kind is Kind.OMEGA:
            ev = cmath.exp(self.val) if isinstance(self.val, complex) else math.exp(self.val)
            return ExtNum.omega(ev, self.use_float)
        return ExtNum.bottom()

    def sin(self) -> ExtNum:
        if self.kind in (Kind.REAL, Kind.COMPLEX):
            return ExtNum(self.kind, cmath.sin(self.val), self.use_float)
        if self.kind is Kind.OMEGA:
            sv = cmath.sin(self.val) if isinstance(self.val, complex) else math.sin(self.val)
            return ExtNum.omega(sv, self.use_float)
        return ExtNum.bottom()

    def cos(self) -> ExtNum:
        if self.kind in (Kind.REAL, Kind.COMPLEX):
            return ExtNum(self.kind, cmath.cos(self.val), self.use_float)
        if self.kind is Kind.OMEGA:
            cv = cmath.cos(self.val) if isinstance(self.val, complex) else math.cos(self.val)
            return ExtNum.omega(cv, self.use_float)
        return ExtNum.bottom()

    def sqrt(self) -> ExtNum:
        if self.kind is Kind.REAL:
            if self.val < 0:
                return ExtNum.complex(cmath.sqrt(self.val), 0, self.use_float)
            return ExtNum.real(math.sqrt(self.val), self.use_float)
        if self.kind is Kind.COMPLEX:
            return ExtNum.complex(cmath.sqrt(self.val), 0, self.use_float)
        if self.kind is Kind.OMEGA:
            sv = (cmath.sqrt(self.val) if isinstance(self.val, complex)
                  else math.sqrt(abs(self.val)))
            return ExtNum.omega(sv, self.use_float)
        return ExtNum.bottom()

    # JSON serialization
    def to_json(self) -> str:
        obj = {"kind": self.kind.name, "use_float": self.use_float}
        if self.kind is Kind.COMPLEX:
            obj["val"] = {"real": str(self.val.real), "imag": str(self.val.imag)}
        elif self.kind is not Kind.BOTTOM:
            obj["val"] = str(self.val)
        return json.dumps(obj)

    @staticmethod
    def from_json(s: str) -> ExtNum:
        o = json.loads(s)
        k = Kind[o["kind"]]
        uf = o.get("use_float", False)
        if k is Kind.BOTTOM:
            return ExtNum.bottom()
        if k is Kind.COMPLEX:
            r = Fraction(o["val"]["real"]) if not uf else float(o["val"]["real"])
            i = Fraction(o["val"]["imag"]) if not uf else float(o["val"]["imag"])
            return ExtNum.complex(r, i, uf)
        v = float(o["val"]) if uf else Fraction(o["val"])
        return ExtNum(k, v, uf)

# Convenience functions
def safe_div(num: Union[Real, Complex, ExtNum],
             den: Union[Real, Complex, ExtNum],
             use_float: bool = False) -> ExtNum:
    n = num if isinstance(num, ExtNum) else ExtNum.real(num, use_float)
    d = den if isinstance(den, ExtNum) else ExtNum.real(den, use_float)
    return n / d

def Ω(a: Real | Fraction | complex, use_float: bool = False) -> ExtNum:
    return ExtNum.omega(a, use_float)

def bottom() -> ExtNum:
    return ExtNum.bottom()
# test_extnum.py
import unittest, math, cmath
from fractions import Fraction
#from extnum import ExtNum, safe_div, Ω, bottom, Kind

# demo_extnum.py

import math, cmath
from fractions import Fraction
#from extnum import ExtNum, safe_div, Ω, bottom, Kind

def demo_real_arith():
    a = ExtNum.real(2) + ExtNum.real(3)
    b = ExtNum.real(2, use_float=True) + ExtNum.real(1.5, use_float=True)
    print("Real arithmetic:")
    print("  2 + 3 =", a)                 # 5
    print("  2.0 + 1.5 =", b, "\n")       # 3.5

def demo_float_pow():
    r = ExtNum.real(2)
    res = r ** 1.5
    print("Float exponent on real:")
    print(f"  2 ** 1.5 = {res} (use_float={res.use_float})\n")

def demo_negative_float_pow():
    r = ExtNum.real(-2)
    c = r ** 0.5
    print("Negative real to float exponent:")
    print(f"  (-2) ** 0.5 = {c} (kind={c.kind})\n")

def demo_complex_arith():
    c1 = ExtNum.complex(1,1)
    c2 = ExtNum.complex(0,2)
    print("Complex arithmetic:")
    print(f"  (1+1j) + (0+2j) = {c1 + c2}\n")

def demo_omega_and_division():
    w = Ω(2)
    z1 = safe_div(2, 0)
    z2 = safe_div(0, 0)
    print("Ω and safe division:")
    print(f"  2/0 → {z1} (is_infinite={z1.is_infinite()})")
    print(f"  0/0 → {z2} (is_undefined={z2.is_undefined()})\n")

def demo_json_roundtrip():
    r = ExtNum.real(3)
    s = r.to_json()
    r2 = ExtNum.from_json(s)
    print("JSON round-trip:")
    print(f"  original: {r}")
    print(f"  json_str: {s}")
    print(f"  from_json: {r2}\n")

if __name__ == "__main__":
    demo_real_arith()
    demo_float_pow()
    demo_negative_float_pow()
    demo_complex_arith()
    demo_omega_and_division()
    demo_json_roundtrip()
