# AXION Config Registry Editor Spec v1

## Product
- Name: **Axion Registry Editor**
- ID: `axion-regedit`

## Goals
- Familiar editor UX for advanced users/admins
- Safer defaults than legacy registry tools
- Full backup/rollback integration

## Core features
- Tree + key/value pane
- Search (exact/contains/regex optional)
- Add/edit/delete keys/values
- Import/export `.reg`-style bundles (Axion-safe format support)
- Compare two snapshots

## Safety controls
- Default read-only mode on protected roots
- Edit mode requires explicit elevation + confirmation
- Pre-change automatic checkpoint + transaction log
- One-click rollback by corr id
- Protected path denylist (unless advanced override)

## UX
- color-coded risk badges (low/med/high)
- inline schema/type validation
- change preview diff before apply

## v1 done
- reliable key/value operations
- safe rollback on every change
- full audit/event trace integration
