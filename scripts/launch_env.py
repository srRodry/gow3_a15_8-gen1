#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared launch environment for run.py (Windows) and run.sh (Linux).

One source for the graphics options, the selected patches and the direct memory (DMEM) /
VBlank those patches need. The two entry points used to duplicate this and drifted apart: the
Linux run.sh missed the GoW3 graphics defaults and the DMEM, so textures were corrupted and the
game faulted building its heaps.
"""
import os
import sys
from pathlib import Path

PORT = Path(__file__).resolve().parent.parent


def derive(game, config, state_path, env):
    """Plan one launch.

    game:       the game folder (eboot.bin)
    config:     gow3.ini path
    state_path: graphics_state.json path (restart confirmation)
    env:        the current environment (GOW3_PATCHES, GOW3_PATCHES_ONLY, explicit overrides)

    Returns:
      updates:     environment variables the graphics options become (GOW3_DEFERRED_READBACK,
                   GOW3_STALE_READBACK, GOW3_ASYNC_SHADERS, GOW3_UPSCALER, GOW3_READBACK_LINEAR)
      patch_names: the selected patch names, resolution and frame rate included
      dmem, vblank: MiB / Hz the selected patches need, or None
      reverted:    a restart never reached the game; the last good options were restored
    """
    sys.path.insert(0, str(PORT / 'scripts'))
    import graphics_options
    from patches import game_profile, game_title_id, patch_profile_status, patch_requirements, selected_patches

    graphics, reverted = graphics_options.prepare(config, state_path)
    updates = dict(graphics_options.environment(graphics))
    # The launcher/in-game settings own the upscaler choice. Do not override GOW3_UPSCALER here:
    # doing so made gow3.ini say fsr3 while Android actually forced "none". Keep only the linear
    # readback safety default; an explicit environment override still wins.
    if 'GOW3_READBACK_LINEAR' not in env:
        updates['GOW3_READBACK_LINEAR'] = '1'
    updates['GOW3_READBACK_LINEAR_SOURCE'] = (
        'override' if 'GOW3_READBACK_LINEAR' in env else 'android-safe-default'
    )

    names, dmem, vblank = [], None, None
    identity = patch_profile_status(game)
    profile = game_profile(identity['title_id'])
    reason = identity['reason'] or 'unknown'
    if identity['reason'] != 'validated':
        # An unknown Android build must never inherit desktop patch names through an env override.
        if profile is None or identity['eboot_matches'] is False:
            updates['GOW3_PATCH_STATUS'] = identity['reason']
    if profile and identity['reason'] == 'validated':
        try:
            names = selected_patches(profile[1], profile[2], env.get('GOW3_PATCHES', ''),
                                     env.get('GOW3_PATCHES_ONLY') == '1')
        except ValueError:
            # Two resolution patches (or another exclusivity violation) cannot both apply.
            names, reason = [], 'patch-conflict'
        if names:
            # gow3.ini decides the resolution and frame rate patches (in-game menu, launcher).
            names = graphics_options.patch_names(names, graphics)
            dmem, vblank = patch_requirements(profile[1], names, profile[2])
            # The retail pool plus the patches' extra DMEM must fit the device (design: gate
            # values by device/runtime capability and fail with a clear log, not an OOM kill).
            device_mem = env.get('GOW3_DEVICE_MEM_MB')
            if dmem and device_mem and str(device_mem).isdigit() and dmem > int(device_mem):
                names, dmem, vblank, reason = [], None, None, 'insufficient-memory-budget'
    updates.update({'GOW3_GAME_TITLE': identity['title_id'] or 'unknown',
                    'GOW3_GAME_VERSION': identity['app_version'] or 'unknown',
                    'GOW3_EBOOT_SHA256': identity['eboot_sha256'] or 'unavailable',
                    'GOW3_PATCH_STATUS': reason})
    return {'updates': updates, 'patch_names': names, 'dmem': dmem, 'vblank': vblank,
            'reverted': reverted, 'identity': identity}


def _quote(value):
    return "'" + value.replace("'", "'\\''") + "'"


def main(argv):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', required=True, type=Path)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--state', required=True, type=Path)
    p.add_argument('--shell', action='store_true',
                   help='print export KEY=VALUE lines (for run.sh) instead of JSON')
    a = p.parse_args(argv)
    plan = derive(a.game, a.config, a.state, dict(os.environ))
    if not a.shell:
        import json
        print(json.dumps(plan))
        return 0
    exports = dict(plan['updates'])
    if plan['patch_names']:
        exports['GOW3_PATCHES'] = ';'.join(plan['patch_names'])
        exports['GOW3_PATCHES_ONLY'] = '1'
    if plan['dmem']:
        exports['GOW3_DMEM_MB'] = str(plan['dmem'])
    if plan['vblank']:
        exports['GOW3_VBLANK_HZ'] = str(plan['vblank'])
    for key, value in exports.items():
        print(f'export {key}={_quote(str(value))}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
