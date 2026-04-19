#!/usr/bin/env python3
"""
=============================================================
  Portfolio Generator -- Build Pipeline
  -------------------------------------
  A single script that replaces ALL old create_*, fix_*, and
  update_* scripts. Reads JSON data, renders Jinja2 templates,
  and outputs a complete static site into /dist.

  Usage:
      python build.py                  # Build default user
      python build.py --user default   # Build specific user
      python build.py --all            # Build ALL users
      python build.py --serve          # Build + local server
=============================================================
"""

import argparse
import json
import os
import shutil
import sys
import traceback
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except ImportError:
    print("ERROR: Jinja2 is required.  Install with:  pip install jinja2")
    sys.exit(1)

# -- Paths --
ROOT_DIR   = Path(__file__).resolve().parent
TMPL_DIR   = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"
USERS_DIR  = ROOT_DIR / "users"
DIST_DIR   = ROOT_DIR / "dist"


# -- Helpers --
def load_json(filepath):
    """Load a JSON file and return the parsed dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def load_user_data(user_dir):
    """Load all JSON data files for a given user directory."""
    data_dir = user_dir / "data"
    data = {}

    # Required
    data["config"] = load_json(data_dir / "config.json")

    # Optional section data
    optional_files = [
        "bio", "experience", "education", "projects",
        "publications", "skills", "workshops", "focus", "graph", "languages"
    ]
    for name in optional_files:
        filepath = data_dir / f"{name}.json"
        if filepath.exists():
            data[name] = load_json(filepath)

    # Graph data for the D3 visualization
    if "graph" in data:
        data["graph_data"] = data["graph"]

    return data


def setup_jinja_env():
    """Create and configure the Jinja2 template environment."""
    env = Environment(
        loader=FileSystemLoader(str(TMPL_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


# -- Page Definitions --
# Each entry: (template_path, output_filename, active_page_id, extra_data_keys)
PAGES = [
    ("pages/index.html",        "index.html",        "home",         []),
    ("pages/graph.html",        "graph.html",        "graph",        ["bio", "graph_data"]),
    ("pages/bio.html",          "bio.html",          "bio",          ["bio"]),
    ("pages/experience.html",   "experience.html",   "experience",   ["experience", "graph_data"]),
    ("pages/education.html",    "education.html",    "education",    ["education", "graph_data"]),
    ("pages/skills.html",       "skills.html",       "skills",       ["skills", "graph_data"]),
    ("pages/projects.html",     "projects.html",     "projects",     ["projects", "graph_data"]),
    ("pages/publications.html", "publications.html", "publications", ["publications", "graph_data"]),
    ("pages/workshops.html",    "workshops.html",    "workshops",    ["workshops", "graph_data"]),
    ("pages/summary.html",      "summary.html",      "focus",        ["focus", "graph_data"]),
    ("pages/contact.html",      "contact.html",      "contact",      ["graph_data"]),
    ("pages/languages.html",    "languages.html",    "languages",    ["languages", "graph_data"]),
]


# -- Build Logic --
def build_user(user_name, env):
    """Build the static site for a single user."""
    user_dir = USERS_DIR / user_name
    if not user_dir.exists():
        print(f"  [X] User directory not found: {user_dir}")
        return False

    print(f"\n  > Building user: {user_name}")

    # Load all data
    data = load_user_data(user_dir)
    config = data["config"]

    # Output directory
    out_dir = DIST_DIR / user_name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Copy static assets
    static_out = out_dir / "static"
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, static_out)
        print(f"    [+] Copied static/ -> {static_out.relative_to(ROOT_DIR)}")

    # Copy user-specific assets (profile image, etc.)
    user_assets = user_dir / "assets"
    if user_assets.exists():
        for asset in user_assets.iterdir():
            shutil.copy2(asset, out_dir / asset.name)
        print(f"    [+] Copied user assets (profile image, etc.)")

    # Render each page
    rendered = 0
    for tmpl_path, out_name, active_page, extra_keys in PAGES:
        try:
            template = env.get_template(tmpl_path)
        except Exception as e:
            print(f"    [X] Template not found: {tmpl_path} - {e}")
            continue

        # Build context: always include config + active_page
        context = {
            "config": config,
            "active_page": active_page,
        }
        # Add extra data keys
        for key in extra_keys:
            if key in data:
                context[key] = data[key]

        # Render
        try:
            html = template.render(**context)
        except Exception as e:
            print(f"    [X] Error rendering {out_name}: {e}")
            traceback.print_exc()
            continue

        # Write output
        out_path = out_dir / out_name
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        rendered += 1

    print(f"    [+] Rendered {rendered}/{len(PAGES)} pages -> {out_dir.relative_to(ROOT_DIR)}/")
    return True


def build_all(env):
    """Build sites for all users in the users/ directory."""
    if not USERS_DIR.exists():
        print("  [X] No users/ directory found.")
        return

    users = [d.name for d in USERS_DIR.iterdir() if d.is_dir()]
    if not users:
        print("  [X] No user directories found in users/")
        return

    print(f"  Found {len(users)} user(s): {', '.join(users)}")
    for user_name in users:
        build_user(user_name, env)


def serve(port=8000):
    """Start a simple HTTP server to preview the built site."""
    import http.server
    import functools

    serve_dir = DIST_DIR / "default"
    if not serve_dir.exists():
        print(f"  [X] Build output not found at {serve_dir}. Run build first.")
        return

    os.chdir(serve_dir)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(serve_dir)
    )
    with http.server.HTTPServer(("", port), handler) as httpd:
        print(f"\n  Serving at http://localhost:{port}")
        print(f"  Serving from: {serve_dir}")
        print(f"  Press Ctrl+C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.")


# -- CLI --
def main():
    parser = argparse.ArgumentParser(
        description="Portfolio Generator - Build Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py                  Build the 'default' user
  python build.py --user john      Build the 'john' user
  python build.py --all            Build all users
  python build.py --serve          Build default + start local server
  python build.py --serve --port 3000
        """
    )
    parser.add_argument("--user", default="default",
                        help="User profile to build (default: 'default')")
    parser.add_argument("--all", action="store_true",
                        help="Build all user profiles")
    parser.add_argument("--serve", action="store_true",
                        help="Start local preview server after build")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port for preview server (default: 8000)")

    args = parser.parse_args()

    print("=" * 55)
    print("  Portfolio Generator - Build Pipeline")
    print("=" * 55)

    env = setup_jinja_env()

    if args.all:
        build_all(env)
    else:
        build_user(args.user, env)

    print("\n" + "-" * 55)
    print("  BUILD COMPLETE!")
    print("-" * 55)

    if args.serve:
        serve(args.port)


if __name__ == "__main__":
    main()
