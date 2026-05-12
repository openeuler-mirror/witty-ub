#include "urma_0561_urma_cmd_unadvise_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0561UrmaCmdUnadviseJfrFunctionFailure> g_urma("urma_0561");

bool Urma0561UrmaCmdUnadviseJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0562"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0561UrmaCmdUnadviseJfrFunctionFailure::GetName() const
{
    return "urma_cmd_unadvise_jfr 函数故障";
}

std::string Urma0561UrmaCmdUnadviseJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0561UrmaCmdUnadviseJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0561UrmaCmdUnadviseJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0561UrmaCmdUnadviseJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0561UrmaCmdUnadviseJfrFunctionFailure::GetId() const
{
    return "urma_0561";
}
} // namespace diag
