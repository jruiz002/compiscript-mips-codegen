function a(): integer {
  class C { function v(): integer { return 1; } }
  let c: C = new C();
  return c.v();
}
function b(): integer {
  class C { function v(): integer { return 2; } }
  let c: C = new C();
  return c.v();
}
print(a());
print(b());
