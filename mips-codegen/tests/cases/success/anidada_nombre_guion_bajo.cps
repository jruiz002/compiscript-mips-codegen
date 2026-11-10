// La anidada se llama `_sumar` / `sumar__dos`: el padre no debe promover sus variables a $s,
// porque la hija las lee y escribe en memoria por el enlace estático.
function externa(): integer {
  let x: integer = 0;
  let i: integer = 0;
  function _sumar(): void { x = x + 10; }
  function sumar__dos(): void { x = x + 2; }
  while (i < 3) {
    _sumar();
    sumar__dos();
    print(x);
    i = i + 1;
  }
  return x;
}
print(externa());
