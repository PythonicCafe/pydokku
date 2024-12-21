#!/bin/bash
# Creates a Debian12-based virtual machine using libvirt so we can run tests on an isolated environment

set -e

function log() { echo; echo; echo "[$(date --iso=seconds)] $@"; }

# DO NOT use genericcloud image, since it seems to be incompatible with cloud-init:
# <https://groups.google.com/g/linux.debian.bugs.dist/c/fpGNuIC7GZc>
PROJECT_NAME="dokkupy"
DEBIAN_QCOW2_URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
DEBIAN_QCOW2="/var/lib/libvirt/images/$(basename $DEBIAN_QCOW2_URL)"
OVERLAY_QCOW2="/var/lib/libvirt/images/${PROJECT_NAME}.qcow2"
OVERLAY_DISK_SIZE="10G"
CLOUDINIT_USER_YAML="/var/lib/libvirt/images/${PROJECT_NAME}-cloud-init-user.yaml"
CLOUDINIT_META_YAML="/var/lib/libvirt/images/${PROJECT_NAME}-cloud-init-meta.yaml"
INSTALL_SCRIPT_PATH="$(dirname "$0")/install.sh"
DEFAULT_USERNAME="debian"
DEFAULT_PASSWORD="password"
TMP_PATH=$(mktemp -d)
VM_NAME="debian12-${PROJECT_NAME}"
VM_VCPUS=2
VM_RAM=2048

log "Installing system packages"
apt update
apt install -y libvirt-daemon-system

log "Configuring libvirt user permission and network"
if ! groups $USER | grep -q "\blibvirt\b"; then
	adduser $USER libvirt
fi
if ! virsh net-info default | grep -q "Active:.*yes"; then
	virsh net-start default
fi
if ! virsh net-info default | grep -q "Autostart:.*yes"; then
	virsh net-autostart default
fi

log "Downloading Debian cloud-ready image"
wget -c -t 0 -O "$DEBIAN_QCOW2" "$DEBIAN_QCOW2_URL"

log "Creating cloud-init YAML files"
cat <<EOF > "$CLOUDINIT_USER_YAML"
#cloud-config

locale: en_US
timezone: America/Sao_Paulo
ssh_pwauth: true
package_update: true
package_upgrade: true
packages:
  - openssh-server

users:
  - name: root
    shell: /bin/bash
  - name: $DEFAULT_USERNAME
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/bash
    lock_passwd: false
    passwd: "$(echo $DEFAULT_PASSWORD | mkpasswd --method=SHA-512 --stdin)"

write_files:
  - path: /root/install.sh
    permissions: '0755'
    content: |
$(sed 's/^/      /' "$INSTALL_SCRIPT_PATH")

runcmd:
  - sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/g' /etc/locale.gen
  - echo 'LANG=en_US.UTF-8' > /etc/default/locale
  - locale-gen
EOF
cat <<EOF > "$CLOUDINIT_META_YAML"
instance-id: $VM_NAME
local-hostname: $VM_NAME
EOF

log "Creating overlay qcow2 image"
qemu-img create -f qcow2 -F qcow2 -b "$DEBIAN_QCOW2" "$OVERLAY_QCOW2" "$OVERLAY_DISK_SIZE"

log "Creating virtual machine"
virt-install \
	--connect "qemu:///system" \
	--name "$VM_NAME" \
	--memory $VM_RAM \
	--vcpus $VM_VCPUS \
	--os-variant debian12 \
	--disk "path=$OVERLAY_QCOW2,format=qcow2,bus=virtio" \
	--cloud-init "meta-data=$CLOUDINIT_META_YAML,disable=on" \
	--cloud-init "user-data=$CLOUDINIT_USER_YAML,disable=on" \
	--network "network=default,model=virtio" \
	--graphics "none" \
	--console "pty,target_type=serial" \
	--boot hd \
	--noautoconsole

log "Waiting for the VM network to be up..."
VM_IP=""
while [[ -z $VM_IP ]]; do
	VM_IP=$(virsh -q domifaddr $VM_NAME | grep --color=no ipv4 | sed 's/.*ipv4\s\+//; s/\/.*//')
done
echo "VM IP address: $VM_IP - connect using (password: $DEFAULT_PASSWORD):"
echo "ssh $DEFAULT_USERNAME@$VM_IP"
