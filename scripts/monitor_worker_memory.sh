#!/usr/bin/env bash
# Monitor memory used by each latency worker process tree.

set -u

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
project_dir=$(cd "$script_dir/.." && pwd)
service_name="witty-ub-backend"
pid_file="$project_dir/.deploy-logs/backend.pid"
main_pid=""
interval=1
run_once=0
output_file="worker-memory-$(date '+%Y%m%d-%H%M%S').svg"
data_file=""
chart_written=0

usage() {
    cat <<'EOF'
Usage: monitor_worker_memory.sh [options]

Options:
  -p, --main-pid PID    FastAPI main process PID (auto-detected by default)
  -f, --pid-file FILE   backend PID file
                        (default: <project>/.deploy-logs/backend.pid)
  -s, --service NAME    systemd user service (default: witty-ub-backend)
  -i, --interval SEC    refresh interval (default: 1)
  -o, --output FILE     SVG output path (default: worker-memory-<time>.svg)
  -1, --once            print one sample and exit
  -h, --help            show this help

Each WORKER row represents one direct multiprocessing child of the FastAPI
process. RSS/PSS include all descendants of that worker, such as
witty-ub-diag-tool and parallel scan helpers. The ALL row shows the
system-wide delta (free "used" - baseline) instead of summed PSS.
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

while (($#)); do
    case "$1" in
        -p|--main-pid)
            (($# >= 2)) || die "$1 requires a PID"
            main_pid=$2
            shift 2
            ;;
        -s|--service)
            (($# >= 2)) || die "$1 requires a service name"
            service_name=$2
            shift 2
            ;;
        -f|--pid-file)
            (($# >= 2)) || die "$1 requires a path"
            pid_file=$2
            shift 2
            ;;
        -i|--interval)
            (($# >= 2)) || die "$1 requires a number of seconds"
            interval=$2
            shift 2
            ;;
        -o|--output)
            (($# >= 2)) || die "$1 requires a path"
            output_file=$2
            shift 2
            ;;
        -1|--once)
            run_once=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
done

[[ $interval =~ ^[0-9]+([.][0-9]+)?$ ]] || die "invalid interval: $interval"

read_free_used_kb() {
    free -m | awk '/^Mem:/ {print $3 * 1024}'
}

discover_main_pid() {
    local pid=""
    # deploy/host defaults to nohup and records the exec'ed FastAPI PID here.
    if [[ -r $pid_file ]]; then
        pid=$(awk 'NR == 1 {print $1; exit}' "$pid_file" 2>/dev/null || true)
        if [[ $pid =~ ^[1-9][0-9]*$ ]] && [[ -r /proc/$pid/status ]]; then
            printf '%s\n' "$pid"
            return 0
        fi
    fi
    # DEPLOY_PM=systemd installs a user unit, not a system unit.
    if command -v systemctl >/dev/null 2>&1; then
        pid=$(systemctl --user show "$service_name.service" \
            -p MainPID --value 2>/dev/null || true)
    fi
    if [[ ! $pid =~ ^[1-9][0-9]*$ ]] || [[ ! -r /proc/$pid/status ]]; then
        pid=$(pgrep -o -f 'latency/access/fastapi_server.py' 2>/dev/null || true)
    fi
    [[ $pid =~ ^[1-9][0-9]*$ ]] || return 1
    printf '%s\n' "$pid"
}

if [[ -z $main_pid ]]; then
    main_pid=$(discover_main_pid) || die \
        "cannot find backend via $pid_file, systemd user unit, or process list; pass --main-pid PID"
fi
[[ $main_pid =~ ^[1-9][0-9]*$ ]] || die "invalid main PID: $main_pid"
[[ -r /proc/$main_pid/status ]] || die "process $main_pid is not readable"

data_file=$(mktemp "${TMPDIR:-/tmp}/witty-worker-memory.XXXXXX") || \
    die "cannot create temporary sample file"
start_epoch=$(date +%s)

children_of() {
    local parent=$1
    local status pid ppid
    for status in /proc/[0-9]*/status; do
        [[ -r $status ]] || continue
        pid=${status#/proc/}
        pid=${pid%/status}
        ppid=$(awk '$1 == "PPid:" {print $2; exit}' "$status" 2>/dev/null)
        [[ $ppid == "$parent" ]] && printf '%s\n' "$pid"
    done
}

is_resource_tracker() {
    local pid=$1 cmdline
    cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
    [[ $cmdline == *multiprocessing.resource_tracker* ]]
}

collect_tree() {
    local root=$1 current child
    local -a queue=("$root")
    local index=0
    while ((index < ${#queue[@]})); do
        current=${queue[$index]}
        ((index += 1))
        [[ -r /proc/$current/status ]] || continue
        printf '%s\n' "$current"
        while IFS= read -r child; do
            [[ -n $child ]] && queue+=("$child")
        done < <(children_of "$current")
    done
}

memory_kb() {
    local pid=$1 field=$2 file value
    if [[ $field == Pss ]]; then
        file="/proc/$pid/smaps_rollup"
    else
        file="/proc/$pid/status"
    fi
    value=$(awk -v key="$field:" '$1 == key {print $2; exit}' "$file" 2>/dev/null)
    printf '%s\n' "${value:-0}"
}

format_kb() {
    awk -v kb="$1" 'BEGIN {
        if (kb >= 1048576) printf "%.2f GiB", kb / 1048576;
        else if (kb >= 1024) printf "%.1f MiB", kb / 1024;
        else printf "%d KiB", kb;
    }'
}

process_label() {
    local root=$1 pid comm cmdline label="python-worker"
    comm=$(awk -F '[()]' '{print $2}' "/proc/$root/stat" 2>/dev/null || true)
    [[ -n $comm ]] && label=$comm
    while IFS= read -r pid; do
        cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
        if [[ $label == python* && $cmdline == *witty-ub-diag-tool* ]]; then
            label="diagnosis-worker"
            break
        fi
    done < <(collect_tree "$root")
    printf '%s\n' "$label"
}

print_sample() {
    local now epoch root pid rss pss total_rss total_pss count cpu label child_pids used free_used free_delta
    local all_rss=0 all_pss=0 worker_count=0 all_used
    now=$(date '+%F %T')
    epoch=$(date +%s)
    printf '\n%s  main_pid=%s  service=%s\n' "$now" "$main_pid" "$service_name"
    printf '%-8s %-8s %-20s %10s %10s %8s %s\n' \
        WORKER PPID TYPE RSS USED CPU% TREE_PIDS

    while IFS= read -r root; do
        [[ -n $root && -r /proc/$root/status ]] || continue
        is_resource_tracker "$root" && continue
        total_rss=0
        total_pss=0
        count=0
        child_pids=""
        while IFS= read -r pid; do
            [[ -n $pid ]] || continue
            rss=$(memory_kb "$pid" VmRSS)
            pss=$(memory_kb "$pid" Pss)
            total_rss=$((total_rss + rss))
            total_pss=$((total_pss + pss))
            count=$((count + 1))
            child_pids+="${child_pids:+,}$pid"
        done < <(collect_tree "$root")
        cpu=$(ps -p "$root" -o %cpu= 2>/dev/null | awk '{$1=$1; print}' || true)
        label=$(process_label "$root")
        used=$total_pss
        ((used > 0)) || used=$total_rss
        all_rss=$((all_rss + total_rss))
        all_pss=$((all_pss + total_pss))
        worker_count=$((worker_count + 1))
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
            "$((epoch - start_epoch))" "$root" "$label" \
            "$total_rss" "$total_pss" "$used" >>"$data_file"
        printf '%-8s %-8s %-20s %10s %10s %8s %s\n' \
            "$root" "$main_pid" "$label" \
            "$(format_kb "$total_rss")" "$(format_kb "$total_pss")" \
            "${cpu:-?}" "$child_pids"
    done < <(children_of "$main_pid")
    if ((worker_count > 0)); then
        free_used=$(read_free_used_kb)
        free_delta=$((free_used - baseline_free_used_kb))
        printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
            "$((epoch - start_epoch))" "ALL" "all-worker-trees" \
            "$all_rss" "$all_pss" "$free_delta" >>"$data_file"
        printf '%-8s %-8s %-20s %10s %10s %8s %s\n' \
            "ALL" "$main_pid" "all-worker-trees" \
            "$(format_kb "$all_rss")" "$(format_kb "$free_delta")" \
            "-" "all"
    fi
    printf 'Note: ALL total = free used - baseline; per-worker uses PSS (RSS double-counts shared pages).\n'
}

render_svg() {
    [[ -n $data_file && -s $data_file ]] || {
        printf 'No worker samples collected; SVG was not generated.\n' >&2
        return 0
    }
    mkdir -p "$(dirname "$output_file")" 2>/dev/null || true
    awk -F '\t' '
    BEGIN {
        W=1200; H=720; L=85; R=285; T=70; B=80;
        colors[1]="#2563eb"; colors[2]="#dc2626"; colors[3]="#16a34a";
        colors[4]="#9333ea"; colors[5]="#ea580c"; colors[6]="#0891b2";
        colors[7]="#4f46e5"; colors[8]="#be123c";
    }
    {
        t[NR]=$1+0; pid[NR]=$2; label[$2]=$3; value[NR]=$6+0;
        if (!($2 in seen)) { seen[$2]=++workers; order[workers]=$2; }
        if (value[NR] > peak[$2]) { peak[$2]=value[NR]; peak_t[$2]=t[NR]; }
        if (t[NR] > max_t) max_t=t[NR];
        if (value[NR] > max_v) max_v=value[NR];
    }
    END {
        if (max_t < 1) max_t=1;
        if (max_v < 1) max_v=1;
        plot_w=W-L-R; plot_h=H-T-B;
        print "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"" W "\" height=\"" H "\" viewBox=\"0 0 " W " " H "\">";
        print "<rect width=\"100%\" height=\"100%\" fill=\"#ffffff\"/>";
        print "<style>text{font-family:system-ui,sans-serif;fill:#1f2937}.grid{stroke:#e5e7eb;stroke-width:1}.axis{stroke:#374151;stroke-width:1.5}</style>";
        print "<text x=\"" L "\" y=\"32\" font-size=\"22\" font-weight=\"700\">Latency worker memory</text>";
        print "<text x=\"" L "\" y=\"54\" font-size=\"12\" fill=\"#6b7280\">Per-worker: PSS (fallback RSS); ALL: free used - baseline</text>";
        for (g=0; g<=5; g++) {
            y=T+plot_h-g*plot_h/5; mib=max_v*g/5/1024;
            print "<line class=\"grid\" x1=\"" L "\" y1=\"" y "\" x2=\"" L+plot_w "\" y2=\"" y "\"/>";
            printf "<text x=\"%d\" y=\"%.1f\" text-anchor=\"end\" font-size=\"11\">%.1f MiB</text>\n", L-8,y+4,mib;
        }
        for (g=0; g<=5; g++) {
            x=L+g*plot_w/5; sec=max_t*g/5;
            print "<line class=\"grid\" x1=\"" x "\" y1=\"" T "\" x2=\"" x "\" y2=\"" T+plot_h "\"/>";
            printf "<text x=\"%.1f\" y=\"%d\" text-anchor=\"middle\" font-size=\"11\">%.0fs</text>\n",x,T+plot_h+22,sec;
        }
        print "<line class=\"axis\" x1=\"" L "\" y1=\"" T "\" x2=\"" L "\" y2=\"" T+plot_h "\"/>";
        print "<line class=\"axis\" x1=\"" L "\" y1=\"" T+plot_h "\" x2=\"" L+plot_w "\" y2=\"" T+plot_h "\"/>";
        for (w=1; w<=workers; w++) {
            p=order[w]; c=colors[(w-1)%8+1]; points="";
            if (p=="ALL") c="#111827";
            for (i=1; i<=NR; i++) if (pid[i]==p) {
                v=(value[i]<0?0:value[i]); x=L+t[i]/max_t*plot_w; y=T+plot_h-v/max_v*plot_h;
                points=points sprintf("%.1f,%.1f ",x,y);
            }
            stroke_width=(p=="ALL" ? 3.5 : 2);
            print "<polyline fill=\"none\" stroke=\"" c "\" stroke-width=\"" stroke_width "\" points=\"" points "\"/>";
            px=L+peak_t[p]/max_t*plot_w; py=T+plot_h-peak[p]/max_v*plot_h;
            print "<circle cx=\"" px "\" cy=\"" py "\" r=\"4\" fill=\"" c "\"/>";
            ly=T+20+(w-1)*48;
            print "<line x1=\"" L+plot_w+25 "\" y1=\"" ly "\" x2=\"" L+plot_w+55 "\" y2=\"" ly "\" stroke=\"" c "\" stroke-width=\"3\"/>";
            legend=(p=="ALL" ? "ALL (free used delta)" : "PID " p " " label[p]);
            print "<text x=\"" L+plot_w+65 "\" y=\"" ly-3 "\" font-size=\"12\" font-weight=\"600\">" legend "</text>";
            printf "<text x=\"%d\" y=\"%.1f\" font-size=\"12\">peak %.1f MiB @ %.0fs</text>\n",L+plot_w+65,ly+15,peak[p]/1024,peak_t[p];
        }
        print "<text x=\"" L+plot_w/2 "\" y=\"" H-25 "\" text-anchor=\"middle\" font-size=\"13\">Elapsed time</text>";
        print "</svg>";
    }' "$data_file" >"$output_file"
    chart_written=1
    printf '\nSVG written: %s\n' "$output_file"
}

cleanup() {
    local status=$?
    if ((chart_written == 0)); then
        render_svg || true
    fi
    [[ -z $data_file ]] || rm -f -- "$data_file"
    return "$status"
}

trap cleanup EXIT
trap 'exit 0' INT TERM

baseline_free_used_kb=$(read_free_used_kb) || die "cannot read free output"
printf 'Baseline free used: %s (ALL total = free used - baseline)\n' \
    "$(format_kb "$baseline_free_used_kb")"

while [[ -r /proc/$main_pid/status ]]; do
    print_sample
    ((run_once == 1)) && exit 0
    sleep "$interval"
done

die "latency main process $main_pid exited"
