import os

from autoops import create_app

app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("AUTOOPS_PORT", "5000")))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
