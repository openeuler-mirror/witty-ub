#include "urma_0002_bondp_jfce_init_comp_attr_not_single_die_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure> g_urma("urma_0002");

bool Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0003", "urma_0004"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::GetName() const
{
    return "bondp_jfce_init_comp_attr_not_single_die 函数故障";
}

std::string Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0002BondpJfceInitCompAttrNotSingleDieFunctionFailure::GetId() const
{
    return "urma_0002";
}
} // namespace diag
