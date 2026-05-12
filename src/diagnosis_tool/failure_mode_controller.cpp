#include "failure_mode_controller.h"
#include "failure_mode.h"

namespace diag {
StepType FailureModeController::GetNextStep()
{
    bool isFailureModeValid = failureMode->IsValid(logContent);
    if (!isFailureModeValid) {
        return StepType::FALLBACK;
    }
    RootCause rootCause = failureMode->AnalyzeRootCause();
    if (rootCause.GetIsFinalRootCause()) {
        return StepType::LEAF;
    } else {
        return StepType::NONLEAF;
    }
}
std::shared_ptr<FailureMode> FailureModeController::GetFailureMode()
{
    return failureMode;
}
} // namespace diag