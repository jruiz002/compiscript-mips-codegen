let v: integer[] = [1, 2, 3];
try {
  print(v[1]);
  print(v[3]);
  print("nunca");
} catch (e) {
  print("capturado: " + e);
}
try { print(v[-1]); } catch (e2) { print(e2); }
print("fin");
