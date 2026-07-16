#!/usr/bin/env bash
set -euo pipefail
COMMIT=c9e97343e0af998cd1696e85583eccba95532b96
PREFIX=/opt/monad/libfive
SRC=/opt/monad/libfive-src
rm -rf "$SRC"
git clone https://github.com/libfive/libfive "$SRC"
git -C "$SRC" checkout "$COMMIT"
cmake -S "$SRC" -B "$SRC/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DBUILD_STUDIO=OFF
cmake --build "$SRC/build" -j2
cmake --install "$SRC/build"
install -m 0755 "$SRC/bin/export-meshes" "$PREFIX/bin/export-meshes"
cat > /usr/local/bin/monad-libfive-export <<EOF
#!/usr/bin/env bash
export GUILE_LOAD_PATH="$PREFIX/share/guile/site/3.0:$PREFIX/share/guile/site/2.2:\${GUILE_LOAD_PATH:-}"
export LD_LIBRARY_PATH="$PREFIX/lib:\${LD_LIBRARY_PATH:-}"
exec guile --no-auto-compile -s "$PREFIX/bin/export-meshes" "\$@"
EOF
chmod 0755 /usr/local/bin/monad-libfive-export
