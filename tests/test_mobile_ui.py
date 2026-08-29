import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MobileUiContractTests(unittest.TestCase):
    def test_phone_companion_controls_and_safe_area_support_are_present(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("viewport-fit=cover", html)
        self.assertIn('id="playBar"', html)
        self.assertIn('id="mobilePrevious"', html)
        self.assertIn('id="mobileCurrent"', html)
        self.assertIn('id="mobileNext"', html)
        self.assertIn("safe-area-inset-bottom", css)
        self.assertIn("prefers-color-scheme: dark", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn('$("#mobilePrevious")', js)
        self.assertIn('$("#mobileNext")', js)
        self.assertIn('$("#mobileCurrent")', js)
        self.assertIn("(max-width: 900px) and (pointer: coarse)", css)

    def test_mobile_restore_and_long_details_are_keyboard_and_overflow_safe(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="chooseRestoreButton"', html)
        self.assertIn('role="alertdialog"', html)
        self.assertIn('aria-labelledby="restoreTitle"', html)
        self.assertIn('$("#confirmRestoreButton").focus()', js)
        self.assertIn("function cancelRestore()", js)
        self.assertIn("overflow-wrap: anywhere", css)
        self.assertIn("scrollIntoView", js)

    def test_phone_setup_diagnoses_security_and_exposes_recovery(self):
        html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        manifest = (ROOT / "web" / "manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('data-view="phone-setup"', html)
        self.assertIn('id="phoneSetupStatus"', html)
        self.assertIn("Local HTTP is online-to-host only", html)
        self.assertIn('href="/api/state-backup"', html)
        self.assertIn("window.isSecureContext", js)
        self.assertIn("Unavailable on this LAN HTTP address", js)
        self.assertIn("Disabled — never queued", js)
        self.assertIn('"display": "standalone"', manifest)

    def test_phone_launcher_opts_in_to_lan_mode(self):
        launcher = (ROOT / "start-guide-phone.sh").read_text(encoding="utf-8")
        windows_launcher = (ROOT / "start-guide-phone.bat").read_text(encoding="utf-8")
        server = (ROOT / "scripts" / "guide_server.py").read_text(encoding="utf-8")
        self.assertIn("--lan --open-browser", launcher)
        self.assertIn("--lan --open-browser", windows_launcher)
        self.assertIn('parser.add_argument("--lan"', server)
        self.assertIn('args.host = "0.0.0.0"', server)


if __name__ == "__main__":
    unittest.main()
