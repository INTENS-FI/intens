% Build model given by env. var. SL_MODEL

[p, n, x] = fileparts(string(getenv('SL_MODEL')));
if p ~= ""
  cd(p);
end
rtwbuild(n + x);
quit;
