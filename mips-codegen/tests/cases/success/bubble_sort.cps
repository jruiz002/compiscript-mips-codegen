function ordenar(a: integer[]): integer {
  let n: integer = 0;
  foreach (x in a) { n = n + 1; }
  let intercambios: integer = 0;
  for (let i: integer = 0; i < n - 1; i = i + 1) {
    for (let j: integer = 0; j < n - 1 - i; j = j + 1) {
      if (a[j] > a[j + 1]) {
        let tmp: integer = a[j];
        a[j] = a[j + 1];
        a[j + 1] = tmp;
        intercambios = intercambios + 1;
      }
    }
  }
  return intercambios;
}
let datos: integer[] = [64, 34, 25, 12, 22, 11, 90, -5, 0];
print("intercambios: " + ordenar(datos));
foreach (d in datos) { print(d); }
