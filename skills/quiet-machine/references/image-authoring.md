# Image authoring

Use the official `github.com/hetznercloud/hcloud` Packer plugin. Project-owned
templates may start from any compatible system image or snapshot and may run
arbitrary provisioners.

An image used by Quiet Machine must provide Linux, systemd, cloud-init, sshd,
bash, curl, Python 3, rsync, `flock`, and `timeout`. It must permit root SSH
during bootstrap. The controller creates the task user and passwordless sudo
policy after boot.

Keep the project setup script idempotent and usable both as a Packer
provisioner and as launch-time setup. Bake slow stable steps into the image;
leave experimental steps in launch setup until they work on a fresh VM.

Before snapshot creation, clean package caches, logs, cloud-init state,
`/etc/machine-id`, SSH host keys, source trees, artifacts, and credentials, then
run `fstrim --all || true` and `sync`.

The starter in [`../assets/packer-rust`](../assets/packer-rust) is functional
but deliberately parameterized. Copy it into the project and edit it there.
