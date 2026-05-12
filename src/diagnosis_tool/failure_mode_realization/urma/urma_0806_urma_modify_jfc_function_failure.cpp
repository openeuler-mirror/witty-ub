#include "urma_0806_urma_modify_jfc_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0806UrmaModifyJfcFunctionFailure> g_urma("urma_0806");

bool Urma0806UrmaModifyJfcFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0807"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0806UrmaModifyJfcFunctionFailure::GetName() const
{
    return "urma_modify_jfc 函数故障";
}

std::string Urma0806UrmaModifyJfcFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0806UrmaModifyJfcFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0806UrmaModifyJfcFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0806UrmaModifyJfcFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0806UrmaModifyJfcFunctionFailure::GetId() const
{
    return "urma_0806";
}
} // namespace diag
