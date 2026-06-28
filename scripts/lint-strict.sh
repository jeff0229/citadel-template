#!/usr/bin/env bash
# LINT-STRICT: deeper checks the standard lint.sh does not cover.
# Usage: bash scripts/lint-strict.sh [--quiet] [--section N]
# Exit:  0 = clean, 1 = at least one finding.
#
# Sections:
#   1  Frontmatter completeness (sources/entities/concepts/synthesis)
#   2  Tier field forbidden on source pages
#   3  Citation typos (year-page smash, e.g. (Author, 20154))
#   3.5 Section heading typos ("Entities and Concepts" / "Gaps and Questions")
#   4  Required source-page section headings
#   5  Tier-promotion eligibility (episodic -> semantic candidates)
#   6  Index-body orphans (file on disk, no bullet in index.md)
#   7  Diacritic prose violations for canonical author names

. "$(dirname "$0")/lib.sh"

QUIET=0
SECTION=""
while [ $# -gt 0 ]; do
  case "$1" in
    --quiet) QUIET=1 ;;
    --section) shift; SECTION="$1" ;;
    --section=*) SECTION="${1#--section=}" ;;
    *) printf 'unknown arg: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

fail=0

run_section() {
  # $1 = section id (string). Returns 0 if section should run.
  [ -z "$SECTION" ] && return 0
  [ "$SECTION" = "$1" ] && return 0
  return 1
}

# Collect all wiki .md files we care about (exclude _archive/).
wiki_md_files() {
  find "$VAULT_ROOT/wiki/sources" "$VAULT_ROOT/wiki/entities" "$VAULT_ROOT/wiki/concepts" "$VAULT_ROOT/wiki/synthesis" \
    -type f -name '*.md' ! -path '*/_archive/*' 2>/dev/null
}

# Extract YAML frontmatter block (between leading '---' lines).
extract_frontmatter() {
  awk 'BEGIN{n=0} /^---[[:space:]]*$/ {n++; next} n==1 {print} n==2 {exit}' "$1"
}

# Read a scalar frontmatter field. Echoes the raw value (may be empty).
fm_field() {
  # $1 file, $2 field
  awk -v field="$2" '
    BEGIN{n=0}
    /^---[[:space:]]*$/ {n++; if(n==2) exit; next}
    n==1 {
      if (match($0, "^[[:space:]]*" field "[[:space:]]*:")) {
        sub("^[[:space:]]*" field "[[:space:]]*:[[:space:]]*", "")
        print
        exit
      }
    }
  ' "$1"
}

# Detect presence of a frontmatter field (1 yes / 0 no).
fm_has() {
  extract_frontmatter "$1" | grep -qE "^[[:space:]]*$2[[:space:]]*:" && echo 1 || echo 0
}

# ----------------------------------------------------------------------------
# Section 1: Frontmatter completeness
# ----------------------------------------------------------------------------
if run_section 1; then
  hits=0
  required="type tags created updated sources confidence last_confirmed"
  while IFS= read -r f; do
    [ -f "$f" ] || continue
    missing=""
    for field in $required; do
      if [ "$(fm_has "$f" "$field")" = "0" ]; then
        missing="$missing $field"
      fi
    done
    # tier (if present) must be one of episodic|semantic|procedural
    tier_val=$(fm_field "$f" "tier" | tr -d '[:space:]')
    bad_tier=""
    if [ -n "$tier_val" ]; then
      case "$tier_val" in
        episodic|semantic|procedural) ;;
        *) bad_tier="$tier_val" ;;
      esac
    fi
    if [ -n "$missing" ] || [ -n "$bad_tier" ]; then
      if [ $hits -eq 0 ]; then
        color_yellow "[STRICT] Section 1: Frontmatter completeness"
      fi
      rel="${f#$VAULT_ROOT/}"
      if [ -n "$missing" ]; then
        printf '  %s  missing:%s\n' "$rel" "$missing"
      fi
      if [ -n "$bad_tier" ]; then
        printf '  %s  bad tier value: %s\n' "$rel" "$bad_tier"
      fi
      hits=$((hits+1))
      fail=1
    fi
  done < <(wiki_md_files)
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 1: frontmatter clean."
  fi
fi

# ----------------------------------------------------------------------------
# Section 2: Tier forbidden on source pages
# ----------------------------------------------------------------------------
if run_section 2; then
  hits=0
  for f in "$SOURCES_DIR"/*.md; do
    [ -f "$f" ] || continue
    tier_val=$(fm_field "$f" "tier" | tr -d '[:space:]')
    if [ -n "$tier_val" ]; then
      if [ $hits -eq 0 ]; then
        color_yellow "[STRICT] Section 2: source pages with forbidden tier:"
      fi
      printf '  %s  tier=%s\n' "$(basename "$f")" "$tier_val"
      hits=$((hits+1))
      fail=1
    fi
  done
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 2: no tier on source pages."
  fi
fi

# ----------------------------------------------------------------------------
# Section 3: Citation year-page smash typos
# ----------------------------------------------------------------------------
if run_section 3; then
  hits=0
  # Pattern: (19|20)YY then 2-4 extra digits attached, no space.
  # Exclude DOIs and ISBN/ISSN-bearing lines, and the lint script itself.
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    file="${line%%:*}"
    rest="${line#*:}"
    lineno="${rest%%:*}"
    text="${rest#*:}"
    # Skip self.
    case "$file" in
      */scripts/lint-strict.sh|*/scripts/lint.sh) continue ;;
    esac
    # Skip DOI / ISBN / ISSN lines.
    case "$text" in
      *doi.org*|*DOI:*|*doi:*) continue ;;
      *ISBN*|*isbn*|*ISSN*|*issn*) continue ;;
    esac
    # Skip lines that look like DOI 10.xxxx/ prefixes.
    if printf '%s' "$text" | grep -qE '10\.[0-9]{4,}/[A-Za-z0-9._/-]+'; then
      continue
    fi
    if [ $hits -eq 0 ]; then
      color_yellow "[STRICT] Section 3: possible year-page smash citations:"
    fi
    rel="${file#$VAULT_ROOT/}"
    printf '  %s:%s  %s\n' "$rel" "$lineno" "$(printf '%s' "$text" | sed 's/^[[:space:]]*//')"
    hits=$((hits+1))
    fail=1
  done < <(grep -rEn --include='*.md' '\b(19|20)[0-9]{2}[0-9]{2,4}\b' "$VAULT_ROOT/wiki" 2>/dev/null)
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 3: no smash-typo citations."
  fi
fi

# ----------------------------------------------------------------------------
# Section 3.5: Section heading typos on source pages
# ----------------------------------------------------------------------------
if run_section 3.5; then
  hits=0
  for f in "$SOURCES_DIR"/*.md; do
    [ -f "$f" ] || continue
    bad1=$(grep -nE '^##[[:space:]]+Entities and Concepts[[:space:]]*$' "$f")
    bad2=$(grep -nE '^##[[:space:]]+Gaps and Questions[[:space:]]*$' "$f")
    if [ -n "$bad1" ] || [ -n "$bad2" ]; then
      if [ $hits -eq 0 ]; then
        color_yellow "[STRICT] Section 3.5: source-page heading typos ('and' instead of '&'):"
      fi
      [ -n "$bad1" ] && printf '  %s  %s\n' "$(basename "$f")" "$bad1"
      [ -n "$bad2" ] && printf '  %s  %s\n' "$(basename "$f")" "$bad2"
      hits=$((hits+1))
      fail=1
    fi
  done
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 3.5: source headings clean."
  fi
fi

# ----------------------------------------------------------------------------
# Section 4: Required source-page section headings
# ----------------------------------------------------------------------------
if run_section 4; then
  hits=0
  required_headings='Overview|Key Points|Quotes|Entities & Concepts|Connections|Gaps & Questions'
  for f in "$SOURCES_DIR"/*.md; do
    [ -f "$f" ] || continue
    missing=""
    for h in "Overview" "Key Points" "Quotes" "Entities & Concepts" "Connections" "Gaps & Questions"; do
      if ! grep -qE "^##[[:space:]]+${h}[[:space:]]*$" "$f"; then
        missing="$missing | $h"
      fi
    done
    if [ -n "$missing" ]; then
      if [ $hits -eq 0 ]; then
        color_yellow "[STRICT] Section 4: source pages missing canonical sections:"
      fi
      printf '  %s  missing:%s\n' "$(basename "$f")" "${missing# |}"
      hits=$((hits+1))
      fail=1
    fi
  done
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 4: source-page sections complete."
  fi
fi

# ----------------------------------------------------------------------------
# Section 5: Tier-promotion eligibility (episodic -> semantic)
# ----------------------------------------------------------------------------
if run_section 5; then
  hits=0
  count_inbound() {
    # $1 = file. Echoes count of inbound wikilinks across wiki/**/*.md excluding self.
    local self="$1"
    local base
    base=$(basename "$self" .md)
    # Escape regex meta in basename for grep -F? Use grep -F-style fixed by piping per-link.
    # Use ripgrep-style pattern: \[\[<base>(\||\])
    # grep -E with escaped base; escape regex specials.
    local esc
    esc=$(printf '%s' "$base" | sed 's/[][\\.^$*+?(){}|/-]/\\&/g')
    grep -rE --include='*.md' "\\[\\[${esc}(\\||\\])" "$VAULT_ROOT/wiki" 2>/dev/null \
      | grep -v "^${self}:" \
      | wc -l | tr -d ' '
  }
  for dir in "$ENTITIES_DIR" "$CONCEPTS_DIR"; do
    [ -d "$dir" ] || continue
    for f in "$dir"/*.md; do
      [ -f "$f" ] || continue
      tier_val=$(fm_field "$f" "tier" | tr -d '[:space:]')
      [ "$tier_val" = "episodic" ] || continue
      conf=$(fm_field "$f" "confidence" | tr -d '[:space:]')
      [ -z "$conf" ] && continue
      # Compare conf >= 0.6 via awk.
      conf_ok=$(awk -v c="$conf" 'BEGIN{print (c+0 >= 0.6) ? 1 : 0}')
      [ "$conf_ok" = "1" ] || continue
      inbound=$(count_inbound "$f")
      if [ "$inbound" -ge 2 ]; then
        if [ $hits -eq 0 ]; then
          color_yellow "[STRICT] Section 5: tier promotion candidates (episodic -> semantic):"
        fi
        rel="${f#$VAULT_ROOT/}"
        printf '  %s  inbound=%s confidence=%s\n' "$rel" "$inbound" "$conf"
        hits=$((hits+1))
        fail=1
      fi
    done
  done
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 5: no pending tier promotions."
  fi
fi

# ----------------------------------------------------------------------------
# Section 6: Index-body orphans (file on disk but not bulleted in index.md)
# ----------------------------------------------------------------------------
if run_section 6; then
  hits=0
  if [ ! -f "$INDEX_FILE" ]; then
    color_yellow "[STRICT] Section 6: index.md not found at $INDEX_FILE"
    fail=1
  else
    # Build list of bulleted [[wikilinks]] under '- [[' in index.md (basename only).
    idx_links=$(grep -oP '(?<=- \[\[)[^\]|#]+(?=\]\]|\|)' "$INDEX_FILE" | awk -F'/' '{print $NF}' | sort -u)
    check_dir() {
      local d="$1"
      [ -d "$d" ] || return
      find "$d" -type f -name '*.md' ! -path '*/_archive/*' ! -name 'index.md' 2>/dev/null
    }
    {
      check_dir "$SOURCES_DIR"
      check_dir "$ENTITIES_DIR"
      check_dir "$CONCEPTS_DIR"
      check_dir "$SYNTHESIS_DIR"
    } | while IFS= read -r f; do
      base=$(basename "$f" .md)
      if ! printf '%s\n' "$idx_links" | grep -Fxq "$base"; then
        if [ $hits -eq 0 ]; then
          color_yellow "[STRICT] Section 6: files on disk missing from index.md body:"
          hits=1
        fi
        rel="${f#$VAULT_ROOT/}"
        printf '  %s\n' "$rel"
      fi
    done
    # Re-check whether anything was printed using a tempfile is overkill; instead, recompute.
    orphan_count=$({
      check_dir "$SOURCES_DIR"
      check_dir "$ENTITIES_DIR"
      check_dir "$CONCEPTS_DIR"
      check_dir "$SYNTHESIS_DIR"
    } | while IFS= read -r f; do
      base=$(basename "$f" .md)
      if ! printf '%s\n' "$idx_links" | grep -Fxq "$base"; then
        echo x
      fi
    done | wc -l | tr -d ' ')
    if [ "$orphan_count" = "0" ] && [ $QUIET -eq 0 ]; then
      color_green "[STRICT] Section 6: every file has an index bullet."
    elif [ "$orphan_count" != "0" ]; then
      fail=1
    fi
  fi
fi

# ----------------------------------------------------------------------------
# Section 7: Diacritic prose violations
# ----------------------------------------------------------------------------
if run_section 7; then
  hits=0
  # canonical|ascii pairs
  pairs="Mihailescu|Mihailescu Tornberg|Tornberg Gobel|Gobel Marin-Llado|Marin-Llado"
  # Use explicit array of pairs (canonical_diacritic ascii_form).
  check_pair() {
    local canonical="$1"
    local ascii="$2"
    # ripgrep ascii across wiki/**/*.md, then filter.
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      file="${line%%:*}"
      rest="${line#*:}"
      lineno="${rest%%:*}"
      text="${rest#*:}"
      # Skip frontmatter lines (between the first pair of --- markers).
      # Cheap heuristic: line begins with a known frontmatter key or is within first 15 lines AND we detect frontmatter.
      # Instead, parse precisely: skip if line is inside frontmatter block.
      in_fm=$(awk -v target="$lineno" 'BEGIN{n=0} /^---[[:space:]]*$/ {n++} {if (NR==target+0) {print (n==1)?1:0; exit}}' "$file")
      [ "$in_fm" = "1" ] && continue
      # Skip wikilink contexts: if every occurrence of $ascii on the line sits inside [[...]], skip.
      # Strip [[...]] then re-check.
      stripped=$(printf '%s' "$text" | sed 's/\[\[[^]]*\]\]//g')
      if ! printf '%s' "$stripped" | grep -q "$ascii"; then
        continue
      fi
      # Skip heading lines that mirror filename (start with '# ' and contain the ascii form).
      case "$text" in
        \#\ *|\#\#\ *|\#\#\#\ *) continue ;;
      esac
      if [ $hits -eq 0 ]; then
        color_yellow "[STRICT] Section 7: ASCII-only prose use of diacritic-bearing names:"
      fi
      rel="${file#$VAULT_ROOT/}"
      printf '  %s:%s  [%s -> %s]  %s\n' "$rel" "$lineno" "$ascii" "$canonical" "$(printf '%s' "$text" | sed 's/^[[:space:]]*//')"
      hits=$((hits+1))
      fail=1
    done < <(grep -rn --include='*.md' -F "$ascii" "$VAULT_ROOT/wiki" 2>/dev/null)
  }
  check_pair "Mihăilescu" "Mihailescu"
  check_pair "Törnberg"  "Tornberg"
  check_pair "Göbel"     "Gobel"
  check_pair "Marín-Lladó" "Marin-Llado"
  if [ $hits -eq 0 ] && [ $QUIET -eq 0 ]; then
    color_green "[STRICT] Section 7: no diacritic prose violations."
  fi
fi

exit $fail
