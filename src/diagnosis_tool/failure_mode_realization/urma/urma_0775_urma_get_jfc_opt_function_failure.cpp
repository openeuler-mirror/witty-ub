#include "urma_0775_urma_get_jfc_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0775UrmaGetJfcOptFunctionFailure> g_urma("urma_0775");

bool Urma0775UrmaGetJfcOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0776", "urma_0777"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0775UrmaGetJfcOptFunctionFailure::GetName() const
{
    return "urma_get_jfc_opt 函数故障";
}

std::string Urma0775UrmaGetJfcOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0775UrmaGetJfcOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0775UrmaGetJfcOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0775UrmaGetJfcOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0775UrmaGetJfcOptFunctionFailure::GetId() const
{
    return "urma_0775";
}
} // namespace diag
