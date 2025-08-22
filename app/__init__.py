from flask import Flask

def create_app():
    # appの設定
    app = Flask(__name__, instance_relative_config=True)
    # app.config.from_pyfile('config.py')

    from app import domain_layer
    from app import application_layer
    from app import presentation_layer
    from app import infrastructure_layer

    return app
