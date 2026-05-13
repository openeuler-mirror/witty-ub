#include "urma_0213_bondp_insert_p_jfce_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0213BondpInsertPJfceFunctionFailure> g_urma("urma_0213");

bool Urma0213BondpInsertPJfceFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0214"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0213BondpInsertPJfceFunctionFailure::GetName() const
{
    return "bondp_insert_p_jfce 函数故障";
}

std::string Urma0213BondpInsertPJfceFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0213BondpInsertPJfceFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0213BondpInsertPJfceFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0213BondpInsertPJfceFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0213BondpInsertPJfceFunctionFailure::GetId() const
{
    return "urma_0213";
}
} // namespace diag
