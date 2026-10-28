let calls: integer = 0;
function t(): boolean { calls = calls + 1; return true; }
function f(): boolean { calls = calls + 1; return false; }
if (f() && t()) { print("no"); }
if (t() || f()) { print("si"); }
let b: boolean = f() || t();
print(b);
print(calls);
print(!b);
