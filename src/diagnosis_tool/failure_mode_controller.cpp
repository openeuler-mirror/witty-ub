#include "failure_mode_controller.h"
#include "failure_mode.h"

#include <iostream>

namespace diag {
StepType FailureModeController::GetNextStep()
{
    bool isFailureModeValid = failureMode->IsValid(logContent);
    std::cout << "FailureModeController::GetNextStep 日志内容：" << std::endl;
    std::cout << logContent << std::endl;
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