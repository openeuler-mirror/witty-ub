#include "urma_0028_bondp_uninit_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0028BondpUninitFunctionFailure> g_urma("urma_0028");

bool Urma0028BondpUninitFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0029"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0028BondpUninitFunctionFailure::GetName() const
{
    return "bondp_uninit 函数故障";
}

std::string Urma0028BondpUninitFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0028BondpUninitFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0028BondpUninitFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0028BondpUninitFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0028BondpUninitFunctionFailure::GetId() const
{
    return "urma_0028";
}
} // namespace diag
