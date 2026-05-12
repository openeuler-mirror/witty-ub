#include "urma_0359_urma_cmd_advise_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0359UrmaCmdAdviseJfrFunctionFailure> g_urma("urma_0359");

bool Urma0359UrmaCmdAdviseJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0360"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0359UrmaCmdAdviseJfrFunctionFailure::GetName() const
{
    return "urma_cmd_advise_jfr 函数故障";
}

std::string Urma0359UrmaCmdAdviseJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0359UrmaCmdAdviseJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0359UrmaCmdAdviseJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0359UrmaCmdAdviseJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0359UrmaCmdAdviseJfrFunctionFailure::GetId() const
{
    return "urma_0359";
}
} // namespace diag
