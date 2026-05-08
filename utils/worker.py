import sys
import traceback
from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, pyqtSlot

class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    """
    Worker thread wrapping a callable to run asynchronously.
    """
    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.cancel_requested = False

    @pyqtSlot()
    def run(self):
        try:
            # Optionally pass self to the fn if it accepts a worker argument to allow cancellation/progress
            result = self.fn(*self.args, **self.kwargs)
            if not self.cancel_requested:
                self.signals.result.emit(result)
        except Exception as e:
            traceback.print_exc()
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

    def cancel(self):
        self.cancel_requested = True
