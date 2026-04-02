import configtony
import functools
import logging
from flask import Blueprint, redirect, url_for, request, session, render_template
from werkzeug.security import check_password_hash

LOCAL_ADDRESSES = ("127.0.0.1", "::1")

class WebAuth:
    def __init__(self, passwd_hash: str | None, config: configtony.Config):
        self.passwd_hash = passwd_hash
        self.config = config
        self.logger = logging.getLogger("webauth")

    def requires_auth(self, f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if self.authed():
                return f(*args, **kwargs)
            return redirect(url_for("webui.login", return_url=request.path))
        return decorated

    def add_routes(self, blueprint: Blueprint):
        @blueprint.route("/login", methods=["GET", "POST"])
        def login():
            return_url = request.args.get("return_url")
            if request.method == "POST":
                password = request.form["password"]
                if check_password_hash(self.passwd_hash, password):
                    session["authed"] = True
                    self.logger.info("Successfully authenticated (IP: %s; UA: '%s')", request.remote_addr, request.headers.get("User-Agent", "[none]"))
                    return redirect(return_url or url_for("webui.list_targets"))
                else:
                    self.logger.info("Failed login attempt (IP: %s; UA: '%s')", request.remote_addr, request.headers.get("User-Agent", "[none]"))
                    return render_template("login.html", incorrect=True, return_url=return_url)
            elif self.authed():
                return redirect(return_url or url_for("webui.list_targets"))
            return render_template("login.html", return_url=return_url)

    def authed(self):
        return not self.passwd_hash or not self.config.get("webui_auth") or session.get("authed") or self.can_bypass_auth()

    def can_bypass_auth(self):
        return self.config.get("webui_localhost_disable_auth") and request.remote_addr in LOCAL_ADDRESSES
