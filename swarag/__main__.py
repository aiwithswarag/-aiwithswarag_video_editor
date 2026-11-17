import argparse
import json
from pathlib import Path
import sys
from .runtime import probe, executable, verify_video
from .pipeline import edit, load_plan
from .transcribe import transcribe
from .effect_runner import engine


def main():
    parser = argparse.ArgumentParser(prog="swarag", description="Swarag Video Director — local editing and finishing")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("effects")
    for command in ("inspect", "verify"):
        p = sub.add_parser(command); p.add_argument("input")
    p = sub.add_parser("transcribe"); p.add_argument("input"); p.add_argument("output")
    p.add_argument("--model", default="small"); p.add_argument("--language"); p.add_argument("--offline", action="store_true")
    p = sub.add_parser("edit")
    p.add_argument("--plan"); p.add_argument("--input"); p.add_argument("--output"); p.add_argument("--overwrite", action="store_true")
    p.add_argument("--no-captions", action="store_true"); p.add_argument("--words")
    p.add_argument("--caption-style", choices=["clean","boxed","emphasis"], default="clean")
    p.add_argument("--trim-silence", action="store_true"); p.add_argument("--width", type=int, default=1080)
    p.add_argument("--exports", nargs="*", default=[])
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            import importlib.metadata as metadata
            from .runtime import run
            result = {"python":sys.version.split()[0], "executable":sys.executable}
            for name in ("ffmpeg","ffprobe"):
                result[name] = executable(name)
                result[name+"_version"] = run([result[name],"-version"]).stdout.splitlines()[0]
            result["packages"] = {n:metadata.version(n) for n in ("numpy","Pillow","mediapipe","faster-whisper")}
            result["effects"] = len(engine().EFFECTS)
            filters = run([executable("ffmpeg"),"-filters"]).stdout
            if not all(n in filters for n in ("subtitles", "loudnorm", "silencedetect", "sidechaincompress")):
                raise RuntimeError("FFmpeg lacks required caption/audio filters")
            print(json.dumps(result,indent=2))
        elif args.command == "effects":
            print(json.dumps({k:v[1] for k,v in engine().EFFECTS.items()},indent=2))
        elif args.command == "inspect":
            print(json.dumps({k:v for k,v in probe(args.input).items() if k!="raw"},indent=2))
        elif args.command == "verify":
            print(json.dumps(verify_video(args.input),indent=2))
        elif args.command == "transcribe":
            transcribe(args.input,args.output,model=args.model,language=args.language,offline=args.offline)
        else:
            if args.plan:
                plan = load_plan(args.plan)
            else:
                if not args.input or not args.output: parser.error("edit needs --plan or --input and --output")
                plan = {"input":args.input,"output":args.output,"width":args.width,"trim":{"silence":args.trim_silence},
                        "captions":{"enabled":not args.no_captions,"style":args.caption_style},"exports":args.exports}
                if args.words: plan["captions"]["words"] = args.words
            edit(plan,overwrite=args.overwrite)
    except (ValueError,RuntimeError,FileNotFoundError,FileExistsError) as exc:
        print(f"Swarag: {exc}",file=sys.stderr); return 1
    except KeyboardInterrupt:
        print("Render cancelled. Existing source and output files were preserved.",file=sys.stderr); return 130
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
