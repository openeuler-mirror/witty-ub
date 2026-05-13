#include "urma_0729_urma_delete_jfce_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0729UrmaDeleteJfceFunctionFailure> g_urma("urma_0729");

bool Urma0729UrmaDeleteJfceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0730", "urma_0731", "urma_0732"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0729UrmaDeleteJfceFunctionFailure::GetName() const
{
    return "urma_delete_jfce 函数故障";
}

std::string Urma0729UrmaDeleteJfceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0729UrmaDeleteJfceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0729UrmaDeleteJfceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0729UrmaDeleteJfceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0729UrmaDeleteJfceFunctionFailure::GetId() const
{
    return "urma_0729";
}
} // namespace diag
