from webproj import app
import uvicorn


def run():
    uvicorn.run(app, host="0.0.0.0", port=5000)#), debug=True)


if __name__ == "__main__":
    run()
