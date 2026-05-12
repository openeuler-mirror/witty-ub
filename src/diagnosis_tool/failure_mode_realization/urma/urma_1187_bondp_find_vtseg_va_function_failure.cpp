#include "urma_1187_bondp_find_vtseg_va_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1187BondpFindVtsegVaFunctionFailure> g_urma("urma_1187");

bool Urma1187BondpFindVtsegVaFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1188"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1187BondpFindVtsegVaFunctionFailure::GetName() const
{
    return "bondp_find_vtseg_by_va 函数故障";
}

std::string Urma1187BondpFindVtsegVaFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1187BondpFindVtsegVaFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1187BondpFindVtsegVaFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1187BondpFindVtsegVaFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1187BondpFindVtsegVaFunctionFailure::GetId() const
{
    return "urma_1187";
}
} // namespace diag
