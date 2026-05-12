#include "urma_0828_urma_set_jfc_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0828UrmaSetJfcOptFunctionFailure> g_urma("urma_0828");

bool Urma0828UrmaSetJfcOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0829", "urma_0830", "urma_0831", "urma_0832"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0828UrmaSetJfcOptFunctionFailure::GetName() const
{
    return "urma_set_jfc_opt 函数故障";
}

std::string Urma0828UrmaSetJfcOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0828UrmaSetJfcOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0828UrmaSetJfcOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0828UrmaSetJfcOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0828UrmaSetJfcOptFunctionFailure::GetId() const
{
    return "urma_0828";
}
} // namespace diag
