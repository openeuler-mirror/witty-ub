#include "urma_0804_urma_modify_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0804UrmaModifyJettyFunctionFailure> g_urma("urma_0804");

bool Urma0804UrmaModifyJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0805"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0804UrmaModifyJettyFunctionFailure::GetName() const
{
    return "urma_modify_jetty 函数故障";
}

std::string Urma0804UrmaModifyJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0804UrmaModifyJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0804UrmaModifyJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0804UrmaModifyJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0804UrmaModifyJettyFunctionFailure::GetId() const
{
    return "urma_0804";
}
} // namespace diag
