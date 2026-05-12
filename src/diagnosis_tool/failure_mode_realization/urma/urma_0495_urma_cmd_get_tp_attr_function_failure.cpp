#include "urma_0495_urma_cmd_get_tp_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0495UrmaCmdGetTpAttrFunctionFailure> g_urma("urma_0495");

bool Urma0495UrmaCmdGetTpAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0496", "urma_0497", "urma_0498"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0495UrmaCmdGetTpAttrFunctionFailure::GetName() const
{
    return "urma_cmd_get_tp_attr 函数故障";
}

std::string Urma0495UrmaCmdGetTpAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0495UrmaCmdGetTpAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0495UrmaCmdGetTpAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0495UrmaCmdGetTpAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0495UrmaCmdGetTpAttrFunctionFailure::GetId() const
{
    return "urma_0495";
}
} // namespace diag
