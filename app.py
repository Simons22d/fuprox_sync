from fuprox import app
import eventlet.wsgi

# import multiprocessing
# multiprocessing function
# caller
if __name__ == "__main__":
    # eventlet.wsgi.server(eventlet.listen(("", 4000)), app)
    app.run("0.0.0.0", port=4000, debug=True)