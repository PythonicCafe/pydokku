from textwrap import dedent

from pydokku import Dokku


def test_parse_list():
    stdout = dedent(
        """
        SOURCE                                                                                                                                                                                                                                                                                           DESTINATION      CODE
        old.example.net                                                                                                                                                                                                                                                                                  new.example.net  301
        too-big-too-big-too-big-too-big.com                                                                                                                                                                                                                                                              olar.net         301
        too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com  olar.net         302
    """
    ).strip()
    dokku = Dokku()
    result = dokku.redirect._parse_list(stdout)
    expected = [
        {
            "source": "old.example.net",
            "destination": "new.example.net",
            "code": 301,
        },
        {
            "source": "too-big-too-big-too-big-too-big.com",
            "destination": "olar.net",
            "code": 301,
        },
        {
            "source": "too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com.too-big-too-big-too-big-too-big.com",
            "destination": "olar.net",
            "code": 302,
        },
    ]
    assert result == expected


def test_set_command():
    dokku = Dokku()
    app_name = "test-app-1"
    old_domain = "old.example.net"
    new_domain = "new.example.net"
    code = 302

    command = dokku.redirect.set(app_name=app_name, source=old_domain, destination=new_domain, execute=False)
    assert command.command == ["dokku", "redirect:set", app_name, old_domain, new_domain]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False

    command = dokku.redirect.set(app_name=app_name, source=old_domain, destination=new_domain, code=code, execute=False)
    assert command.command == ["dokku", "redirect:set", app_name, old_domain, new_domain, str(code)]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_unset_command():
    dokku = Dokku()
    app_name = "test-app-1"
    old_domain = "old.example.net"

    command = dokku.redirect.unset(app_name=app_name, source=old_domain, execute=False)
    assert command.command == ["dokku", "redirect:unset", app_name, old_domain]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


# TODO: test object_list
# TODO: test object_create
