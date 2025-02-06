import datetime
from pathlib import Path

from pydokku import Dokku
from pydokku.models import Nginx
from tests.utils import requires_dokku


def test_object_classes():
    dokku = Dokku()
    assert dokku.nginx.object_classes == (Nginx,)


def test_access_logs_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.nginx.access_logs(app_name=app_name, execute=False)
    assert command.command == ["dokku", "nginx:access-logs", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_error_logs_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.nginx.error_logs(app_name=app_name, execute=False)
    assert command.command == ["dokku", "nginx:error-logs", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_parse_stdout():
    stdout = """
        =====> test-app-1 nginx information
            Nginx access log format:
            Nginx computed access log format:
            Nginx global access log format:
            Nginx access log path:
            Nginx computed access log path: /var/log/nginx/test-app-1-access.log
            Nginx global access log path:  /var/log/nginx/test-app-1-access.log
            Nginx bind address ipv4:
            Nginx computed bind address ipv4:
            Nginx global bind address ipv4:
            Nginx bind address ipv6:
            Nginx computed bind address ipv6: ::
            Nginx global bind address ipv6: ::
            Nginx client body timeout:
            Nginx computed client body timeout: 60s
            Nginx global client body timeout: 60s
            Nginx client header timeout:
            Nginx computed client header timeout: 60s
            Nginx global client header timeout: 60s
            Nginx client max body size:
            Nginx computed client max body size: 1m
            Nginx global client max body size: 1m
            Nginx disable custom config:
            Nginx computed disable custom config: false
            Nginx global disable custom config: false
            Nginx error log path:
            Nginx computed error log path: /var/log/nginx/test-app-1-error.log
            Nginx global error log path:   /var/log/nginx/test-app-1-error.log
            Nginx hsts include subdomains:
            Nginx computed hsts include subdomains: true
            Nginx global hsts include subdomains: true
            Nginx hsts max age:
            Nginx computed hsts max age:   15724800
            Nginx global hsts max age:     15724800
            Nginx hsts preload:
            Nginx computed hsts preload:   false
            Nginx global hsts preload:     false
            Nginx hsts:
            Nginx computed hsts:           true
            Nginx global hsts:             true
            Nginx last visited at:         1736745546
            Nginx keepalive timeout:
            Nginx computed keepalive timeout: 75s
            Nginx global keepalive timeout: 75s
            Nginx lingering timeout:
            Nginx computed lingering timeout: 5s
            Nginx global lingering timeout: 5s
            Nginx nginx conf sigil path:
            Nginx computed nginx conf sigil path: nginx.conf.sigil
            Nginx global nginx conf sigil path: nginx.conf.sigil
            Nginx proxy buffer size:
            Nginx computed proxy buffer size: 4k
            Nginx global proxy buffer size: 4k
            Nginx proxy buffering:
            Nginx computed proxy buffering: on
            Nginx global proxy buffering:  on
            Nginx proxy buffers:
            Nginx computed proxy buffers:  8 4k
            Nginx global proxy buffers:    8 4k
            Nginx proxy busy buffers size:
            Nginx computed proxy busy buffers size: 8k
            Nginx global proxy busy buffers size: 8k
            Nginx proxy connect timeout:
            Nginx computed proxy connect timeout: 60s
            Nginx global proxy connect timeout: 60s
            Nginx proxy read timeout:
            Nginx computed proxy read timeout: 60s
            Nginx global proxy read timeout: 60s
            Nginx proxy send timeout:
            Nginx computed proxy send timeout: 60s
            Nginx global proxy send timeout: 60s
            Nginx send timeout:
            Nginx computed send timeout:   60s
            Nginx global send timeout:     60s
            Nginx underscore in headers:
            Nginx computed underscore in headers: off
            Nginx global underscore in headers: off
            Nginx x forwarded for value:
            Nginx computed x forwarded for value: $remote_addr
            Nginx global x forwarded for value: $remote_addr
            Nginx x forwarded port value:
            Nginx computed x forwarded port value: $server_port
            Nginx global x forwarded port value: $server_port
            Nginx x forwarded proto value:
            Nginx computed x forwarded proto value: $scheme
            Nginx global x forwarded proto value: $scheme
            Nginx x forwarded ssl:
            Nginx computed x forwarded ssl:
            Nginx global x forwarded ssl:
    """
    expected = [
        {
            "app_name": "test-app-1",
            "access_log_format": None,
            "global_access_log_format": None,
            "access_log_path": None,
            "global_access_log_path": Path("/var/log/nginx/test-app-1-access.log"),
            "bind_address_ipv4": None,
            "global_bind_address_ipv4": None,
            "bind_address_ipv6": None,
            "global_bind_address_ipv6": "::",
            "client_body_timeout": None,
            "global_client_body_timeout": "60s",
            "client_header_timeout": None,
            "global_client_header_timeout": "60s",
            "client_max_body_size": None,
            "global_client_max_body_size": "1m",
            "disable_custom_config": None,
            "global_disable_custom_config": False,
            "error_log_path": None,
            "global_error_log_path": Path("/var/log/nginx/test-app-1-error.log"),
            "hsts_include_subdomains": None,
            "global_hsts_include_subdomains": True,
            "hsts_max_age": None,
            "global_hsts_max_age": datetime.timedelta(days=182),
            "hsts_preload": None,
            "global_hsts_preload": False,
            "hsts": None,
            "global_hsts": True,
            "last_visited_at": datetime.datetime(2025, 1, 13, 5, 19, 6).utctimetuple(),
            "keepalive_timeout": None,
            "global_keepalive_timeout": "75s",
            "lingering_timeout": None,
            "global_lingering_timeout": "5s",
            "nginx_conf_sigil_path": None,
            "global_nginx_conf_sigil_path": Path("nginx.conf.sigil"),
            "proxy_buffer_size": None,
            "global_proxy_buffer_size": "4k",
            "proxy_buffering": None,
            "global_proxy_buffering": "on",
            "proxy_buffers": None,
            "global_proxy_buffers": "8 4k",
            "proxy_busy_buffers_size": None,
            "global_proxy_busy_buffers_size": "8k",
            "proxy_connect_timeout": None,
            "global_proxy_connect_timeout": "60s",
            "proxy_read_timeout": None,
            "global_proxy_read_timeout": "60s",
            "proxy_send_timeout": None,
            "global_proxy_send_timeout": "60s",
            "send_timeout": None,
            "global_send_timeout": "60s",
            "underscore_in_headers": None,
            "global_underscore_in_headers": "off",
            "x_forwarded_for_value": None,
            "global_x_forwarded_for_value": "$remote_addr",
            "x_forwarded_port_value": None,
            "global_x_forwarded_port_value": "$server_port",
            "x_forwarded_proto_value": None,
            "global_x_forwarded_proto_value": "$scheme",
            "x_forwarded_ssl": None,
            "global_x_forwarded_ssl": None,
        }
    ]
    dokku = Dokku()
    rows_parser = dokku.nginx._get_rows_parser()
    result = rows_parser(stdout)
    result[0]["last_visited_at"] = result[0]["last_visited_at"].utctimetuple()
    assert result == expected


def test_convert_rows():
    input_data = [
        {
            "app_name": "test-app-1",
            "access_log_format": None,
            "global_access_log_format": None,
            "access_log_path": Path("/var/log/nginx/test-app-1-access.log"),
            "global_access_log_path": Path("/var/log/nginx/test-app-1-access.log"),
            "bind_address_ipv4": None,
            "global_bind_address_ipv4": None,
            "bind_address_ipv6": None,
            "global_bind_address_ipv6": "::",
            "client_body_timeout": None,
            "global_client_body_timeout": "60s",
            "client_header_timeout": None,
            "global_client_header_timeout": "60s",
            "client_max_body_size": None,
            "global_client_max_body_size": "1m",
            "disable_custom_config": None,
            "global_disable_custom_config": False,
            "error_log_path": None,
            "global_error_log_path": Path("/var/log/nginx/test-app-1-error.log"),
            "hsts_include_subdomains": None,
            "global_hsts_include_subdomains": True,
            "hsts_max_age": None,
            "global_hsts_max_age": datetime.timedelta(days=182),
            "hsts_preload": None,
            "global_hsts_preload": False,
            "hsts": None,
            "global_hsts": True,
            "last_visited_at": datetime.datetime(2025, 1, 13, 5, 19, 6).utctimetuple(),
            "keepalive_timeout": None,
            "global_keepalive_timeout": "75s",
            "lingering_timeout": None,
            "global_lingering_timeout": "5s",
            "nginx_conf_sigil_path": None,
            "global_nginx_conf_sigil_path": Path("nginx.conf.sigil"),
            "proxy_buffer_size": None,
            "global_proxy_buffer_size": "4k",
            "proxy_buffering": None,
            "global_proxy_buffering": "on",
            "proxy_buffers": None,
            "global_proxy_buffers": "8 4k",
            "proxy_busy_buffers_size": None,
            "global_proxy_busy_buffers_size": "8k",
            "proxy_connect_timeout": None,
            "global_proxy_connect_timeout": "60s",
            "proxy_read_timeout": None,
            "global_proxy_read_timeout": "60s",
            "proxy_send_timeout": None,
            "global_proxy_send_timeout": "60s",
            "send_timeout": None,
            "global_send_timeout": "60s",
            "underscore_in_headers": None,
            "global_underscore_in_headers": "off",
            "x_forwarded_for_value": None,
            "global_x_forwarded_for_value": "$remote_addr",
            "x_forwarded_port_value": None,
            "global_x_forwarded_port_value": "$server_port",
            "x_forwarded_proto_value": None,
            "global_x_forwarded_proto_value": "$scheme",
            "x_forwarded_ssl": None,
            "global_x_forwarded_ssl": None,
        }
    ]
    expected = [
        Nginx(
            app_name=None,
            access_log_format=None,
            access_log_path=None,
            bind_address_ipv4=None,
            bind_address_ipv6="::",
            client_body_timeout="60s",
            client_header_timeout="60s",
            client_max_body_size="1m",
            disable_custom_config=False,
            error_log_path=None,
            hsts=True,
            hsts_include_subdomains=True,
            hsts_max_age=datetime.timedelta(days=182),
            hsts_preload=False,
            keepalive_timeout="75s",
            lingering_timeout="5s",
            nginx_conf_sigil_path=Path("nginx.conf.sigil"),
            proxy_buffer_size="4k",
            proxy_buffering="on",
            proxy_buffers="8 4k",
            proxy_busy_buffers_size="8k",
            proxy_connect_timeout="60s",
            proxy_read_timeout="60s",
            proxy_send_timeout="60s",
            send_timeout="60s",
            underscore_in_headers="off",
            x_forwarded_for_value="$remote_addr",
            x_forwarded_port_value="$server_port",
            x_forwarded_proto_value="$scheme",
            x_forwarded_ssl=None,
        ),
        Nginx(
            app_name="test-app-1",
            access_log_format=None,
            access_log_path=Path("/var/log/nginx/test-app-1-access.log"),
            bind_address_ipv4=None,
            bind_address_ipv6=None,
            client_body_timeout=None,
            client_header_timeout=None,
            client_max_body_size=None,
            disable_custom_config=None,
            error_log_path=Path("/var/log/nginx/test-app-1-error.log"),
            hsts=None,
            hsts_include_subdomains=None,
            hsts_max_age=None,
            hsts_preload=None,
            keepalive_timeout=None,
            last_visited_at=datetime.datetime(2025, 1, 13, 5, 19, 6).utctimetuple(),
            lingering_timeout=None,
            nginx_conf_sigil_path=None,
            proxy_buffer_size=None,
            proxy_buffering=None,
            proxy_buffers=None,
            proxy_busy_buffers_size=None,
            proxy_connect_timeout=None,
            proxy_read_timeout=None,
            proxy_send_timeout=None,
            send_timeout=None,
            underscore_in_headers=None,
            x_forwarded_for_value=None,
            x_forwarded_port_value=None,
            x_forwarded_proto_value=None,
            x_forwarded_ssl=None,
        ),
    ]
    dokku = Dokku()
    result = dokku.nginx._convert_rows(input_data)
    assert result == expected


def test_set_command():
    app_name = "test-app-1"
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    command = dokku.nginx.set(app_name=app_name, key="some-key", value=True, execute=False)
    assert command.command == ["dokku", "nginx:set", app_name, "some-key", "true"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    # Old versions don't support setting some configs globally
    command = dokku.nginx.set(app_name=None, key="some-key", value=123, execute=False)
    assert command.command == ["dokku", "nginx:set", "--global", "some-key", "123"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.nginx.set(app_name=None, key="some-key", value=datetime.timedelta(days=182), execute=False)
    assert command.command == ["dokku", "nginx:set", "--global", "some-key", "15724800"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_unset_command():
    app_name = "test-app-1"
    dokku = Dokku()
    dokku._dokku_version = (0, 35, 15)
    command = dokku.nginx.unset(app_name=app_name, key="some-key", execute=False)
    assert command.command == ["dokku", "nginx:set", app_name, "some-key"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    # Old versions don't support setting some configs globally
    command = dokku.nginx.unset(app_name=None, key="some-key", execute=False)
    assert command.command == ["dokku", "nginx:set", "--global", "some-key"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_start_command():
    dokku = Dokku()
    command = dokku.nginx.start(execute=False)
    assert command.command == ["dokku", "nginx:start"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_stop_command():
    dokku = Dokku()
    command = dokku.nginx.stop(execute=False)
    assert command.command == ["dokku", "nginx:stop"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


def test_validate_config_command():
    app_name = "test-app-1"
    dokku = Dokku()
    command = dokku.nginx.validate_config(app_name=app_name, execute=False)
    assert command.command == ["dokku", "nginx:validate-config", app_name]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False
    command = dokku.nginx.validate_config(app_name=app_name, clean=True, execute=False)
    assert command.command == ["dokku", "nginx:validate-config", app_name, "--clean"]
    assert command.stdin is None
    assert command.check is True
    assert command.sudo is False


@requires_dokku
def test_set_unset_list(create_apps):
    dokku, apps_names = create_apps

    before = [obj for obj in dokku.nginx.list() if obj.app_name in [None] + apps_names]
    assert len(before) == len(apps_names) + 1  # apps + global

    if dokku.version() >= (0, 31, 0):
        dokku.nginx.set(app_name=None, key="client-max-body-size", value="500m")
        dokku.nginx.set(app_name=apps_names[0], key="hsts-max-age", value=84600)
        dokku.nginx.set(app_name=apps_names[1], key="send-timeout", value="120s")
        after = [obj for obj in dokku.nginx.list() if obj.app_name in [None] + apps_names]
        assert after[0].app_name is None
        assert before[0].client_max_body_size != "500m"
        assert after[0].client_max_body_size == "500m"
        assert after[1].app_name == apps_names[0]
        assert before[1].hsts_max_age != datetime.timedelta(seconds=84600)
        assert after[1].hsts_max_age == datetime.timedelta(seconds=84600)
        assert after[2].app_name == apps_names[1]
        assert before[2].send_timeout != "120s"
        assert after[2].send_timeout == "120s"
    else:
        # Old versions don't support setting some configs globally
        dokku.nginx.set(app_name=apps_names[0], key="hsts-max-age", value=84600)
        after = [obj for obj in dokku.nginx.list() if obj.app_name in [None] + apps_names]
        assert after[0].app_name is None
        assert before[0].client_max_body_size is None
        assert after[0].client_max_body_size is None
        assert after[1].app_name == apps_names[0]
        assert before[1].hsts_max_age != datetime.timedelta(seconds=84600)
        assert after[1].hsts_max_age == datetime.timedelta(seconds=84600)
