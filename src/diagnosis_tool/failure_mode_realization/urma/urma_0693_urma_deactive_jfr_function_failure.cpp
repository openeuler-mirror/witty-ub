#include "urma_0693_urma_deactive_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0693UrmaDeactiveJfrFunctionFailure> g_urma("urma_0693");

bool Urma0693UrmaDeactiveJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0694", "urma_0695", "urma_0696"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0693UrmaDeactiveJfrFunctionFailure::GetName() const
{
    return "urma_deactive_jfr 函数故障";
}

std::string Urma0693UrmaDeactiveJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0693UrmaDeactiveJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0693UrmaDeactiveJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0693UrmaDeactiveJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0693UrmaDeactiveJfrFunctionFailure::GetId() const
{
    return "urma_0693";
}
} // namespace diag
