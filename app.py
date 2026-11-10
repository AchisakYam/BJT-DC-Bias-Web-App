from flask import Flask, render_template, request

import dc_bias


def create_app():
    app = Flask(__name__)

    def render_index(form, errors, result):
        return render_template(
            "index.html",
            form=form,
            errors=errors,
            result=result,
            defaults=dc_bias.DEFAULTS,
        )

    @app.get("/")
    def index():
        return render_index(dict(dc_bias.DEFAULTS), [], None)

    @app.post("/calculate")
    def calculate_bias():
        raw = {name: request.form.get(name, "") for name in dc_bias.FIELD_NAMES}
        try:
            inputs = dc_bias.parse_form(raw)
        except dc_bias.ValidationError as exc:
            return render_index(raw, exc.errors, None)
        result = dc_bias.calculate(
            inputs.vcc, inputs.r1, inputs.r2, inputs.rc, inputs.re, inputs.beta, inputs.vbe
        )
        return render_index(raw, [], result)

    return app


app = create_app()
