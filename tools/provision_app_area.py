"""Sets the `app_metadata.app_area` claim of a Supabase account (operator tool, never run by the apps).

The backend only accepts account tokens whose server-controlled `app_metadata.app_area` equals the app
being used. Clients cannot set it; an operator with the service-role key does. Dry run by default.

    SUPABASE_URL=https://<project>.supabase.co SUPABASE_SERVICE_ROLE_KEY=... \
        python3 tools/provision_app_area.py --user-id <uuid> --area niknolig --apply
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

AREAS = ("niknolig", "niknolig-defense")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def build_request(base_url, service_key, user_id, area):
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.query or parsed.fragment \
            or parsed.path not in ("", "/"):
        raise ValueError("SUPABASE_URL must be an https origin")
    if area not in AREAS:
        raise ValueError("area must be one of: " + ", ".join(AREAS))
    user_id = str(uuid.UUID(user_id))
    if not service_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
    url = f"https://{parsed.netloc}/auth/v1/admin/users/{user_id}"
    body = json.dumps({"app_metadata": {"app_area": area}}).encode()
    headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key,
               "Content-Type": "application/json"}
    return urllib.request.Request(url, data=body, headers=headers, method="PUT")


def main(argv=None, opener=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--area", required=True, choices=AREAS)
    parser.add_argument("--apply", action="store_true", help="perform the change (default: dry run)")
    args = parser.parse_args(argv)
    try:
        request = build_request(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
                                args.user_id, args.area)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if not args.apply:
        print(f"dry run: would set app_metadata.app_area={args.area} for {args.user_id} (use --apply)")
        return 0
    opener = opener or urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=15) as response:
            claims = json.load(response).get("app_metadata", {})
    except (urllib.error.URLError, ValueError) as error:
        print(f"error: request failed ({type(error).__name__})", file=sys.stderr)
        return 1
    if claims.get("app_area") != args.area:
        print("error: server did not confirm the app_area claim", file=sys.stderr)
        return 1
    print(f"app_area={args.area} set for {args.user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
