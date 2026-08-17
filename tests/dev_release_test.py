import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from scripts.release import ReleaseError, bump_version, current_version, scan_secrets

    assert bump_version("2.0.1", "patch") == "2.0.2"
    assert bump_version("2.0.1", "minor") == "2.1.0"
    assert bump_version("2.0.1", "major") == "3.0.0"
    current = current_version()
    assert len(current.split(".")) == 3
    scan_secrets()
    try:
        bump_version("2.0.1", "unknown")
    except ReleaseError:
        pass
    else:
        raise AssertionError("unknown bump type must be rejected")
    print("RELEASE AUTOMATION TEST OK")


if __name__ == "__main__":
    main()

# 版本: v2.0.1 (2026-08-17) 更新: 语义版本与 Secret 发布门测试
