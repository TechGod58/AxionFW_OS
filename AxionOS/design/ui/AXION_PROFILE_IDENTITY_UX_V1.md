# AXION Profile Identity UX v1

Purpose: make profile/username changes easy and safe without breaking paths, permissions, or app data.

## 1) Goals
- One-click guided rename flow
- Keep user data paths stable via immutable internal user ID
- Preserve app settings/tokens/permissions after rename

## 2) Model
- `user_id` (immutable internal key, never changes)
- `display_name` (easy to change)
- `handle` (optional @name, can change)
- `profile_path_alias` (stable alias mapped to user_id)

## 3) Rename Flow
1. User opens Profile Settings -> Identity
2. Edits display name/handle
3. System validates uniqueness/policy
4. Applies update atomically
5. Rebuilds UI references (taskbar/start/menu/account chip)
6. Emits audit event `profile.identity.updated`

## 4) Compatibility Rules
- Avoid hard-binding app data to mutable username strings
- Legacy paths use alias/symlink mapping where needed
- Existing permissions follow `user_id`, not display name

## 5) v1 Done
- Rename completes without breaking app data or login state
- Username change reflected across shell UI instantly
