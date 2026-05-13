#include "urma_0843_urma_set_tp_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0843UrmaSetTpAttrFunctionFailure> g_urma("urma_0843");

bool Urma0843UrmaSetTpAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0844"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0843UrmaSetTpAttrFunctionFailure::GetName() const
{
    return "urma_set_tp_attr 函数故障";
}

std::string Urma0843UrmaSetTpAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0843UrmaSetTpAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0843UrmaSetTpAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0843UrmaSetTpAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0843UrmaSetTpAttrFunctionFailure::GetId() const
{
    return "urma_0843";
}
} // namespace diag
