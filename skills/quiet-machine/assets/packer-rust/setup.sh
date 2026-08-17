#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends build-essential ca-certificates curl git python3 rsync sudo
id quiet >/dev/null 2>&1 || useradd --create-home --shell /bin/bash quiet
install -d -o quiet -g quiet /home/quiet/.cargo
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs |
  sudo -u quiet env RUSTUP_HOME=/home/quiet/.rustup CARGO_HOME=/home/quiet/.cargo sh -s -- -y --profile minimal --default-toolchain "${RUST_TOOLCHAIN:-stable}"
