from flask import Flask, render_template, request

import dc_bias


def create_app():
    app = Flask(__name__)

    def render_index(form, errors, result, mode):
        render_mode = mode if dc_bias.is_known_mode(mode) else dc_bias.DEFAULT_MODE
        return render_template(
            "index.html",
            form=form,
            errors=errors,
            result=result,
            defaults=dc_bias.DEFAULTS,
            mode=render_mode,
            mode_labels=dc_bias.MODE_LABELS,
        )

    @app.get("/")
    def index():
        form = dict(dc_bias.DEFAULTS)
        form["rb"] = dc_bias.RB_DEFAULT
        form["mode"] = dc_bias.DEFAULT_MODE
        return render_index(form, [], None, dc_bias.DEFAULT_MODE)

    @app.post("/calculate")
    def calculate_bias():
        raw = {name: request.form.get(name, "") for name in dc_bias.ALL_FIELD_NAMES}
        raw["mode"] = request.form.get("mode", dc_bias.DEFAULT_MODE)
        mode = str(raw["mode"]).strip().lower()
        render_mode = mode if dc_bias.is_known_mode(mode) else dc_bias.DEFAULT_MODE
        raw["mode"] = render_mode

        try:
            inputs = dc_bias.parse_form(raw, mode=mode)
            result = dc_bias.calculate_for_mode(mode, inputs)
        except dc_bias.ValidationError as exc:
            return render_index(raw, exc.errors, None, render_mode)

        return render_index(raw, [], result, render_mode)

    return app


app = create_app()
