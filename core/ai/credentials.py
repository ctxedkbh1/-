import os
from dataclasses import dataclass
from typing import Protocol


SERVICE_NAME = "PaperAssistant"


class CredentialStore(Protocol):
    def get(self, reference: str) -> str:
        ...

    def set(self, reference: str, secret: str) -> None:
        ...

    def delete(self, reference: str) -> None:
        ...


@dataclass(frozen=True, slots=True)
class CredentialError(RuntimeError):
    message: str

    def __str__(self) -> str:
        return self.message


class MemoryCredentialStore:
    def __init__(self, values: dict[str, str] | None = None):
        self._values = dict(values or {})

    def get(self, reference: str) -> str:
        return self._values.get(reference, "")

    def set(self, reference: str, secret: str) -> None:
        self._values[reference] = str(secret or "")

    def delete(self, reference: str) -> None:
        self._values.pop(reference, None)


class NullCredentialStore:
    def get(self, reference: str) -> str:
        return ""

    def set(self, reference: str, secret: str) -> None:
        raise CredentialError("系统安全凭据存储不可用")

    def delete(self, reference: str) -> None:
        return


class WindowsCredentialStore:
    def __init__(self, service_name: str = SERVICE_NAME):
        self.service_name = service_name
        try:
            import keyring
        except ImportError as exc:
            raise CredentialError("未安装 keyring，无法使用 Windows Credential Manager") from exc
        self._keyring = keyring

    def get(self, reference: str) -> str:
        try:
            return str(self._keyring.get_password(self.service_name, reference) or "")
        except self._keyring.errors.KeyringError as exc:
            raise CredentialError(f"读取 Windows 凭据失败: {exc}") from exc

    def set(self, reference: str, secret: str) -> None:
        try:
            self._keyring.set_password(self.service_name, reference, str(secret or ""))
        except self._keyring.errors.KeyringError as exc:
            raise CredentialError(f"保存 Windows 凭据失败: {exc}") from exc

    def delete(self, reference: str) -> None:
        try:
            self._keyring.delete_password(self.service_name, reference)
        except self._keyring.errors.PasswordDeleteError:
            return
        except self._keyring.errors.KeyringError as exc:
            raise CredentialError(f"删除 Windows 凭据失败: {exc}") from exc


@dataclass(frozen=True, slots=True)
class MigrationReport:
    migrated: int
    failed: tuple[str, ...]


def resolve_api_key(provider, store: CredentialStore, legacy_key: str = "") -> str:
    if provider.env_key:
        env_value = os.environ.get(provider.env_key, "").strip()
        if env_value:
            return env_value
    references = [provider.credential_ref or f"provider:{provider.provider_id}"]
    legacy_reference = f"legacy:{provider.provider_id}:top-level"
    if legacy_reference not in references:
        references.append(legacy_reference)
    for reference in references:
        stored = store.get(reference)
        if stored:
            return stored
    return str(legacy_key or "").strip()


def migrate_legacy_credentials(config, store: CredentialStore) -> MigrationReport:
    migrated = 0
    failed = []
    changed = False

    for model_key, model in config.models().items():
        secret = str(model.get("api_key") or "").strip()
        if not secret:
            continue
        reference = f"provider:{model_key}"
        try:
            store.set(reference, secret)
            if store.get(reference) != secret:
                raise CredentialError("凭据写入后校验失败")
        except CredentialError as exc:
            failed.append(f"{model_key}: {exc}")
            continue
        model["api_key"] = ""
        migrated += 1
        changed = True

    top_level = str(config.get("deepseek_api_key") or "").strip()
    if top_level:
        reference = "legacy:deepseek:top-level"
        try:
            store.set(reference, top_level)
            if store.get(reference) != top_level:
                raise CredentialError("旧 DeepSeek 凭据写入后校验失败")
        except CredentialError as exc:
            failed.append(f"deepseek_api_key: {exc}")
        else:
            config.data["deepseek_api_key"] = ""
            migrated += 1
            changed = True

    if changed:
        config.data.setdefault("ai_center", {}).setdefault("migration", {})[
            "credentials_migrated"
        ] = not failed
        config.save()
    return MigrationReport(migrated=migrated, failed=tuple(failed))

# 版本: v2.0.1 (2026-08-17) 更新: Windows 安全凭据与旧 Key 迁移
