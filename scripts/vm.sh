#!/bin/bash
# Manages a Debian12-based virtual machine using libvirt so we can run tests on an isolated environment
# WARNING: DO NOT use "genericcloud" image, since it seems to be incompatible with cloud-init:
# <https://groups.google.com/g/linux.debian.bugs.dist/c/fpGNuIC7GZc>

set -e

PROJECT_NAME="pydokku"
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
SHARED_FOLDER="/var/lib/libvirt/shared/${VM_NAME}"

function log() {
  echo
  echo
  echo "[$(date --iso=seconds)] $@"
}

function vm_create() {
  log "Installing system packages"
  install_libs
  config_permissions
  qemu_connect
  create_shared_folder
  download_image

  log "Creating cloud-init YAML files"
  cat <<EOF >"$CLOUDINIT_USER_YAML"
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
  cat <<EOF >"$CLOUDINIT_META_YAML"
instance-id: $VM_NAME
local-hostname: $VM_NAME
EOF

  log "Creating overlay qcow2 image"
  qemu-img create -f qcow2 -F qcow2 -b "$DEBIAN_QCOW2" "$OVERLAY_QCOW2" "$OVERLAY_DISK_SIZE"

  log "Creating virtual machine"

  if is_gentoo; then
    mkdir /var/lib/libvirt/shared/debian12-pydokku
    mkdir /var/lib/libvirt/boot
  fi

  virt-install \
    --connect "qemu:///system" \
    --name "$VM_NAME" \
    --memory $VM_RAM \
    --vcpus $VM_VCPUS \
    --os-variant debian12 \
    --disk "path=$OVERLAY_QCOW2,format=qcow2,bus=virtio" \
    --filesystem "source.dir=${SHARED_FOLDER},target.dir=host_shared,driver.type=virtiofs" \
    --memorybacking "source.type=memfd,access.mode=shared" \
    --cloud-init "meta-data=$CLOUDINIT_META_YAML,disable=on" \
    --cloud-init "user-data=$CLOUDINIT_USER_YAML,disable=on" \
    --network "network=default,model=virtio" \
    --graphics "none" \
    --console "pty,target_type=serial" \
    --boot hd \
    --noautoconsole

  log "Waiting for the VM network to be up..."
  ip=$(vm_wait_for_ip)
  echo "VM IP address: $ip"
  echo "Use: ssh $DEFAULT_USERNAME@$ip (password: $DEFAULT_PASSWORD)"
}

function is_gentoo() {
  if uname -r | grep -iq "gentoo"; then
    true
  else
    false
  fi
}

function install_libs() {
  if is_gentoo; then
    echo "Gentoo system detected. Running emerge --sync..."
    emerge --sync
    emerge --deep app-emulation/libvirt app-emulation/qemu virtiofsd app-emulation/virt-manager whois
    systemctl start libvirtd
  else
    echo "Non-Gentoo system detected. Running apt update..."
    apt update
    apt install -y libvirt-daemon-system virtiofsd
  fi
}

function config_permissions() {
  log "Configuring libvirt user permission and network"
  if ! groups $USER | grep -q "\blibvirt\b"; then
    usermod -a -G libvirt $USER
  fi
}

function qemu_connect() {
  if ! virsh --connect "qemu:///system" net-info default | grep -q "Active:.*yes"; then
    virsh --connect "qemu:///system" net-start default
  fi
  if ! virsh --connect "qemu:///system" net-info default | grep -q "Autostart:.*yes"; then
    virsh --connect "qemu:///system" net-autostart default
  fi
}

function create_shared_folder() {
  log "Creating shared folder"
  mkdir -p "$SHARED_FOLDER"
  chown -R ${SUDO_USER:-$USER}:libvirt "$SHARED_FOLDER"
}

function download_image() {
  log "Downloading Debian cloud-ready image"

  if is_gentoo; then
    mkdir -p /var/lib/libvirt/images
  fi
  wget -c -t 0 -O "$DEBIAN_QCOW2" "$DEBIAN_QCOW2_URL"
}

function vm_start() {
  virsh --connect "qemu:///system" start "$VM_NAME"
  while [[ $(virsh --connect "qemu:///system" -q domstate "$VM_NAME") != "running" ]]; do
    sleep 0.1
  done
}

function vm_stop() {
  virsh --connect "qemu:///system" shutdown "$VM_NAME"
  while [[ $(virsh --connect "qemu:///system" -q domstate "$VM_NAME") != "shut off" ]]; do
    sleep 0.1
  done
}

function vm_delete() {
  virsh --connect "qemu:///system" destroy "$VM_NAME" 2>/dev/null || true
  virsh --connect "qemu:///system" undefine "$VM_NAME" --remove-all-storage 2>/dev/null || true
  rm -f "$OVERLAY_QCOW2" "$CLOUDINIT_USER_YAML" "$CLOUDINIT_META_YAML"
  rm -rf "$SHARED_FOLDER"
}

function vm_wait_for_ip() {
  local VM_IP=""
  while [[ -z "$VM_IP" ]]; do
    VM_IP=$(virsh --connect "qemu:///system" -q domifaddr "$VM_NAME" | grep --color=no ipv4 | sed 's/.*ipv4\s\+//; s/\/.*//')
    sleep 1
  done
  echo "$VM_IP"
}

function vm_ssh() {
  ip=$(vm_wait_for_ip)
  echo "Connecting to ${ip}. Use the password: $DEFAULT_PASSWORD"
  ssh $DEFAULT_USERNAME@$ip
}

subcommand="${1:-}"
case "$subcommand" in
create)
  vm_create
  ;;
start)
  vm_start
  ;;
stop)
  vm_stop
  ;;
ip)
  vm_wait_for_ip
  ;;
ssh)
  vm_ssh
  ;;
delete)
  vm_delete
  ;;
*)
  echo "Usage: $0 {create|start|stop|ip|delete}"
  exit 1
  ;;
esac
