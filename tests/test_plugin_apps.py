from dokkupy.dokku_cli import Dokku

# TODO: may use dokkupy.inspector to assert the result of each command or mock the command execution and check the
# to-be-executed command (list of strings)


def test_list_create_destroy_app():
    app_name = "test-app"
    dokku = Dokku()
    apps_before = dokku.apps.list()
    dokku.apps.create(app_name)
    apps_after = dokku.apps.list()
    assert len(apps_before) + 1 == len(apps_after)
    assert apps_after[-1].name == app_name
    dokku.apps.destroy(app_name)
    assert len(dokku.apps.list()) == 0


# TODO: implement tests for apps:clone
# TODO: implement tests for apps:lock/unlock
# TODO: implement tests for apps:rename
