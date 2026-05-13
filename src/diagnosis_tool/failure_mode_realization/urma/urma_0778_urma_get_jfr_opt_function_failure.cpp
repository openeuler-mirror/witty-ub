#include "urma_0778_urma_get_jfr_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0778UrmaGetJfrOptFunctionFailure> g_urma("urma_0778");

bool Urma0778UrmaGetJfrOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0779", "urma_0780"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0778UrmaGetJfrOptFunctionFailure::GetName() const
{
    return "urma_get_jfr_opt 函数故障";
}

std::string Urma0778UrmaGetJfrOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0778UrmaGetJfrOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0778UrmaGetJfrOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0778UrmaGetJfrOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0778UrmaGetJfrOptFunctionFailure::GetId() const
{
    return "urma_0778";
}
} // namespace diag
