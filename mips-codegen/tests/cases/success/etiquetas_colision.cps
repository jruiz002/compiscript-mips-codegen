function x(): integer { return 1; }
class f {
  function x(): integer { return 2; }
}
let o: f = new f();
print(x());
print(o.x());
