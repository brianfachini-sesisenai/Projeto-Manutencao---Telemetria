"""Ponto de entrada: python run.py  ->  http://localhost:8050"""
import os

from predictive import datagen, store


def main():
    if datagen.ensure_data():
        print("Dados fictícios gerados em ./data")
    store.reset_live_file()
    from predictive.app import create_app

    app, sim = create_app()
    sim.start()
    port = int(os.getenv("PORT", "8050"))
    print(f"PredictaMaq em http://localhost:{port}")
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
