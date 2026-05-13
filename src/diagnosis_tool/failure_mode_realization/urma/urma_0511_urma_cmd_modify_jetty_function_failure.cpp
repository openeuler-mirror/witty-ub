#include "urma_0511_urma_cmd_modify_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0511UrmaCmdModifyJettyFunctionFailure> g_urma("urma_0511");

bool Urma0511UrmaCmdModifyJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0512"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0511UrmaCmdModifyJettyFunctionFailure::GetName() const
{
    return "urma_cmd_modify_jetty 函数故障";
}

std::string Urma0511UrmaCmdModifyJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0511UrmaCmdModifyJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0511UrmaCmdModifyJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0511UrmaCmdModifyJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0511UrmaCmdModifyJettyFunctionFailure::GetId() const
{
    return "urma_0511";
}
} // namespace diag
