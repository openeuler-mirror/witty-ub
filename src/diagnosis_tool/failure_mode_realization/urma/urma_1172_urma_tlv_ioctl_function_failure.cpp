#include "urma_1172_urma_tlv_ioctl_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1172UrmaTlvIoctlFunctionFailure> g_urma("urma_1172");

bool Urma1172UrmaTlvIoctlFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1173"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1172UrmaTlvIoctlFunctionFailure::GetName() const
{
    return "urma_tlv_ioctl 函数故障";
}

std::string Urma1172UrmaTlvIoctlFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1172UrmaTlvIoctlFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1172UrmaTlvIoctlFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1172UrmaTlvIoctlFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1172UrmaTlvIoctlFunctionFailure::GetId() const
{
    return "urma_1172";
}
} // namespace diag
