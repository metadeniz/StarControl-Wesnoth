#!/usr/bin/env bash
# Play many headless AI-vs-AI games and summarise who wins.
#
#   tools/ai_battles.sh [games-per-map-and-side] [parallel jobs] [faction] [faction] [first seed]
#
# Factions default to SC_Alliance and SC_Hierarchy (others: SC_NewAlliance,
# SC_DeathMarch).
#
# Each map is played with the Alliance as side 1 and again as side 2, so
# first-move advantage cancels out. Needs Wesnoth 1.16 (wesnoth-1.16 or
# wesnoth on PATH) and the add-on linked into a userdata dir; the script
# makes a throwaway one.
set -euo pipefail

GAMES=${1:-10}
JOBS=${2:-$(nproc)}
FA=${3:-SC_Alliance}
FB=${4:-SC_Hierarchy}
SEED0=${5:-1}
HERE=$(cd "$(dirname "$0")/.." && pwd)
WESNOTH=$(command -v wesnoth-1.16 || command -v /usr/games/wesnoth-1.16 || command -v wesnoth)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/user/data/add-ons"
ln -s "$HERE" "$WORK/user/data/add-ons/Star_Control_TC"

# Warm the cache once so parallel games don't all rebuild it.
"$WESNOTH" --userdata-dir "$WORK/user" --nogui --multiplayer --scenario SC_2p_Procyon_Front \
	--era SC_Era_UrQuan_War --controller 1:ai --controller 2:ai --turns 1 --exit-at-end >/dev/null 2>&1 || true

jobs_file="$WORK/jobs"
for map in SC_2p_Procyon_Front SC_2p_Vela_Nebula; do
	for order in "$FA $FB" "$FB $FA"; do
		set -- $order
		for seed in $(seq "$SEED0" $((SEED0 + GAMES - 1))); do
			echo "$map $1 $2 $seed"
		done
	done
done > "$jobs_file"

run_one() {
	local map=$1 s1=$2 s2=$3 seed=$4
	local line
	line=$(timeout 900 "$WESNOTH" --userdata-dir "$WORK/user" --nogui --multiplayer \
		--scenario "$map" --era SC_Era_UrQuan_War \
		--controller 1:ai --controller 2:ai --side "1:$s1" --side "2:$s2" \
		--turns 40 --exit-at-end --rng-seed "$seed" 2>&1 | grep '^SC_RESULT' | head -1 || true)
	echo "$map seed=$seed $line"
}
export -f run_one
export WESNOTH WORK

xargs -P "$JOBS" -L 1 bash -c 'run_one "$@"' _ < "$jobs_file" | tee "$WORK/results"

python3 - "$WORK/results" <<'EOF'
import re, sys, collections
wins = collections.Counter()
by_map = collections.defaultdict(collections.Counter)
recruits = collections.defaultdict(collections.Counter)
turns = []
games = 0
for line in open(sys.argv[1]):
    m = re.search(r"SC_RESULT turn=(\d+) (.*?) glory", line)
    if not m:
        print("NO RESULT:", line.strip()); continue
    games += 1
    turns.append(int(m.group(1)))
    sides = re.findall(r"side(\d)=(\S+) units=(\d+) leader=(\w+)", m.group(2))
    alive = [s for s in sides if s[3] == "true"]
    if len(alive) == 1:
        winner = alive[0][1]
    else:
        # time over: more units left wins, else draw
        a, b = sides
        winner = a[1] if int(a[2]) > int(b[2]) else b[1] if int(b[2]) > int(a[2]) else "draw"
        winner += " (on time)" if winner != "draw" else ""
    wins[winner] += 1
    mp = line.split()[0]
    by_map[mp][winner] += 1
    side_faction = {s[0]: s[1] for s in sides}
    for side, typ, n in re.findall(r"(\d)_(\w+)=(\d+)", line.split("recruits:")[-1]):
        recruits[side_faction[side]][typ] += int(n)
print(f"\n{games} games, average length {sum(turns)/max(1,len(turns)):.1f} turns")
for w, n in wins.most_common():
    print(f"  {w:32s} {n:3d}  ({100*n/games:.0f}%)")
for mp, c in by_map.items():
    print(f"  {mp}: " + ", ".join(f"{w} {n}" for w, n in c.most_common()))
for fac, c in recruits.items():
    print(f"  {fac} recruits: " + ", ".join(f"{t} {n}" for t, n in c.most_common()))
EOF
