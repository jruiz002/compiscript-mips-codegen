// break/continue dentro de un try deben cerrar su handler: una excepción posterior
// no puede volver a saltar al catch de un try del que ya se salió.
let a: integer[] = [1];
let i: integer = 0;
while (i < 3) {
  i = i + 1;
  try {
    if (i == 1) { continue; }
    if (i == 2) { break; }
  } catch (e) {
    print("no deberia: " + e);
  }
}
print("i = " + i);
for (let j: integer = 0; j < 2; j = j + 1) {
  try {
    try { continue; } catch (e) { print("interno"); }
  } catch (e) {
    print("externo");
  }
}
try {
  print(a[5]);
} catch (e) {
  print("atrapado: " + e);
}
