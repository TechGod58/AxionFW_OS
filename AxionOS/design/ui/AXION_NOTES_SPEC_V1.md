# AXION Notes (Post-It Style) Spec v1

## Goal
OS-level sticky notes utility for quick capture, always-available, low-friction workflow.

## Name
- Product: **Axion Notes**
- ID: `axion-notes`

## Core UX (Windows-familiar)
- Create sticky note instantly
- Pin note above windows
- Color tags
- Auto-save continuously
- Optional reminder timestamp
- Quick search across notes

## Data model (v1)
- note_id
- title (optional)
- body
- color
- pinned (bool)
- created_at / updated_at
- reminder_at (optional)

## Storage
- Local first in Axion profile data
- Optional sync later (v2)
- Crash-safe autosave journal

## Security
- Notes are user-private by default
- Optional lock for sensitive notes
- Audit events for export/delete operations

## v1 acceptance
- Notes persist across restart
- Pin, color, search work
- Fast launch from desktop/taskbar/launcher
