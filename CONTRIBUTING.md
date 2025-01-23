# Contributing

## Testing

You can run tests in two different environments: without dokku installed locally (majority of them) and with dokku
installed.


### Without Dokku installed

This method won't run all tests but will run the majority of them. It requires Python and
`requirements-development.txt` packages installed. You may want to use a virtualenv for this.

On the first time, execute:

```shell
python -m venv venv
source venv/bin/activate
pip install -r requirements-development.txt
```

Then:

```shell
make test  # Use `make test-v` for the verbose option
```


### With Dokku installed

The "real" tests executes Dokku commands. To make it easier to run we provide a script to help running a virtual
machine so you can test Dokku easily.


#### Creating the VM

The `make vm-create` script is meant to be run on a Debian GNU/Linux machine, requires `sudo` and will:

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
make vm-create # ~2min with a good Internet connection
```

The VM's IP address will be shown. You may want to copy your SSH public key so it's easier to connect:

```shell
ssh-copy-id debian@$(make vm-ip)
```

After that you can connect to the VM and install Docker, Dokku and some Dokku plugins so you can run the tests:

```shell
ssh debian@$(make vm-ip) sudo /root/install.sh  # ~4min
```

You may also download and compile other Python versions using pyenv with:

```shell
ssh debian@$(make vm-ip) bash -i /home/debian/install-pythons.sh  # ~12min
```

After that, you may want to create a snapshot of the current disk, so you can easily go back to this fresh install
state if the tests make the disk dirty:

```shell
OVERLAY_QCOW2="/var/lib/libvirt/images/pydokku.qcow2"

make vm-stop
sudo qemu-img snapshot -c "Docker and Dokku installed" "$OVERLAY_QCOW2"
make vm-start
```

And to return to a specific snapshot:

```shell
OVERLAY_QCOW2="/var/lib/libvirt/images/pydokku.qcow2"

make vm-stop
sudo qemu-img snapshot -a "Docker and Dokku installed" "$OVERLAY_QCOW2"
make vm-start
```

You can list all snapshots by running `sudo qemu-img snapshot -l $OVERLAY_QCOW2`.


#### Running tests inside the VM

By now, the only way to run tests inside the VM is:
- Use the shared folder to create a Git bare repository
- From your host machine, push the current repository to the shared one
- From the VM, clone the repository, install dependencies and run `make test`

To execute these steps, first run on your host machine:

```shell
HOST_SHARED="/var/lib/libvirt/shared/debian12-pydokku"
REPO_PATH="${HOST_SHARED}/repo.git/"

sudo mkdir -p "$REPO_PATH"
sudo chown -R ${SUDO_USER:-$USER}:libvirt "$HOST_SHARED"
git init --bare --initial-branch=develop "$REPO_PATH"
git remote add shared "$REPO_PATH"
git push shared develop
```

Connect to the VM using `make vm-ssh` and run inside the VM as the user `debian`:

```shell
cd
source venv/bin/activate
git clone /shared/repo.git pydokku
cd pydokku
make test
```

If you make changes to the repository on the host machine, push them by running `git push shared` and then, inside the
VM:

```shell
cd ~/pydokku
git fetch origin
git reset --hard origin/develop # WARNING: this will REMOVE all changes made in the VM repository!
make test
```
