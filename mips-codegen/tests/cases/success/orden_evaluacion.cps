let g: integer = 5;
function bump(): integer { g = g + 10; return 1; }
function suma(a: integer, b: integer): integer { return a * 100 + b; }
class Par {
  let a: integer;
  let b: integer;
  function constructor(a: integer, b: integer) { this.a = a; this.b = b; }
  function mas(x: integer, y: integer): integer { return this.a + x * 100 + y; }
}

print(g + bump() + g);
print(g * bump());
print(g - bump() * 2);
if (g == bump() + 34) { print("igual"); } else { print("distinto"); }
if (g < bump() * 50) { print("menor"); } else { print("no menor"); }
let m: boolean = g > bump() * 60;
print(m);
print(suma(g, bump()));
let p: Par = new Par(g, bump());
print(p.a);
print(p.mas(g, bump()));

let arr: integer[] = [10, 20, 30];
let i: integer = 0;
function avanza(): integer { i = i + 1; return 100; }
function cambia(): integer { arr = [7, 8, 9]; return 1; }
print(arr[i] + avanza());
print(i + avanza() + i);
print(arr[cambia()]);
print(arr[0]);

let s: string = "a";
function cambiaS(): integer { s = "b"; return 1; }
print(s + cambiaS());
print(s);
print(g);
