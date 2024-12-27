from dokkupy.dokku_cli import Dokku

# TODO: may use dokkupy.inspector to assert the result of each command or mock the command execution and check the
# to-be-executed command (list of strings)


def test_ssh_keys():
    dokku = Dokku()
    keys = dokku.ssh_keys.list()
    assert len(keys) == 0

    name = "debian"
    content = """
        ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC9bIQ9NsZXsOVy/ho6KmRob3MPDgXdmj3XsRzUUjTgjMOPjrGkzKnKQmT+Cq05eGqYqJJChsbWrbazYsEntfYwqE2UGuYJRCs7zlXs10nXb007QkxBaiGkrJz94zayR/8qt6+geGejVl9I7l8EINRK1+SOvv62+8fc1TWQwnsboY0kMN59eS64Lvq35k3gSFn6ZC03ompqZp1OJFqMW+wT7FHGCm9Hoe0si+XU6GWqIKrjg+1GBLUxdtcmfxmUjiimHwAcof3OYl+iTl0zCykYLvamTVwjNLV9guRJ9sq68ljtmxNEZtMs3SgS1y9my/HYM8LQYeePxCuXAFFu3lh493e/mu4YrMdk4rO+3Fqlkr10im+SkEIo3EmKnCWturUrf2i3d37w2QNnX+77T313yH6FYx826ZxfoDknktVZYEmeVQNHG1903bmFNfoDY+R+PI3Pkn0NCs7uhXLFL+pDYJHw12ys32XALYQXyIQbx2H2NHFlugGTGemqYQhCm5U= debian@localhost
    """.strip()
    fingerprint = "SHA256:XiRjUCWNDCrKwSFRSqhR2kP33fEkDsUKbbwhCbnJXas"
    dokku.ssh_keys.add(name=name, content=content)

    keys = dokku.ssh_keys.list()
    assert len(keys) == 1
    assert keys[0]["name"] == name
    assert keys[0]["fingerprint"] == fingerprint

    # (venv) debian@localhost:~$ cat .ssh/id_rsa.pub | sudo dokku ssh-keys:add turicas
    # Duplicate ssh key name
    #  !     sshcommand returned an error: 1

    # (venv) debian@localhost:~$ echo "oiioioi" | sudo dokku ssh-keys:add turicasssss
    #  !     Key specified in is not a valid ssh public key


# TODO: implement tests for deleting existing key
# TODO: implement tests for trying to delete a non-existing key
# TODO: implement tests for SSH (key without passphrase)
# TODO: implement tests for SSH (key with passphrase)
