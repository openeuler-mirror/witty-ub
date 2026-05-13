#include "urma_0541_urma_cmd_set_jfc_opt_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0541UrmaCmdSetJfcOptFunctionFailure> g_urma("urma_0541");

bool Urma0541UrmaCmdSetJfcOptFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0542", "urma_0543", "urma_0544"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0541UrmaCmdSetJfcOptFunctionFailure::GetName() const
{
    return "urma_cmd_set_jfc_opt 函数故障";
}

std::string Urma0541UrmaCmdSetJfcOptFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0541UrmaCmdSetJfcOptFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0541UrmaCmdSetJfcOptFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0541UrmaCmdSetJfcOptFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0541UrmaCmdSetJfcOptFunctionFailure::GetId() const
{
    return "urma_0541";
}
} // namespace diag
