#include "urma_0139_bondp_delete_jfr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0139BondpDeleteJfrFunctionFailure> g_urma("urma_0139");

bool Urma0139BondpDeleteJfrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0140", "urma_0141", "urma_0142"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0139BondpDeleteJfrFunctionFailure::GetName() const
{
    return "bondp_delete_jfr 函数故障";
}

std::string Urma0139BondpDeleteJfrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0139BondpDeleteJfrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0139BondpDeleteJfrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0139BondpDeleteJfrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0139BondpDeleteJfrFunctionFailure::GetId() const
{
    return "urma_0139";
}
} // namespace diag
