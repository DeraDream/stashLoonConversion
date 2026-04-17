#!/usr/bin/env python3
import json
import mimetypes
import os
import re
import secrets
import socket
import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, quote, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
INDEX_PATH = DATA_DIR / "index.json"


def load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def detect_local_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://{detect_local_ip()}:{PORT}").rstrip("/")
SUBSCRIPTION_USERINFO = os.getenv("SUBSCRIPTION_USERINFO", "")


class ConfigError(ValueError):
    pass


@dataclass
class ProxyNode:
    scheme: str
    name: str
    server: str
    port: int
    uuid: str = ""
    password: str = ""
    network: str = "tcp"
    tls: bool = False
    sni: str = ""
    ws_path: str = "/"
    ws_host: str = ""
    flow: str = ""
    security: str = ""
    fingerprint: str = ""
    public_key: str = ""
    short_id: str = ""
    skip_cert_verify: bool = True
    extras: Dict[str, str] = field(default_factory=dict)


def ensure_dirs() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_PATH.exists():
        INDEX_PATH.write_text("[]\n", encoding="utf-8")


def load_template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def json_bytes(payload: Dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slugify_name(name: str) -> str:
    cleaned = re.sub(r"[\r\n\t,=]+", " ", name).strip()
    return cleaned or "Unnamed"


def split_lines(value: str) -> List[str]:
    return [line.strip() for line in value.replace("\r\n", "\n").split("\n") if line.strip()]


def parse_node_text(node_text: str) -> List[ProxyNode]:
    nodes: List[ProxyNode] = []
    for raw in split_lines(node_text):
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        if scheme == "vless":
            nodes.append(parse_vless_link(raw))
            continue
        raise ConfigError(f"暂不支持的节点协议: {scheme}")
    if not nodes:
        raise ConfigError("没有检测到可用节点")
    return nodes


def parse_vless_link(link: str) -> ProxyNode:
    parsed = urlparse(link)
    if not parsed.hostname or not parsed.port:
        raise ConfigError("VLESS 节点缺少服务器地址或端口")
    uuid = unquote(parsed.username or "").strip()
    if not uuid:
        raise ConfigError("VLESS 节点缺少 UUID")

    query = parse_qs(parsed.query, keep_blank_values=True)
    network = first(query, "type", default="tcp").lower()
    security = first(query, "security", default="none").lower()
    name = slugify_name(unquote(parsed.fragment or "VLESS"))
    host = first(query, "host")
    sni = first(query, "sni") or first(query, "serverName")
    path = unquote(first(query, "path", default="/") or "/")
    fingerprint = first(query, "fp")
    public_key = first(query, "pbk")
    short_id = first(query, "sid")
    flow = first(query, "flow")
    skip_cert_verify = first(query, "allowInsecure", default="1") != "0"

    return ProxyNode(
        scheme="vless",
        name=name,
        server=parsed.hostname,
        port=int(parsed.port),
        uuid=uuid,
        network=network,
        tls=security in {"tls", "xtls", "reality"},
        sni=sni,
        ws_path=path,
        ws_host=host,
        flow=flow,
        security=security,
        fingerprint=fingerprint,
        public_key=public_key,
        short_id=short_id,
        skip_cert_verify=skip_cert_verify,
    )


def first(query: Dict[str, List[str]], key: str, default: str = "") -> str:
    values = query.get(key)
    return values[0] if values else default


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_stash_proxy(node: ProxyNode) -> str:
    lines = [
        f"  - name: {yaml_quote(node.name)}",
        f"    type: {node.scheme}",
        f"    server: {node.server}",
        f"    port: {node.port}",
        f"    uuid: {yaml_quote(node.uuid)}",
        f"    udp: true",
    ]
    if node.tls:
        lines.append("    tls: true")
    if node.sni:
        lines.append(f"    servername: {yaml_quote(node.sni)}")
    if node.skip_cert_verify:
        lines.append("    skip-cert-verify: true")
    if node.flow:
        lines.append(f"    flow: {yaml_quote(node.flow)}")
    if node.network and node.network != "tcp":
        lines.append(f"    network: {node.network}")
    if node.network == "ws":
        lines.extend(
            [
                "    ws-opts:",
                f"      path: {yaml_quote(node.ws_path or '/')}",
            ]
        )
        if node.ws_host:
            lines.extend(
                [
                    "      headers:",
                    f"        Host: {yaml_quote(node.ws_host)}",
                ]
            )
    if node.security == "reality":
        lines.append("    reality-opts:")
        if node.public_key:
            lines.append(f"      public-key: {yaml_quote(node.public_key)}")
        if node.short_id:
            lines.append(f"      short-id: {yaml_quote(node.short_id)}")
        if node.fingerprint:
            lines.append(f"    client-fingerprint: {yaml_quote(node.fingerprint)}")
    return "\n".join(lines)


def render_stash_config(nodes: List[ProxyNode], subscribed_url: str) -> str:
    template = load_template("stash-template.yaml")
    proxy_blocks = "\n".join(render_stash_proxy(node) for node in nodes)
    proxy_names = "\n".join(f"      - {yaml_quote(node.name)}" for node in nodes)
    return (
        template.replace("{{SUBSCRIBED_URL}}", subscribed_url)
        .replace("{{PROXIES}}", proxy_blocks)
        .replace("{{PROXY_NAMES}}", proxy_names)
    )


def render_loon_node(node: ProxyNode) -> str:
    parts = [
        f"{node.name} = VLESS",
        node.server,
        str(node.port),
        f'"{node.uuid}"',
        f"transport={node.network or 'tcp'}",
        f"over-tls={'true' if node.tls else 'false'}",
        "udp=true",
    ]
    if node.network in {"ws", "http"}:
        parts.append(f"path={node.ws_path or '/'}")
        if node.ws_host:
            parts.append(f"host={node.ws_host}")
    if node.sni:
        parts.append(f"sni={node.sni}")
    if node.flow:
        parts.append(f"flow={node.flow}")
    if node.public_key:
        parts.append(f'public-key="{node.public_key}"')
    if node.short_id:
        parts.append(f"short-id={node.short_id}")
    if node.fingerprint:
        parts.append(f"tls-cert-sha256={node.fingerprint}")
    if node.skip_cert_verify:
        parts.append("skip-cert-verify=true")
    return ",".join(parts)


def render_loon_config(nodes: List[ProxyNode], subscribed_url: str) -> str:
    template = load_template("loon-template.conf")
    node_lines = "\n".join(render_loon_node(node) for node in nodes)
    csv_names = ",".join(node.name for node in nodes)
    return (
        template.replace("{{SUBSCRIBED_URL}}", subscribed_url)
        .replace("{{NODES}}", node_lines)
        .replace("{{NODE_NAMES_CSV}}", csv_names)
    )


def parse_stash_yaml(content: str) -> List[ProxyNode]:
    if "proxies:" not in content:
        raise ConfigError("上传内容里没有检测到 proxies 段")
    lines = content.replace("\r\n", "\n").split("\n")
    proxies: List[ProxyNode] = []
    current: Optional[Dict[str, object]] = None
    in_proxies = False
    in_ws_opts = False
    in_headers = False

    for raw_line in lines:
        if not raw_line.strip():
            continue
        if raw_line.startswith("proxies:"):
            in_proxies = True
            continue
        if in_proxies and re.match(r"^[A-Za-z0-9_-]+:", raw_line):
            break
        if not in_proxies:
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 2 and line.startswith("- "):
            if current:
                proxies.append(proxy_from_yaml_map(current))
            current = {}
            in_ws_opts = False
            in_headers = False
            key, value = split_yaml_kv(line[2:])
            current[key] = value
            continue

        if current is None:
            continue

        if indent == 4 and line.endswith(":"):
            in_ws_opts = line[:-1] == "ws-opts"
            in_headers = False
            if in_ws_opts:
                current["ws-opts"] = {}
            continue

        if indent == 6 and in_ws_opts and line.endswith(":") and line[:-1] == "headers":
            in_headers = True
            ws_opts = current.setdefault("ws-opts", {})
            if isinstance(ws_opts, dict):
                ws_opts["headers"] = {}
            continue

        if indent == 4:
            key, value = split_yaml_kv(line)
            current[key] = value
            in_ws_opts = False
            in_headers = False
            continue

        if indent == 6 and in_ws_opts:
            key, value = split_yaml_kv(line)
            ws_opts = current.setdefault("ws-opts", {})
            if isinstance(ws_opts, dict):
                ws_opts[key] = value
            continue

        if indent == 8 and in_headers:
            key, value = split_yaml_kv(line)
            ws_opts = current.setdefault("ws-opts", {})
            if isinstance(ws_opts, dict):
                headers = ws_opts.setdefault("headers", {})
                if isinstance(headers, dict):
                    headers[key] = value

    if current:
        proxies.append(proxy_from_yaml_map(current))

    supported = [proxy for proxy in proxies if proxy.scheme == "vless"]
    if not supported:
        raise ConfigError("上传的 YAML 中没有检测到可转换的 vless 节点")
    return supported


def split_yaml_kv(line: str) -> List[str]:
    key, value = line.split(":", 1)
    return [key.strip(), strip_yaml_value(value.strip())]


def strip_yaml_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def proxy_from_yaml_map(mapping: Dict[str, object]) -> ProxyNode:
    scheme = str(mapping.get("type", "")).lower()
    if scheme != "vless":
        return ProxyNode(scheme=scheme or "unknown", name=str(mapping.get("name", "ignored")), server="", port=0)

    ws_opts = mapping.get("ws-opts", {})
    headers = ws_opts.get("headers", {}) if isinstance(ws_opts, dict) else {}
    return ProxyNode(
        scheme="vless",
        name=slugify_name(str(mapping.get("name", "VLESS"))),
        server=str(mapping.get("server", "")),
        port=int(mapping.get("port", 0)),
        uuid=str(mapping.get("uuid", "")),
        network=str(mapping.get("network", "tcp")),
        tls=str(mapping.get("tls", "false")).lower() == "true",
        sni=str(mapping.get("servername", "")),
        ws_path=str(ws_opts.get("path", "/")) if isinstance(ws_opts, dict) else "/",
        ws_host=str(headers.get("Host", "")) if isinstance(headers, dict) else "",
        flow=str(mapping.get("flow", "")),
        public_key=str(mapping.get("public-key", "")),
        short_id=str(mapping.get("short-id", "")),
        skip_cert_verify=str(mapping.get("skip-cert-verify", "true")).lower() == "true",
    )


def build_file_urls(token: str) -> Dict[str, str]:
    stash_url = f"{PUBLIC_BASE_URL}/files/{token}/stash.yaml"
    loon_url = f"{PUBLIC_BASE_URL}/files/{token}/loon.conf"
    return {
        "stash_url": stash_url,
        "loon_url": loon_url,
        "stash_import_url": f"stash://install-config?url={quote(stash_url, safe='')}",
        "loon_import_url": f"loon://import?sub={quote(loon_url, safe='')}",
        "loon_universal_url": f"https://www.nsloon.com/openloon/import?sub={quote(loon_url, safe='')}",
    }


def read_index() -> List[Dict]:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def write_index(records: List[Dict]) -> None:
    INDEX_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_record(token: str, source_name: str, source_type: str, nodes_count: int) -> Dict:
    urls = build_file_urls(token)
    return {
        "token": token,
        "name": source_name,
        "source_type": source_type,
        "nodes_count": nodes_count,
        "created_at": now_iso(),
        "files": urls,
    }


def save_record(record: Dict) -> None:
    records = read_index()
    records = [item for item in records if item.get("token") != record["token"]]
    records.insert(0, record)
    write_index(records)


def list_records() -> List[Dict]:
    records = read_index()
    cleaned: List[Dict] = []
    changed = False
    for record in records:
        token = record.get("token", "")
        if not token:
            changed = True
            continue
        bundle_dir = GENERATED_DIR / token
        if not (bundle_dir / "stash.yaml").exists():
            changed = True
            continue
        record["files"] = build_file_urls(token)
        cleaned.append(record)
    if changed:
        write_index(cleaned)
    return cleaned


def save_generated_bundle(
    stash_content: str,
    loon_content: str,
    source_name: str,
    source_type: str,
    nodes_count: int,
) -> Dict:
    token = secrets.token_urlsafe(8)
    bundle_dir = GENERATED_DIR / token
    bundle_dir.mkdir(parents=True, exist_ok=True)

    stash_path = bundle_dir / "stash.yaml"
    loon_path = bundle_dir / "loon.conf"
    meta_path = bundle_dir / "meta.json"

    stash_path.write_text(stash_content, encoding="utf-8")
    loon_path.write_text(loon_content, encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {
                "token": token,
                "source_name": source_name,
                "source_type": source_type,
                "nodes_count": nodes_count,
                "created_at": now_iso(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    record = build_record(token, source_name, source_type, nodes_count)
    save_record(record)
    return record


class AppHandler(BaseHTTPRequestHandler):
    server_version = "stash-and-loon/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.end_headers()

    def do_HEAD(self) -> None:
        self.route_request(head_only=True)

    def do_GET(self) -> None:
        self.route_request(head_only=False)

    def do_POST(self) -> None:
        if self.path == "/api/generate":
            self.handle_generate()
            return
        if self.path == "/api/convert-upload":
            self.handle_convert_upload()
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def route_request(self, head_only: bool) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.serve_file(STATIC_DIR / "index.html", head_only=head_only)
            return
        if path in {"/convert", "/convert.html"}:
            self.serve_file(STATIC_DIR / "convert.html", head_only=head_only)
            return
        if path == "/api/records":
            self.send_json({"items": list_records()})
            return
        if path.startswith("/static/"):
            relative = path[len("/static/") :]
            self.serve_file(STATIC_DIR / relative, head_only=head_only)
            return
        if path.startswith("/files/"):
            parts = path.split("/")
            if len(parts) != 4:
                self.send_json({"error": "Invalid file path"}, status=HTTPStatus.NOT_FOUND)
                return
            token, filename = parts[2], parts[3]
            self.serve_file(GENERATED_DIR / token / filename, head_only=head_only, subscription=True)
            return
        self.send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def handle_generate(self) -> None:
        try:
            payload = self.read_json()
            node_text = str(payload.get("node_text", "")).strip()
            profile_name = slugify_name(str(payload.get("profile_name", "自定义配置")).strip() or "自定义配置")
            nodes = parse_node_text(node_text)
            preview_urls = build_file_urls("preview-token")
            stash_content = render_stash_config(nodes, preview_urls["stash_url"])
            loon_content = render_loon_config(nodes, preview_urls["loon_url"])
            record = save_generated_bundle(
                stash_content,
                loon_content,
                profile_name,
                "nodes",
                len(nodes),
            )
            urls = record["files"]
            stash_content = render_stash_config(nodes, urls["stash_url"])
            loon_content = render_loon_config(nodes, urls["loon_url"])
            # 保存第二次，确保配置里的订阅地址是真实链接
            token = record["token"]
            (GENERATED_DIR / token / "stash.yaml").write_text(stash_content, encoding="utf-8")
            (GENERATED_DIR / token / "loon.conf").write_text(loon_content, encoding="utf-8")
            self.send_json(
                {
                    "ok": True,
                    "profile_name": profile_name,
                    "nodes_count": len(nodes),
                    "record": record,
                    "files": urls,
                    "stash_preview": stash_content,
                    "loon_preview": loon_content,
                }
            )
        except ConfigError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self.send_json({"error": f"服务器处理失败: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_convert_upload(self) -> None:
        try:
            payload = self.read_json()
            content = str(payload.get("content", "")).strip()
            filename = slugify_name(str(payload.get("filename", "uploaded-stash.yaml")))
            if not content:
                raise ConfigError("上传内容不能为空")
            nodes = parse_stash_yaml(content)
            preview_urls = build_file_urls("preview-token")
            loon_content = render_loon_config(nodes, preview_urls["loon_url"])
            record = save_generated_bundle(
                content,
                loon_content,
                filename,
                "upload",
                len(nodes),
            )
            urls = record["files"]
            loon_content = render_loon_config(nodes, urls["loon_url"])
            token = record["token"]
            (GENERATED_DIR / token / "loon.conf").write_text(loon_content, encoding="utf-8")
            self.send_json(
                {
                    "ok": True,
                    "profile_name": filename,
                    "nodes_count": len(nodes),
                    "record": record,
                    "files": urls,
                    "stash_preview": content,
                    "loon_preview": loon_content,
                }
            )
        except ConfigError as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            self.send_json({"error": f"服务器处理失败: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json(self) -> Dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def serve_file(self, path: Path, head_only: bool = False, subscription: bool = False) -> None:
        if not path.exists() or not path.is_file():
            self.send_json({"error": "File not found"}, status=HTTPStatus.NOT_FOUND)
            return

        body = path.read_bytes()
        mime_type, _ = mimetypes.guess_type(str(path))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        if subscription and SUBSCRIPTION_USERINFO:
            self.send_header("Subscription-Userinfo", SUBSCRIPTION_USERINFO)
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def send_json(self, payload: Dict, status: int = HTTPStatus.OK) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    ensure_dirs()
    server = ThreadingHTTPServer((HOST, PORT), AppHandler)
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] running on {HOST}:{PORT}")
    print(f"public base url: {PUBLIC_BASE_URL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
