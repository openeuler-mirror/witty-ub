#include "urma_0590_urma_active_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0590UrmaActiveJfrFunctionFailure> g_urma("urma_0590");

bool Urma0590UrmaActiveJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0591", "urma_0592", "urma_0593", "urma_0594", "urma_0595"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0590UrmaActiveJfrFunctionFailure::GetName() const
{
    return "urma_active_jfr 函数故障";
}

std::string Urma0590UrmaActiveJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0590UrmaActiveJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0590UrmaActiveJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0590UrmaActiveJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0590UrmaActiveJfrFunctionFailure::GetId() const
{
    return "urma_0590";
}
} // namespace diag
