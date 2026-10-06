"""Compatibility entrypoint; initialize the project database via the supported script."""


def main() -> None:
    raise SystemExit("Use .\\script\\init_db.ps1 instead. It preserves existing project data.")


if __name__ == "__main__":
    main()
