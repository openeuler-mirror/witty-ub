#include "urma_0889_bondp_set_aggr_mode_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0889BondpSetAggrModeFunctionFailure> g_urma("urma_0889");

bool Urma0889BondpSetAggrModeFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0890"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0889BondpSetAggrModeFunctionFailure::GetName() const
{
    return "bondp_set_aggr_mode 函数故障";
}

std::string Urma0889BondpSetAggrModeFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0889BondpSetAggrModeFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0889BondpSetAggrModeFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0889BondpSetAggrModeFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0889BondpSetAggrModeFunctionFailure::GetId() const
{
    return "urma_0889";
}
} // namespace diag
