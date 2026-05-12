#include "urma_0374_urma_cmd_bind_jetty_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0374UrmaCmdBindJettyFunctionFailure> g_urma("urma_0374");

bool Urma0374UrmaCmdBindJettyFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0375"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0374UrmaCmdBindJettyFunctionFailure::GetName() const
{
    return "urma_cmd_bind_jetty 函数故障";
}

std::string Urma0374UrmaCmdBindJettyFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0374UrmaCmdBindJettyFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0374UrmaCmdBindJettyFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0374UrmaCmdBindJettyFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0374UrmaCmdBindJettyFunctionFailure::GetId() const
{
    return "urma_0374";
}
} // namespace diag
