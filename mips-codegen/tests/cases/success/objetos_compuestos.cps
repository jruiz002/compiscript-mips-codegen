class Motor {
  let potencia: integer;
  function constructor(p: integer) { this.potencia = p; }
  function turbo(): integer { return this.potencia * 2; }
}
class Auto {
  let motor: Motor;
  let nombre: string;
  function constructor(n: string, m: Motor) { this.nombre = n; this.motor = m; }
  function info(): string { return this.nombre + ":" + this.potencia(); }
  function potencia(): integer { return this.motor.turbo() + 1; }
}
function crear(n: string, p: integer): Auto { return new Auto(n, new Motor(p)); }
let a: Auto = crear("rapido", 100);
let b: Auto = crear("lento", 7);
print(a.info()); print(b.info());
a.motor.potencia = 5;
print(a.potencia());
