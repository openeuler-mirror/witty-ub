#include "urma_0053_urma_init_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0053UrmaInitFunctionFailure> g_urma("urma_0053");

bool Urma0053UrmaInitFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0054", "urma_0055"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0053UrmaInitFunctionFailure::GetName() const
{
    return "urma_init 函数故障";
}

std::string Urma0053UrmaInitFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0053UrmaInitFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0053UrmaInitFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0053UrmaInitFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0053UrmaInitFunctionFailure::GetId() const
{
    return "urma_0053";
}
} // namespace diag
