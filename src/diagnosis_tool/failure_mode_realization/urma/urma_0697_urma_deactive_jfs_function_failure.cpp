#include "urma_0697_urma_deactive_jfs_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0697UrmaDeactiveJfsFunctionFailure> g_urma("urma_0697");

bool Urma0697UrmaDeactiveJfsFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0698", "urma_0699", "urma_0700"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0697UrmaDeactiveJfsFunctionFailure::GetName() const
{
    return "urma_deactive_jfs 函数故障";
}

std::string Urma0697UrmaDeactiveJfsFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0697UrmaDeactiveJfsFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0697UrmaDeactiveJfsFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0697UrmaDeactiveJfsFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0697UrmaDeactiveJfsFunctionFailure::GetId() const
{
    return "urma_0697";
}
} // namespace diag
