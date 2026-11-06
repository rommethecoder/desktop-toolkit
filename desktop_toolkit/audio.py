"""Switch between two explicitly configured PulseAudio/PipeWire-Pulse sinks."""

import argparse
import subprocess


def choose(current, first, second, available):
    if first == second or any(s not in available for s in [first, second]):
        raise ValueError("Choose two different sink names from pactl list short sinks.")
    return second if current == first else first


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("first")
    p.add_argument("second")
    args = p.parse_args()
    try:
        available = [
            line.split("\t")[1]
            for line in subprocess.check_output(
                ["pactl", "list", "short", "sinks"], text=True
            ).splitlines()
        ]
        current = subprocess.check_output(
            ["pactl", "get-default-sink"], text=True
        ).strip()
        target = choose(current, args.first, args.second, available)
        subprocess.run(["pactl", "set-default-sink", target], check=True)
        print("Default output:", target)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        p.exit(1, str(e) + "\n")


if __name__ == "__main__":
    main()
