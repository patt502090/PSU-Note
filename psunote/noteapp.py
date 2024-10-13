import flask

import models
import forms


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "This is secret key"
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgresql://coe:CoEpasswd@localhost:5432/coedb"

models.init_app(app)


@app.route("/")
def index():
    db = models.db
    notes = db.session.execute(
        db.select(models.Note).order_by(models.Note.title)
    ).scalars()
    return flask.render_template(
        "index.html",
        notes=notes,
    )


@app.route("/notes/create", methods=["GET", "POST"])
def notes_create():
    form = forms.NoteForm()
    if not form.validate_on_submit():
        print("error", form.errors)
        return flask.render_template(
            "notes-create.html",
            form=form,
        )
    note = models.Note()
    form.populate_obj(note)
    note.tags = []

    db = models.db
    for tag_name in form.tags.data:
        tag = (
            db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
            .scalars()
            .first()
        )

        if not tag:
            tag = models.Tag(name=tag_name)
            db.session.add(tag)

        note.tags.append(tag)

    db.session.add(note)
    db.session.commit()

    return flask.redirect(flask.url_for("index"))


@app.route("/tags/<tag_name>")
def tags_view(tag_name):
    db = models.db
    tag = (
        db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
        .scalars()
        .first()
    )
    notes = db.session.execute(
        db.select(models.Note).where(models.Note.tags.any(id=tag.id))
    ).scalars()

    return flask.render_template(
        "tags-view.html",
        tag_name=tag_name,
        notes=notes,
    )
    
@app.route("/notes/edit/<int:note_id>", methods=["GET", "POST"])
def notes_edit(note_id):
    db = models.db
    note = db.session.get(models.Note, note_id)

    if not note:
        return flask.redirect(flask.url_for("index"))

    form = forms.NoteForm(obj=note)
    form.tags.data = [tag.name for tag in note.tags] 

    if form.validate_on_submit():
        note.title = form.title.data
        note.description = form.description.data

        current_tags = {tag.name for tag in note.tags}  
        new_tags = set(form.tags.data)

        for tag_name in current_tags - new_tags:
            tag_to_remove = db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name)).scalars().first()
            if tag_to_remove:
                note.tags.remove(tag_to_remove)

        for tag_name in new_tags - current_tags:
            tag = db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name)).scalars().first()
            if not tag:
                tag = models.Tag(name=tag_name)
                db.session.add(tag)
            note.tags.append(tag)

        db.session.commit()
        return flask.redirect(flask.url_for("index"))

    return flask.render_template("notes-edit.html", form=form, note=note)


@app.route("/notes/delete/<int:note_id>", methods=["POST"])
def notes_delete(note_id):
    db = models.db
    note = db.session.get(models.Note, note_id)

    if note:
        db.session.delete(note)
        db.session.commit()
        
    return flask.redirect(flask.url_for("index"))

@app.route("/tags/edit/<tag_name>", methods=["GET", "POST"])
def tags_edit(tag_name):
    db = models.db
    tag = db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name)).scalars().first()

    if not tag:
        return flask.redirect(flask.url_for("index"))

    if flask.request.method == "POST":
        new_name = flask.request.form["new_name"]
        tag.name = new_name
        db.session.commit()
        return flask.redirect(flask.url_for("tags_view", tag_name=new_name))

    return flask.render_template("tags-edit.html", tag=tag)

@app.route("/tags/delete/<string:tag_name>", methods=["POST"])
def tags_delete(tag_name):
    db = models.db
    tag = db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name)).scalars().first()
    
    if tag:
        db.session.execute(db.delete(models.NoteTag).where(models.NoteTag.tag_id == tag.id))
        
        db.session.delete(tag)
        db.session.commit()

    return flask.redirect(flask.url_for("index"))



if __name__ == "__main__":
    app.run(debug=True)
