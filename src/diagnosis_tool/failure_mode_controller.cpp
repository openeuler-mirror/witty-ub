#include "failure_mode_controller.h"
#include "failure_mode.h"

namespace diag {
StepType FailureModeController::GetNextStep()
{
    bool isFailureModeValid = failureMode->IsValid();
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
void FailureModeController::AddSubFailureModeInView(const std::string &subFailureModeId)
{
    subFailureModesInView.insert(subFailureModeId);
}
void FailureModeController::AddHitCount()
{
    hitCount++;
}
void FailureModeController::AddLogInfo(const FailureLogInfo &logInfo)
{
    logInfos.push_back(logInfo);
}
std::unordered_set<std::string> &FailureModeController::GetSubFailureModesInView()
{
    return subFailureModesInView;
}
int FailureModeController::GetHitCount()
{
    return hitCount;
}
const std::vector<FailureLogInfo> &FailureModeController::GetLogInfos() const
{
    return logInfos;
}
} // namespace diag
