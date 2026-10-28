class Animal {
  let nombre: string;
  let patas: integer = 4;
  function constructor(nombre: string) { this.nombre = nombre; }
  function hablar(): string { return this.nombre + " hace ruido"; }
  function patas2(): integer { return this.patas * 2; }
}
class Perro : Animal {
  function hablar(): string { return this.nombre + " ladra"; }
}
class Pajaro : Animal {
  let alas: integer = 2;
  function constructor(n: string) { this.nombre = n; this.patas = 2; }
  function volar(): integer { return this.alas + this.patas; }
}
let a: Animal = new Animal("Bicho");
let p: Animal = new Perro("Toby");
let b: Pajaro = new Pajaro("Piolin");
print(a.hablar()); print(p.hablar()); print(b.hablar());
print(a.patas2()); print(b.patas2()); print(b.volar());
