function f(n: integer): integer {
  class C {
    let x: integer = n;
    function clon(): C { return new C(); }
  }
  let c: C = new C();
  return c.clon().x;
}
print(f(7));
