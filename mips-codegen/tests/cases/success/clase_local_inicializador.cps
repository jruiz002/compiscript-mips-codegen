function f1(n: integer): integer {
  class A { let x: integer = n; }
  let c: A = new A();
  return c.x;
}
function f(n: integer): integer {
  class C { let x: integer = n * 2; }
  function g(): integer { let c: C = new C(); return c.x; }
  return g();
}
class G {
  function m(k: integer): integer {
    function h(): integer {
      class D { let y: integer = k + 1; }
      let d: D = new D();
      return d.y;
    }
    return h();
  }
}
print(f1(7));
print(f(7));
let o: G = new G();
print(o.m(4));
