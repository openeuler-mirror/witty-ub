#include "urma_0689_urma_deactive_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0689UrmaDeactiveJfcFunctionFailure> g_urma("urma_0689");

bool Urma0689UrmaDeactiveJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0690", "urma_0691", "urma_0692"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0689UrmaDeactiveJfcFunctionFailure::GetName() const
{
    return "urma_deactive_jfc 函数故障";
}

std::string Urma0689UrmaDeactiveJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0689UrmaDeactiveJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0689UrmaDeactiveJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0689UrmaDeactiveJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0689UrmaDeactiveJfcFunctionFailure::GetId() const
{
    return "urma_0689";
}
} // namespace diag
