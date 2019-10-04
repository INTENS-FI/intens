% Build model given by env. var. SL_MODEL

sup = getenv('MAT_SETUP');
if ~isempty(sup)
  run(sup);
end

[p, n, x] = fileparts(string(getenv('SL_MODEL')));
if p ~= ""
  cd(p);
end
rtwbuild(n + x);
quit;
