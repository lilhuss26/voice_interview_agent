from src.api.app import create_app

app = create_app()
app.run(debug=True, port=4567)

if __name__ == "__main__":
    app.run(debug=True)
