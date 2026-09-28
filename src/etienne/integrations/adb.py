import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pathlib import Path

from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner


@dataclass
class UIElement:
    text: str
    content_description: str
    resource_id: str
    package: str
    class_name: str
    focused: bool
    focusable: bool
    clickable: bool
    selected: bool
    bounds: str


class ADBClient:
    def __init__(
        self,
        host: str,
        port: int = 5555,
        key_path: str = ".adb/adbkey",
    ):
        self.device = AdbDeviceTcpAsync(
            host,
            port,
            default_transport_timeout_s=10.0,
        )
        self.key_path = Path(key_path)

    async def connect(self) -> None:
        self.key_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.key_path.exists():
            keygen(str(self.key_path))

        private_key = self.key_path.read_text()
        public_key = Path(
            f"{self.key_path}.pub"
        ).read_text()

        signer = PythonRSASigner(
            public_key,
            private_key,
        )

        await self.device.connect(
            rsa_keys=[signer],
            auth_timeout_s=10.0,
        )

    async def shell(self, command: str) -> str:
        return await self.device.shell(command)

    async def send_key(self, key: str) -> None:
        await self.shell(
            f"input keyevent {key}"
        )

    async def open_app(self, package: str) -> None:
        """Open an Android app by package name."""
        await self.shell(
            f"monkey -p {package} 1"
        )

    async def get_ui_xml(self) -> str:
        """Get raw UI XML from the current screen."""
        await self.shell(
            "uiautomator dump /sdcard/window.xml"
        )

        return await self.shell(
            "cat /sdcard/window.xml"
        )

    async def get_ui(self) -> list[UIElement]:
        """Parse raw UI XML into UIElement objects."""
        xml = await self.get_ui_xml()
        root = ET.fromstring(xml)

        elements: list[UIElement] = []

        for node in root.iter("node"):
            attributes = node.attrib

            elements.append(
                UIElement(
                    text=attributes.get("text", ""),
                    content_description=attributes.get(
                        "content-desc",
                        "",
                    ),
                    resource_id=attributes.get(
                        "resource-id",
                        "",
                    ),
                    package=attributes.get("package", ""),
                    class_name=attributes.get("class", ""),
                    focused=attributes.get("focused") == "true",
                    focusable=attributes.get("focusable") == "true",
                    clickable=attributes.get("clickable") == "true",
                    selected=attributes.get("selected") == "true",
                    bounds=attributes.get("bounds", ""),
                )
            )

        return elements

    async def get_focused_element(self) -> UIElement | None:
        """Find the currently focused UI element."""
        elements = await self.get_ui()

        for element in elements:
            if element.focused:
                return element

        return None