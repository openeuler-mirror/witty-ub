#include "urma_0114_bondp_create_pjfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0114BondpCreatePjfrFunctionFailure> g_urma("urma_0114");

bool Urma0114BondpCreatePjfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0115", "urma_0116"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0114BondpCreatePjfrFunctionFailure::GetName() const
{
    return "bondp_create_pjfr 函数故障";
}

std::string Urma0114BondpCreatePjfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0114BondpCreatePjfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0114BondpCreatePjfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0114BondpCreatePjfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0114BondpCreatePjfrFunctionFailure::GetId() const
{
    return "urma_0114";
}
} // namespace diag
