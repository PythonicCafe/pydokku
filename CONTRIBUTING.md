# Contributing



## Testing

We provide a script to help running a virtual machine so you can test Dokku easily. This script is meant to be run on a
Debian GNU/Linux machine and will:

1. Install required system packages to manage virtual machines with libvirt
2. Configure user permissions and the default libvirt network
3. Download an official Debian 12 "cloud-ready" QCOW2 image
4. Generate cloud-init YAML files to configure the virtual machine with:
   - Locale and timezone settings
   - SSH password authentication enabled
   - A root user and a default non-root user (`debian`) with sudo privileges
   - Pre-installed `openssh-server` package for remote access
   - A custom Docker + Dokku installation script (`/root/install.sh`)
5. Create an overlay QCOW2 disk image (so the original Debian 12 won't be overwritten)
6. Use `virt-install` to create a VM with 2 GB of RAM, 2 vCPUs, the overlay QCOW2 disk and cloud-init configs
7. Wait for the virtual machine's network to become available and retrieve its IP address

Note that you must install and properly configure libvirt before running the script. This step is out of the scope of
this script, but the commands below could help making the Internet connection work inside the VM:

```shell
# Replace 'enp0s31f6' with your network interface
iptables -I FORWARD -i virbr0 -o enp0s31f6 -j ACCEPT
iptables -I FORWARD -i enp0s31f6 -o virbr0 -m state --state RELATED,ESTABLISHED -j ACCEPT
```

After having libvirt configured and running, create the virtual machine by executing:

```shell
sudo ./scripts/create-vm.sh  # ~2min with a good Internet connection
```

The VM's IP address will be shown. After that you can ssh into the machine and install Docker, Dokku and some Dokku
plugins, so we can run the tests:

```shell
ssh debian@<ip-address> sudo /root/install.sh  # ~4min
```

After that, you may want to create a snapshot of the current disk, so you can easily go back to this fresh install
state if the tests make the disk dirty:

```shell
VM_NAME="debian12-dokkupy"
OVERLAY_QCOW2="/var/lib/libvirt/images/dokkupy.qcow2"

make vm-stop
sudo qemu-img snapshot -c "Docker and Dokku installed" "$OVERLAY_QCOW2"
sudo virsh start "$VM_NAME"
```

And to return to a specific snapshot:

```shell
make vm-stop
sudo qemu-img snapshot -a "Docker and Dokku installed" "$OVERLAY_QCOW2"
sudo virsh start "$VM_NAME"
```

You can list all snapshots by running `sudo qemu-img snapshot -l $OVERLAY_QCOW2`.
