import os
import argparse
import uvicorn
from omegaconf import OmegaConf

ASC_DIR = os.path.dirname(os.path.abspath(__file__))


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--model_name",
        type=str,
        choices=["tree", "mil", "ensemble"],
        help="choose model to use",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=30052,
        help="API service port to expose",
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=1,
        help="Number of workers (child process)",
    )
    return parser.parse_args()


if __name__ == "__main__":
  
    # If you have a CLI argument parser, you can still use that.
    ARGS = get_args()

    # Override the port with the one provided by Heroku if it exists
    port = int(os.environ.get("PORT", ARGS.port))
    
    # Optionally, print which port is being used for debugging
    print(f"Starting server on port {port}")

    CONFIG = OmegaConf.load(os.path.join(ASC_DIR, "config.yaml"))
    uvicorn.run(
        app="app:app",
        host="0.0.0.0",
        port=ARGS.port,
        workers=ARGS.workers,
        reload=False,
    )
