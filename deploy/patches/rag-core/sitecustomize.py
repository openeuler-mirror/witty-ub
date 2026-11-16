"""Load Witty-UB's RAG runtime compatibility patches in service processes."""

# Python imports ``sitecustomize`` automatically after initializing site paths.
# Importing the mounted process-handler patch here makes its OpenGauss vector
# search compatibility fix active in the API process as well as parse workers.
import sys

# Importing ProcessHandler allocates a multiprocessing lock, which starts the
# resource tracker.  The tracker is itself a Python process and also imports
# sitecustomize, so skip it to avoid recursively creating trackers.
startup_args = [*getattr(sys, "orig_argv", ()), *sys.argv]
if not any("multiprocessing.resource_tracker" in arg for arg in startup_args):
    # Importing the module applies both the search and process-slot patches.
    import rag_core.task.process_handler  # noqa: F401
