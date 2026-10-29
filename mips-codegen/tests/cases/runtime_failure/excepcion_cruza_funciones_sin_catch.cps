function a(v: integer[]): integer { return v[7]; }
function b(): integer { let v: integer[] = [1]; print("antes"); return a(v); }
print(b());
