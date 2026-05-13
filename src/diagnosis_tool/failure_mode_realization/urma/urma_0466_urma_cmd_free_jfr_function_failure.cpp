#include "urma_0466_urma_cmd_free_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0466UrmaCmdFreeJfrFunctionFailure> g_urma("urma_0466");

bool Urma0466UrmaCmdFreeJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0467", "urma_0468"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0466UrmaCmdFreeJfrFunctionFailure::GetName() const
{
    return "urma_cmd_free_jfr 函数故障";
}

std::string Urma0466UrmaCmdFreeJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0466UrmaCmdFreeJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0466UrmaCmdFreeJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0466UrmaCmdFreeJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0466UrmaCmdFreeJfrFunctionFailure::GetId() const
{
    return "urma_0466";
}
} // namespace diag
