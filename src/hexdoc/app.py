from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('table_of_contents.html.jinja')

if __name__ == '__main__':
    app.run(debug=True)
