{pkgs}: {
  deps = [
    pkgs.redis
    pkgs.ta-lib
    pkgs.glibcLocales
    pkgs.postgresql
    pkgs.openssl
  ];
}
