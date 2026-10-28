let m: integer[][] = [[1, 2, 3], [4, 5, 6]];
let s: integer = 0;
for (let i: integer = 0; i < 2; i = i + 1) {
  for (let j: integer = 0; j < 3; j = j + 1) {
    m[i][j] = m[i][j] * (i + 1);
    s = s + m[i][j];
  }
}
print(s);
foreach (fila in m) { foreach (v in fila) { print(v); } }
