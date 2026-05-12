#include "urma_0784_urma_get_tp_attr_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0784UrmaGetTpAttrFunctionFailure> g_urma("urma_0784");

bool Urma0784UrmaGetTpAttrFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0785"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0784UrmaGetTpAttrFunctionFailure::GetName() const
{
    return "urma_get_tp_attr 函数故障";
}

std::string Urma0784UrmaGetTpAttrFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0784UrmaGetTpAttrFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0784UrmaGetTpAttrFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0784UrmaGetTpAttrFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0784UrmaGetTpAttrFunctionFailure::GetId() const
{
    return "urma_0784";
}
} // namespace diag
