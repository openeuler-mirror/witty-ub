#include "urma_1120_urma_write_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1120UrmaWriteFunctionFailure> g_urma("urma_1120");

bool Urma1120UrmaWriteFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1121"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1120UrmaWriteFunctionFailure::GetName() const
{
    return "urma_write 函数故障";
}

std::string Urma1120UrmaWriteFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1120UrmaWriteFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1120UrmaWriteFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1120UrmaWriteFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1120UrmaWriteFunctionFailure::GetId() const
{
    return "urma_1120";
}
} // namespace diag
