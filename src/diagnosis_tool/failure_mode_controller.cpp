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
void FailureModeController::AddSubFailureModeValid(const std::string &subFailureModeId)
{
    subFailureModesValid.insert(subFailureModeId);
}
void FailureModeController::AddHitCount(std::string traceId)
{
    if (traceIds.find(traceId) == traceIds.end()) {
        hitCount++;
        traceIds.insert(traceId);
    }
}
bool FailureModeController::HasTraceId(std::string traceId)
{
    return traceIds.find(traceId) != traceIds.end();
}
void FailureModeController::AddLogInfo(const FailureLogInfo &logInfo)
{
    logInfos.push_back(logInfo);
}
std::unordered_set<std::string> &FailureModeController::GetSubFailureModesValid()
{
    return subFailureModesValid;
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
