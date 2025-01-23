#!/bin/bash
# Manages a Debian12-based virtual machine using libvirt so we can run tests on an isolated environment
# WARNING: DO NOT use "genericcloud" image, since it seems to be incompatible with cloud-init:
# <https://groups.google.com/g/linux.debian.bugs.dist/c/fpGNuIC7GZc>

set -e

PROJECT_NAME="pydokku"
DEBIAN_QCOW2_URL="https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-generic-amd64.qcow2"
DEBIAN_QCOW2="/var/lib/libvirt/images/$(basename $DEBIAN_QCOW2_URL)"
OVERLAY_QCOW2="/var/lib/libvirt/images/${PROJECT_NAME}.qcow2"
OVERLAY_DISK_SIZE="40G"
CLOUDINIT_USER_YAML="/var/lib/libvirt/images/${PROJECT_NAME}-cloud-init-user.yaml"
CLOUDINIT_META_YAML="/var/lib/libvirt/images/${PROJECT_NAME}-cloud-init-meta.yaml"
INSTALL_SCRIPT_PATH="$(dirname "$0")/install.sh"
INSTALL_PYTHONS_SCRIPT_PATH="$(dirname "$0")/install-pythons.sh"
REPO_PATH="$(dirname "$(dirname "$0")")"
REQUIREMENTS_PATH="${REPO_PATH}/requirements.txt"
REQUIREMENTS_DEVELOPMENT_PATH="${REPO_PATH}/requirements-development.txt"
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
	apt update
	apt install -y libvirt-daemon-system virtiofsd

	log "Configuring libvirt user permission and network"
	if ! groups $USER | grep -q "\blibvirt\b"; then
		adduser $USER libvirt
	fi
	if ! virsh --connect "qemu:///system" net-info default | grep -q "Active:.*yes"; then
		virsh --connect "qemu:///system" net-start default
	fi
	if ! virsh --connect "qemu:///system" net-info default | grep -q "Autostart:.*yes"; then
		virsh --connect "qemu:///system" net-autostart default
	fi
	mkdir -p "$SHARED_FOLDER"
	chown -R ${SUDO_USER:-$USER}:libvirt "$SHARED_FOLDER"

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
  - path: /home/debian/requirements.txt
    permissions: '0755'
    content: |
$(sed 's/^/      /' "$REQUIREMENTS_PATH")
  - path: /home/debian/requirements-development.txt
    permissions: '0755'
    content: |
$(sed 's/^/      /' "$REQUIREMENTS_DEVELOPMENT_PATH")
  - path: /root/install.sh
    permissions: '0755'
    content: |
$(sed 's/^/      /' "$INSTALL_SCRIPT_PATH")
  - path: /home/debian/install-pythons.sh
    permissions: '0755'
    content: |
$(sed 's/^/      /' "$INSTALL_PYTHONS_SCRIPT_PATH")

runcmd:
  - cloud-init-per once setlocales localectl set-locale en_US.UTF-8
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
