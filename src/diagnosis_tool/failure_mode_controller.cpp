#include "failure_mode_controller.h"
#include "failure_mode.h"

namespace diag {
StepType FailureModeController::GetNextStep() {
    bool isFailureModeValid = failureMode -> isValid();
    if (!isFailureModeValid) {
        return StepType::Fallback;
    }
    RootCause rootCause = failureMode -> AnalyzeRootCause();
    if (rootCause.GetIsFinalRootCause()) {
        return StepType::Leaf;
    } else {
        return StepType::NonLeaf;
    }
}
std::shared_ptr<FailureMode> FailureModeController::GetFailureMode() {
    return failureMode;
}
}