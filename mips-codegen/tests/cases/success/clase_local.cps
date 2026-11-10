function fabrica(n: integer): integer {
  class Contador {
    let valor: integer;
    function constructor(v: integer) { this.valor = v; }
    function doble(): integer { return this.valor * 2; }
  }
  let c: Contador = new Contador(n);
  return c.doble() + 1;
}
print(fabrica(20));
print(fabrica(3));
