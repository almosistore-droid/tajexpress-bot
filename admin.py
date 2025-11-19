from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_admin(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    db.init_app(app)
    admin = Admin(app, name="TAJ-EXPRESS Admin", template_mode='bootstrap3')
    # Здесь можно добавлять модели для админки, например: admin.add_view(ModelView(YourModel, db.session))
