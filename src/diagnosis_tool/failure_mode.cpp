#include "failure_mode.h"
#include <memory>
#include "iostream"
namespace diag {
bool RootCause::GetIsFinalRootCause()
{
    return isFinalRootCause;
}
std::string RootCause::GetRootCause()
{
    return rootCause;
}
void FailureMode::PrintDesc()
{
    std::cout << "故障模式: " << GetName() << std::endl;
    std::cout << "故障表现: " << GetValidationMethodDesc() << std::endl;
    std::cout << "故障根因: " << GetRootCauseDesc() << std::endl;
    std::cout << "修复建议: " << GetFixSuggDesc() << std::endl;
}

void FailureMode::AddSubFailureMode(std::string failureModeId)
{
    subFailureModes.push_back(failureModeId);
    return;
}

std::vector<std::string> FailureMode::GetSubFailureModes()
{
    return subFailureModes;
}

const FailureLogInfo &FailureMode::GetFailureLogInfoCache() const
{
    return failureLogInfoCache;
}

FailureLogInfo &FailureMode::GetMutableFailureLogInfoCache()
{
    return failureLogInfoCache;
}

RootCause FailureMode::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}
} // namespace diag