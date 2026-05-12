#include "urma_0733_urma_delete_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0733UrmaDeleteJfrFunctionFailure> g_urma("urma_0733");

bool Urma0733UrmaDeleteJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0734", "urma_0735", "urma_0736"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0733UrmaDeleteJfrFunctionFailure::GetName() const
{
    return "urma_delete_jfr 函数故障";
}

std::string Urma0733UrmaDeleteJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0733UrmaDeleteJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0733UrmaDeleteJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0733UrmaDeleteJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0733UrmaDeleteJfrFunctionFailure::GetId() const
{
    return "urma_0733";
}
} // namespace diag
