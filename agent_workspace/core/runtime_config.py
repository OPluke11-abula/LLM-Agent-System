import os
from dataclasses import dataclass
from typing import Mapping


class FeatureFlagError(ValueError):
    pass


_TRUE_VALUES = frozenset({"true", "1", "yes", "on"})
_FALSE_VALUES = frozenset({"false", "0", "no", "off"})


def _parse_bool(name: str, value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise FeatureFlagError(
        f"{name} must be one of true, 1, yes, on, false, 0, no, off."
    )


@dataclass(frozen=True)
class RuntimeFeatureFlags:
    enable_stripe: bool = False
    enable_redis_swarm: bool = False
    enable_multi_worker: bool = False
    enable_audit_consensus: bool = False

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "RuntimeFeatureFlags":
        values = os.environ if environ is None else environ
        return cls(
            enable_stripe=_parse_bool("LAS_ENABLE_STRIPE", values.get("LAS_ENABLE_STRIPE")),
            enable_redis_swarm=_parse_bool("LAS_ENABLE_REDIS_SWARM", values.get("LAS_ENABLE_REDIS_SWARM")),
            enable_multi_worker=_parse_bool("LAS_ENABLE_MULTI_WORKER", values.get("LAS_ENABLE_MULTI_WORKER")),
            enable_audit_consensus=_parse_bool(
                "LAS_ENABLE_AUDIT_CONSENSUS", values.get("LAS_ENABLE_AUDIT_CONSENSUS")
            ),
        )

    @property
    def distributed_enabled(self) -> bool:
        return self.enable_redis_swarm and self.enable_multi_worker


def get_runtime_feature_flags() -> RuntimeFeatureFlags:
    return RuntimeFeatureFlags.from_env()
