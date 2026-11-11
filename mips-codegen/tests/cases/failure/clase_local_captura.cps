function externa(): integer {
  let secreto: integer = 7;
  class Caja {
    function leer(): integer { return secreto; }
  }
  let c: Caja = new Caja();
  return c.leer();
}
print(externa());
