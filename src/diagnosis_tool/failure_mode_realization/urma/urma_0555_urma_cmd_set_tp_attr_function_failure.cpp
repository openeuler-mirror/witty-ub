#include "urma_0555_urma_cmd_set_tp_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0555UrmaCmdSetTpAttrFunctionFailure> g_urma("urma_0555");

bool Urma0555UrmaCmdSetTpAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0556", "urma_0557", "urma_0558"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0555UrmaCmdSetTpAttrFunctionFailure::GetName() const
{
    return "urma_cmd_set_tp_attr 函数故障";
}

std::string Urma0555UrmaCmdSetTpAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0555UrmaCmdSetTpAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0555UrmaCmdSetTpAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0555UrmaCmdSetTpAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0555UrmaCmdSetTpAttrFunctionFailure::GetId() const
{
    return "urma_0555";
}
} // namespace diag
