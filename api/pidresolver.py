import httpx
import idutils


def get_resolved_pid_status_code(pid: str) -> dict:
    id_scheme = idutils.detect_identifier_schemes(pid)
    if id_scheme:
        pidx = idutils.to_url(pid, id_scheme[0])
        respons = resolvepid(pidx, True)
        return {pidx: respons}
    return {pid: "Identifier scheme not recognised"}


def resolvepid(pid: str, verify: bool) -> str:
    client = httpx.Client(follow_redirects=True, timeout=httpx.Timeout(10.0, connect=10.0), verify=verify, max_redirects=20)
    try:
        response = client.get(pid)
        print(f"{pid}; Status {response.status_code}; #Redirs:{len(response.history)}" + (" =>SSL validation disabled" if not verify else ""))
        return response.status_code
    except httpx.HTTPError as error:  # See: https://www.python-httpx.org/exceptions/ & https://www.python-httpx.org/quickstart/#exceptions
        if verify:
            resolvepid(pid, False)
        else:
            # print(f"Unresolvable: {pid} : {error}")
            return error
