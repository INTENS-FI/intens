% Download a compatible Matlab runtime package (unless already done)
% and print information about it into mcr.json.
compiler.runtime.download;
s = struct;
s.file = mcrinstaller;
[s.major, s.minor] = mcrversion;
f = fopen('mcr.json', 'w');
fprintf(f, '%s\n', jsonencode(s));
fclose(f);
quit;
