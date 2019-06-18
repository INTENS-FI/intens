% Build model given by env. var. SL_MODEL

[p, n, x] = fileparts(string(getenv('SL_MODEL')));
cd(p);
rtwbuild(n + x);
quit;
