#include "urma_0968_urma_ioctl_get_eid_list_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0968UrmaIoctlGetEidListFunctionFailure> g_urma("urma_0968");

bool Urma0968UrmaIoctlGetEidListFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0969"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0968UrmaIoctlGetEidListFunctionFailure::GetName() const
{
    return "urma_ioctl_get_eid_list 函数故障";
}

std::string Urma0968UrmaIoctlGetEidListFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0968UrmaIoctlGetEidListFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0968UrmaIoctlGetEidListFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0968UrmaIoctlGetEidListFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0968UrmaIoctlGetEidListFunctionFailure::GetId() const
{
    return "urma_0968";
}
} // namespace diag
