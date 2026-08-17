packer {
  required_plugins {
    hcloud = {
      version = "= 1.7.2"
      source  = "github.com/hetznercloud/hcloud"
    }
  }
}
variable "base_image" { type = string; default = "ubuntu-24.04" }
variable "location" { type = string }
variable "server_type" { type = string; default = "cx23" }
variable "rust_toolchain" { type = string; default = "stable" }
variable "setup_script" { type = string; default = "setup.sh" }

source "hcloud" "rust" {
  token           = env("HCLOUD_TOKEN")
  image           = var.base_image
  location        = var.location
  server_type     = var.server_type
  ssh_username    = "root"
  snapshot_name   = "quiet-rust-${var.rust_toolchain}-${formatdate("YYYYMMDDhhmm", timestamp())}"
  snapshot_labels = { "quiet-machine-image" = "rust", "rust-toolchain" = var.rust_toolchain }
}

build {
  sources = ["source.hcloud.rust"]
  provisioner "file" { source = var.setup_script; destination = "/tmp/quiet-setup.sh" }
  provisioner "shell" {
    environment_vars = ["RUST_TOOLCHAIN=${var.rust_toolchain}"]
    inline = [
      "chmod +x /tmp/quiet-setup.sh && /tmp/quiet-setup.sh",
      "cloud-init clean --logs --machine-id --seed --configs all",
      "rm -rf /run/cloud-init/* /var/lib/cloud/* /tmp/quiet-setup.sh",
      "rm -f /etc/ssh/ssh_host_* /root/.ssh/authorized_keys",
      "apt-get clean || true",
      "journalctl --rotate --vacuum-time=1s || true",
      "fstrim --all || true",
      "sync"
    ]
  }
}
