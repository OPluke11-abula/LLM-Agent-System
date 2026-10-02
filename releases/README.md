# Release Evidence & Artifact Catalog

This directory contains release artifacts and cryptographic verification evidence for the FindAi Studio / LLM Agent System (LAS) Desktop Control Plane.

## 0.1.1 Windows NSIS Installer

| Field | Value |
| --- | --- |
| **Artifact** | `aai-agent-topology-viewer_0.1.1_x64-setup.exe` |
| **Platform** | Windows 10 / 11 (x64) |
| **Framework** | Tauri 2.10 (Rust 1.97 / MSVC) + WebView2 Evergreen |
| **Format** | NSIS Standalone Installer |
| **Size** | 2,459,111 bytes (~2.34 MB) |
| **Authenticode Signature** | **Not signed** (Community / Developer Distribution) |
| **SHA-256 Checksum** | `1D4A47DA57E60D641EFE729E7F347DBABCAE84033D1AF0EF45220CE0B6C49B47` |
| **Release Status** | Verified & Active |

## Cryptographic Integrity Verification

Before running or deploying the installer, verify its SHA-256 hash using PowerShell:

```powershell
Get-FileHash .\releases\aai-agent-topology-viewer_0.1.1_x64-setup.exe -Algorithm SHA256
```

Expected output:
```
Algorithm       Hash                                                                   Path
---------       ----                                                                   ----
SHA256          1D4A47DA57E60D641EFE729E7F347DBABCAE84033D1AF0EF45220CE0B6C49B47       ...\releases\aai-agent-topology-viewer_0.1.1_x64-setup.exe
```

> [!NOTE]
> The checksum provides binary integrity verification against corruption or tampering. It does not replace an Authenticode code-signing certificate.

## Building from Source

To build a fresh installer on Windows:

```powershell
# Ensure frontend dependencies and production build are present
npm.cmd --prefix viewer install
npm.cmd --prefix viewer run build

# Package NSIS desktop installer
npm.cmd --prefix viewer run tauri -- build --bundles nsis
```

The output executable is generated at:
`viewer/src-tauri/target/release/bundle/nsis/aai-agent-topology-viewer_0.1.1_x64-setup.exe`

### Build Environment Notes

- **Windows AppLocker / WDAC**: Environments enforcing strict Windows Defender Application Control (WDAC) or AppLocker policies will block temporary intermediate compilation executables in `target/release/build/` (yielding `os error 4551`). Ensure the build directory or cargo target path is appropriately allowed in local execution policies.
- **WiX / MSI**: MSI packaging is currently excluded from standard release bundles pending upstream WiX toolset ICE validation alignment on Windows 11.
