"""Known UE runtime outputs excluded from immutable shipped payload hashes/copies."""
def is_runtime_file(relative):
    path=relative.as_posix()
    # Player/runtime state. Never ship personal saves in the recovery archive.
    if path.startswith('AnomalyLab/Saved/'):return True
    # UE5.8 Core/Private/Misc/ConfigManifest.cpp writes this migration index
    # during normal startup (FConfigManifest::UpgradeFromPreviousVersions).
    return path=='Engine/Saved/Config/Windows/Manifest.ini'
