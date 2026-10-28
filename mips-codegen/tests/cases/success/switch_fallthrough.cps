function f(x: integer) {
  switch (x) {
    case 1: print("uno");
    case 2: print("dos"); break;
    case 3: print("tres");
    default: print("otro");
  }
}
f(1); f(2); f(3); f(9);
